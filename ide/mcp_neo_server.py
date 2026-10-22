#!/usr/bin/env python3
"""MCP (Model Context Protocol) Server for Neo Conflict Detection.

Allows Claude Code IDE to call Neo conflict detection via MCP protocol.
Runs as a subprocess managed by Claude Code, speaking real MCP
(JSON-RPC 2.0 over stdio, including the `initialize` handshake) via the
official `mcp` SDK.
"""

import os
import sys
import time
import logging
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.mcpserver import MCPServer

from core.activity_log_adapter import ActivityLogAdapter
from core.activity_log import ActivityEntry
from core.pre_gen_check import check_for_conflicts, check_source_staleness
from core.delta_refresh import DeltaGenerator, ContextRefreshBuilder
from core.symbol_hasher import snapshot_file
from core.freshness import get_base_snapshot
from core.blast_radius import BlastRadiusCalculator
from core.coupling_metrics import CouplingMetricsCollector
from core.entropy_coupling import EntropyCouplingDetector, analyze_entropy_coupling
from core.breaking_change_tracker import BreakingChangeTracker
from core.dependency_resolver import DependencyResolver

TENANT_ID = os.getenv("CLAUDE_TENANT_ID", "default")
MULTITENANCY = os.getenv("NEO_MULTITENANCY", "false").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("NEO_RATE_LIMIT", "100"))
DEBUG_MODE = os.getenv("NEO_DEBUG", "false").lower() == "true"

logger = logging.getLogger("neo-mcp")
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

mcp = MCPServer(name="neo-conflict-detection", version="1.0")


class RateLimiter:
    """Rate limiter for MCP requests per tenant."""

    def __init__(self, requests_per_minute: int = 100):
        self.limit = requests_per_minute
        self.requests: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, tenant_id: str) -> bool:
        """Check if request is allowed for tenant."""
        now = time.time()
        minute_ago = now - 60

        while self.requests[tenant_id] and self.requests[tenant_id][0] < minute_ago:
            self.requests[tenant_id].popleft()

        if len(self.requests[tenant_id]) >= self.limit:
            return False

        self.requests[tenant_id].append(now)
        return True

    def get_remaining(self, tenant_id: str) -> int:
        """Get remaining requests for tenant this minute."""
        now = time.time()
        minute_ago = now - 60

        while self.requests[tenant_id] and self.requests[tenant_id][0] < minute_ago:
            self.requests[tenant_id].popleft()

        return self.limit - len(self.requests[tenant_id])


def _validate_tenant_id(tenant_id: Optional[str]) -> bool:
    """Validate tenant_id format (alphanumeric + hyphens)."""
    if not tenant_id:
        return True
    return bool(re.match(r"^[a-zA-Z0-9\-_]+$", tenant_id))


def _tenant() -> Optional[str]:
    return TENANT_ID if MULTITENANCY else None


rate_limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)


@mcp.tool(name="neo_check_conflicts")
def neo_check_conflicts(
    agent_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Check for conflicts before code generation.

    Args:
        agent_id: Unique identifier for the calling agent.
        file_path: File being modified.
        intent: Description of what the agent intends to do.
        region: Optional region (lines/function) being modified.
        tenant_id: Optional tenant for multitenancy (overrides env if provided).
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        risk_level, message, lock_info = check_for_conflicts(
            agent_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
            tenant_id=final_tenant,
        )
        risk_str = risk_level.value if hasattr(risk_level, "value") else str(risk_level)

        return {
            "success": True,
            "risk_level": risk_str,
            "message": message,
            "should_block": risk_str == "HIGH",
            "should_warn": risk_str == "MEDIUM",
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Conflict check failed: {e}")
        return {
            "success": False,
            "error": f"Conflict check failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_log_activity")
def neo_log_activity(
    agent_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
    intent_category: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Log a developer's or agent's intent to work on a file.

    Args:
        agent_id: Unique identifier for the calling agent.
        file_path: File being modified.
        intent: Description of what the agent intends to do.
        region: Optional region (lines/function) being modified.
        intent_category: Optional category (feature/bugfix/refactor/other).
        tenant_id: Optional tenant for multitenancy (overrides env if provided).
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        entry = ActivityEntry(
            developer_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
            timestamp=time.time(),
            tenant_id=final_tenant,
            intent_category=intent_category,
        )
        ActivityLogAdapter.append_entry(entry, tenant_id=final_tenant)
        return {
            "success": True,
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Activity log write failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_get_active_work")
def neo_get_active_work(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """View all active developers/agents currently logged as working.

    Args:
        tenant_id: Optional tenant for multitenancy (overrides env if provided).
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        entries = ActivityLogAdapter.get_active_entries(tenant_id=final_tenant)
        return {
            "success": True,
            "active_entries": [
                e.to_dict() if hasattr(e, "to_dict") else e.__dict__ for e in entries
            ],
            "count": len(entries),
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Active work query failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "active_entries": [],
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_check_source_staleness")
def neo_check_source_staleness(
    file_path: str,
    agent_id: str,
    read_time: float,
    dependency_symbols: Optional[list] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Check if source file is stale using C1 (symbol-level hash detection).

    Args:
        file_path: Path to the file to check
        agent_id: Agent that originally read the file
        read_time: When the file was read (Unix timestamp)
        dependency_symbols: Specific symbols to check (None = whole file)
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        state, report = check_source_staleness(
            file_path=file_path,
            agent_id=agent_id,
            read_time=read_time,
            dependency_symbols=dependency_symbols,
            tenant_id=final_tenant,
        )

        return {
            "success": True,
            "staleness_state": state,  # CURRENT / STALE_SOURCE / UNVERIFIABLE
            "report": report,
            "is_current": state == "CURRENT",
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Staleness check failed: {e}")
        return {
            "success": False,
            "error": f"Staleness check failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_get_context_refresh")
def neo_get_context_refresh(
    file_path: str,
    agent_id: str,
    base_snapshot_time: float,
    dependency_symbols: Optional[list] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get symbol-level context refresh delta (C2).

    Uses delta refresh to send only changed symbols instead of full file,
    reducing token costs by 10-100x.

    Args:
        file_path: Path to the file to refresh
        agent_id: Agent requesting the refresh
        base_snapshot_time: When agent last read the file
        dependency_symbols: Specific symbols to include (None = all)
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        # Create base snapshot from when file was originally read
        base_snap = get_base_snapshot(agent_id, file_path)
        if base_snap is None:
            return {
                "success": False,
                "error": "No read recorded for this developer on this file. Read the file first.",
                "status_code": 400,
                "tenant_id": final_tenant,
            }

        if base_snap.parse_error:
            return {
                "success": False,
                "error": f"Couldn't parse file at snapshot time: {base_snap.parse_error}",
                "status_code": 400,
                "tenant_id": final_tenant,
            }

        # Generate delta from base to current
        delta = DeltaGenerator.generate(
            base_snap,
            file_path,
            dep_syms=dependency_symbols
        )

        # Build human-readable message
        message = ContextRefreshBuilder.build_message([delta], agent_id, file_path)

        # Estimate token cost
        tokens = ContextRefreshBuilder.estimate_tokens(delta)

        return {
            "success": True,
            "delta_type": delta.delta_type,  # symbols / unified_diff / full_file
            "message": message,
            "token_estimate": tokens,
            "added_symbols": delta.added_symbols or [],
            "removed_symbols": delta.removed_symbols or [],
            "changed_symbols": delta.changed_symbols or [],
            "delta": delta.to_dict(),
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Context refresh failed: {e}")
        return {
            "success": False,
            "error": f"Context refresh failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_get_status")
def neo_get_status() -> Dict[str, Any]:
    """Check Neo MCP server status."""
    return {
        "success": True,
        "status": "ok",
        "multitenancy_enabled": MULTITENANCY,
        "tenant_id": TENANT_ID,
        "version": "2.0",
        "features": [
            "conflict_detection",
            "activity_logging",
            "c1_staleness",
            "c2_delta_refresh",
            "blast_radius",
            "coupling_trends",
            "entropy_coupling",
            "breaking_change_tracking",
            "dependency_resolution",
            "cross_repo_validation",
        ],
    }


@mcp.tool(name="neo_calculate_blast_radius")
def neo_calculate_blast_radius(
    file_path: str,
    change_type: str = "general",
    dependencies: Optional[dict] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate blast radius (impact assessment) for a file change.

    Args:
        file_path: File that changed
        change_type: Type of change ("signature", "logic", "refactor", "general")
        dependencies: Optional dependency map {file -> [dependents]}
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        calculator = BlastRadiusCalculator(dependencies or {})
        report = calculator.calculate(file_path, change_type)

        return {
            "success": True,
            "source_file": report.source_file,
            "total_affected_files": report.total_dependents,
            "easy_fixes": report.easy_fixes,
            "medium_fixes": report.medium_fixes,
            "hard_fixes": report.hard_fixes,
            "estimated_hours": round(report.total_estimated_hours, 1),
            "estimated_token_cost": report.total_token_cost,
            "affected_files": [
                {
                    "file": d.file_path,
                    "complexity": d.complexity,
                    "estimated_minutes": d.estimated_minutes,
                    "token_estimate": d.token_estimate,
                    "fix_type": d.fix_type,
                    "reason": d.reason,
                }
                for d in report.details
            ],
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Blast radius calculation failed: {e}")
        return {
            "success": False,
            "error": f"Blast radius calculation failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_record_change_set")
def neo_record_change_set(
    changed_files: list,
    developer_id: str,
    intent: str,
    timestamp: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a set of files changed together for coupling analysis.

    Args:
        changed_files: List of files that changed together
        developer_id: Developer who made changes
        intent: Description of intent
        timestamp: Optional timestamp (defaults to now)
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        metrics_dir = f".devsync/coupling" if not MULTITENANCY else f".devsync/{final_tenant}/coupling"
        collector = CouplingMetricsCollector(metrics_dir)
        collector.record_change_set(changed_files, developer_id, intent, timestamp)

        return {
            "success": True,
            "files_recorded": len(changed_files),
            "developer": developer_id,
            "intent": intent,
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Change set recording failed: {e}")
        return {
            "success": False,
            "error": f"Change set recording failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_get_coupling_trends")
def neo_get_coupling_trends(
    window_days: int = 90,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get coupling trends between services over time.

    Args:
        window_days: Time window for analysis (default 90 days)
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        metrics_dir = f".devsync/coupling" if not MULTITENANCY else f".devsync/{final_tenant}/coupling"
        collector = CouplingMetricsCollector(metrics_dir)

        # Get trends
        trends = collector.compute_trends(window_days)
        coupling_matrix = collector.compute_coupling_matrix(window_days)

        # Identify regressions
        regressions = [t for t in trends if t.regression]
        increasing = [t for t in trends if t.direction == "increasing" and t.velocity > 0.01]

        return {
            "success": True,
            "window_days": window_days,
            "total_trends": len(trends),
            "regressions": [
                {
                    "services": [t.service_a, t.service_b],
                    "previous_score": round(t.previous_score, 2),
                    "current_score": round(t.current_score, 2),
                    "age_days": t.age_days,
                }
                for t in regressions
            ],
            "increasing_coupling": [
                {
                    "services": [t.service_a, t.service_b],
                    "current_score": round(t.current_score, 2),
                    "velocity": round(t.velocity, 3),
                    "direction": t.direction,
                }
                for t in increasing[:10]
            ],
            "coupling_matrix": {
                f"{k[0]},{k[1]}": round(v, 2)
                for k, v in coupling_matrix.items()
                if v > 0.3  # Only include significant couplings
            },
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Coupling trends analysis failed: {e}")
        return {
            "success": False,
            "error": f"Coupling trends analysis failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_analyze_entropy_coupling")
def neo_analyze_entropy_coupling(
    actual_imports: Optional[dict] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze hidden coupling using entropy-based detection.

    Args:
        actual_imports: Optional import graph {service -> [imports]}
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        history_file = ".devsync/coupling/coupling_history.jsonl"
        if MULTITENANCY:
            history_file = f".devsync/{final_tenant}/coupling/coupling_history.jsonl"

        result = analyze_entropy_coupling(history_file, actual_imports)

        if result["success"]:
            return {
                "success": True,
                "coupling_matrix_size": len(result.get("coupling_matrix", {})),
                "clusters": result.get("clusters", []),
                "hidden_couplings": [
                    m for m in result.get("misalignments", [])
                    if m["type"] == "hidden_coupling"
                ],
                "unnecessary_separations": [
                    m for m in result.get("misalignments", [])
                    if m["type"] == "unnecessary_separation"
                ],
                "tenant_id": final_tenant,
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
                "status_code": 500,
                "tenant_id": final_tenant,
            }
    except Exception as e:
        logger.warning(f"Entropy coupling analysis failed: {e}")
        return {
            "success": False,
            "error": f"Entropy coupling analysis failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_record_breaking_change")
def neo_record_breaking_change(
    repo: str,
    file_path: str,
    symbol: str,
    change_type: str,
    old_value: str,
    new_value: str,
    severity: str,
    affected_services: Optional[list] = None,
    description: str = "",
    auto_detect: bool = False,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a breaking change in a service.

    Args:
        repo: Service/repo name
        file_path: File where change occurred
        symbol: Function/class/API endpoint name
        change_type: "signature", "return_type", "removed", "deprecated"
        old_value: Previous signature/value
        new_value: New signature/value
        severity: "LOW", "MEDIUM", "HIGH"
        affected_services: List of services affected by this change
        description: Human-readable description
        auto_detect: If true, auto-detect other breaking changes
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        tracker_dir = ".devsync/breaking-changes" if not MULTITENANCY else f".devsync/{final_tenant}/breaking-changes"
        tracker = BreakingChangeTracker(tracker_dir)

        change = tracker.record_breaking_change(
            repo=repo,
            file_path=file_path,
            symbol=symbol,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            severity=severity,
            affected_services=affected_services or [],
            recorded_by=TENANT_ID,
            description=description,
        )

        return {
            "success": True,
            "breaking_change": {
                "repo": change.repo,
                "symbol": change.symbol,
                "change_type": change.change_type,
                "severity": change.severity,
                "status": change.status,
                "affected_services": change.affected_services,
                "description": change.description,
            },
            "message": f"Breaking change recorded: {change.symbol} in {change.repo}",
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Breaking change recording failed: {e}")
        return {
            "success": False,
            "error": f"Breaking change recording failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_check_unresolved_dependencies")
def neo_check_unresolved_dependencies(
    service: str,
    file_path: str = "",
    intent: str = "",
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Check if a service has unresolved upstream breaking changes.

    Args:
        service: Service name to check
        file_path: File being modified (optional)
        intent: Developer intent (optional)
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        resolver_dir = ".devsync/dependencies" if not MULTITENANCY else f".devsync/{final_tenant}/dependencies"
        resolver = DependencyResolver(resolver_dir)

        unresolved = resolver.check_unresolved_dependencies(service)

        if unresolved:
            # HARD BLOCK: Cannot proceed if unresolved deps exist
            blocking_services = set(dep.blocking_repo for dep in unresolved)
            high_severity = [d for d in unresolved if d.severity == "HIGH"]

            return {
                "success": True,
                "has_unresolved_deps": True,
                "blocks_work": True,
                "status": "BLOCKED",
                "service": service,
                "blocking_services": list(blocking_services),
                "unresolved_count": len(unresolved),
                "high_severity_count": len(high_severity),
                "blocking_changes": [
                    {
                        "repo": dep.blocking_repo,
                        "symbol": dep.breaking_change.symbol,
                        "change_type": dep.breaking_change.change_type,
                        "severity": dep.severity,
                        "description": dep.breaking_change.description,
                        "affected": service,
                    }
                    for dep in unresolved
                ],
                "message": f"🚫 BLOCKED: {service} has {len(unresolved)} unresolved upstream breaking changes. "
                          f"Cannot proceed with work until resolved.",
                "tenant_id": final_tenant,
            }
        else:
            return {
                "success": True,
                "has_unresolved_deps": False,
                "blocks_work": False,
                "status": "CLEAR",
                "service": service,
                "message": f"✅ {service} has no unresolved dependencies. Safe to proceed.",
                "tenant_id": final_tenant,
            }
    except Exception as e:
        logger.warning(f"Dependency check failed: {e}")
        return {
            "success": False,
            "error": f"Dependency check failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_resolve_dependency")
def neo_resolve_dependency(
    repo: str,
    symbol: str,
    resolution_notes: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve a breaking change (auto or manual).

    Args:
        repo: Repo that had the breaking change
        symbol: Symbol that was changed
        resolution_notes: How it was resolved
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        tracker_dir = ".devsync/breaking-changes" if not MULTITENANCY else f".devsync/{final_tenant}/breaking-changes"
        tracker = BreakingChangeTracker(tracker_dir)

        resolved = tracker.resolve_breaking_change(
            repo=repo,
            symbol=symbol,
            resolution_notes=resolution_notes,
        )

        if resolved:
            return {
                "success": True,
                "status": "RESOLVED",
                "repo": repo,
                "symbol": symbol,
                "message": f"✅ Breaking change {symbol} in {repo} marked as resolved",
                "resolution_notes": resolution_notes,
                "tenant_id": final_tenant,
            }
        else:
            return {
                "success": False,
                "error": f"Breaking change {symbol} in {repo} not found or already resolved",
                "status_code": 404,
                "tenant_id": final_tenant,
            }
    except Exception as e:
        logger.warning(f"Dependency resolution failed: {e}")
        return {
            "success": False,
            "error": f"Dependency resolution failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

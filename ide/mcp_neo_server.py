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
from core.unified_pre_gen_check import (
    check_all_pre_gen_risks,
    calculate_blast_radius,
    get_coupling_trends,
    record_change_set,
    analyze_entropy_couplings,
)

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
    use_unified_check: bool = True,
) -> Dict[str, Any]:
    """Check for conflicts before code generation (unified check with staged layers).

    Uses unified pre-generation check combining conflict detection with impact alerts.
    Returns both semantic conflict analysis and impact assessment.

    Args:
        agent_id: Unique identifier for the calling agent.
        file_path: File being modified.
        intent: Description of what the agent intends to do.
        region: Optional region (lines/function) being modified.
        tenant_id: Optional tenant for multitenancy (overrides env if provided).
        use_unified_check: Whether to use unified check (default True) or legacy check.
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
        if use_unified_check:
            result = check_all_pre_gen_risks(
                file_path=file_path,
                agent_id=agent_id,
                intent=intent,
                region=region,
                tenant_id=final_tenant,
            )
            return {
                "success": True,
                "status": result["status"],
                "file": result["file"],
                "safe_to_proceed": result["safe_to_proceed"],
                "conflicts": result["conflicts"],
                "impacts": result["impacts"],
                "recommendations": result["recommendations"],
                "display_message": result["display_message"],
                "tenant_id": final_tenant,
            }
        else:
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
        base_snap = snapshot_file(file_path, agent_id, base_snapshot_time)

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
            dependency_symbols=dependency_symbols
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


@mcp.tool(name="neo_calculate_blast_radius")
def neo_calculate_blast_radius(
    file_path: str,
    change_type: str = "general",
    dependencies: Optional[Dict[str, list]] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate blast radius for a file change.

    Shows estimated impact scope and cost in dev-hours and tokens.

    Args:
        file_path: File that changed.
        change_type: Type of change ("signature", "logic", "refactor", "general").
        dependencies: Optional dependency map (file_path -> [dependent_files]).
        tenant_id: Optional tenant for multitenancy.
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
        result = calculate_blast_radius(
            file_path=file_path,
            change_type=change_type,
            dependencies=dependencies or {},
        )
        return {
            "success": result.get("success", False),
            "blast_radius": result.get("blast_radius"),
            "summary": result.get("summary"),
            "easy_count": result.get("easy_count"),
            "medium_count": result.get("medium_count"),
            "hard_count": result.get("hard_count"),
            "total_hours": result.get("total_hours"),
            "total_token_cost": result.get("total_token_cost"),
            "error": result.get("error"),
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


@mcp.tool(name="neo_get_coupling_trends")
def neo_get_coupling_trends(
    window_days: int = 90,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get coupling trends between services.

    Shows which services are becoming increasingly coupled (regressions),
    and which are stable/decreasing.

    Args:
        window_days: Analysis window (default 90 days).
        tenant_id: Optional tenant for multitenancy.
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
        result = get_coupling_trends(window_days=window_days)
        return {
            "success": result.get("success", False),
            "trends": result.get("trends"),
            "summary": result.get("summary"),
            "regressions": result.get("regressions"),
            "increasing": result.get("increasing"),
            "error": result.get("error"),
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Coupling trends query failed: {e}")
        return {
            "success": False,
            "error": f"Coupling trends query failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_record_change_set")
def neo_record_change_set(
    changed_files: list,
    developer_id: str,
    intent: str,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Record a set of files changed together.

    Used to build coupling metrics over time for architecture analysis.

    Args:
        changed_files: List of files modified in this change.
        developer_id: Developer who made the change.
        intent: Intent of the change.
        tenant_id: Optional tenant for multitenancy.
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
        result = record_change_set(
            changed_files=changed_files,
            developer_id=developer_id,
            intent=intent,
        )
        return {
            "success": result.get("success", False),
            "message": result.get("message"),
            "error": result.get("error"),
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


@mcp.tool(name="neo_analyze_entropy_coupling")
def neo_analyze_entropy_coupling(
    history_file: str = ".devsync/coupling/coupling_history.jsonl",
    actual_imports: Optional[Dict[str, list]] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze service coupling using entropy (information theory).

    Discovers implicit coupling that isn't visible in imports.
    Identifies services that change together and architectural misalignments.

    Requires 3-6 months of change history to be meaningful.

    Args:
        history_file: Path to change history (JSONL format).
        actual_imports: Optional import graph (service -> [imports]).
        tenant_id: Optional tenant for multitenancy.
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
        result = analyze_entropy_couplings(
            history_file=history_file,
            actual_imports=actual_imports,
        )
        return {
            "success": result.get("success", False),
            "coupling_matrix": result.get("coupling_matrix"),
            "clusters": result.get("clusters"),
            "misalignments": result.get("misalignments"),
            "report": result.get("report"),
            "data_age_status": result.get("data_age_status"),
            "error": result.get("error"),
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


@mcp.tool(name="neo_get_status")
def neo_get_status() -> Dict[str, Any]:
    """Check Neo MCP server status."""
    return {
        "success": True,
        "status": "ok",
        "multitenancy_enabled": MULTITENANCY,
        "tenant_id": TENANT_ID,
        "version": "1.0",
        "features": [
            "conflict_detection",
            "staged_conflict_analysis",
            "activity_logging",
            "c1_staleness",
            "c2_delta_refresh",
            "blast_radius",
            "coupling_metrics",
            "entropy_coupling",
            "impact_alerts",
        ],
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

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
        risk_level, message = check_for_conflicts(
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


@mcp.tool(name="neo_get_status")
def neo_get_status() -> Dict[str, Any]:
    """Check Neo MCP server status."""
    return {
        "success": True,
        "status": "ok",
        "multitenancy_enabled": MULTITENANCY,
        "tenant_id": TENANT_ID,
        "version": "1.0",
        "features": ["conflict_detection", "activity_logging", "c1_staleness", "c2_delta_refresh"],
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""MCP (Model Context Protocol) Server for Neo Conflict Detection.

Allows Claude Code IDE to call Neo conflict detection via MCP protocol.
Runs as a subprocess managed by Claude Code, speaking real MCP
(JSON-RPC 2.0 over stdio, including the `initialize` handshake) via the
official `mcp` SDK.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.mcpserver import MCPServer

from core.activity_log import log_activity, get_active_entries
from core.pre_gen_check import check_for_conflicts

TENANT_ID = os.getenv("CLAUDE_TENANT_ID", "default")
MULTITENANCY = os.getenv("NEO_MULTITENANCY", "false").lower() == "true"

mcp = MCPServer(name="neo-conflict-detection", version="1.0")


def _tenant() -> Optional[str]:
    return TENANT_ID if MULTITENANCY else None


@mcp.tool(name="neo_check_conflicts")
def neo_check_conflicts(
    agent_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
) -> Dict[str, Any]:
    """Check for conflicts before code generation.

    Args:
        agent_id: Unique identifier for the calling agent.
        file_path: File being modified.
        intent: Description of what the agent intends to do.
        region: Optional region (lines/function) being modified.
    """
    risk_level, message = check_for_conflicts(
        agent_id=agent_id,
        file_path=file_path,
        intent=intent,
        region=region,
        tenant_id=_tenant(),
    )
    risk_str = risk_level.value if hasattr(risk_level, "value") else str(risk_level)

    return {
        "success": True,
        "risk_level": risk_str,
        "message": message,
        "should_block": risk_str == "HIGH",
        "should_warn": risk_str == "MEDIUM",
        "tenant_id": _tenant(),
    }


@mcp.tool(name="neo_log_activity")
def neo_log_activity(
    agent_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
    intent_category: Optional[str] = None,
) -> Dict[str, Any]:
    """Log a developer's or agent's intent to work on a file.

    Args:
        agent_id: Unique identifier for the calling agent.
        file_path: File being modified.
        intent: Description of what the agent intends to do.
        region: Optional region (lines/function) being modified.
        intent_category: Optional category (feature/bugfix/refactor/other).
    """
    log_activity(
        developer_id=agent_id,
        file_path=file_path,
        intent=intent,
        region=region,
        intent_category=intent_category,
        tenant_id=_tenant(),
    )

    return {
        "success": True,
        "tenant_id": _tenant(),
    }


@mcp.tool(name="neo_get_active_work")
def neo_get_active_work() -> Dict[str, Any]:
    """View all active developers/agents currently logged as working."""
    entries = get_active_entries(tenant_id=_tenant())

    return {
        "success": True,
        "active_entries": [e if isinstance(e, dict) else e.to_dict() for e in entries],
        "count": len(entries),
        "tenant_id": _tenant(),
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
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

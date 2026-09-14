#!/usr/bin/env python3
"""
Neo MCP Server - Enable Claude Code IDE integration for conflict coordination.

Exposes Neo's coordination APIs as MCP resources and tools for integration with:
- Claude Code IDE
- Cursor IDE
- VS Code extensions
- Multi-agent Claude sessions

Usage:
    python3 -m core.mcp_server

Or as MCP server in Claude Code:
    claude mcp install neo
"""

import json
import sys
from pathlib import Path
from typing import Any, Optional

try:
    from mcp.server import Server
    from mcp.types import (
        Resource,
        Tool,
        TextContent,
        ToolResult,
    )
except ImportError:
    print("Error: MCP library not installed")
    print("Install with: pip install mcp")
    sys.exit(1)

from core.activity_log import (
    log_activity,
    get_active_entries,
    read_log,
    clear_log,
)
from core.pre_gen_check import check_for_conflicts, handle_conflict_response
from core.risk_classifier import RiskLevel

# Initialize MCP server
server = Server("neo-coordination")

# ============================================================================
# RESOURCES - Static/dynamic data Neo exposes
# ============================================================================


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all Neo resources available to clients."""
    log_file = Path(".devsync/activity-log.json")

    resources = [
        Resource(
            uri="neo://activity-log",
            name="Activity Log",
            description="Shared activity log of all agent intents and work declarations",
            mimeType="application/json",
        ),
        Resource(
            uri="neo://conflict-status",
            name="Conflict Status",
            description="Current conflict detection status and coordination metrics",
            mimeType="application/json",
        ),
        Resource(
            uri="neo://active-entries",
            name="Active Entries",
            description="Currently active work entries that haven't expired (30 min)",
            mimeType="application/json",
        ),
    ]

    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content by URI."""
    if uri == "neo://activity-log":
        log_content = read_log()
        return json.dumps(log_content, indent=2)

    elif uri == "neo://active-entries":
        active = get_active_entries()
        return json.dumps(active, indent=2)

    elif uri == "neo://conflict-status":
        active = get_active_entries()

        # Calculate metrics
        files_with_conflicts = {}
        for entry in active:
            file_path = entry.get("file_path")
            if file_path:
                if file_path not in files_with_conflicts:
                    files_with_conflicts[file_path] = []
                files_with_conflicts[file_path].append(entry.get("developer_id"))

        status = {
            "active_entries": len(active),
            "files_with_activity": len(files_with_conflicts),
            "potential_conflicts": sum(
                1 for developers in files_with_conflicts.values() if len(developers) > 1
            ),
            "files_with_multiple_agents": {
                file_path: developers
                for file_path, developers in files_with_conflicts.items()
                if len(developers) > 1
            },
        }
        return json.dumps(status, indent=2)

    else:
        raise ValueError(f"Unknown resource: {uri}")


# ============================================================================
# TOOLS - Functions Neo exposes for agent coordination
# ============================================================================


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all Neo coordination tools available to clients."""
    return [
        Tool(
            name="neo_log_activity",
            description="Declare agent intent to work on a file. Called before code generation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Unique identifier for the agent (e.g., 'claude-opus-1')",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file being modified",
                    },
                    "intent": {
                        "type": "string",
                        "description": "What the agent intends to do (e.g., 'Add OAuth2 support')",
                    },
                    "region": {
                        "type": "string",
                        "description": "Optional: specific region (lines/function) being modified",
                    },
                    "intent_category": {
                        "type": "string",
                        "enum": ["feature", "bugfix", "refactor", "chore"],
                        "description": "Category of work being done",
                    },
                },
                "required": ["agent_id", "file_path", "intent"],
            },
        ),
        Tool(
            name="neo_check_conflicts",
            description="Check for conflicts before code generation. Returns risk level and guidance.",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {
                        "type": "string",
                        "description": "Unique identifier for the checking agent",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Path to the file being modified",
                    },
                    "intent": {
                        "type": "string",
                        "description": "What the agent intends to do",
                    },
                    "region": {
                        "type": "string",
                        "description": "Optional: specific region being modified",
                    },
                },
                "required": ["agent_id", "file_path", "intent"],
            },
        ),
        Tool(
            name="neo_get_active_entries",
            description="Get all currently active work entries (not expired)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Optional: filter by specific file",
                    },
                },
            },
        ),
        Tool(
            name="neo_clear_log",
            description="Clear the activity log (for testing/cleanup only)",
            inputSchema={"type": "object", "properties": {}},
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from clients."""

    if name == "neo_log_activity":
        agent_id = arguments.get("agent_id")
        file_path = arguments.get("file_path")
        intent = arguments.get("intent")
        region = arguments.get("region")
        intent_category = arguments.get("intent_category")

        entry = log_activity(
            developer_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
            intent_category=intent_category,
        )

        return [
            TextContent(
                type="text",
                text=f"✓ Logged: {agent_id} on {file_path}\n"
                f"  Intent: {intent}\n"
                f"  Region: {region or '(whole file)'}\n"
                f"  Category: {intent_category or 'general'}",
            )
        ]

    elif name == "neo_check_conflicts":
        agent_id = arguments.get("agent_id")
        file_path = arguments.get("file_path")
        intent = arguments.get("intent")
        region = arguments.get("region")

        risk, message = check_for_conflicts(
            agent_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
        )

        # Format response with guidance
        guidance = ""
        if risk == RiskLevel.HIGH:
            guidance = (
                "\n\n⚠️  BLOCKING: Coordinate with the conflicting agent before proceeding. "
                "Neo has detected a high-risk conflict that requires explicit coordination."
            )
        elif risk == RiskLevel.MEDIUM:
            guidance = (
                "\n\n⚡ WARNING: Overlapping regions detected. Proceed with caution and "
                "consider coordinating with the other agent."
            )
        else:
            guidance = "\n\n✓ Safe to proceed. No conflicts detected."

        return [
            TextContent(
                type="text",
                text=f"Risk Level: {risk.value}\n{message}{guidance}",
            )
        ]

    elif name == "neo_get_active_entries":
        file_path = arguments.get("file_path")
        active = get_active_entries(file_path=file_path if file_path else None)

        return [
            TextContent(
                type="text",
                text=json.dumps(active, indent=2),
            )
        ]

    elif name == "neo_clear_log":
        clear_log()
        return [
            TextContent(
                type="text",
                text="✓ Activity log cleared",
            )
        ]

    else:
        raise ValueError(f"Unknown tool: {name}")


# ============================================================================
# SERVER LIFECYCLE
# ============================================================================


async def main():
    """Run the Neo MCP server."""
    print("Neo MCP Server starting...")
    print("Exposes:")
    print("  - Resources: activity-log, conflict-status, active-entries")
    print("  - Tools: neo_log_activity, neo_check_conflicts, neo_get_active_entries")
    print("  - Clear: neo_clear_log (testing only)")
    print("")

    async with server:
        print("✓ Neo MCP Server ready")
        print("  Listening on stdio")
        await server.wait()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())

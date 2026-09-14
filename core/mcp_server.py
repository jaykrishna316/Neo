#!/usr/bin/env python3
"""
Neo MCP Server - Enable Claude Code IDE integration for conflict coordination (tenant-isolated).

Exposes Neo's coordination APIs as MCP resources and tools for integration with:
- Claude Code IDE
- Cursor IDE
- VS Code extensions
- Multi-agent Claude sessions

Multitenancy Support:
- Each tenant (company) has isolated activity logs
- Conflict checks only see same-tenant work
- Tenant ID resolved from CLAUDE_TENANT_ID environment variable

Usage:
    export CLAUDE_TENANT_ID=acme-corp
    python3 -m core.mcp_server

Or as MCP server in Claude Code:
    claude mcp install neo
"""

import json
import os
import re
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
    DEFAULT_TENANT_ID,
    MULTITENANCY_ENABLED,
)
from core.pre_gen_check import check_for_conflicts, handle_conflict_response
from core.risk_classifier import RiskLevel

# Multitenancy configuration
def resolve_tenant_context(tenant_id: Optional[str] = None) -> str:
    """Resolve tenant context from parameter or environment."""
    if tenant_id:
        return tenant_id
    return DEFAULT_TENANT_ID


def validate_tenant_id(tenant_id: str) -> bool:
    """Validate tenant ID format (alphanumeric, hyphens, underscores)."""
    if not tenant_id:
        return False
    return bool(re.match(r"^[a-z0-9_-]{1,64}$", tenant_id, re.IGNORECASE))


# Initialize MCP server
server = Server("neo-coordination")

# ============================================================================
# RESOURCES - Static/dynamic data Neo exposes
# ============================================================================


@server.list_resources()
async def list_resources() -> list[Resource]:
    """List all Neo resources available to clients (tenant-isolated)."""
    tenant = resolve_tenant_context()

    resources = [
        Resource(
            uri=f"neo://tenants/{tenant}/activity-log",
            name="Activity Log",
            description=f"Shared activity log for tenant '{tenant}'",
            mimeType="application/json",
        ),
        Resource(
            uri=f"neo://tenants/{tenant}/conflict-status",
            name="Conflict Status",
            description=f"Conflict detection metrics for tenant '{tenant}'",
            mimeType="application/json",
        ),
        Resource(
            uri=f"neo://tenants/{tenant}/active-entries",
            name="Active Entries",
            description=f"Currently active work for tenant '{tenant}' (30 min expiry)",
            mimeType="application/json",
        ),
    ]

    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read resource content by URI (tenant-isolated)."""
    tenant = resolve_tenant_context()

    # Handle tenant-scoped URIs: neo://tenants/{tenant}/...
    if uri == f"neo://tenants/{tenant}/activity-log":
        log_content = read_log(tenant_id=tenant)
        return json.dumps(log_content, indent=2)

    elif uri == f"neo://tenants/{tenant}/active-entries":
        active = get_active_entries(tenant_id=tenant)
        return json.dumps(active, indent=2)

    elif uri == f"neo://tenants/{tenant}/conflict-status":
        active = get_active_entries(tenant_id=tenant)

        # Calculate metrics for this tenant only
        files_with_conflicts = {}
        for entry in active:
            file_path = entry.get("file_path")
            if file_path:
                if file_path not in files_with_conflicts:
                    files_with_conflicts[file_path] = []
                files_with_conflicts[file_path].append(entry.get("developer_id"))

        status = {
            "tenant_id": tenant,
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
    """List all Neo coordination tools available to clients (tenant-isolated)."""
    return [
        Tool(
            name="neo_log_activity",
            description="Declare agent intent to work on a file. Called before code generation (tenant-isolated).",
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
                    "tenant_id": {
                        "type": "string",
                        "description": f"Tenant ID (company). Defaults to CLAUDE_TENANT_ID={DEFAULT_TENANT_ID}",
                    },
                },
                "required": ["agent_id", "file_path", "intent"],
            },
        ),
        Tool(
            name="neo_check_conflicts",
            description="Check for conflicts before code generation. Tenant-isolated (tenant-isolated).",
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
                    "tenant_id": {
                        "type": "string",
                        "description": f"Tenant ID (company). Defaults to CLAUDE_TENANT_ID={DEFAULT_TENANT_ID}",
                    },
                },
                "required": ["agent_id", "file_path", "intent"],
            },
        ),
        Tool(
            name="neo_get_active_entries",
            description="Get currently active work entries (not expired) for this tenant",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Optional: filter by specific file",
                    },
                    "tenant_id": {
                        "type": "string",
                        "description": f"Tenant ID (company). Defaults to CLAUDE_TENANT_ID={DEFAULT_TENANT_ID}",
                    },
                },
            },
        ),
        Tool(
            name="neo_clear_log",
            description="Clear the activity log for this tenant (for testing/cleanup only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "tenant_id": {
                        "type": "string",
                        "description": f"Tenant ID (company). Defaults to CLAUDE_TENANT_ID={DEFAULT_TENANT_ID}",
                    },
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from clients (tenant-isolated)."""

    if name == "neo_log_activity":
        tenant_id = arguments.get("tenant_id", DEFAULT_TENANT_ID)

        # Validate tenant ID
        if not validate_tenant_id(tenant_id):
            return [
                TextContent(
                    type="text",
                    text=f"❌ Invalid tenant ID format: '{tenant_id}'. "
                    f"Must be alphanumeric with hyphens/underscores (1-64 chars).",
                )
            ]

        agent_id = arguments.get("agent_id")
        file_path = arguments.get("file_path")
        intent = arguments.get("intent")
        region = arguments.get("region")
        intent_category = arguments.get("intent_category")

        try:
            entry = log_activity(
                developer_id=agent_id,
                file_path=file_path,
                intent=intent,
                region=region,
                intent_category=intent_category,
                tenant_id=tenant_id,
            )

            return [
                TextContent(
                    type="text",
                    text=f"✓ Intent logged for tenant '{tenant_id}'\n"
                    f"  Agent: {agent_id}\n"
                    f"  File: {file_path}\n"
                    f"  Intent: {intent}\n"
                    f"  Region: {region or '(whole file)'}\n"
                    f"  Category: {intent_category or 'general'}",
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error logging activity: {str(e)}",
                )
            ]

    elif name == "neo_check_conflicts":
        tenant_id = arguments.get("tenant_id", DEFAULT_TENANT_ID)

        # Validate tenant ID
        if not validate_tenant_id(tenant_id):
            return [
                TextContent(
                    type="text",
                    text=f"❌ Invalid tenant ID format: '{tenant_id}'. "
                    f"Must be alphanumeric with hyphens/underscores (1-64 chars).",
                )
            ]

        agent_id = arguments.get("agent_id")
        file_path = arguments.get("file_path")
        intent = arguments.get("intent")
        region = arguments.get("region")

        try:
            risk, message = check_for_conflicts(
                agent_id=agent_id,
                file_path=file_path,
                intent=intent,
                region=region,
                tenant_id=tenant_id,
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
                    text=f"Tenant: {tenant_id}\nRisk Level: {risk.value}\n{message}{guidance}",
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error checking conflicts: {str(e)}",
                )
            ]

    elif name == "neo_get_active_entries":
        tenant_id = arguments.get("tenant_id", DEFAULT_TENANT_ID)

        # Validate tenant ID
        if not validate_tenant_id(tenant_id):
            return [
                TextContent(
                    type="text",
                    text=f"❌ Invalid tenant ID format: '{tenant_id}'. "
                    f"Must be alphanumeric with hyphens/underscores (1-64 chars).",
                )
            ]

        file_path = arguments.get("file_path")

        try:
            active = get_active_entries(
                file_path=file_path if file_path else None,
                tenant_id=tenant_id
            )

            return [
                TextContent(
                    type="text",
                    text=f"Active entries for tenant '{tenant_id}':\n\n"
                    + json.dumps(active, indent=2),
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error retrieving active entries: {str(e)}",
                )
            ]

    elif name == "neo_clear_log":
        tenant_id = arguments.get("tenant_id", DEFAULT_TENANT_ID)

        # Validate tenant ID
        if not validate_tenant_id(tenant_id):
            return [
                TextContent(
                    type="text",
                    text=f"❌ Invalid tenant ID format: '{tenant_id}'. "
                    f"Must be alphanumeric with hyphens/underscores (1-64 chars).",
                )
            ]

        try:
            clear_log(tenant_id=tenant_id)
            return [
                TextContent(
                    type="text",
                    text=f"✓ Activity log cleared for tenant '{tenant_id}'",
                )
            ]
        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=f"❌ Error clearing log: {str(e)}",
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

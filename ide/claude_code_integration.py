#!/usr/bin/env python3
"""Claude Code IDE Integration for Neo Conflict Detection

Automatically runs conflict checks before code generation.
Integrates with Claude Code's pre-generation hook system.
"""

import os
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel


class NeoIDEHook:
    """Pre-generation hook for Claude Code IDE.

    Called automatically before Claude Code generates code.
    Checks for conflicts and returns risk level + message.
    """

    def __init__(self, tenant_id: Optional[str] = None):
        """Initialize IDE hook.

        Args:
            tenant_id: Optional tenant ID for multitenancy.
                      If not provided, uses CLAUDE_TENANT_ID env var.
        """
        self.tenant_id = tenant_id or os.getenv("CLAUDE_TENANT_ID", "default")
        self.multitenancy_enabled = os.getenv("NEO_MULTITENANCY", "false").lower() == "true"

    def check_before_generation(
        self,
        agent_id: str,
        file_path: str,
        intent: str,
        selection: Optional[str] = None
    ) -> Tuple[str, str, Dict[str, Any]]:
        """Check for conflicts before code generation.

        This is called by Claude Code just before generating code.

        Args:
            agent_id: Agent/session ID (e.g., "claude-opus-1")
            file_path: File being modified (e.g., "src/auth.py")
            intent: What the agent intends to do (e.g., "Add OAuth2 support")
            selection: Selected code region (e.g., "authenticate_user function")

        Returns:
            Tuple of (risk_level, message, metadata)
            - risk_level: "LOW", "MEDIUM", or "HIGH"
            - message: Human-readable explanation
            - metadata: Dict with details (conflicts, agents, regions, etc.)
        """
        risk_level, message = check_for_conflicts(
            agent_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=selection,
            tenant_id=self.tenant_id
        )

        # Convert RiskLevel enum to string for IDE
        risk_str = risk_level.value if hasattr(risk_level, 'value') else str(risk_level)

        metadata = {
            "tenant_id": self.tenant_id if self.multitenancy_enabled else None,
            "risk_level": risk_str,
            "file": file_path,
            "agent": agent_id,
            "intent": intent,
            "timestamp": str(Path(".devsync/tenants" if self.multitenancy_enabled else ".devsync").resolve())
        }

        return risk_str, message, metadata

    def should_block(self, risk_level: str) -> bool:
        """Check if code generation should be blocked.

        Args:
            risk_level: Risk level from check_before_generation

        Returns:
            True if generation should be blocked (requires confirmation)
        """
        return risk_level == "HIGH"

    def should_warn(self, risk_level: str) -> bool:
        """Check if user should be warned before generation.

        Args:
            risk_level: Risk level from check_before_generation

        Returns:
            True if warning should be shown
        """
        return risk_level == "MEDIUM"

    def get_ui_state(self, risk_level: str) -> Dict[str, Any]:
        """Get UI state for Claude Code IDE.

        Args:
            risk_level: Risk level from check_before_generation

        Returns:
            Dict with UI configuration for the IDE
        """
        if risk_level == "HIGH":
            return {
                "status": "blocked",
                "color": "red",
                "icon": "🚫",
                "action": "requires_confirmation",
                "tooltip": "Conflict detected - confirm or wait"
            }
        elif risk_level == "MEDIUM":
            return {
                "status": "warning",
                "color": "orange",
                "icon": "⚠️",
                "action": "show_warning",
                "tooltip": "Potential conflict - proceed with caution"
            }
        else:  # LOW
            return {
                "status": "safe",
                "color": "green",
                "icon": "✅",
                "action": "continue",
                "tooltip": "Safe to generate"
            }


class NeoMCPServer:
    """MCP Server for Neo conflict detection.

    Exposes Neo as an MCP resource for Claude Code IDE.
    """

    @staticmethod
    def get_mcp_config() -> Dict[str, Any]:
        """Get MCP server configuration for claude.ai.

        This config goes in ~/.claude/mcp_servers.json for Claude Code IDE.

        Returns:
            Dict with MCP server configuration
        """
        return {
            "neo-conflict-detection": {
                "command": "python3",
                "args": ["-m", "ide.mcp_neo_server"],
                "env": {
                    "NEO_MULTITENANCY": os.getenv("NEO_MULTITENANCY", "false"),
                    "CLAUDE_TENANT_ID": os.getenv("CLAUDE_TENANT_ID", "default")
                }
            }
        }

    @staticmethod
    def install_instructions() -> str:
        """Get installation instructions for Claude Code.

        Returns:
            Human-readable setup instructions
        """
        return """
# Neo Conflict Detection for Claude Code

## Installation

1. Add to ~/.claude/mcp_servers.json:

{
  "neo-conflict-detection": {
    "command": "python3",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "NEO_MULTITENANCY": "false",
      "CLAUDE_TENANT_ID": "default"
    }
  }
}

2. Restart Claude Code IDE

3. Neo will now automatically check for conflicts before code generation

## Configuration

### Single-Tenant (Default)
No additional setup needed. Neo runs in single-tenant mode.

### Multi-Tenant Mode
Set environment before starting Claude Code:

export NEO_MULTITENANCY=true
export CLAUDE_TENANT_ID=your-org-name
export MCP_SERVER_URL=https://localhost:8000/mcp

Then restart Claude Code.

## Usage

Neo runs automatically before code generation. You'll see:

- ✅ GREEN (LOW risk) → Code generates normally
- ⚠️ ORANGE (MEDIUM risk) → Warning shown, you can proceed or wait
- 🚫 RED (HIGH risk) → Generation blocked, requires confirmation

## Disabling

Remove the neo-conflict-detection entry from ~/.claude/mcp_servers.json
and restart Claude Code.
"""


def create_ide_hook() -> NeoIDEHook:
    """Factory to create IDE hook with proper tenant configuration.

    Returns:
        NeoIDEHook instance configured from environment
    """
    return NeoIDEHook()


if __name__ == "__main__":
    # Print installation instructions
    print(NeoMCPServer.install_instructions())
    print("\n" + "="*60)
    print("MCP Configuration:")
    print("="*60)
    print(json.dumps(NeoMCPServer.get_mcp_config(), indent=2))

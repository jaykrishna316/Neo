#!/usr/bin/env python3
"""MCP (Model Context Protocol) Server for Neo Conflict Detection.

Allows Claude Code IDE to call Neo conflict detection via MCP protocol.
Runs as a subprocess managed by Claude Code.
"""

import json
import sys
import os
from typing import Any, Dict
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import log_activity, get_active_entries
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel


class NeoMCPServer:
    """MCP server implementation for Neo."""

    def __init__(self):
        self.tenant_id = os.getenv("CLAUDE_TENANT_ID", "default")
        self.multitenancy = os.getenv("NEO_MULTITENANCY", "false").lower() == "true"

    def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request from Claude Code.

        Args:
            request: MCP request dict with method and params

        Returns:
            Response dict with result or error
        """
        method = request.get("method")
        params = request.get("params", {})

        try:
            if method == "neo/check_conflicts":
                return self.check_conflicts(params)
            elif method == "neo/log_activity":
                return self.log_activity_handler(params)
            elif method == "neo/get_active_work":
                return self.get_active_work(params)
            elif method == "neo/get_status":
                return self.get_status()
            else:
                return {
                    "error": f"Unknown method: {method}",
                    "code": "METHOD_NOT_FOUND"
                }
        except Exception as e:
            return {
                "error": str(e),
                "code": "INTERNAL_ERROR"
            }

    def check_conflicts(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Check for conflicts before code generation.

        MCP method: neo/check_conflicts

        Params:
            agent_id: Agent ID
            file_path: File being modified
            intent: What agent intends to do
            region: (optional) Code region

        Returns:
            {
                "risk_level": "LOW" | "MEDIUM" | "HIGH",
                "message": "...",
                "should_block": boolean,
                "active_conflicts": [...],
                "tenant_id": "..."
            }
        """
        risk_level, message = check_for_conflicts(
            agent_id=params["agent_id"],
            file_path=params["file_path"],
            intent=params["intent"],
            region=params.get("region"),
            tenant_id=self.tenant_id if self.multitenancy else None
        )

        risk_str = risk_level.value if hasattr(risk_level, 'value') else str(risk_level)

        return {
            "success": True,
            "risk_level": risk_str,
            "message": message,
            "should_block": risk_str == "HIGH",
            "should_warn": risk_str == "MEDIUM",
            "tenant_id": self.tenant_id if self.multitenancy else None
        }

    def log_activity_handler(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Log agent activity/intent.

        MCP method: neo/log_activity

        Params:
            agent_id: Agent ID
            file_path: File being modified
            intent: What agent intends to do
            region: (optional) Code region
            intent_category: (optional) feature|bugfix|refactor|other

        Returns:
            {
                "success": True,
                "logged_at": timestamp,
                "log_path": "..."
            }
        """
        log_activity(
            developer_id=params["agent_id"],
            file_path=params["file_path"],
            intent=params["intent"],
            region=params.get("region"),
            intent_category=params.get("intent_category"),
            tenant_id=self.tenant_id if self.multitenancy else None
        )

        return {
            "success": True,
            "tenant_id": self.tenant_id if self.multitenancy else None
        }

    def get_active_work(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get all active work for current tenant.

        MCP method: neo/get_active_work

        Returns:
            {
                "active_entries": [...],
                "count": number,
                "tenant_id": "..."
            }
        """
        entries = get_active_entries(
            tenant_id=self.tenant_id if self.multitenancy else None
        )

        return {
            "success": True,
            "active_entries": [e if isinstance(e, dict) else e.to_dict() for e in entries],
            "count": len(entries),
            "tenant_id": self.tenant_id if self.multitenancy else None
        }

    def get_status(self) -> Dict[str, Any]:
        """Get Neo server status.

        MCP method: neo/get_status

        Returns:
            {
                "status": "ok",
                "multitenancy_enabled": boolean,
                "tenant_id": "...",
                "version": "1.0"
            }
        """
        return {
            "success": True,
            "status": "ok",
            "multitenancy_enabled": self.multitenancy,
            "tenant_id": self.tenant_id,
            "version": "1.0"
        }


def main():
    """Main entry point for MCP server.

    Reads JSON requests from stdin, writes responses to stdout.
    """
    server = NeoMCPServer()

    # Initialize response
    print(json.dumps({
        "name": "neo-conflict-detection",
        "version": "1.0",
        "supported_methods": [
            "neo/check_conflicts",
            "neo/log_activity",
            "neo/get_active_work",
            "neo/get_status"
        ]
    }))
    sys.stdout.flush()

    # Process requests
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = server.handle_request(request)
            print(json.dumps(response))
            sys.stdout.flush()

        except json.JSONDecodeError:
            print(json.dumps({
                "error": "Invalid JSON",
                "code": "PARSE_ERROR"
            }))
            sys.stdout.flush()
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(json.dumps({
                "error": str(e),
                "code": "FATAL_ERROR"
            }))
            sys.stdout.flush()
            break


if __name__ == "__main__":
    main()

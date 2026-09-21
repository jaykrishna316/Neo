#!/usr/bin/env python3
"""Hook script for pre-generation conflict detection.

Reads hook input JSON from stdin, calls Neo MCP server to check conflicts,
and returns hook response JSON to stdout.
"""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import read_log
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel


def process_hook():
    """Process the hook input and return conflict check response."""
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        print(json.dumps({
            "continue": True,
            "systemMessage": "⚠️ Could not parse hook input"
        }))
        return

    # Extract file path from tool input
    tool_input = hook_input.get("tool_input", {})
    file_path = tool_input.get("file_path") or tool_input.get("path")

    if not file_path:
        # No file path - allow to proceed
        print(json.dumps({"continue": True}))
        return

    # Check conflicts
    try:
        risk_level, message = check_for_conflicts(
            agent_id="claude-code",
            file_path=file_path,
            intent="code generation",
            region=None,
            tenant_id=None
        )

        risk_str = risk_level.value if hasattr(risk_level, 'value') else str(risk_level)

        if risk_str == "HIGH":
            # Block high-risk changes
            print(json.dumps({
                "continue": False,
                "stopReason": f"🚫 HIGH CONFLICT DETECTED: {message}\n\nCoordinate with other developers first before proceeding."
            }))
        elif risk_str == "MEDIUM":
            # Warn on medium risk but allow to proceed
            print(json.dumps({
                "continue": True,
                "systemMessage": f"⚠️ MEDIUM CONFLICT WARNING: {message}\n\nProceed with caution."
            }))
        else:
            # Low risk - proceed normally
            print(json.dumps({"continue": True}))

    except Exception as e:
        # On error, allow to proceed but show message
        print(json.dumps({
            "continue": True,
            "systemMessage": f"⚠️ Conflict check error: {str(e)}"
        }))


if __name__ == "__main__":
    process_hook()

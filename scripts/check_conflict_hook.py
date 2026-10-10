#!/usr/bin/env python3
"""
Neo conflict detection hook for Claude Code pre-edit checks.

Integrates:
1. C1 staleness detection (symbol-level hash-based freshness)
2. Conflict detection (multi-agent coordination)
3. Lock management (file-level serialization)
"""
import json
import sys
import os
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Write proof the hook ran
log_file = Path.home() / ".neo_hook_log.txt"
with open(log_file, "a") as f:
    f.write(f"[{datetime.now().isoformat()}] Hook executed\n")

# Import Neo conflict and staleness detection
from core.pre_gen_check import check_for_conflicts, check_source_staleness

try:
    hook_input = json.loads(sys.stdin.read())
except:
    print(json.dumps({"continue": True}))
    sys.exit(0)

tool_input = hook_input.get("tool_input", {})
file_path = tool_input.get("file_path")

if not file_path:
    print(json.dumps({"continue": True}))
    sys.exit(0)

try:
    # STEP 1: Check source staleness (C1 - symbol-level hash-based detection)
    # This checks if the file content has changed since the agent last read it
    stale_state, stale_report = check_source_staleness(
        file_path=file_path,
        agent_id="claude-code",
        read_time=time.time(),  # Would come from agent context in real usage
        dependency_symbols=None,  # Check whole file
        tenant_id=None
    )

    # If source is STALE or UNVERIFIABLE, warn the agent
    if stale_state in ("STALE_SOURCE", "UNVERIFIABLE"):
        print(json.dumps({
            "continue": True,
            "systemMessage": f"⚠️ SOURCE STALENESS: {stale_report.get('reason')}. Consider reading {file_path} again."
        }))
        # Continue anyway but warn - agent can choose to re-read

    # STEP 2: Check for conflicts with other agents
    risk_level, message, lock_info = check_for_conflicts(
        agent_id="claude-code",
        file_path=file_path,
        intent="code generation",
        region=None,
        tenant_id=None
    )

    risk_str = risk_level.value if hasattr(risk_level, 'value') else str(risk_level)

    if risk_str == "HIGH":
        print(json.dumps({"continue": False, "stopReason": f"🚫 HIGH CONFLICT: {message}"}))
    elif risk_str == "MEDIUM":
        msg = f"⚠️ MEDIUM: {message}"
        if stale_state in ("STALE_SOURCE", "UNVERIFIABLE"):
            msg += f" (Source staleness: {stale_report.get('reason')})"
        print(json.dumps({"continue": True, "systemMessage": msg}))
    else:
        print(json.dumps({"continue": True}))
except Exception as e:
    print(json.dumps({"continue": True}))

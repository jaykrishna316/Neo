#!/usr/bin/env python3
import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

# Write proof the hook ran
log_file = Path.home() / ".neo_hook_log.txt"
with open(log_file, "a") as f:
    f.write(f"[{datetime.now().isoformat()}] Hook executed\n")

# Now check conflicts
from core.pre_gen_check import check_for_conflicts

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
    risk_level, message = check_for_conflicts(
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
        print(json.dumps({"continue": True, "systemMessage": f"⚠️ MEDIUM: {message}"}))
    else:
        print(json.dumps({"continue": True}))
except Exception as e:
    print(json.dumps({"continue": True}))

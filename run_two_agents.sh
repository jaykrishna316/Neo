#!/bin/bash
# Run Neo with 2 agents in parallel terminals
# Usage: ./run_two_agents.sh [conflict_level]
# conflict_level: LOW, MEDIUM, or HIGH (default: MEDIUM)

CONFLICT_LEVEL="${1:-MEDIUM}"

echo "Starting Neo Two-Agent Simulation (${CONFLICT_LEVEL} conflict)..."
echo "Opening 2 terminals..."
echo ""

# Create Python script that agents will use
cat > /tmp/agent_demo.py << 'PYEOF'
import sys
import time
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import log_activity, get_active_entries, clear_log
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel

def run_agent(agent_name, scenario):
    """Simulate an agent working on code."""
    clear_log()
    time.sleep(0.5)

    if scenario == "LOW":
        # Non-overlapping regions
        print(f"[{agent_name}] Declaring intent...")
        log_activity(
            agent_id="Agent-A",
            file_path="src/auth.py",
            intent="Refactor login_user function",
            region="login_user (lines 20-40)"
        )
        time.sleep(1)

        print(f"[{agent_name}] Agent-B checking for conflicts...")
        risk, msg = check_for_conflicts(
            agent_id="Agent-B",
            file_path="src/auth.py",
            intent="Add validation to register_user",
            region="register_user (lines 50-70)"
        )
        print(f"[{agent_name}] Risk: {risk.value}")
        print(f"[{agent_name}] Message: {msg}")

    elif scenario == "MEDIUM":
        # Overlapping regions
        print(f"[{agent_name}] Declaring intent...")
        log_activity(
            agent_id="Agent-A",
            file_path="src/auth.py",
            intent="Refactor login_user function",
            region="login_user (lines 20-40)"
        )
        time.sleep(1)

        print(f"[{agent_name}] Agent-B checking for conflicts...")
        risk, msg = check_for_conflicts(
            agent_id="Agent-B",
            file_path="src/auth.py",
            intent="Add logging to login_user",
            region="login_user (lines 25-35)"
        )
        print(f"[{agent_name}] Risk: {risk.value}")
        print(f"[{agent_name}] Message: {msg}")

    elif scenario == "HIGH":
        # Signature change
        print(f"[{agent_name}] Declaring intent...")
        log_activity(
            agent_id="Agent-A",
            file_path="src/auth.py",
            intent="Rename login_user to authenticate",
            region="login_user (lines 20-40)"
        )
        time.sleep(1)

        print(f"[{agent_name}] Agent-B checking for conflicts...")
        risk, msg = check_for_conflicts(
            agent_id="Agent-B",
            file_path="src/auth.py",
            intent="Call login_user from new flow",
            region="login_user (lines 20-40)"
        )
        print(f"[{agent_name}] Risk: {risk.value}")
        print(f"[{agent_name}] Message: {msg}")

if __name__ == "__main__":
    scenario = sys.argv[1] if len(sys.argv) > 1 else "MEDIUM"
    run_agent("Agent-Demo", scenario)
PYEOF

# Try to open in separate terminals
if command -v gnome-terminal &> /dev/null; then
    # GNOME Terminal
    echo "Opening GNOME Terminal windows..."
    gnome-terminal -- python3 /tmp/agent_demo.py "$CONFLICT_LEVEL" &
    sleep 1
    gnome-terminal -- python3 /tmp/agent_demo.py "$CONFLICT_LEVEL" &
elif command -v xterm &> /dev/null; then
    # xterm
    echo "Opening xterm windows..."
    xterm -e python3 /tmp/agent_demo.py "$CONFLICT_LEVEL" &
    sleep 1
    xterm -e python3 /tmp/agent_demo.py "$CONFLICT_LEVEL" &
elif command -v osascript &> /dev/null; then
    # macOS
    echo "Opening Terminal windows (macOS)..."
    osascript << OSASCRIPT
tell application "Terminal"
    do script "cd $(pwd) && python3 /tmp/agent_demo.py $CONFLICT_LEVEL"
    delay 1
    do script "cd $(pwd) && python3 /tmp/agent_demo.py $CONFLICT_LEVEL"
end tell
OSASCRIPT
else
    echo "No supported terminal found. Running inline instead..."
    python3 /tmp/agent_demo.py "$CONFLICT_LEVEL"
fi

echo ""
echo "✓ Neo agents running. Watch the conflict detection work in real-time!"

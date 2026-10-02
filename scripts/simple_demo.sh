#!/bin/bash
#
# Neo Simple Interactive Demo
# Spawns windows for developers, watchers, and activity log
#

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$NEO_DIR"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "\n${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        NEO INTERACTIVE DEVELOPER COORDINATION DEMO              ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

# Check tmux
if ! command -v tmux &> /dev/null; then
    echo "ERROR: tmux required. Install with: brew install tmux"
    exit 1
fi

SESSION_NAME="neo-demo-$$"

echo -e "${YELLOW}Creating session: $SESSION_NAME${NC}\n"

# Create session with a window
tmux new-session -d -s "$SESSION_NAME"
sleep 1

# Clean activity log
rm -rf .devsync 2>/dev/null || true
mkdir -p .devsync
echo "[]" > .devsync/activity-log.json

# ============================================================================
# Window 1: Activity Log
# ============================================================================
tmux rename-window -t "$SESSION_NAME" "activity-log"
tmux send-keys -t "$SESSION_NAME" "cd '$NEO_DIR' && clear" Enter
sleep 0.3
tmux send-keys -t "$SESSION_NAME" "python3 << 'EOF'
import time, json
while True:
    print('\\033[H\\033[2J')  # Clear screen
    print('📊 ACTIVITY LOG VIEWER')
    print('─' * 50)
    try:
        with open('.devsync/activity-log.json') as f:
            data = json.load(f)
        print(f'Total entries: {len(data)}')
        print()
        for entry in data:
            dev = entry.get('developer_id')
            lock = entry.get('lock_state', 'N/A')
            queue = entry.get('queue_position', '')
            print(f'  {dev}: lock={lock} queue={queue}')
    except:
        print('Waiting for activity...')
    print()
    print('(Ctrl-C to stop)')
    time.sleep(0.5)
EOF" Enter

# ============================================================================
# Window 2: Developer Alice
# ============================================================================
echo -e "${BLUE}[1/5] Activity Log Viewer${NC}"
tmux new-window -t "$SESSION_NAME" -n "alice"
tmux send-keys -t "$SESSION_NAME:alice" "cd '$NEO_DIR' && python3 scripts/simulate_2dev_workflow.py 2>&1 | head -40" Enter

# ============================================================================
# Window 3: Watcher Alice
# ============================================================================
echo -e "${BLUE}[2/5] Developer: Alice${NC}"
tmux new-window -t "$SESSION_NAME" -n "watcher-alice"
tmux send-keys -t "$SESSION_NAME:watcher-alice" "cd '$NEO_DIR' && python3 << 'EOF'
import sys, time
sys.path.insert(0, '.')
from core.pre_gen_check import check_for_conflicts

print('\\n' + '='*50)
print('WATCHER: ALICE')
print('='*50)
print('Monitoring conflicts for alice')
print()

for i in range(10):
    time.sleep(1)
    try:
        risk, msg, lock = check_for_conflicts('alice', 'auth.py', 'Add bcrypt')
        print(f'Check {i+1}: Risk = {risk.value}')
    except:
        print(f'Check {i+1}: Waiting for activity...')
EOF" Enter

# ============================================================================
# Window 4: Developer Bob
# ============================================================================
echo -e "${BLUE}[3/5] Watcher: Alice${NC}"
tmux new-window -t "$SESSION_NAME" -n "bob"
tmux send-keys -t "$SESSION_NAME:bob" "cd '$NEO_DIR' && sleep 2 && python3 << 'EOF'
import sys, time
sys.path.insert(0, '.')
from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts

print('\\n' + '='*50)
print('DEVELOPER: BOB')
print('='*50)
print()

print('⏱️  Declaring intent...')
log_activity('bob', 'auth.py', 'Add JWT support', 'feature')
time.sleep(0.5)

print('Checking conflicts...')
risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT')
print(f'Risk: {risk.value}')
if lock:
    print(f'Queue Position: {lock.get(\"queue_position\")}')
print()

print('⏳ Waiting for Alice...')
time.sleep(3)

print('📖 Getting fresh context...')
print('✏️  Generating code...')
time.sleep(1)
print('✅ Published!')
EOF" Enter

# ============================================================================
# Window 5: Watcher Bob
# ============================================================================
echo -e "${BLUE}[4/5] Developer: Bob${NC}"
tmux new-window -t "$SESSION_NAME" -n "watcher-bob"
tmux send-keys -t "$SESSION_NAME:watcher-bob" "cd '$NEO_DIR' && sleep 1.5 && python3 << 'EOF'
import sys, time
sys.path.insert(0, '.')
from core.pre_gen_check import check_for_conflicts

print('\\n' + '='*50)
print('WATCHER: BOB')
print('='*50)
print('Monitoring conflicts for bob')
print()

for i in range(10):
    time.sleep(1)
    try:
        risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT')
        print(f'Check {i+1}: Risk = {risk.value}', end='')
        if lock:
            print(f' (queue: {lock.get(\"queue_position\")})', end='')
        print()
    except:
        print(f'Check {i+1}: Waiting...')
EOF" Enter

echo -e "${BLUE}[5/5] Watcher: Bob${NC}\n"

sleep 2

echo -e "${GREEN}✓ Demo windows created${NC}\n"
echo -e "${YELLOW}Window layout:${NC}"
tmux list-windows -t "$SESSION_NAME"
echo ""

echo -e "${YELLOW}Navigation:${NC}"
echo -e "  Ctrl-b n = next window"
echo -e "  Ctrl-b p = previous window"
echo -e "  Ctrl-b 0 = activity-log"
echo -e "  Ctrl-b 1 = alice"
echo -e "  Ctrl-b 2 = watcher-alice"
echo -e "  Ctrl-b 3 = bob"
echo -e "  Ctrl-b 4 = watcher-bob"
echo -e "  Ctrl-b :kill-session = exit all\n"

tmux attach-session -t "$SESSION_NAME"

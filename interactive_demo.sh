#!/bin/bash
#
# Neo Interactive Demo - Real Terminal Simulation
# Spawns actual terminals for developers, watchers, and activity log
# Shows real-time coordination workflow
#

set -e

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$NEO_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║        NEO INTERACTIVE DEVELOPER COORDINATION DEMO              ║${NC}"
echo -e "${CYAN}║                                                                ║${NC}"
echo -e "${CYAN}║  This demo spawns real terminals showing:                      ║${NC}"
echo -e "${CYAN}║  • Developer terminals declaring intent & checking conflicts    ║${NC}"
echo -e "${CYAN}║  • Watcher terminals monitoring for conflicts                   ║${NC}"
echo -e "${CYAN}║  • Activity log viewer showing real-time coordination           ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}\n"

if ! command -v tmux &> /dev/null; then
    echo -e "${RED}ERROR: tmux is required but not installed${NC}"
    echo "Install tmux with: brew install tmux (macOS) or apt-get install tmux (Linux)"
    exit 1
fi

SESSION_NAME="neo-demo-$(date +%s)"

echo -e "${YELLOW}Creating tmux session: $SESSION_NAME${NC}"
echo -e "${YELLOW}Spawning terminals for interactive demo...${NC}\n"

# Create main session
tmux new-session -d -s "$SESSION_NAME" -x 200 -y 50

# Kill the initial empty window
tmux kill-window -t "$SESSION_NAME:0"

# ============================================================================
# WINDOW 1: Activity Log Viewer (Center stage)
# ============================================================================
echo -e "${BLUE}[1/5] Setting up Activity Log Viewer${NC}"
tmux new-window -t "$SESSION_NAME" -n "activity-log"
tmux send-keys -t "$SESSION_NAME:activity-log" "cd '$NEO_DIR'" Enter
sleep 0.5
tmux send-keys -t "$SESSION_NAME:activity-log" "
clear
echo '${CYAN}════════════════════════════════════════════════════════════════${NC}'
echo '${CYAN}                    ACTIVITY LOG MONITOR                          ${NC}'
echo '${CYAN}════════════════════════════════════════════════════════════════${NC}'
echo ''
while true; do
  clear
  echo '${CYAN}════════════════════════════════════════════════════════════════${NC}'
  echo '${CYAN}ACTIVITY LOG VIEWER${NC} (Last updated: '\$(date '+%H:%M:%S')')'
  echo '${CYAN}════════════════════════════════════════════════════════════════${NC}'
  echo ''
  if [ -f .devsync/activity-log.json ]; then
    python3 << 'EOVIEWER'
import json
try:
    with open('.devsync/activity-log.json') as f:
        data = json.load(f)

    print('📊 ACTIVITY LOG STATUS')
    print('─' * 64)
    print(f'Total Entries: {len(data)}')
    print()

    if data:
        print('📝 DEVELOPER ACTIVITY:')
        print()
        by_dev = {}
        for entry in data:
            dev = entry.get('developer_id', 'unknown')
            if dev not in by_dev:
                by_dev[dev] = []
            by_dev[dev].append(entry)

        for dev in sorted(by_dev.keys()):
            entries = by_dev[dev]
            latest = entries[-1]
            lock_state = latest.get('lock_state', 'N/A')
            queue_pos = latest.get('queue_position', 'N/A')
            file_path = latest.get('file_path', 'unknown')
            intent = latest.get('intent', 'unknown')

            print(f'  👤 {dev.upper()}:')
            print(f'     📄 File: {file_path}')
            print(f'     💭 Intent: {intent}')
            print(f'     🔒 Lock State: {lock_state}')
            if queue_pos != 'N/A':
                print(f'     📊 Queue Position: {queue_pos}')
            print()
    else:
        print('⏳ Waiting for developer activity...')
except Exception as e:
    print(f'Error reading log: {e}')
EOVIEWER
  else
    echo '⏳ Activity log not yet created'
  fi

  echo ''
  echo '${CYAN}─ Auto-refreshing every 1 second (Ctrl-C to stop) ─${NC}'
  sleep 1
done
" Enter

# ============================================================================
# WINDOW 2-3: 2-Developer Demo (Alice & Bob)
# ============================================================================
echo -e "${BLUE}[2/5] Setting up 2-Developer Workflow${NC}"

echo -e "${BLUE}[2/5] → Alice's Terminal${NC}"
tmux new-window -t "$SESSION_NAME" -n "dev-alice"
tmux send-keys -t "$SESSION_NAME:dev-alice" "cd '$NEO_DIR' && clear && python3 << 'EOALICE'
import sys
sys.path.insert(0, '.')
from core.activity_log import clear_log
clear_log()
import time
print('\n' + '${GREEN}' + '='*70 + '${NC}')
print('${GREEN}DEVELOPER: ALICE${NC}')
print('${GREEN}' + '='*70 + '${NC}')
print('${YELLOW}Workspace: auth.py${NC}')
print('${YELLOW}Task: Add bcrypt password hashing${NC}\n')

from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts

print('⏱️  [T+0s] Declaring intent to modify auth.py...')
log_activity('alice', 'auth.py', 'Add bcrypt password hashing', 'feature')
print('✅ Intent logged\n')

time.sleep(1)
print('⏱️  [T+1s] Checking for conflicts...')
risk, msg, lock = check_for_conflicts('alice', 'auth.py', 'Add bcrypt password hashing')
print(f'✅ Risk: ${GREEN}{risk.value}${NC} - {msg}\n')

time.sleep(2)
print('⏱️  [T+3s] Generating code...')
time.sleep(1)
print('  ✏️  Generated: password_hash() function')
print('  ✏️  Generated: verify_hash() function')
print('  ✏️  Generated: bcrypt integration\n')

print('⏱️  [T+4s] Publishing changes...')
print('${GREEN}✅ Code published to repository${NC}\n')

print('${YELLOW}Alice finished. Waiting for other developers...${NC}')
import select
print('(Press Ctrl-C to close this window)')
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOALICE
" Enter

echo -e "${BLUE}[3/5] → Bob's Terminal${NC}"
tmux new-window -t "$SESSION_NAME" -n "dev-bob"
tmux send-keys -t "$SESSION_NAME:dev-bob" "cd '$NEO_DIR' && sleep 1 && clear && python3 << 'EOBOB'
import sys
import time
sys.path.insert(0, '.')
print('\n' + '${GREEN}' + '='*70 + '${NC}')
print('${GREEN}DEVELOPER: BOB${NC}')
print('${GREEN}' + '='*70 + '${NC}')
print('${YELLOW}Workspace: auth.py${NC}')
print('${YELLOW}Task: Add JWT token support${NC}\n')

from core.activity_log import log_activity, read_log
from core.pre_gen_check import check_for_conflicts

print('⏱️  [T+1s] Declaring intent to modify auth.py...')
log_activity('bob', 'auth.py', 'Add JWT token support', 'feature')
print('✅ Intent logged\n')

time.sleep(1)
print('⏱️  [T+2s] Checking for conflicts...')
risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT token support')
print(f'${YELLOW}⚠️  Risk: {risk.value}${NC} - {msg}')
if lock:
    print(f'${YELLOW}🔒 Queue Position: {lock.get(\"queue_position\")}${NC}')
    print(f'${YELLOW}⏳ Waiting for: {lock.get(\"lock_holder\")}${NC}\n')

time.sleep(3)
print('⏱️  [T+5s] Checking again (Alice should be done)...')
logs = read_log()
alice_changes = [e for e in logs if e.get('developer_id') == 'alice']
print(f'${GREEN}✅ Found {len(alice_changes)} entries from Alice${NC}')
print('📖 Merging Alice\\'s changes into context...\n')

time.sleep(1)
print('⏱️  [T+6s] Generating code...')
time.sleep(1)
print('  ✏️  Generated: JWT token creation')
print('  ✏️  Generated: Token validation middleware')
print('  ✏️  Generated: Refresh token logic\n')

print('⏱️  [T+7s] Publishing changes...')
print('${GREEN}✅ Code published to repository${NC}\n')

print('${YELLOW}Bob finished. Workflow complete!${NC}')
import select
print('(Press Ctrl-C to close this window)')
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOBOB
" Enter

# ============================================================================
# WINDOW 4-5: Watcher Terminals
# ============================================================================
echo -e "${BLUE}[4/5] Setting up Conflict Watchers${NC}"

echo -e "${BLUE}[4/5] → Alice's Watcher${NC}"
tmux new-window -t "$SESSION_NAME" -n "watcher-alice"
tmux send-keys -t "$SESSION_NAME:watcher-alice" "cd '$NEO_DIR' && sleep 0.5 && clear && python3 << 'EOWATCH_A'
import time
import sys
sys.path.insert(0, '.')
print('${CYAN}' + '='*70 + '${NC}')
print('${CYAN}WATCHER: ALICE${NC}')
print('${CYAN}' + '='*70 + '${NC}')
print('Monitoring conflicts for alice@auth.py\n')

from core.pre_gen_check import check_for_conflicts

intervals = [(2, 'Initial check'), (4, 'Check after 1s'), (8, 'Check after 2s')]

for t, label in intervals:
    time.sleep(t)
    risk, msg, lock = check_for_conflicts('alice', 'auth.py', 'Add bcrypt password hashing')
    print(f'⏱️  [T+{t}s] {label}')
    print(f'   Risk: {risk.value} - {msg}')
    print(f'   ${GREEN}✅ No conflicts for alice${NC}\n')

print('${CYAN}Monitoring complete${NC}')
import select
print('(Press Ctrl-C to close)')
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOWATCH_A
" Enter

echo -e "${BLUE}[5/5] → Bob's Watcher${NC}"
tmux new-window -t "$SESSION_NAME" -n "watcher-bob"
tmux send-keys -t "$SESSION_NAME:watcher-bob" "cd '$NEO_DIR' && sleep 1.5 && clear && python3 << 'EOWATCH_B'
import time
import sys
sys.path.insert(0, '.')
print('${CYAN}' + '='*70 + '${NC}')
print('${CYAN}WATCHER: BOB${NC}')
print('${CYAN}' + '='*70 + '${NC}')
print('Monitoring conflicts for bob@auth.py\n')

from core.pre_gen_check import check_for_conflicts

print('⏱️  [T+1s] Initial check')
risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT token support')
print(f'   Risk: {risk.value} - {msg}')
if lock:
    print(f'   ${YELLOW}🔒 Queued! Position: {lock.get(\"queue_position\")}${NC}\n')

time.sleep(4)
print('⏱️  [T+5s] Retry after Alice completes')
risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT token support')
print(f'   Risk: {risk.value} - Safe to proceed!')
print(f'   ${GREEN}✅ Lock released, Bob can generate!${NC}\n')

print('${CYAN}Monitoring complete${NC}')
import select
print('(Press Ctrl-C to close)')
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOWATCH_B
" Enter

# ============================================================================
# Display and Attach
# ============================================================================
echo -e "\n${GREEN}✓ All windows created${NC}"
echo -e "${YELLOW}Session: $SESSION_NAME${NC}\n"

sleep 2

echo -e "${BLUE}Current window layout:${NC}"
tmux list-windows -t "$SESSION_NAME"
echo ""

echo -e "${GREEN}Attaching to session in 2 seconds...${NC}"
sleep 2

echo -e "${YELLOW}Navigation:${NC}"
echo -e "  • ${CYAN}Ctrl-b n${NC} = next window"
echo -e "  • ${CYAN}Ctrl-b p${NC} = previous window"
echo -e "  • ${CYAN}Ctrl-b 0${NC} = activity-log"
echo -e "  • ${CYAN}Ctrl-b 1${NC} = dev-alice"
echo -e "  • ${CYAN}Ctrl-b 2${NC} = dev-bob"
echo -e "  • ${CYAN}Ctrl-b 3${NC} = watcher-alice"
echo -e "  • ${CYAN}Ctrl-b 4${NC} = watcher-bob"
echo -e "  • ${CYAN}Ctrl-b :kill-session${NC} = exit all\n"

tmux attach-session -t "$SESSION_NAME"

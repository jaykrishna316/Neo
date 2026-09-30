#!/bin/bash
#
# Neo Parallel Test Runner
# Automatically spawns multiple terminals and runs 2-dev and 3-dev tests
# Displays all output in real-time
#

set -e

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$NEO_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Neo Parallel Test Runner${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Check if tmux is available
if ! command -v tmux &> /dev/null; then
    echo -e "${RED}ERROR: tmux is required but not installed${NC}"
    echo "Install tmux with: brew install tmux (macOS) or apt-get install tmux (Linux)"
    exit 1
fi

# Create session name with timestamp to avoid conflicts
SESSION_NAME="neo-test-$(date +%s)"

echo -e "${YELLOW}Creating tmux session: $SESSION_NAME${NC}"
echo -e "${YELLOW}This will run tests in parallel windows${NC}\n"

# Create a new tmux session
tmux new-session -d -s "$SESSION_NAME" -x 200 -y 50

# Helper function to run test in a window
run_test() {
    local window_name=$1
    local test_script=$2
    local description=$3

    echo -e "${BLUE}Setting up window: $window_name${NC}"

    # Create new window
    tmux new-window -t "$SESSION_NAME" -n "$window_name"

    # Send commands to the window
    tmux send-keys -t "$SESSION_NAME:$window_name" "cd '$NEO_DIR'" Enter
    sleep 0.5
    tmux send-keys -t "$SESSION_NAME:$window_name" "echo '=================================================='" Enter
    tmux send-keys -t "$SESSION_NAME:$window_name" "echo '$description'" Enter
    tmux send-keys -t "$SESSION_NAME:$window_name" "echo '=================================================='" Enter
    tmux send-keys -t "$SESSION_NAME:$window_name" "echo ''" Enter
    sleep 0.5

    # Run the test
    tmux send-keys -t "$SESSION_NAME:$window_name" "$test_script" Enter
}

# Setup: Clean activity log before running tests
echo -e "${YELLOW}Cleaning activity log...${NC}"
rm -rf .devsync
mkdir -p .devsync
echo "[]" > .devsync/activity-log.json
echo -e "${GREEN}✓ Activity log cleaned${NC}\n"

# Kill the initial empty window
tmux kill-window -t "$SESSION_NAME:0"

# Run Phase 2 Unit Tests
echo -e "${BLUE}Setting up Phase 2 Unit Tests${NC}"
run_test "phase2-unit" \
    "python3 tests/test_phase2_waiting_agent_fix.py" \
    "PHASE 2 UNIT TESTS: Lock Holder Conflict Detection"

# Run Explicit Lock Tests
echo -e "${BLUE}Setting up Explicit Lock Tests${NC}"
run_test "explicit-locks" \
    "python3 tests/test_explicit_locks.py" \
    "EXPLICIT LOCK TESTS: Core Lock Mechanism"

# Run End-to-End Validation Test
echo -e "${BLUE}Setting up End-to-End Validation Test${NC}"
run_test "e2e-validation" \
    "python3 << 'EOF'
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from core.activity_log import clear_log, log_activity, read_log
from core.pre_gen_check import check_for_conflicts
from core.lock_manager import LockManager

print('\n' + '='*70)
print('PHASE 2 END-TO-END VALIDATION TEST')
print('Scenario: 3-Developer Coordination with Lock Holder Fix')
print('='*70 + '\n')

clear_log()

print('STEP 1: Alice declares intent on auth.py')
print('-' * 70)
log_activity('alice', 'auth.py', 'Add authentication system', 'feature')
risk_a1, msg_a1, lock_a1 = check_for_conflicts('alice', 'auth.py', 'Add authentication system')
print(f'✅ Alice declares: Risk={risk_a1.value}')

print('\nSTEP 2: Bob declares intent on same file (auth.py)')
print('-' * 70)
log_activity('bob', 'auth.py', 'Add JWT support', 'feature')
risk_b1, msg_b1, lock_b1 = check_for_conflicts('bob', 'auth.py', 'Add JWT support')
print(f'⏳ Bob declares: Risk={risk_b1.value} (MEDIUM - queued for lock)')
if lock_b1:
    print(f'   Queue Position: {lock_b1.get(\"queue_position\")}')

print('\nSTEP 3: Charlie declares intent on same file (auth.py)')
print('-' * 70)
log_activity('charlie', 'auth.py', 'Add OAuth support', 'feature')
risk_c1, msg_c1, lock_c1 = check_for_conflicts('charlie', 'auth.py', 'Add OAuth support')
print(f'⏳ Charlie declares: Risk={risk_c1.value} (MEDIUM - queued for lock)')
if lock_c1:
    print(f'   Queue Position: {lock_c1.get(\"queue_position\")}')

print('\nSTEP 4: Alice checks conflicts WHILE bob and charlie are waiting')
print('-' * 70)
risk_a2, msg_a2, lock_a2 = check_for_conflicts('alice', 'auth.py', 'Add authentication system')
print(f'✅ Alice second check: Risk={risk_a2.value} (LOW - PHASE 2 FIX WORKING!)')

print('\nSTEP 5: Verification Summary')
print('-' * 70)
checks = {
    'Alice 1st check = LOW': risk_a1.value == 'LOW',
    'Bob declares = MEDIUM': risk_b1.value == 'MEDIUM',
    'Charlie declares = MEDIUM': risk_c1.value == 'MEDIUM',
    'Bob queue_position = 0': lock_b1 and lock_b1.get('queue_position') == 0,
    'Charlie queue_position = 1': lock_c1 and lock_c1.get('queue_position') == 1,
    'Alice 2nd check = LOW (FIX!)': risk_a2.value == 'LOW',
}

passed = sum(1 for v in checks.values() if v)
total = len(checks)

for check, result in checks.items():
    status = '✅' if result else '❌'
    print(f'{status} {check}')

print(f'\n{passed}/{total} checks passed')

if passed == total:
    print('\n' + '='*70)
    print('✅ ALL VALIDATIONS PASSED')
    print('='*70)
else:
    print('\n❌ VALIDATION FAILED')
    sys.exit(1)
EOF" \
    "END-TO-END VALIDATION: 3-Developer Scenario"

# Display summary
echo -e "\n${GREEN}✓ All test windows created${NC}"
echo -e "${YELLOW}Attaching to tmux session in 2 seconds...${NC}\n"
sleep 2

# Show the tmux session layout
echo -e "${BLUE}Current window layout:${NC}"
tmux list-windows -t "$SESSION_NAME"
echo ""

# Attach to the session
echo -e "${GREEN}Attaching to session: $SESSION_NAME${NC}"
echo -e "${YELLOW}Navigation tips:${NC}"
echo -e "  • Use ${BLUE}Ctrl-b n${NC} to go to next window"
echo -e "  • Use ${BLUE}Ctrl-b p${NC} to go to previous window"
echo -e "  • Use ${BLUE}Ctrl-b l${NC} to toggle last window"
echo -e "  • Use ${BLUE}Ctrl-b :kill-session${NC} to exit all windows"
echo -e "  • Use ${BLUE}Ctrl-b [${NC} to scroll (q to exit scroll mode)"
echo ""

tmux attach-session -t "$SESSION_NAME"

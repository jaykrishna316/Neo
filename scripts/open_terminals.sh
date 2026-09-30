#!/bin/bash
#
# Neo Multi-Terminal Demo (macOS)
# Opens actual separate Terminal windows for each actor
#

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$NEO_DIR"

# Clean activity log
rm -rf .devsync 2>/dev/null || true
mkdir -p .devsync
echo "[]" > .devsync/activity-log.json

echo "Opening Neo Demo Windows..."
echo "(5 separate Terminal windows will open)\n"

# Function to open a terminal window running a command
open_terminal() {
    local title=$1
    local command=$2

    osascript <<EOF
tell application "Terminal"
    activate
    set newWindow to do script "cd '$NEO_DIR' && $command"
    tell application "System Events" to keystroke "t" using command down
end tell
EOF

    sleep 0.3
}

# ============================================================================
# Window 1: Activity Log Viewer
# ============================================================================
echo "🔍 Opening Activity Log Viewer..."
osascript <<'APPLESCRIPT'
tell application "Terminal"
    activate
    do script "cd '$NEO_DIR' && python3 << 'EOF'
import time, json, os
os.system('clear')
print('=' * 70)
print('📊 ACTIVITY LOG VIEWER')
print('=' * 70)
print()

while True:
    os.system('clear')
    print('=' * 70)
    print('📊 ACTIVITY LOG VIEWER (Updated: ' + time.strftime('%H:%M:%S') + ')')
    print('=' * 70)
    print()

    try:
        with open('.devsync/activity-log.json') as f:
            data = json.load(f)

        print(f'Total Entries: {len(data)}')
        print()

        if data:
            print('DEVELOPER ACTIVITY:')
            print()
            by_dev = {}
            for entry in data:
                dev = entry.get('developer_id')
                if dev not in by_dev:
                    by_dev[dev] = []
                by_dev[dev].append(entry)

            for dev in sorted(by_dev.keys()):
                latest = by_dev[dev][-1]
                lock = latest.get('lock_state', 'N/A')
                queue = latest.get('queue_position', '')
                file = latest.get('file_path', '')
                intent = latest.get('intent', '')

                print(f'  👤 {dev.upper()}')
                print(f'     📄 File: {file}')
                print(f'     💭 Intent: {intent}')
                print(f'     🔒 Lock State: {lock}', end='')
                if queue != '':
                    print(f' (Queue: {queue})', end='')
                print()
        else:
            print('⏳ Waiting for developer activity...')

        print()
        print('(Refreshing every 1 second)')
    except Exception as e:
        print(f'Error: {e}')

    time.sleep(1)
EOF"
end tell
APPLESCRIPT

sleep 1

# ============================================================================
# Window 2: Developer Alice
# ============================================================================
echo "👤 Opening Developer Alice Terminal..."
osascript <<'APPLESCRIPT'
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.3
    do script "cd '$NEO_DIR' && python3 << 'EOF'
import sys, time
sys.path.insert(0, '.')
from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts

print('\\n' + '='*70)
print('👤 DEVELOPER: ALICE')
print('='*70)
print('\\nWorkspace: auth.py')
print('Task: Add bcrypt password hashing')
print()

print('⏱️  [T+0s] Declaring intent to modify auth.py...')
log_activity('alice', 'auth.py', 'Add bcrypt password hashing', 'feature')
print('✅ Intent logged')
print()

time.sleep(1)
print('⏱️  [T+1s] Checking for conflicts...')
risk, msg, lock = check_for_conflicts('alice', 'auth.py', 'Add bcrypt password hashing')
print(f'✅ Risk Level: {risk.value}')
print(f'   Message: {msg}')
print()

time.sleep(2)
print('⏱️  [T+3s] Generating code...')
time.sleep(1)
print('   ✏️  Generated: password_hash() function')
print('   ✏️  Generated: verify_hash() function')
print('   ✏️  Generated: bcrypt integration')
print()

print('⏱️  [T+4s] Publishing changes...')
print('✅ Code published to repository')
print()
print('━' * 70)
print('Alice workflow complete. Waiting for other developers...')
print('(Ctrl-C to close)')

import select
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOF" in front window
end tell
APPLESCRIPT

sleep 1

# ============================================================================
# Window 3: Developer Bob
# ============================================================================
echo "👤 Opening Developer Bob Terminal..."
osascript <<'APPLESCRIPT'
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.3
    do script "cd '$NEO_DIR' && sleep 1.5 && python3 << 'EOF'
import sys, time
sys.path.insert(0, '.')
from core.activity_log import log_activity, read_log
from core.pre_gen_check import check_for_conflicts

print('\\n' + '='*70)
print('👤 DEVELOPER: BOB')
print('='*70)
print('\\nWorkspace: auth.py')
print('Task: Add JWT token support')
print()

print('⏱️  [T+1s] Declaring intent to modify auth.py...')
log_activity('bob', 'auth.py', 'Add JWT token support', 'feature')
print('✅ Intent logged')
print()

time.sleep(1)
print('⏱️  [T+2s] Checking for conflicts...')
risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT token support')
print(f'⚠️  Risk Level: {risk.value}')
print(f'   Message: {msg}')
if lock:
    print(f'   🔒 Queue Position: {lock.get(\"queue_position\")}')
    print(f'   ⏳ Waiting for: {lock.get(\"lock_holder\")}')
print()

time.sleep(3)
print('⏱️  [T+5s] Checking again (Alice should be done now)...')
logs = read_log()
alice_changes = [e for e in logs if e.get('developer_id') == 'alice']
print(f'✅ Found {len(alice_changes)} entries from Alice')
print('📖 Merging Alice\\'s changes into context...')
print()

time.sleep(1)
print('⏱️  [T+6s] Generating code...')
time.sleep(1)
print('   ✏️  Generated: JWT token creation')
print('   ✏️  Generated: Token validation middleware')
print('   ✏️  Generated: Refresh token logic')
print()

print('⏱️  [T+7s] Publishing changes...')
print('✅ Code published to repository')
print()
print('━' * 70)
print('Bob workflow complete!')
print('(Ctrl-C to close)')

import select
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOF" in front window
end tell
APPLESCRIPT

sleep 1

# ============================================================================
# Window 4: Watcher Alice
# ============================================================================
echo "👁️ Opening Watcher Alice Terminal..."
osascript <<'APPLESCRIPT'
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.3
    do script "cd '$NEO_DIR' && python3 << 'EOF'
import sys, time
sys.path.insert(0, '.')
from core.pre_gen_check import check_for_conflicts

print('\\n' + '='*70)
print('👁️  WATCHER: ALICE')
print('='*70)
print('\\nMonitoring conflicts for: alice@auth.py')
print()

times = [2, 4, 6, 8]
for t in times:
    time.sleep(t)
    try:
        risk, msg, lock = check_for_conflicts('alice', 'auth.py', 'Add bcrypt')
        print(f'⏱️  [T+{t}s] Risk = {risk.value} ✅ (No conflicts)')
    except Exception as e:
        print(f'⏱️  [T+{t}s] Error: {e}')

print()
print('━' * 70)
print('Monitoring complete')
print('(Ctrl-C to close)')

import select
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOF" in front window
end tell
APPLESCRIPT

sleep 1

# ============================================================================
# Window 5: Watcher Bob
# ============================================================================
echo "👁️ Opening Watcher Bob Terminal..."
osascript <<'APPLESCRIPT'
tell application "Terminal"
    tell application "System Events" to keystroke "t" using command down
    delay 0.3
    do script "cd '$NEO_DIR' && sleep 1 && python3 << 'EOF'
import sys, time
sys.path.insert(0, '.')
from core.pre_gen_check import check_for_conflicts

print('\\n' + '='*70)
print('👁️  WATCHER: BOB')
print('='*70)
print('\\nMonitoring conflicts for: bob@auth.py')
print()

print('⏱️  [T+1s] Initial check...')
try:
    risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT')
    print(f'   Risk = {risk.value}', end='')
    if lock:
        print(f' | Queue Position: {lock.get(\"queue_position\")}', end='')
    print()
except Exception as e:
    print(f'   Waiting for activity... ({e})')

time.sleep(4)
print()
print('⏱️  [T+5s] Retry after Alice completes...')
try:
    risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT')
    print(f'   Risk = {risk.value} ✅')
    print('   Lock released - Bob can proceed!')
except Exception as e:
    print(f'   Error: {e}')

print()
print('━' * 70)
print('Monitoring complete')
print('(Ctrl-C to close)')

import select
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOF" in front window
end tell
APPLESCRIPT

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 5 Terminal windows opened!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Windows:"
echo "  1️⃣  Activity Log Viewer - Shows real-time activity log updates"
echo "  2️⃣  Developer Alice - Declares intent, checks conflicts, generates"
echo "  3️⃣  Developer Bob - Waits, gets context from Alice, generates"
echo "  4️⃣  Watcher Alice - Monitors Alice's conflict checks"
echo "  5️⃣  Watcher Bob - Monitors Bob's queue position"
echo ""
echo "The workflow shows:"
echo "  ⏱️  [T+0s]  Alice declares intent → Risk: LOW"
echo "  ⏱️  [T+1s]  Bob declares intent → Risk: MEDIUM (queued)"
echo "  ⏱️  [T+4s]  Alice publishes code"
echo "  ⏱️  [T+5s]  Bob gets fresh context → generates → publishes"
echo ""

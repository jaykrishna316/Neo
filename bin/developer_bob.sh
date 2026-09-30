#!/bin/bash
# Developer Bob - 2-Developer Workflow
# This script runs in its own Terminal window

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$NEO_DIR"

python3 << 'EOF'
import sys
import time
sys.path.insert(0, '.')

from core.activity_log import log_activity, read_log
from core.pre_gen_check import check_for_conflicts

time.sleep(1)  # Let Alice declare first

print("\n" + "="*70)
print("👤 DEVELOPER: BOB")
print("="*70)
print("📄 Workspace: auth.py")
print("💭 Task: Add JWT token support\n")

# Step 1: Declare intent
print("⏱️  [T+1s] Declaring intent to modify auth.py...")
log_activity('bob', 'auth.py', 'Add JWT token support', 'feature')
print("✅ Intent logged\n")

time.sleep(1)

# Step 2: Check for conflicts
print("⏱️  [T+2s] Checking for conflicts...")
risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT token support')
print(f"⚠️  Risk Level: {risk.value}")
print(f"   Message: {msg}")
if lock:
    print(f"   🔒 Queue Position: {lock.get('queue_position')}")
    print(f"   ⏳ Waiting for: {lock.get('lock_holder')}\n")

time.sleep(3)

# Step 3: Check again (Alice should be done)
print("⏱️  [T+5s] Checking again (Alice should be done now)...")
logs = read_log()
alice_changes = [e for e in logs if e.get('developer_id') == 'alice']
print(f"✅ Found {len(alice_changes)} entries from Alice")
print("📖 Merging Alice's changes into context...\n")

time.sleep(1)

# Step 4: Generate code
print("⏱️  [T+6s] Generating code...")
time.sleep(1)
print("   ✏️  Generated: JWT token creation")
print("   ✏️  Generated: Token validation middleware")
print("   ✏️  Generated: Refresh token logic\n")

time.sleep(1)

# Step 5: Publish
print("⏱️  [T+7s] Publishing changes...")
print("✅ Code published to repository\n")

print("━" * 70)
print("Bob workflow complete!")
print("(Press Ctrl-C to close)")

import select
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOF

#!/bin/bash
# Developer Charlie - 3-Developer Workflow
# This script runs in its own Terminal window

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$NEO_DIR"

python3 << 'EOF'
import sys
import time
sys.path.insert(0, '.')

from core.activity_log import log_activity, read_log
from core.pre_gen_check import check_for_conflicts

time.sleep(2.5)  # Let Alice and Bob declare first

print("\n" + "="*70)
print("👤 DEVELOPER: CHARLIE")
print("="*70)
print("📄 Workspace: auth.py")
print("💭 Task: Add OAuth2 support\n")

# Step 1: Declare intent
print("⏱️  [T+2.5s] Declaring intent to modify auth.py...")
log_activity('charlie', 'auth.py', 'Add OAuth2 support', 'feature')
print("✅ Intent logged\n")

time.sleep(0.5)

# Step 2: Check for conflicts
print("⏱️  [T+3s] Checking for conflicts...")
risk, msg, lock = check_for_conflicts('charlie', 'auth.py', 'Add OAuth2 support')
print(f"⚠️  Risk Level: {risk.value}")
print(f"   Message: {msg}")
if lock:
    print(f"   🔒 Queue Position: {lock.get('queue_position')}")
    print(f"   ⏳ Waiting for: {lock.get('lock_holder')}\n")

time.sleep(5)

# Step 3: Check again (Alice and Bob should be done)
print("⏱️  [T+8.5s] Checking again (Alice & Bob should be done)...")
logs = read_log()
other_changes = [e for e in logs if e.get('developer_id') in ['alice', 'bob']]
print(f"✅ Found {len(other_changes)} entries from Alice & Bob")
print("📖 Merging all changes into context...\n")

time.sleep(1)

# Step 4: Generate code
print("⏱️  [T+9.5s] Generating code...")
time.sleep(1)
print("   ✏️  Generated: OAuth2 provider configuration")
print("   ✏️  Generated: Token exchange handlers")
print("   ✏️  Generated: Authorization flow\n")

time.sleep(1)

# Step 5: Publish
print("⏱️  [T+11.5s] Publishing changes...")
print("✅ Code published to repository\n")

print("━" * 70)
print("Charlie workflow complete! All 3 developers finished.")
print("(Press Ctrl-C to close)")

import select
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOF

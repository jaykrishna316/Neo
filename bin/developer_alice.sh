#!/bin/bash
# Developer Alice - 2-Developer Workflow
# This script runs in its own Terminal window

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$NEO_DIR"

python3 << 'EOF'
import sys
import time
sys.path.insert(0, '.')

from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts

print("\n" + "="*70)
print("👤 DEVELOPER: ALICE")
print("="*70)
print("📄 Workspace: auth.py")
print("💭 Task: Add bcrypt password hashing\n")

# Step 1: Declare intent
print("⏱️  [T+0s] Declaring intent to modify auth.py...")
log_activity('alice', 'auth.py', 'Add bcrypt password hashing', 'feature')
print("✅ Intent logged\n")

time.sleep(1)

# Step 2: Check for conflicts
print("⏱️  [T+1s] Checking for conflicts...")
risk, msg, lock = check_for_conflicts('alice', 'auth.py', 'Add bcrypt password hashing')
print(f"✅ Risk Level: {risk.value}")
print(f"   Message: {msg}\n")

time.sleep(2)

# Step 3: Generate code
print("⏱️  [T+3s] Generating code...")
time.sleep(1)
print("   ✏️  Generated: password_hash() function")
print("   ✏️  Generated: verify_hash() function")
print("   ✏️  Generated: bcrypt integration\n")

time.sleep(1)

# Step 4: Publish
print("⏱️  [T+4s] Publishing changes...")
print("✅ Code published to repository\n")

print("━" * 70)
print("Alice workflow complete. Waiting for other developers...")
print("(Press Ctrl-C to close)")

import select
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOF

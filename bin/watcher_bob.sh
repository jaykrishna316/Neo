#!/bin/bash
# Watcher Bob - Monitors Bob's conflicts and queue position
# This script runs in its own Terminal window

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$NEO_DIR"

python3 << 'EOF'
import sys
import time
sys.path.insert(0, '.')

from core.pre_gen_check import check_for_conflicts

print("\n" + "="*70)
print("👁️  WATCHER: BOB")
print("="*70)
print("📊 Monitoring conflicts for: bob@auth.py\n")

print("⏱️  [T+1s] Initial check...")
try:
    risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT')
    print(f"   Risk = {risk.value}", end='')
    if lock:
        print(f" | Queue Position: {lock.get('queue_position')}", end='')
    print()
except Exception as e:
    print(f"   Waiting for activity... ({e})")

time.sleep(4)

print("\n⏱️  [T+5s] Retry after Alice completes...")
try:
    risk, msg, lock = check_for_conflicts('bob', 'auth.py', 'Add JWT')
    print(f"   Risk = {risk.value} ✅")
    print("   Lock released - Bob can proceed!")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "━" * 70)
print("Monitoring complete")
print("(Press Ctrl-C to close)")

import select
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOF

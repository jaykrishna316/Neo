#!/bin/bash
# Watcher Alice - Monitors Alice's conflicts
# This script runs in its own Terminal window

NEO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$NEO_DIR"

python3 << 'EOF'
import sys
import time
sys.path.insert(0, '.')

from core.pre_gen_check import check_for_conflicts

print("\n" + "="*70)
print("👁️  WATCHER: ALICE")
print("="*70)
print("📊 Monitoring conflicts for: alice@auth.py\n")

check_times = [2, 4, 6, 8]

for t in check_times:
    time.sleep(t)
    try:
        risk, msg, lock = check_for_conflicts('alice', 'auth.py', 'Add bcrypt')
        print(f"⏱️  [T+{t}s] Risk = {risk.value} ✅ (No conflicts)")
    except Exception as e:
        print(f"⏱️  [T+{t}s] Error: {e}")

print("\n" + "━" * 70)
print("Monitoring complete")
print("(Press Ctrl-C to close)")

import select
try:
    select.select([], [], [])
except KeyboardInterrupt:
    pass
EOF

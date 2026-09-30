#!/usr/bin/env python3
"""
2-Developer Workflow Simulation
Simulates two developers working on the same file with Neo coordination
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path.cwd()))

from core.activity_log import log_activity, read_log
from core.pre_gen_check import check_for_conflicts

def simulate_dev_a():
    """Developer A: Alice"""
    print("\n" + "="*70)
    print("DEVELOPER A: ALICE")
    print("="*70 + "\n")

    print("⏱️  [00:01] Alice: Declaring intent to modify auth.py")
    log_activity('alice', 'auth.py', 'Add bcrypt password hashing', 'feature')

    time.sleep(0.5)
    print("⏱️  [00:02] Alice: Checking for conflicts...")
    risk, msg, lock_info = check_for_conflicts('alice', 'auth.py', 'Add bcrypt password hashing')
    print(f"   ✅ Risk Level: {risk.value}")
    print(f"   📝 Message: {msg}\n")

    time.sleep(2)
    print("⏱️  [00:05] Alice: Writing authentication code...")
    time.sleep(2)
    print("   ✏️  Generated: password validation function")
    print("   ✏️  Generated: bcrypt integration\n")

    time.sleep(1)
    print("⏱️  [00:08] Alice: Code complete, publishing changes...")
    print("   ✅ Published to repository\n")

def simulate_dev_b():
    """Developer B: Bob"""
    time.sleep(2)  # Let Alice declare first

    print("\n" + "="*70)
    print("DEVELOPER B: BOB")
    print("="*70 + "\n")

    print("⏱️  [00:03] Bob: Declaring intent to modify auth.py")
    log_activity('bob', 'auth.py', 'Add JWT token support', 'feature')

    time.sleep(0.5)
    print("⏱️  [00:04] Bob: Checking for conflicts...")
    risk, msg, lock_info = check_for_conflicts('bob', 'auth.py', 'Add JWT token support')
    print(f"   ⚠️  Risk Level: {risk.value}")
    print(f"   📝 Message: {msg}")
    if lock_info:
        print(f"   🔒 Lock Status: WAITING (queue_position={lock_info.get('queue_position')})")
        print(f"   ⏳ Waiting for: {lock_info.get('lock_holder')}\n")

    print("⏱️  [00:05] Bob: Waiting for Alice to complete...\n")
    time.sleep(4)

    print("⏱️  [00:09] Bob: Alice finished! Fetching fresh context...")
    logs = read_log()
    alice_entries = [e for e in logs if e.get('developer_id') == 'alice']
    print(f"   📖 Found {len(alice_entries)} entries from Alice")
    print("   🔄 Merged Alice's changes into context\n")

    time.sleep(1)
    print("⏱️  [00:10] Bob: Writing JWT implementation...")
    time.sleep(1.5)
    print("   ✏️  Generated: JWT token creation")
    print("   ✏️  Generated: Token validation middleware\n")

    print("⏱️  [00:12] Bob: Code complete, publishing changes...")
    print("   ✅ Published to repository\n")

if __name__ == "__main__":
    import concurrent.futures

    print("\n" + "🎬 "*35)
    print("NEO 2-DEVELOPER COORDINATION WORKFLOW")
    print("Scenario: Alice and Bob modifying auth.py")
    print("🎬 "*35 + "\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(simulate_dev_a)
        executor.submit(simulate_dev_b)

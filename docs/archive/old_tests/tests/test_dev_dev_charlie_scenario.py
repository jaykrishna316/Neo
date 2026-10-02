#!/usr/bin/env python3
"""Test scenario for Developer Charlie"""
import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.activity_log import log_activity, get_active_entries, read_log
from core.pre_gen_check import check_for_conflicts

print("\n" + "="*80)
print("CHARLIE: Declaring intent to add 2FA support")
print("="*80)

ts_start = datetime.now()

# Wait for Alice and Bob to start
print("[Charlie waiting 2 seconds for Alice and Bob to declare...]")
import time
time.sleep(2)

# Charlie declares on SAME file as Alice and Bob
log_activity(
    developer_id="dev_charlie",
    file_path="src/auth.py",
    intent="Add 2FA support",
    intent_category="feature"
)

# Check conflicts (should see both Alice AND Bob)
risk, msg, _ = check_for_conflicts(
    agent_id="dev_charlie",
    file_path="src/auth.py",
    intent="Add 2FA support"
)

print(f"\n✓ Charlie logged intent (3rd dev on auth.py)")
print(f"✓ Risk level: {risk}")
print(f"✓ Message: {msg}")

# Check activity log
log_entries = read_log()
alice_entries = [e for e in log_entries if e.get('developer_id') == 'dev_alice']
bob_entries = [e for e in log_entries if e.get('developer_id') == 'dev_bob']

print(f"✓ Can see Alice: {len(alice_entries)} entries")
print(f"✓ Can see Bob: {len(bob_entries)} entries")
print(f"✓ Total developers tracked: {len(set(e.get('developer_id') for e in log_entries))}")

# Simulate work
print("\n[Charlie working for 2 seconds...]")
time.sleep(2)

# Save results
results = {
    "developer": "dev_charlie",
    "status": "completed",
    "risk_level": str(risk),
    "alice_visible": len(alice_entries) > 0,
    "bob_visible": len(bob_entries) > 0,
    "total_entries": len(log_entries),
    "total_developers": len(set(e.get('developer_id') for e in log_entries)),
    "timestamp": ts_start.isoformat(),
    "duration_seconds": (datetime.now() - ts_start).total_seconds()
}

results_file = Path(".test_results/dev_charlie.json")
results_file.parent.mkdir(exist_ok=True)
with open(results_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✓ Results saved to {results_file}")

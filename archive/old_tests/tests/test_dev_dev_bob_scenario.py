#!/usr/bin/env python3
"""Test scenario for Developer Bob"""
import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.activity_log import log_activity, get_active_entries, read_log
from core.pre_gen_check import check_for_conflicts

print("\n" + "="*80)
print("BOB: Declaring intent to add JWT token validation")
print("="*80)

ts_start = datetime.now()

# Wait a bit for Alice to start
print("[Bob waiting 1 second for Alice to declare...]")
import time
time.sleep(1)

# Bob declares intent on same file as Alice
log_activity(
    developer_id="dev_bob",
    file_path="src/auth.py",
    intent="Add JWT token validation",
    intent_category="feature"
)

# Check conflicts (should see Alice's work now)
risk, msg, _ = check_for_conflicts(
    agent_id="dev_bob",
    file_path="src/auth.py",
    intent="Add JWT token validation"
)

print(f"\n✓ Bob logged intent (same file as Alice)")
print(f"✓ Risk level: {risk}")
print(f"✓ Message: {msg}")

# Check activity log to see Alice's entry
log_entries = read_log()
alice_entry = [e for e in log_entries if e.get('developer_id') == 'dev_alice']
print(f"✓ Can see Alice in activity log: {len(alice_entry)} entry/entries")

# Simulate work
print("\n[Bob working for 2 seconds...]")
time.sleep(2)

# Save results
results = {
    "developer": "dev_bob",
    "status": "completed",
    "risk_level": str(risk),
    "alice_visible": len(alice_entry) > 0,
    "total_entries": len(log_entries),
    "timestamp": ts_start.isoformat(),
    "duration_seconds": (datetime.now() - ts_start).total_seconds()
}

results_file = Path(".test_results/dev_bob.json")
results_file.parent.mkdir(exist_ok=True)
with open(results_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✓ Results saved to {results_file}")

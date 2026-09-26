#!/usr/bin/env python3
"""Test scenario for Developer Alice"""
import json
from pathlib import Path
from datetime import datetime
import sys
sys.path.insert(0, str(Path(__file__).parent))

from core.activity_log import log_activity, get_active_entries
from core.pre_gen_check import check_for_conflicts

print("\n" + "="*80)
print("ALICE: Declaring intent to add OAuth2 authentication")
print("="*80)

ts_start = datetime.now()

# Alice declares intent
log_activity(
    developer_id="dev_alice",
    file_path="src/auth.py",
    intent="Add OAuth2 authentication module",
    intent_category="feature"
)

# Check conflicts (should be LOW - only her)
risk, msg = check_for_conflicts(
    agent_id="dev_alice",
    file_path="src/auth.py",
    intent="Add OAuth2 authentication module"
)

print(f"\n✓ Alice logged intent")
print(f"✓ Risk level: {risk}")
print(f"✓ Message: {msg}")

# Simulate work
print("\n[Alice working for 2 seconds...]")
import time
time.sleep(2)

# Record completion
entries = get_active_entries()
print(f"✓ Active entries: {len(entries)}")

# Save results
results = {
    "developer": "dev_alice",
    "status": "completed",
    "risk_level": str(risk),
    "active_entries": len(entries),
    "timestamp": ts_start.isoformat(),
    "duration_seconds": (datetime.now() - ts_start).total_seconds()
}

results_file = Path(".test_results/dev_alice.json")
results_file.parent.mkdir(exist_ok=True)
with open(results_file, 'w') as f:
    json.dump(results, f, indent=2)

print(f"\n✓ Results saved to {results_file}")

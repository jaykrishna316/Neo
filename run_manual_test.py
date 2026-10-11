#!/usr/bin/env python3
"""
Manual Neo coordination test - run step by step in terminal.
No automatic progression - you control each step.
"""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from core.activity_log import ActivityLog
from core.pre_gen_check import check_for_conflicts, RiskLevel

def show_activity_log():
    """Display current activity log."""
    log_file = Path(".devsync/activity-log.json")
    if not log_file.exists():
        print("  (activity log empty)")
        return
    
    with open(log_file) as f:
        entries = json.load(f)
    
    print(f"\n  📋 ACTIVITY LOG ({len(entries)} entries):\n")
    for i, entry in enumerate(entries, 1):
        dev = entry.get("developer_id", "system")
        intent = entry.get("intent", "N/A")[:60]
        lock = entry.get("lock_state") or "—"
        waiting = f" (waiting for {entry.get('waiting_for')})" if entry.get("waiting_for") else ""
        
        print(f"    [{i:2d}] {dev:12s} | {lock:8s} | {intent}{waiting}")

def step_1():
    print("\n" + "="*80)
    print("STEP 1: Alice declares intent to refactor password validation")
    print("="*80)
    
    log = ActivityLog()
    log.log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor password validation to use bcrypt",
        intent_category="refactor",
        region="validate_password (lines 45-65)"
    )
    
    print("\n✓ Alice logged her intent")
    show_activity_log()

def step_2():
    print("\n" + "="*80)
    print("STEP 2: Bob checks for conflicts")
    print("="*80)
    
    risk, msg = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add password strength requirements",
        region="validate_password (lines 50-70)"
    )
    
    print(f"\n✓ Bob's conflict check:")
    print(f"  Risk Level: {risk.name}")
    print(f"  Message: {msg}")

def step_3():
    print("\n" + "="*80)
    print("STEP 3: Bob declares intent (gets added to queue)")
    print("="*80)
    
    log = ActivityLog()
    log.log_activity(
        developer_id="bob",
        file_path="auth.py",
        intent="Add password strength requirements",
        intent_category="feature",
        region="validate_password (lines 50-70)"
    )
    
    print("\n✓ Bob logged his intent")
    show_activity_log()

def step_4():
    print("\n" + "="*80)
    print("STEP 4: Charlie declares intent (different region, no conflict)")
    print("="*80)
    
    risk, msg = check_for_conflicts(
        agent_id="charlie",
        file_path="auth.py",
        intent="Add authentication logging",
        region="authenticate (lines 80-100)"
    )
    
    print(f"\n✓ Charlie's conflict check:")
    print(f"  Risk Level: {risk.name}")
    print(f"  Message: {msg}")
    
    log = ActivityLog()
    log.log_activity(
        developer_id="charlie",
        file_path="auth.py",
        intent="Add authentication logging",
        intent_category="feature",
        region="authenticate (lines 80-100)"
    )
    
    print("\n✓ Charlie logged her intent")
    show_activity_log()

def step_5():
    print("\n" + "="*80)
    print("STEP 5: Alice completes her work")
    print("="*80)
    
    log = ActivityLog()
    log.log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="COMPLETED: Refactored password validation to use bcrypt",
        intent_category="completed",
        region="validate_password"
    )
    
    print("\n✓ Alice logged completion (+20 lines, -5 lines)")
    show_activity_log()

def step_6():
    print("\n" + "="*80)
    print("STEP 6: Bob gets fresh context and completes")
    print("="*80)
    
    log = ActivityLog()
    log.log_activity(
        developer_id="bob",
        file_path="auth.py",
        intent="COMPLETED: Added password strength requirements (built on alice's changes)",
        intent_category="completed",
        region="validate_password"
    )
    
    print("\n✓ Bob logged completion (+15 lines, -0 lines)")
    show_activity_log()

def step_7():
    print("\n" + "="*80)
    print("STEP 7: Charlie completes (built on alice + bob)")
    print("="*80)
    
    log = ActivityLog()
    log.log_activity(
        developer_id="charlie",
        file_path="auth.py",
        intent="COMPLETED: Added authentication logging (built on bob's changes)",
        intent_category="completed",
        region="authenticate"
    )
    
    print("\n✓ Charlie logged completion (+18 lines, -2 lines)")
    show_activity_log()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 run_manual_test.py <step>")
        print("\nSteps:")
        print("  step1 - Alice declares intent")
        print("  step2 - Bob checks for conflicts")
        print("  step3 - Bob declares intent")
        print("  step4 - Charlie declares intent")
        print("  step5 - Alice completes")
        print("  step6 - Bob completes")
        print("  step7 - Charlie completes")
        print("  clear - Clear activity log")
        sys.exit(0)
    
    step = sys.argv[1].lower()
    
    if step == "clear":
        Path(".devsync/activity-log.json").unlink(missing_ok=True)
        print("✓ Activity log cleared")
    elif step == "step1":
        step_1()
    elif step == "step2":
        step_2()
    elif step == "step3":
        step_3()
    elif step == "step4":
        step_4()
    elif step == "step5":
        step_5()
    elif step == "step6":
        step_6()
    elif step == "step7":
        step_7()
    else:
        print(f"Unknown step: {step}")

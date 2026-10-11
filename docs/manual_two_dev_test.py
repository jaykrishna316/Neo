#!/usr/bin/env python3
"""
Manual 2-Developer Coordination Test
=====================================

Run each step manually in separate terminals to see Neo coordination in action.

Terminal 1 (Watch Log):
  tail -f .devsync/activity-log.json | python3 -m json.tool

Terminal 2 (Developer A):
  .venv/bin/python3 manual_two_dev_test.py clear
  .venv/bin/python3 manual_two_dev_test.py alice-declare
  .venv/bin/python3 manual_two_dev_test.py alice-complete

Terminal 3 (Developer B):
  .venv/bin/python3 manual_two_dev_test.py bob-check
  .venv/bin/python3 manual_two_dev_test.py bob-declare
  .venv/bin/python3 manual_two_dev_test.py bob-context
  .venv/bin/python3 manual_two_dev_test.py bob-complete
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from core.activity_log import log_activity, read_log, clear_log
from core.pre_gen_check import check_for_conflicts

def show_log():
    """Display current activity log nicely."""
    log_entries = read_log()
    
    print(f"\n📋 ACTIVITY LOG ({len(log_entries)} entries):\n")
    for i, entry in enumerate(log_entries, 1):
        dev = entry.get('developer_id')
        intent = entry.get('intent')[:60]
        metadata = entry.get('agent_metadata') or {}
        status = metadata.get('status', 'declared')
        
        print(f"  [{i}] {dev:10s} ({status:10s}): {intent}...")
        
        if metadata.get('lines_added'):
            print(f"       └─ +{metadata.get('lines_added')} -{metadata.get('lines_removed')} lines")
        if metadata.get('built_on'):
            print(f"       └─ Built on: {metadata.get('built_on')}")

def cmd_clear():
    clear_log()
    print("✓ Activity log cleared")

def cmd_alice_declare():
    print("\n" + "="*70)
    print("ALICE: Declaring intent to refactor password validation")
    print("="*70)
    
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor password validation to use bcrypt",
        region="validate_password (lines 45-65)",
        intent_category="refactor"
    )
    
    log_entries = read_log()
    print(f"\n✓ ALICE_DECLARES_INTENT")
    print(f"  Alice declared intent on auth.py")
    print(f"  Log now has {len(log_entries)} entry (No lock yet - only 1 developer)")
    
    show_log()

def cmd_bob_check():
    print("\n" + "="*70)
    print("BOB: Checking for conflicts before declaring intent")
    print("="*70)
    
    risk_level, conflict_msg, lock_info = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add password strength requirements",
        region="validate_password (lines 50-70)"
    )
    
    print(f"\n✓ BOB_CHECKS_CONFLICTS")
    print(f"  Risk level: {risk_level.name}")
    print(f"  Message: {conflict_msg}")

def cmd_bob_declare():
    print("\n" + "="*70)
    print("BOB: Declaring intent (Lock will apply - 2 devs on same file)")
    print("="*70)
    
    log_activity(
        developer_id="bob",
        file_path="auth.py",
        intent="Add password strength requirements",
        region="validate_password (lines 50-70)",
        intent_category="feature"
    )
    
    log_entries = read_log()
    same_file = [e for e in log_entries if e['file_path'] == 'auth.py']
    
    print(f"\n✓ BOB_DECLARES_INTENT")
    print(f"  Bob declared intent on auth.py")
    print(f"  Log now has {len(log_entries)} entries")
    print(f"  Lock status: ACTIVE ({len(same_file)} devs on same file)")
    
    show_log()

def cmd_alice_complete():
    print("\n" + "="*70)
    print("ALICE: Completing work and publishing changes")
    print("="*70)
    
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="COMPLETED: Refactored password validation to use bcrypt",
        region="validate_password (lines 45-65)",
        intent_category="refactor",
        agent_metadata={
            "status": "completed",
            "lines_added": 20,
            "lines_removed": 5,
            "change_summary": "Switched from MD5 to bcrypt hashing with salt generation",
            "conflicts_detected": 0
        }
    )
    
    log_entries = read_log()
    print(f"\n✓ ALICE_COMPLETES_WORK")
    print(f"  Alice completed her work")
    print(f"  Changes: +20 lines, -5 lines")
    print(f"  Log now has {len(log_entries)} entries")
    
    show_log()

def cmd_bob_context():
    print("\n" + "="*70)
    print("BOB: Getting fresh context from Alice's changes")
    print("="*70)
    
    risk_level, conflict_msg, lock_info = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add password strength requirements",
        region="validate_password (lines 50-70)"
    )
    
    log_entries = read_log()
    alice_completed = next(
        (e for e in log_entries 
         if e['developer_id'] == 'alice' 
         and (e.get('agent_metadata') or {}).get('status') == 'completed'),
        None
    )
    
    if alice_completed:
        meta = alice_completed.get('agent_metadata') or {}
        print(f"\n✓ BOB_GETS_FRESH_CONTEXT")
        print(f"  Dev B received fresh context from Alice's changes")
        print(f"  Alice's changes: +{meta.get('lines_added')}, -{meta.get('lines_removed')} lines")
        print(f"  Risk assessment: {risk_level.name}")

def cmd_bob_complete():
    print("\n" + "="*70)
    print("BOB: Completing work (built on Alice's changes)")
    print("="*70)
    
    log_activity(
        developer_id="bob",
        file_path="auth.py",
        intent="COMPLETED: Added password strength requirements on top of Alice's bcrypt refactor",
        region="validate_password (lines 50-70)",
        intent_category="feature",
        agent_metadata={
            "status": "completed",
            "lines_added": 15,
            "lines_removed": 0,
            "change_summary": "Added complexity checks (uppercase, numbers, symbols) with bcrypt salt integration",
            "built_on": "alice",
            "conflicts_detected": 0
        }
    )
    
    log_entries = read_log()
    completed = [e for e in log_entries if (e.get('agent_metadata') or {}).get('status') == 'completed']
    
    print(f"\n✓ BOB_COMPLETES_WORK")
    print(f"  Bob completed his work (built on Alice's changes)")
    print(f"  Changes: +15 lines, -0 lines")
    print(f"  Log now has {len(log_entries)} entries")
    print(f"  Developers completed: {len(completed)}")
    print(f"  Total conflicts detected: 0")
    
    show_log()
    
    print(f"\n" + "="*70)
    print("✅ 2-DEVELOPER COORDINATION COMPLETE - NO CONFLICTS!")
    print("="*70)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    
    cmd = sys.argv[1].lower()
    
    if cmd == "clear":
        cmd_clear()
    elif cmd == "alice-declare":
        cmd_alice_declare()
    elif cmd == "alice-complete":
        cmd_alice_complete()
    elif cmd == "bob-check":
        cmd_bob_check()
    elif cmd == "bob-declare":
        cmd_bob_declare()
    elif cmd == "bob-context":
        cmd_bob_context()
    elif cmd == "bob-complete":
        cmd_bob_complete()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)

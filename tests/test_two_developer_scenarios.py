#!/usr/bin/env python3
"""
Neo 4.0: Comprehensive 2-Developer Test Scenarios

This test demonstrates Neo working with multiple conflict scenarios:
1. Low Conflict (Different Regions) - No lock needed
2. Medium Conflict (Overlapping Regions) - Lock applies, sequential workflow
3. High Conflict (Same Lines) - Lock applies, Bob must wait for Alice
4. Different Files - No conflict, parallel work
5. Rapid Declarations - Both declare simultaneously

Run with: python tests/test_two_developer_scenarios.py
"""

import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import log_activity, read_log, clear_log, ensure_log_exists
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel


def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def print_step(step_num, description):
    print(f"\n[Step {step_num}] {description}")


def verify_lock_state(expected_holder, expected_waiting_for=None):
    """Verify lock state in activity log"""
    entries = read_log()

    # Find lock holder
    lock_holder = None
    for entry in entries:
        if entry.get('lock_state') == 'ACQUIRED':
            lock_holder = entry.get('lock_holder')
            break

    # Find waiting developer
    waiting_dev = None
    for entry in entries:
        if entry.get('lock_state') == 'WAITING':
            waiting_dev = {
                'developer': entry.get('developer_id'),
                'waiting_for': entry.get('waiting_for'),
                'queue_pos': entry.get('queue_position')
            }
            break

    return {
        'lock_holder': lock_holder,
        'waiting_dev': waiting_dev,
        'correct': lock_holder == expected_holder and
                   (expected_waiting_for is None or (waiting_dev and waiting_dev['waiting_for'] == expected_waiting_for))
    }


# ============================================================================
# SCENARIO 1: LOW CONFLICT (Different Regions in Same File)
# ============================================================================

def test_low_conflict_different_regions():
    print_section("SCENARIO 1: LOW CONFLICT (Different Regions)")
    print("Alice and Bob work on different regions of same file")
    print("Expected: LOW risk, no lock needed")

    clear_log()

    # Alice on lines 10-20
    print_step(1, "Alice declares intent on auth.py (lines 10-20)")
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Add bcrypt password hashing",
        region="validate_password (lines 10-20)",
        intent_category="feature"
    )
    print("    ✓ Alice working on lines 10-20")

    # Bob on lines 50-60 (different region)
    print_step(2, "Bob checks conflicts on auth.py (lines 50-60)")
    risk_level, message, lock_info = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add JWT token support",
        region="token_handler (lines 50-60)"
    )
    print(f"    Risk Level: {risk_level.name}")
    print(f"    Message: {message[:80]}...")

    if risk_level == RiskLevel.LOW:
        print("    ✓ PASS: Correctly identified as LOW risk (different regions)")
    else:
        print(f"    ✗ FAIL: Expected LOW, got {risk_level.name}")

    return risk_level == RiskLevel.LOW


# ============================================================================
# SCENARIO 2: HIGH CONFLICT (Same Lines in Same File)
# ============================================================================

def test_high_conflict_same_lines():
    print_section("SCENARIO 2: CRITICAL CONFLICT (Same Lines/Overlapping Regions)")
    print("Alice and Bob work on THE SAME LINES of the same file")
    print("Expected: MEDIUM/HIGH risk, lock applies, Alice holds lock, Bob waits")

    clear_log()

    # Alice on lines 45-65
    print_step(1, "Alice declares intent on auth.py (lines 45-65)")
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor authentication logic completely",
        region="authenticate_user (lines 45-65)",
        intent_category="refactor"
    )
    print("    ✓ Alice working on lines 45-65")

    # Bob on SAME lines 45-65
    print_step(2, "Bob checks conflicts on auth.py (SAME lines 45-65)")
    risk_level, message, lock_info = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add OAuth2 support to authentication",
        region="authenticate_user (lines 45-65)"
    )
    print(f"    Risk Level: {risk_level.name}")
    print(f"    Message: {message[:80]}...")

    # Verify lock state
    lock_state = verify_lock_state(expected_holder="alice", expected_waiting_for="alice")

    checks = [
        (risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH), "MEDIUM/HIGH risk detected"),
        (lock_state['lock_holder'] == 'alice', "Alice holds lock"),
        (lock_state['waiting_dev'] and lock_state['waiting_dev']['waiting_for'] == 'alice', "Bob waiting for Alice"),
    ]

    for check, desc in checks:
        status = "✓ PASS" if check else "✗ FAIL"
        print(f"    {status}: {desc}")

    all_pass = all(check for check, _ in checks)

    # Simulate Alice completing
    print_step(3, "Alice completes work on auth.py")
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="COMPLETED: Refactored authentication logic",
        region="authenticate_user (lines 45-65)",
        intent_category="refactor",
        agent_metadata={
            'status': 'completed',
            'lines_added': 30,
            'lines_removed': 15,
            'change_summary': 'Complete rewrite of authenticate_user function',
            'conflicts_detected': 0
        }
    )
    print("    ✓ Alice marked as completed")

    # Bob now proceeds with Alice's context
    print_step(4, "Bob gets fresh context from Alice's changes")
    entries = read_log()
    alice_completed = [e for e in entries if e.get('developer_id') == 'alice' and
                      (e.get('agent_metadata') or {}).get('status') == 'completed']

    if alice_completed:
        metadata = alice_completed[0].get('agent_metadata', {})
        print(f"    ✓ Bob sees Alice's changes:")
        print(f"      +{metadata.get('lines_added')} lines, -{metadata.get('lines_removed')} lines")
        print(f"      Summary: {metadata.get('change_summary')[:50]}...")

    print_step(5, "Bob completes work (built on Alice's code)")
    log_activity(
        developer_id="bob",
        file_path="auth.py",
        intent="COMPLETED: Added OAuth2 support on top of Alice's refactor",
        region="authenticate_user (lines 45-65)",
        intent_category="feature",
        agent_metadata={
            'status': 'completed',
            'lines_added': 25,
            'lines_removed': 0,
            'change_summary': 'Added OAuth2 provider support using Alice\' refactored interface',
            'built_on': 'alice',
            'conflicts_detected': 0
        }
    )
    print("    ✓ Bob marked as completed (built on Alice)")

    return all_pass


# ============================================================================
# SCENARIO 3: DIFFERENT FILES (No Conflict)
# ============================================================================

def test_different_files_no_conflict():
    print_section("SCENARIO 3: DIFFERENT FILES (Parallel Work)")
    print("Alice and Bob work on completely different files")
    print("Expected: LOW risk, no lock, parallel work allowed")

    clear_log()

    # Alice on auth.py
    print_step(1, "Alice declares intent on auth.py")
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Add password validation",
        intent_category="feature"
    )
    print("    ✓ Alice on auth.py")

    # Bob on database.py (different file)
    print_step(2, "Bob declares intent on database.py (different file)")
    risk_level, message, lock_info = check_for_conflicts(
        agent_id="bob",
        file_path="database.py",
        intent="Add connection pooling"
    )
    print(f"    Risk Level: {risk_level.name}")
    print("    ✓ Bob on database.py")

    if risk_level == RiskLevel.LOW:
        print("    ✓ PASS: No conflict detected (different files)")
        return True
    else:
        print(f"    ✗ FAIL: Expected LOW, got {risk_level.name}")
        return False


# ============================================================================
# SCENARIO 4: RAPID DECLARATIONS (Both Declare Almost Simultaneously)
# ============================================================================

def test_rapid_declarations():
    print_section("SCENARIO 4: RAPID DECLARATIONS (Simultaneous Intent)")
    print("Alice and Bob declare intent on same file within milliseconds")
    print("Expected: MEDIUM risk, lock applies to whoever declared first")

    clear_log()

    # Alice declares first (even if just barely)
    print_step(1, "Alice declares intent on auth.py")
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Add password hashing",
        intent_category="feature"
    )

    # Bob declares immediately after
    print_step(2, "Bob declares intent on auth.py (milliseconds later)")
    log_activity(
        developer_id="bob",
        file_path="auth.py",
        intent="Add password validation",
        intent_category="feature"
    )

    # Now check conflicts
    print_step(3, "Bob checks conflicts (both already declared)")
    risk_level, message, lock_info = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add password validation",
        region="validate_password"
    )

    lock_state = verify_lock_state(expected_holder="alice", expected_waiting_for="alice")

    checks = [
        (risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH), "MEDIUM/HIGH risk detected"),
        (lock_state['lock_holder'] == 'alice', "Alice holds lock (declared first)"),
    ]

    for check, desc in checks:
        status = "✓ PASS" if check else "✗ FAIL"
        print(f"    {status}: {desc}")

    return all(check for check, _ in checks)


# ============================================================================
# SCENARIO 5: 3-DEVELOPER QUEUE (Scaling Test)
# ============================================================================

def test_three_developer_queue():
    print_section("SCENARIO 5: 3-DEVELOPER QUEUE (Scaling)")
    print("Alice, Bob, and Charlie all declare intent on same file")
    print("Expected: Lock active, queue managed, sequential completion")

    clear_log()

    # Alice declares first
    print_step(1, "Alice declares intent on auth.py")
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Add bcrypt hashing",
        intent_category="feature"
    )
    print("    ✓ Alice declared (1st)")

    # Bob declares second
    print_step(2, "Bob declares intent on auth.py")
    log_activity(
        developer_id="bob",
        file_path="auth.py",
        intent="Add password strength validation",
        intent_category="feature"
    )
    risk_bob, _, _ = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add password strength validation",
        region="authenticate_user"
    )
    print(f"    ✓ Bob declared (2nd) - Risk: {risk_bob.name}")

    # Charlie declares third
    print_step(3, "Charlie declares intent on auth.py")
    log_activity(
        developer_id="charlie",
        file_path="auth.py",
        intent="Add OAuth2 support",
        intent_category="feature"
    )
    risk_charlie, _, _ = check_for_conflicts(
        agent_id="charlie",
        file_path="auth.py",
        intent="Add OAuth2 support",
        region="authenticate_user"
    )
    print(f"    ✓ Charlie declared (3rd) - Risk: {risk_charlie.name}")

    # Verify queue
    entries = read_log()
    num_waiting = sum(1 for e in entries if e.get('lock_state') == 'WAITING')
    num_held = sum(1 for e in entries if e.get('lock_state') == 'ACQUIRED')

    print_step(4, "Verify queue state")
    print(f"    Lock holders: {num_held}")
    print(f"    Developers waiting: {num_waiting}")

    checks = [
        (risk_bob in (RiskLevel.MEDIUM, RiskLevel.HIGH), "Bob detected conflict"),
        (risk_charlie in (RiskLevel.MEDIUM, RiskLevel.HIGH), "Charlie detected conflict"),
        (num_held >= 1, "Lock is held"),
        (num_waiting >= 1, "Queue has waiting developers"),
    ]

    for check, desc in checks:
        status = "✓ PASS" if check else "✗ FAIL"
        print(f"    {status}: {desc}")

    return all(check for check, _ in checks)


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

def main():
    ensure_log_exists()

    results = {
        'Low Conflict (Different Regions)': test_low_conflict_different_regions(),
        'High Conflict (Same Lines)': test_high_conflict_same_lines(),
        'Different Files': test_different_files_no_conflict(),
        'Rapid Declarations': test_rapid_declarations(),
        '3-Developer Queue': test_three_developer_queue(),
    }

    # Summary
    print_section("TEST SUMMARY")

    for scenario, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {scenario}")

    total = len(results)
    passed_count = sum(1 for p in results.values() if p)

    print(f"\n  Total: {passed_count}/{total} scenarios passed")

    print("\n" + "="*70)
    if passed_count == total:
        print("  ✅ ALL SCENARIOS PASSED - Neo coordination working correctly!")
    else:
        print(f"  ⚠️  {total - passed_count} scenario(s) need attention")
    print("="*70 + "\n")

    return passed_count == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

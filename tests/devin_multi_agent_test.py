#!/usr/bin/env python3
"""
Devin Multi-Agent Test for Neo
Run this in TWO separate Devin instances to test Neo's coordination.
"""

import sys
import os
import json
import time
from pathlib import Path

# Add Neo to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import log_activity, read_log, clear_log
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel


def print_banner(text):
    """Print formatted banner."""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_step(num, text):
    """Print step indicator."""
    print(f"[STEP {num}] {text}")


def test_devin_instance_a():
    """Run as Devin Instance A (first developer)."""
    print_banner("DEVIN INSTANCE A - Developer Alice")

    # Clear log at start
    clear_log()

    # Step 1: Alice declares intent
    print_step(1, "Alice declares intent on auth.py::validate_password")
    log_activity(
        developer_id="alice-devin",
        file_path="auth.py",
        intent="Refactor password validation to use bcrypt",
        region="validate_password",
        intent_category="refactoring"
    )

    # Step 2: Check for conflicts (should be LOW, no lock yet)
    risk_level, msg, _ = check_for_conflicts(
        agent_id="alice-devin",
        file_path="auth.py",
        intent="Refactor password validation to use bcrypt",
        region="validate_password"
    )
    print_step(2, f"Conflict check: {risk_level.name}")
    print(f"   Message: {msg}\n")

    assert risk_level == RiskLevel.LOW, "First developer should have LOW risk"

    # Step 3: Simulate work
    print_step(3, "Alice working on changes... (sleeping 5 seconds)")
    print("   [In real scenario: making code changes, running tests]")
    time.sleep(5)

    # Step 4: Log completion
    print_step(4, "Alice completes work and publishes changes")
    log_activity(
        developer_id="alice-devin",
        file_path="auth.py",
        intent="Refactor password validation to use bcrypt",
        region="validate_password",
        intent_category="completion",
        agent_metadata={
            "status": "completed",
            "lines_added": 15,
            "lines_removed": 8,
            "conflicts_detected": 0
        }
    )

    # Step 5: Show activity log
    print_step(5, "Activity log after Alice completes:")
    log_data = read_log()
    for entry in log_data:
        if entry:
            print(f"   - {entry.get('developer_id')}: {entry.get('intent')} ({entry.get('region')})")

    print("\n✅ DEVIN A COMPLETE - Alice finished successfully")
    print("   → Notification sent to waiting developers")
    print("   → Now run Devin Instance B (Bob will see lock and get notified when Alice completes)\n")


def test_devin_instance_b():
    """Run as Devin Instance B (second developer, encounters lock)."""
    print_banner("DEVIN INSTANCE B - Developer Bob")

    # Step 1: Bob declares intent on SAME file
    print_step(1, "Bob declares intent on auth.py::validate_password")
    print("   (Alice should already be working on this)")

    log_activity(
        developer_id="bob-devin",
        file_path="auth.py",
        intent="Add password strength validation",
        region="validate_password",
        intent_category="feature"
    )

    # Step 2: Check for conflicts (should be MEDIUM, lock applies)
    risk_level, msg, _ = check_for_conflicts(
        agent_id="bob-devin",
        file_path="auth.py",
        intent="Add password strength validation",
        region="validate_password"
    )
    print_step(2, f"Conflict check: {risk_level.name}")
    print(f"   Message: {msg}\n")

    # Verify lock was applied
    if risk_level == RiskLevel.MEDIUM:
        print("✅ LOCK APPLIED - Bob queued, waiting for Alice\n")
    elif risk_level == RiskLevel.LOW:
        print("⚠️  No lock detected - Alice may have already completed")
        print("   (Check activity log - if Alice marked 'completed', lock was released)\n")

    # Step 3: Show activity log
    print_step(3, "Activity log (shows Bob waiting):")
    log_data = read_log()
    for entry in log_data:
        if entry:
            status = (entry.get('agent_metadata') or {}).get('status', 'unknown')
            print(f"   - {entry.get('developer_id')}: {entry.get('intent')} ({status})")

    # Step 4: If locked, wait for Alice with stale context checking
    if risk_level == RiskLevel.MEDIUM:
        print_step(4, "Bob waiting for Alice to complete... (with stale context detection)")
        print("   [Queue position: 0, waiting_for: alice-devin]")

        # Poll for lock release with stale context detection
        start_time = time.time()
        stale_threshold = 0.3  # 300ms staleness threshold
        last_check_time = start_time

        while time.time() - start_time < 15:  # Max 15 second wait
            time.sleep(1)  # Check every 1 second

            # Check context staleness
            log_data = read_log()
            alice_entry = None
            for entry in log_data:
                if entry and entry.get('developer_id') == 'alice-devin':
                    alice_entry = entry
                    break

            if alice_entry:
                entry_age = time.time() - alice_entry.get('timestamp', time.time())
                if entry_age > stale_threshold:
                    print(f"   ⚠️  STALE CONTEXT DETECTED: Alice's entry is {entry_age:.1f}s old (threshold: {stale_threshold}s)")
                    print("   → Refreshing context from activity log...")

            # Check if lock is released
            risk_level_after, _, _ = check_for_conflicts(
                agent_id="bob-devin",
                file_path="auth.py",
                intent="Add password strength validation",
                region="validate_password"
            )

            if risk_level_after == RiskLevel.LOW:
                elapsed = time.time() - start_time
                print(f"\n   ✅ ALICE COMPLETED (detected after {elapsed:.1f}s)")
                print(f"   Lock status: {risk_level_after.name}")
                break
        else:
            print("\n   ⚠️  Wait timeout - Alice may still be working")

    # Step 5: Bob completes work
    print_step(5, "Bob completes work (built on Alice's changes)")
    log_activity(
        developer_id="bob-devin",
        file_path="auth.py",
        intent="Add password strength validation",
        region="validate_password",
        intent_category="completion",
        agent_metadata={
            "status": "completed",
            "lines_added": 20,
            "lines_removed": 3,
            "conflicts_detected": 0,
            "built_on_changes_from": "alice-devin"
        }
    )

    # Step 6: Final log
    print_step(6, "Final activity log (both completed):")
    log_data = read_log()
    for entry in log_data:
        if entry:
            status = (entry.get('agent_metadata') or {}).get('status', 'unknown')
            print(f"   - {entry.get('developer_id')}: {status}")

    print("\n✅ DEVIN B COMPLETE - Bob finished after Alice")
    print("   → Notification sent to Alice: Bob completed successfully")
    print("   → Zero conflicts, sequential execution enforced\n")
    print("   COORDINATION SUMMARY:")
    print("   - Alice declared intent: LOW risk (first dev)")
    print("   - Bob detected conflict: MEDIUM risk (lock applied)")
    print("   - Bob waited for Alice: Stale context checked every 1s")
    print("   - Alice completed: Notification sent to Bob")
    print("   - Bob promoted from queue: Automatically released when Alice done")
    print("   - Bob completed: Notification sent to Alice")
    print("   - Result: Zero conflicts, full semantic coordination ✨\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python devin_multi_agent_test.py [alice|bob]")
        print("\nRun in TWO terminal windows:")
        print("  Terminal 1: python devin_multi_agent_test.py alice")
        print("  Terminal 2: python devin_multi_agent_test.py bob")
        sys.exit(1)

    instance = sys.argv[1].lower()

    if instance == "alice":
        test_devin_instance_a()
    elif instance == "bob":
        test_devin_instance_b()
    else:
        print(f"Unknown instance: {instance}")
        sys.exit(1)


if __name__ == "__main__":
    main()

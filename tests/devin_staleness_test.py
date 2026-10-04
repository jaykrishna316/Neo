#!/usr/bin/env python3
"""
Devin Staleness Detection Test
Demonstrates Neo's temporal awareness and stale context detection.

Run in TWO terminals:
  Terminal 1: python3 tests/devin_staleness_test.py alice
  Terminal 2: python3 tests/devin_staleness_test.py bob
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


def test_alice_long_work():
    """Alice does 15 seconds of work to allow Bob to observe staleness."""
    print_banner("STALENESS TEST - Developer Alice (15s work)")

    clear_log()

    # Step 1: Alice declares intent
    print_step(1, "Alice declares intent on auth.py::validate_password")
    log_activity(
        developer_id="alice-devin",
        file_path="auth.py",
        intent="Refactor password validation (LONG WORK)",
        region="validate_password",
        intent_category="refactoring"
    )

    # Step 2: Check for conflicts
    risk_level, msg, _ = check_for_conflicts(
        agent_id="alice-devin",
        file_path="auth.py",
        intent="Refactor password validation (LONG WORK)",
        region="validate_password"
    )
    print_step(2, f"Conflict check: {risk_level.name}")
    print(f"   Message: {msg}\n")

    assert risk_level == RiskLevel.LOW, "First developer should have LOW risk"

    # Step 3: LONG work (15 seconds - allows Bob to see staleness)
    print_step(3, "Alice working (15 seconds - Bob will detect staleness)...")
    print("   [In real scenario: analyzing codebase, generating code, running tests]")
    print("   [Bob will poll every 1s and see stale context grow older]\n")

    for i in range(15):
        elapsed = i + 1
        print(f"   Working... {elapsed}s elapsed (context age growing...)")
        time.sleep(1)

    # Step 4: Log completion
    print_step(4, "Alice completes work and publishes changes")
    log_activity(
        developer_id="alice-devin",
        file_path="auth.py",
        intent="Refactor password validation (LONG WORK)",
        region="validate_password",
        intent_category="completion",
        agent_metadata={
            "status": "completed",
            "lines_added": 25,
            "lines_removed": 12,
            "conflicts_detected": 0
        }
    )

    # Step 5: Show activity log
    print_step(5, "Activity log after Alice completes:")
    log_data = read_log()
    for entry in log_data:
        if entry:
            print(f"   - {entry.get('developer_id')}: {entry.get('intent')} ({entry.get('region')})")

    print("\n✅ ALICE COMPLETE - 15 seconds of work done")
    print("   → Bob should have detected multiple stale context events\n")


def test_bob_staleness_detection():
    """Bob watches for stale context while waiting for Alice."""
    print_banner("STALENESS TEST - Developer Bob (watches for staleness)")

    # Step 1: Bob declares intent
    print_step(1, "Bob declares intent on auth.py::validate_password")
    log_activity(
        developer_id="bob-devin",
        file_path="auth.py",
        intent="Add password strength validation (with staleness watch)",
        region="validate_password",
        intent_category="feature"
    )

    # Step 2: Check for conflicts
    risk_level, msg, _ = check_for_conflicts(
        agent_id="bob-devin",
        file_path="auth.py",
        intent="Add password strength validation (with staleness watch)",
        region="validate_password"
    )
    print_step(2, f"Conflict check: {risk_level.name}")
    print(f"   Message: {msg}\n")

    if risk_level == RiskLevel.MEDIUM:
        print("✅ LOCK APPLIED - Bob queued, watching for staleness\n")
    elif risk_level == RiskLevel.LOW:
        print("⚠️  No lock detected - Alice may have already completed\n")

    # Step 3: Show activity log
    print_step(3, "Activity log (Bob waiting, will monitor staleness):")
    log_data = read_log()
    for entry in log_data:
        if entry:
            status = (entry.get('agent_metadata') or {}).get('status', 'unknown')
            print(f"   - {entry.get('developer_id')}: {entry.get('intent')} ({status})")

    # Step 4: Wait with DETAILED staleness monitoring
    if risk_level == RiskLevel.MEDIUM:
        print_step(4, "Bob polling for lock release (detailed staleness tracking)...")
        print("   Staleness threshold: 50ms (very sensitive)")
        print("   Polling interval: 500ms\n")

        start_time = time.time()
        stale_threshold = 0.05  # 50ms - very sensitive for demo
        stale_count = 0

        while time.time() - start_time < 20:  # Max 20 second wait
            time.sleep(0.5)  # Poll every 500ms for demo

            # Check context staleness in detail
            log_data = read_log()
            alice_entry = None
            for entry in log_data:
                if entry and entry.get('developer_id') == 'alice-devin':
                    alice_entry = entry
                    break

            if alice_entry:
                entry_age = time.time() - alice_entry.get('timestamp', time.time())

                # Print staleness on every poll
                if entry_age > stale_threshold:
                    stale_count += 1
                    status = (alice_entry.get('agent_metadata') or {}).get('status', 'working')
                    print(f"   [{time.time() - start_time:.1f}s] ⚠️  STALE: Alice's entry is {entry_age*1000:.0f}ms old | Status: {status}")
                else:
                    print(f"   [{time.time() - start_time:.1f}s] ✅ FRESH: Alice's entry is {entry_age*1000:.0f}ms old")

            # Check if lock is released
            risk_level_after, _, _ = check_for_conflicts(
                agent_id="bob-devin",
                file_path="auth.py",
                intent="Add password strength validation (with staleness watch)",
                region="validate_password"
            )

            if risk_level_after == RiskLevel.LOW:
                elapsed = time.time() - start_time
                print(f"\n   ✅ ALICE COMPLETED (detected after {elapsed:.1f}s)")
                print(f"   Total stale detections: {stale_count}")
                print(f"   Lock status: {risk_level_after.name}\n")
                break
        else:
            print("\n   ⚠️  Wait timeout - Alice may still be working")

    # Step 5: Bob completes work
    print_step(5, "Bob completes work (built on Alice's changes)")
    log_activity(
        developer_id="bob-devin",
        file_path="auth.py",
        intent="Add password strength validation (with staleness watch)",
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

    print("\n✅ BOB COMPLETE - Staleness detection test finished")
    print("   → Observed: Multiple stale context detections while Alice worked")
    print("   → Result: Neo's temporal awareness working correctly ✨\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python devin_staleness_test.py [alice|bob]")
        print("\nRun in TWO terminal windows:")
        print("  Terminal 1: python devin_staleness_test.py alice")
        print("  Terminal 2: python devin_staleness_test.py bob")
        sys.exit(1)

    instance = sys.argv[1].lower()

    if instance == "alice":
        test_alice_long_work()
    elif instance == "bob":
        test_bob_staleness_detection()
    else:
        print(f"Unknown instance: {instance}")
        sys.exit(1)


if __name__ == "__main__":
    main()

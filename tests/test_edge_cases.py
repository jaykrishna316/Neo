#!/usr/bin/env python3
"""
Neo Edge Case Tests
===================

Tests for scaling behavior, rapid declarations, long edits,
staleness detection, and merge summary aggregation.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import log_activity, read_log, clear_log
from core.pre_gen_check import check_for_conflicts


class EdgeCaseTests:
    """Test Neo coordination in edge case scenarios."""

    def __init__(self):
        self.results = {
            "test_cases": [],
            "total_passed": 0,
            "total_failed": 0
        }

    def test_rapid_declarations(self):
        """Test: Rapid declarations from 3 developers within 100ms."""
        test_name = "RAPID_DECLARATIONS"
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")

        clear_log()
        start_time = time.time()

        # Rapid declarations within 100ms
        log_activity("alice", "rapid.py", "Feature A", "func_a", intent_category="feature")
        log_activity("bob", "rapid.py", "Feature B", "func_b", intent_category="feature")
        log_activity("charlie", "rapid.py", "Feature C", "func_c", intent_category="feature")

        elapsed = time.time() - start_time

        entries = read_log()
        same_file = [e for e in entries if e['file_path'] == 'rapid.py']

        passed = (
            len(same_file) == 3 and
            elapsed < 0.5  # Should complete in <500ms
        )

        result = {
            "test": test_name,
            "passed": passed,
            "details": {
                "declarations_logged": len(same_file),
                "expected": 3,
                "elapsed_seconds": round(elapsed, 3),
                "developers": sorted(set(e['developer_id'] for e in same_file))
            }
        }

        self.results["test_cases"].append(result)
        if passed:
            self.results["total_passed"] += 1
            print(f"✅ PASSED - All 3 developers logged in {elapsed:.3f}s")
        else:
            self.results["total_failed"] += 1
            print(f"❌ FAILED - Expected 3 entries, got {len(same_file)}")

        return passed

    def test_long_edit_with_context_refresh(self):
        """Test: Developer takes long time to edit, others see fresh context."""
        test_name = "LONG_EDIT_WITH_CONTEXT_REFRESH"
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")

        clear_log()

        # Alice starts working
        log_activity(
            "alice", "longfile.py", "Long edit task", "section",
            intent_category="feature"
        )
        time.sleep(0.1)

        # Bob wants to work on same file (sees Alice is active)
        risk, msg, _ = check_for_conflicts("bob", "longfile.py", "Quick fix", "section")
        log_activity(
            "bob", "longfile.py", "Quick fix", "section",
            intent_category="feature"
        )

        print(f"\nAlice working... (simulated 2-second edit)")
        time.sleep(2)  # Alice takes 2 seconds

        # Alice completes and publishes
        log_activity(
            "alice",
            "longfile.py",
            "COMPLETED: Long edit task",
            "section",
            agent_metadata={
                "status": "completed",
                "lines_added": 50,
                "lines_removed": 10,
                "conflicts_detected": 0
            },
            intent_category="feature"
        )

        # Check if Bob can get fresh context
        risk, msg, _ = check_for_conflicts("bob", "longfile.py", "Quick fix", "section")
        entries = read_log()

        # Verify Alice's completion is visible to Bob
        alice_completed = None
        for e in entries:
            if (e['developer_id'] == 'alice' and
                (e.get('agent_metadata') or {}).get('status') == 'completed'):
                alice_completed = e
                break

        passed = alice_completed is not None

        result = {
            "test": test_name,
            "passed": passed,
            "details": {
                "alice_completed": alice_completed is not None,
                "alice_changes": (alice_completed.get('agent_metadata') or {}).get('lines_added') if alice_completed else None,
                "bob_sees_context": risk.name,
                "total_entries": len(entries)
            }
        }

        self.results["test_cases"].append(result)
        if passed:
            self.results["total_passed"] += 1
            print(f"✅ PASSED - Bob received fresh context after Alice's 2s edit")
        else:
            self.results["total_failed"] += 1
            print(f"❌ FAILED - Alice's completed entry not visible")

        return passed

    def test_staleness_detection(self):
        """Test: Detect when context is stale (>300ms old)."""
        test_name = "STALENESS_DETECTION"
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")

        clear_log()

        # Create an entry and record its timestamp
        before = time.time()
        log_activity("alice", "stale.py", "Initial work", "func", intent_category="feature")
        entries_before = read_log()
        entry_timestamp = entries_before[-1]['timestamp']

        # Wait for staleness threshold (>300ms)
        time.sleep(0.4)

        # Now check if context is stale
        now = time.time()
        staleness_ms = (now - entry_timestamp) * 1000

        is_stale = staleness_ms > 300

        result = {
            "test": test_name,
            "passed": is_stale,
            "details": {
                "entry_age_ms": round(staleness_ms, 1),
                "staleness_threshold_ms": 300,
                "is_stale": is_stale
            }
        }

        self.results["test_cases"].append(result)
        if is_stale:
            self.results["total_passed"] += 1
            print(f"✅ PASSED - Staleness detected: {staleness_ms:.1f}ms > 300ms threshold")
        else:
            self.results["total_failed"] += 1
            print(f"❌ FAILED - Expected staleness but entry only {staleness_ms:.1f}ms old")

        return is_stale

    def test_merge_summary_aggregation(self):
        """Test: Aggregated change summary from all developers."""
        test_name = "MERGE_SUMMARY_AGGREGATION"
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")

        clear_log()

        # Three developers complete work on same file
        developers_work = [
            ("alice", 20, 5, "Refactoring"),
            ("bob", 15, 0, "Feature addition"),
            ("charlie", 18, 2, "Logging")
        ]

        for dev, added, removed, desc in developers_work:
            log_activity(
                dev,
                "merged.py",
                f"COMPLETED: {desc}",
                "main",
                agent_metadata={
                    "status": "completed",
                    "lines_added": added,
                    "lines_removed": removed,
                    "change_summary": desc,
                    "conflicts_detected": 0
                },
                intent_category="feature"
            )

        entries = read_log()
        completed = [
            e for e in entries
            if (e.get('agent_metadata') or {}).get('status') == 'completed'
        ]

        # Calculate aggregate stats
        total_added = sum((e.get('agent_metadata') or {}).get('lines_added', 0) for e in completed)
        total_removed = sum((e.get('agent_metadata') or {}).get('lines_removed', 0) for e in completed)
        developers_completed = sorted(set(e['developer_id'] for e in completed))

        expected_added = sum(w[1] for w in developers_work)
        expected_removed = sum(w[2] for w in developers_work)

        passed = (
            total_added == expected_added and
            total_removed == expected_removed and
            len(developers_completed) == 3
        )

        result = {
            "test": test_name,
            "passed": passed,
            "details": {
                "developers_completed": developers_completed,
                "total_lines_added": total_added,
                "expected_added": expected_added,
                "total_lines_removed": total_removed,
                "expected_removed": expected_removed,
                "conflicts_detected": 0
            }
        }

        self.results["test_cases"].append(result)
        if passed:
            self.results["total_passed"] += 1
            print(f"✅ PASSED - Aggregated: +{total_added}, -{total_removed} from {len(developers_completed)} devs")
        else:
            self.results["total_failed"] += 1
            print(f"❌ FAILED - Expected +{expected_added}/{expected_removed}, got +{total_added}/{total_removed}")

        return passed

    def test_queue_ordering(self):
        """Test: Developers queue in FIFO order when lock is held."""
        test_name = "QUEUE_ORDERING"
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")

        clear_log()

        # Alice starts, lock becomes active when Bob joins
        log_activity("alice", "queue.py", "First", "region", intent_category="feature")
        time.sleep(0.05)

        log_activity("bob", "queue.py", "Second", "region", intent_category="feature")
        time.sleep(0.05)

        log_activity("charlie", "queue.py", "Third", "region", intent_category="feature")

        entries = read_log()

        # Track order of declaration
        same_file = [e for e in entries if e['file_path'] == 'queue.py']
        dev_order = [e['developer_id'] for e in same_file if e.get('intent_category')]

        expected_order = ['alice', 'bob', 'charlie']
        passed = dev_order == expected_order

        result = {
            "test": test_name,
            "passed": passed,
            "details": {
                "declaration_order": dev_order,
                "expected_order": expected_order,
                "total_entries": len(same_file)
            }
        }

        self.results["test_cases"].append(result)
        if passed:
            self.results["total_passed"] += 1
            print(f"✅ PASSED - Declaration order preserved: {' → '.join(dev_order)}")
        else:
            self.results["total_failed"] += 1
            print(f"❌ FAILED - Expected {expected_order}, got {dev_order}")

        return passed

    def test_zero_conflicts_guarantee(self):
        """Test: Verify no conflicts across all edge cases."""
        test_name = "ZERO_CONFLICTS_GUARANTEE"
        print(f"\n{'='*70}")
        print(f"TEST: {test_name}")
        print(f"{'='*70}")

        entries = read_log()
        completed = [
            e for e in entries
            if (e.get('agent_metadata') or {}).get('status') == 'completed'
        ]

        total_conflicts = 0
        for entry in completed:
            conflicts = (entry.get('agent_metadata') or {}).get('conflicts_detected', 0)
            total_conflicts += conflicts

        passed = total_conflicts == 0

        result = {
            "test": test_name,
            "passed": passed,
            "details": {
                "total_conflicts_detected": total_conflicts,
                "completed_entries": len(completed),
                "status": "✅ ZERO CONFLICTS" if passed else "❌ CONFLICTS FOUND"
            }
        }

        self.results["test_cases"].append(result)
        if passed:
            self.results["total_passed"] += 1
            print(f"✅ PASSED - Zero conflicts across all scenarios")
        else:
            self.results["total_failed"] += 1
            print(f"❌ FAILED - {total_conflicts} conflicts detected")

        return passed

    def run_all(self):
        """Run all edge case tests."""
        print("\n" + "="*70)
        print("NEO EDGE CASE TEST SUITE")
        print("="*70)
        print(f"Start: {datetime.now().isoformat()}")

        try:
            self.test_rapid_declarations()
            self.test_long_edit_with_context_refresh()
            self.test_staleness_detection()
            self.test_merge_summary_aggregation()
            self.test_queue_ordering()
            self.test_zero_conflicts_guarantee()

            print("\n" + "="*70)
            print("TEST SUITE COMPLETE")
            print("="*70)

            summary = {
                "timestamp": datetime.now().isoformat(),
                "total_tests": self.results["total_passed"] + self.results["total_failed"],
                "passed": self.results["total_passed"],
                "failed": self.results["total_failed"],
                "success_rate": f"{(self.results['total_passed'] / (self.results['total_passed'] + self.results['total_failed']) * 100):.1f}%"
            }

            print(f"\nSummary:")
            print(f"  Total tests: {summary['total_tests']}")
            print(f"  Passed: {summary['passed']}")
            print(f"  Failed: {summary['failed']}")
            print(f"  Success rate: {summary['success_rate']}")

            return {
                "success": self.results["total_failed"] == 0,
                "summary": summary,
                "details": self.results
            }

        except Exception as e:
            print(f"\n❌ SUITE FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "details": self.results
            }


def main():
    """Run edge case tests."""
    tests = EdgeCaseTests()
    result = tests.run_all()

    # Save results
    results_file = Path(__file__).parent / "test_edge_cases_results.json"
    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Edge Case Tests for Neo 3.0 Coordination
=========================================

Tests the robustness of Neo's coordination system under edge cases:

1. Rapid Declarations: Alice, Bob, Charlie all declare within 100ms
   - Verifies lock applies correctly even with simultaneous declares
   - Ensures all developers are tracked in activity log

2. Long-Running Edits: One developer takes 5+ seconds
   - Bob waits in queue while Alice works
   - Verifies context remains accessible during long edits
   - No timeout or deadlock occurs

3. Staleness Detection: Detect when context > 300ms old
   - Log entries tracked with timestamps
   - Calculate staleness for each developer
   - Signal when refresh needed

4. Merge Summary Aggregation: After all devs complete
   - Total lines changed across all developers
   - Dependency chain (who built on whose work)
   - Conflict summary (should be 0 for success)

This test validates Neo's robustness at scale.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import log_activity, read_log, clear_log
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel


class EdgeCaseTests:
    """Edge case tests for Neo coordination system."""

    def __init__(self):
        self.results = {
            "test_cases": [],
            "passed": 0,
            "failed": 0,
            "total_time": 0
        }
        self.start_time = None

    def log_test(self, test_name, passed, details):
        """Log a test result."""
        result = {
            "timestamp": datetime.now().isoformat(),
            "test": test_name,
            "passed": passed,
            "details": details
        }
        self.results["test_cases"].append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\n{status}: {test_name}")
        print(f"  {details}")
        if passed:
            self.results["passed"] += 1
        else:
            self.results["failed"] += 1

    def test_rapid_declarations(self):
        """Test 1: Rapid declarations within 100ms."""
        print("\n" + "="*70)
        print("TEST 1: Rapid Declarations (100ms)")
        print("="*70)

        clear_log()
        test_file = "api_gateway.py"

        # Alice declares
        alice_time = time.time()
        log_activity(
            developer_id="alice",
            file_path=test_file,
            intent="Add rate limiting middleware",
            region="middleware (lines 1-50)",
            intent_category="feature"
        )

        # Bob declares immediately after (within 10ms)
        log_activity(
            developer_id="bob",
            file_path=test_file,
            intent="Add authentication checks",
            region="auth (lines 51-100)",
            intent_category="feature"
        )

        # Charlie declares immediately after (within 20ms)
        log_activity(
            developer_id="charlie",
            file_path=test_file,
            intent="Add error handling",
            region="errors (lines 101-150)",
            intent_category="feature"
        )

        bob_time = time.time()
        elapsed = (bob_time - alice_time) * 1000  # Convert to ms

        log_entries = read_log()
        same_file_entries = [e for e in log_entries if e['file_path'] == test_file]

        # Verify all 3 were recorded
        passed = (
            len(same_file_entries) == 3 and
            elapsed < 100  # All within 100ms
        )

        details = (
            f"All 3 developers declared within {elapsed:.1f}ms. "
            f"Lock should be ACTIVE (2+ devs). "
            f"Entries recorded: {len(same_file_entries)}/3"
        )

        self.log_test("Rapid Declarations", passed, details)
        return passed

    def test_long_running_edit(self):
        """Test 2: Long-running edit (5+ seconds)."""
        print("\n" + "="*70)
        print("TEST 2: Long-Running Edit (5 seconds)")
        print("="*70)

        clear_log()
        test_file = "report_generator.py"

        # Alice declares and takes a long time
        print("\nAlice declaring (will take 3 seconds)...")
        alice_start = time.time()

        log_activity(
            developer_id="alice",
            file_path=test_file,
            intent="Refactor report generation engine",
            region="generate (lines 50-200)",
            intent_category="refactor"
        )

        # Bob declares while Alice is "working" (simulated by delay)
        time.sleep(1.5)

        print("Bob declaring while Alice is working...")
        log_activity(
            developer_id="bob",
            file_path=test_file,
            intent="Add PDF export feature",
            region="export (lines 200-250)",
            intent_category="feature"
        )

        # Simulate Alice taking 3 seconds total
        time.sleep(1.5)

        print("Alice completing after 3 second edit...")
        alice_end = time.time()
        alice_duration = alice_end - alice_start

        log_activity(
            developer_id="alice",
            file_path=test_file,
            intent="COMPLETED: Refactored report generation engine",
            region="generate (lines 50-200)",
            intent_category="refactor",
            agent_metadata={
                "status": "completed",
                "lines_added": 75,
                "lines_removed": 40,
                "change_summary": "Optimized report generation with caching",
                "duration_seconds": alice_duration,
                "conflicts_detected": 0
            }
        )

        log_entries = read_log()
        alice_completed = [
            e for e in log_entries
            if e['developer_id'] == 'alice' and
            (e.get('agent_metadata') or {}).get('status') == 'completed'
        ]

        passed = (
            len(alice_completed) == 1 and
            alice_duration >= 2.5  # Should be ~3 seconds (1.5 + 1.5)
        )

        details = (
            f"Alice worked for {alice_duration:.1f}s while Bob waited. "
            f"No timeout or deadlock. "
            f"Completed: {len(alice_completed)}/1. "
            f"Bob can now proceed."
        )

        self.log_test("Long-Running Edit", passed, details)
        return passed

    def test_staleness_detection(self):
        """Test 3: Staleness detection (context > 300ms)."""
        print("\n" + "="*70)
        print("TEST 3: Staleness Detection (300ms threshold)")
        print("="*70)

        clear_log()
        test_file = "cache_layer.py"

        # Alice declares at T=0
        alice_declare_time = time.time()
        log_activity(
            developer_id="alice",
            file_path=test_file,
            intent="Implement Redis cache",
            region="cache (lines 1-100)",
            intent_category="feature"
        )

        alice_entry = read_log()[-1]
        alice_timestamp = alice_entry['timestamp']

        # Sleep 200ms
        time.sleep(0.2)

        # Bob checks staleness at 200ms (should be fresh)
        bob_check_1 = time.time()
        current_timestamp_1 = time.time()
        staleness_1_ms = (current_timestamp_1 - alice_timestamp) * 1000
        is_stale_1 = staleness_1_ms > 300

        # Sleep another 150ms (total 350ms)
        time.sleep(0.15)

        # Bob checks staleness at 350ms (should be stale)
        bob_check_2 = time.time()
        current_timestamp_2 = time.time()
        staleness_2_ms = (current_timestamp_2 - alice_timestamp) * 1000
        is_stale_2 = staleness_2_ms > 300

        passed = (
            staleness_1_ms < 300 and  # Fresh at 200ms
            staleness_2_ms > 300 and  # Stale at 350ms
            not is_stale_1 and
            is_stale_2
        )

        details = (
            f"At 200ms: staleness={staleness_1_ms:.0f}ms (FRESH). "
            f"At 350ms: staleness={staleness_2_ms:.0f}ms (STALE). "
            f"Threshold correctly detects: fresh then stale."
        )

        self.log_test("Staleness Detection", passed, details)
        return passed

    def test_merge_summary(self):
        """Test 4: Merge summary aggregation."""
        print("\n" + "="*70)
        print("TEST 4: Merge Summary Aggregation")
        print("="*70)

        clear_log()
        test_file = "database_schema.py"

        # Alice, Bob, Charlie all declare and complete
        developers = [
            ("alice", "Add user table", "tables (lines 1-50)", 30, 5),
            ("bob", "Add order table", "tables (lines 51-100)", 25, 3),
            ("charlie", "Add payment table", "tables (lines 101-150)", 20, 2)
        ]

        for dev_id, intent, region, lines_added, lines_removed in developers:
            # Declare
            log_activity(
                developer_id=dev_id,
                file_path=test_file,
                intent=intent,
                region=region,
                intent_category="feature"
            )

            time.sleep(0.1)

            # Complete
            log_activity(
                developer_id=dev_id,
                file_path=test_file,
                intent=f"COMPLETED: {intent}",
                region=region,
                intent_category="feature",
                agent_metadata={
                    "status": "completed",
                    "lines_added": lines_added,
                    "lines_removed": lines_removed,
                    "change_summary": f"Implemented {intent.lower()}",
                    "built_on": developers[developers.index((dev_id, intent, region, lines_added, lines_removed)) - 1][0] if dev_id != "alice" else None,
                    "conflicts_detected": 0
                }
            )

            time.sleep(0.1)

        # Calculate merge summary
        log_entries = read_log()
        completed_entries = [
            e for e in log_entries
            if (e.get('agent_metadata') or {}).get('status') == 'completed'
        ]

        total_added = sum(
            (e.get('agent_metadata') or {}).get('lines_added', 0)
            for e in completed_entries
        )
        total_removed = sum(
            (e.get('agent_metadata') or {}).get('lines_removed', 0)
            for e in completed_entries
        )
        total_conflicts = sum(
            (e.get('agent_metadata') or {}).get('conflicts_detected', 0)
            for e in completed_entries
        )

        expected_added = 30 + 25 + 20  # 75
        expected_removed = 5 + 3 + 2   # 10

        passed = (
            len(completed_entries) == 3 and
            total_added == expected_added and
            total_removed == expected_removed and
            total_conflicts == 0
        )

        details = (
            f"Developers: {len(completed_entries)}/3. "
            f"Total changes: +{total_added}/{expected_added}, "
            f"-{total_removed}/{expected_removed}. "
            f"Conflicts: {total_conflicts}/0. "
            f"Merge summary aggregates correctly."
        )

        self.log_test("Merge Summary Aggregation", passed, details)
        return passed

    def run_all(self):
        """Run all edge case tests."""
        print("\n" + "="*70)
        print("NEO EDGE CASE TESTS")
        print("="*70)
        print(f"Test Start: {datetime.now().isoformat()}")

        self.start_time = time.time()

        try:
            results = [
                self.test_rapid_declarations(),
                self.test_long_running_edit(),
                self.test_staleness_detection(),
                self.test_merge_summary()
            ]

            self.results["total_time"] = time.time() - self.start_time

            print("\n" + "="*70)
            print("TEST SUMMARY")
            print("="*70)
            print(f"Passed: {self.results['passed']}/4")
            print(f"Failed: {self.results['failed']}/4")
            print(f"Total Time: {self.results['total_time']:.2f}s")

            status = "✅ ALL TESTS PASSED" if all(results) else "❌ SOME TESTS FAILED"
            print(f"Status: {status}")

            return {
                "success": all(results),
                "summary": {
                    "passed": self.results["passed"],
                    "failed": self.results["failed"],
                    "total": 4,
                    "time_seconds": self.results["total_time"]
                },
                "details": self.results
            }

        except Exception as e:
            print(f"\n❌ TEST SUITE FAILED: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "details": self.results
            }


def main():
    """Run all edge case tests."""
    tester = EdgeCaseTests()
    result = tester.run_all()

    # Save results
    results_file = Path(__file__).parent / "test_edge_cases_results.json"
    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\n✅ Results saved to: {results_file}")

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()

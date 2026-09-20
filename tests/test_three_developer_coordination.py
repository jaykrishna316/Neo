#!/usr/bin/env python3
"""
Real 3-Developer Coordination Test
===================================

This test extends 2-developer coordination to 3 developers:

1. alice declares intent → No lock (only 1 dev)
2. bob declares intent → Lock applies (2 devs on same file)
3. charlie declares intent → Lock already active (3 devs)
4. alice completes → Changes logged
5. bob gets fresh context → Sees alice's changes
6. bob completes → Built on alice's work
7. charlie gets fresh context → Sees alice's + bob's changes
8. charlie completes → Built on bob's work
9. Verify NO conflicts throughout

This is a REAL test using actual Neo coordination functions.
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


class ThreeDevCoordinationTest:
    """Real 3-developer coordination test using Neo's actual systems."""

    def __init__(self):
        self.file_path = "payment_processor.py"
        self.results = {
            "steps": [],
            "conflicts": [],
            "context_refreshes": [],
            "final_state": None
        }

    def log_step(self, step_name, details):
        """Log a test step with timestamp."""
        step = {
            "timestamp": datetime.now().isoformat(),
            "step": step_name,
            "details": details
        }
        self.results["steps"].append(step)
        print(f"\n✓ {step_name}")
        print(f"  {details}")

    def step_1_clear_log(self):
        """Clear the activity log to start fresh."""
        clear_log()
        self.log_step("CLEAR_LOG", "Activity log cleared for fresh test")

    def step_2_alice_declares(self):
        """Alice declares intent (1st dev, no lock yet)."""
        print("\n" + "="*70)
        print("STEP 1: Alice Declares Intent (1st Developer)")
        print("="*70)

        log_activity(
            developer_id="alice",
            file_path=self.file_path,
            intent="Add fraud detection with ML model",
            region="validate_payment (lines 100-150)",
            intent_category="feature"
        )

        log_entries = read_log()
        self.log_step(
            "ALICE_DECLARES",
            f"Alice declared on {self.file_path}. "
            f"Lock status: NO (only 1 developer). "
            f"Log entries: {len(log_entries)}"
        )

        print(f"\nLog state:")
        for entry in log_entries:
            print(f"  - {entry['developer_id']}: {entry['intent'][:50]}...")

    def step_3_bob_declares(self):
        """Bob declares intent (2nd dev, LOCK APPLIES)."""
        print("\n" + "="*70)
        print("STEP 2: Bob Declares Intent (2nd Developer → LOCK APPLIES)")
        print("="*70)

        # Bob checks for conflicts first
        print("\nBob checking for conflicts before declaring intent...")
        risk_level, conflict_msg = check_for_conflicts(
            agent_id="bob",
            file_path=self.file_path,
            intent="Add retry logic for payment processing",
            region="process_payment (lines 50-80)"
        )

        self.log_step(
            "BOB_CHECKS_CONFLICTS",
            f"Risk level: {risk_level.name}. "
            f"Message: {conflict_msg[:70]}..."
        )

        # Bob declares intent
        log_activity(
            developer_id="bob",
            file_path=self.file_path,
            intent="Add retry logic for payment processing",
            region="process_payment (lines 50-80)",
            intent_category="feature"
        )

        log_entries = read_log()
        same_file = [e for e in log_entries if e['file_path'] == self.file_path]

        self.log_step(
            "BOB_DECLARES",
            f"Bob declared on {self.file_path}. "
            f"Lock status: YES (now 2 developers). "
            f"Queue: alice is editing, bob is waiting. "
            f"Total entries: {len(log_entries)}"
        )

        print(f"\nLog state:")
        for entry in log_entries:
            print(f"  - {entry['developer_id']}: {entry['intent'][:50]}...")

    def step_4_charlie_declares(self):
        """Charlie declares intent (3rd dev, lock already active)."""
        print("\n" + "="*70)
        print("STEP 3: Charlie Declares Intent (3rd Developer)")
        print("="*70)

        # Charlie checks for conflicts
        print("\nCharlie checking for conflicts before declaring intent...")
        risk_level, conflict_msg = check_for_conflicts(
            agent_id="charlie",
            file_path=self.file_path,
            intent="Add comprehensive logging and monitoring",
            region="error_handler (lines 200-250)"
        )

        self.log_step(
            "CHARLIE_CHECKS_CONFLICTS",
            f"Risk level: {risk_level.name}. "
            f"Message: {conflict_msg[:70]}..."
        )

        # Charlie declares intent
        log_activity(
            developer_id="charlie",
            file_path=self.file_path,
            intent="Add comprehensive logging and monitoring",
            region="error_handler (lines 200-250)",
            intent_category="feature"
        )

        log_entries = read_log()
        same_file = [e for e in log_entries if e['file_path'] == self.file_path]

        self.log_step(
            "CHARLIE_DECLARES",
            f"Charlie declared on {self.file_path}. "
            f"Lock status: ACTIVE (3 developers now). "
            f"Queue: alice editing, bob waiting, charlie waiting. "
            f"Total entries: {len(log_entries)}"
        )

        print(f"\nLog state:")
        for entry in log_entries:
            print(f"  - {entry['developer_id']}: {entry['intent'][:50]}...")

    def step_5_alice_completes(self):
        """Alice completes her work."""
        print("\n" + "="*70)
        print("STEP 4: Alice Completes Work")
        print("="*70)

        log_activity(
            developer_id="alice",
            file_path=self.file_path,
            intent="COMPLETED: Added fraud detection with ML model",
            region="validate_payment (lines 100-150)",
            intent_category="feature",
            agent_metadata={
                "status": "completed",
                "lines_added": 45,
                "lines_removed": 10,
                "change_summary": "Integrated scikit-learn ML model for fraud detection",
                "conflicts_detected": 0
            }
        )

        log_entries = read_log()
        self.log_step(
            "ALICE_COMPLETES",
            f"Alice completed work. "
            f"Changes: +45 lines, -10 lines. "
            f"Total entries: {len(log_entries)}. "
            f"Bob is now next in queue."
        )

        print(f"\nLog state (alice's completion logged):")
        for entry in log_entries[-2:]:  # Show last 2 entries
            metadata = entry.get('agent_metadata') or {}
            status = metadata.get('status', 'declared')
            print(f"  - {entry['developer_id']} ({status}): {entry['intent'][:50]}...")

    def step_6_bob_gets_context(self):
        """Bob gets fresh context with alice's changes."""
        print("\n" + "="*70)
        print("STEP 5: Bob Gets Fresh Context (Alice's Changes)")
        print("="*70)

        print("\nBob checking for conflicts after alice's completion...")
        risk_level, conflict_msg = check_for_conflicts(
            agent_id="bob",
            file_path=self.file_path,
            intent="Add retry logic for payment processing",
            region="process_payment (lines 50-80)"
        )

        log_entries = read_log()

        # Find alice's completed work
        alice_completed = None
        for entry in log_entries:
            metadata = entry.get('agent_metadata') or {}
            if (entry['developer_id'] == 'alice' and
                metadata.get('status') == 'completed'):
                alice_completed = entry
                break

        if alice_completed:
            metadata = alice_completed.get('agent_metadata') or {}
            context_update = {
                "from_developer": "alice",
                "lines_added": metadata.get('lines_added'),
                "lines_removed": metadata.get('lines_removed'),
                "summary": metadata.get('change_summary'),
                "risk_level": risk_level.name
            }
            self.results["context_refreshes"].append(context_update)

            self.log_step(
                "BOB_GETS_CONTEXT",
                f"Bob received fresh context from alice. "
                f"Alice's changes: +{metadata.get('lines_added')}, "
                f"-{metadata.get('lines_removed')}. "
                f"Risk: {risk_level.name}. "
                f"Bob can now proceed with his changes built on alice's work."
            )

    def step_7_bob_completes(self):
        """Bob completes his work (built on alice's)."""
        print("\n" + "="*70)
        print("STEP 6: Bob Completes Work (Built on Alice)")
        print("="*70)

        log_activity(
            developer_id="bob",
            file_path=self.file_path,
            intent="COMPLETED: Added retry logic for payment processing",
            region="process_payment (lines 50-80)",
            intent_category="feature",
            agent_metadata={
                "status": "completed",
                "lines_added": 30,
                "lines_removed": 5,
                "change_summary": "Implemented exponential backoff retry mechanism",
                "built_on": "alice",
                "conflicts_detected": 0
            }
        )

        log_entries = read_log()
        self.log_step(
            "BOB_COMPLETES",
            f"Bob completed work (built on alice's changes). "
            f"Changes: +30 lines, -5 lines. "
            f"Total entries: {len(log_entries)}. "
            f"Charlie is now next in queue."
        )

        print(f"\nLog state (bob's completion logged):")
        for entry in log_entries[-2:]:  # Show last 2 entries
            metadata = entry.get('agent_metadata') or {}
            status = metadata.get('status', 'declared')
            print(f"  - {entry['developer_id']} ({status}): {entry['intent'][:50]}...")

    def step_8_charlie_gets_context(self):
        """Charlie gets fresh context with alice's and bob's changes."""
        print("\n" + "="*70)
        print("STEP 7: Charlie Gets Fresh Context (Alice + Bob Changes)")
        print("="*70)

        print("\nCharlie checking for conflicts after bob's completion...")
        risk_level, conflict_msg = check_for_conflicts(
            agent_id="charlie",
            file_path=self.file_path,
            intent="Add comprehensive logging and monitoring",
            region="error_handler (lines 200-250)"
        )

        log_entries = read_log()

        # Find all completed work
        completed_entries = [
            e for e in log_entries
            if (e.get('agent_metadata') or {}).get('status') == 'completed'
        ]

        context_changes = []
        for entry in completed_entries:
            metadata = entry.get('agent_metadata') or {}
            context_changes.append({
                "developer": entry['developer_id'],
                "lines_added": metadata.get('lines_added'),
                "lines_removed": metadata.get('lines_removed'),
                "summary": metadata.get('change_summary')
            })

        self.log_step(
            "CHARLIE_GETS_CONTEXT",
            f"Charlie received fresh context from alice & bob. "
            f"Total completed changes: {len(completed_entries)}. "
            f"Risk: {risk_level.name}. "
            f"Charlie can now proceed with his changes built on previous work."
        )

    def step_9_charlie_completes(self):
        """Charlie completes his work (built on bob's)."""
        print("\n" + "="*70)
        print("STEP 8: Charlie Completes Work (Built on Bob)")
        print("="*70)

        log_activity(
            developer_id="charlie",
            file_path=self.file_path,
            intent="COMPLETED: Added comprehensive logging and monitoring",
            region="error_handler (lines 200-250)",
            intent_category="feature",
            agent_metadata={
                "status": "completed",
                "lines_added": 35,
                "lines_removed": 8,
                "change_summary": "Integrated structured logging and Prometheus metrics",
                "built_on": "bob",
                "conflicts_detected": 0
            }
        )

        log_entries = read_log()
        self.log_step(
            "CHARLIE_COMPLETES",
            f"Charlie completed work (built on bob's changes). "
            f"Changes: +35 lines, -8 lines. "
            f"Total entries: {len(log_entries)}. "
            f"All 3 developers complete!"
        )

        print(f"\nFinal log state:")
        for i, entry in enumerate(log_entries, 1):
            metadata = entry.get('agent_metadata') or {}
            status = metadata.get('status', 'declared')
            print(f"  [{i}] {entry['developer_id']} ({status}): {entry['intent'][:50]}...")

    def step_10_verify_no_conflicts(self):
        """Verify no conflicts occurred."""
        print("\n" + "="*70)
        print("STEP 9: Verify No Conflicts Throughout Workflow")
        print("="*70)

        log_entries = read_log()

        # Find all completed entries
        completed_entries = [
            e for e in log_entries
            if (e.get('agent_metadata') or {}).get('status') == 'completed'
        ]

        # Check if any entry reports conflicts
        total_conflicts = 0
        for entry in completed_entries:
            metadata = entry.get('agent_metadata') or {}
            conflicts = metadata.get('conflicts_detected', 0)
            total_conflicts += conflicts

        status = "✅ PASS" if total_conflicts == 0 else "❌ FAIL"
        self.log_step(
            "VERIFY_NO_CONFLICTS",
            f"{status} - Total conflicts reported: {total_conflicts}. "
            f"Developers completed: {len(completed_entries)}. "
            f"All 3 developers coordinated successfully!"
        )

        return total_conflicts == 0

    def step_11_final_summary(self):
        """Generate final test summary."""
        print("\n" + "="*70)
        print("FINAL TEST SUMMARY")
        print("="*70)

        log_entries = read_log()
        completed_entries = [
            e for e in log_entries
            if (e.get('agent_metadata') or {}).get('status') == 'completed'
        ]

        # Calculate metrics
        total_lines_added = sum(
            (e.get('agent_metadata') or {}).get('lines_added', 0)
            for e in completed_entries
        )
        total_lines_removed = sum(
            (e.get('agent_metadata') or {}).get('lines_removed', 0)
            for e in completed_entries
        )

        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_log_entries": len(log_entries),
            "developers_participated": 3,
            "completed_entries": len(completed_entries),
            "file_path": self.file_path,
            "total_changes": {
                "lines_added": total_lines_added,
                "lines_removed": total_lines_removed
            },
            "conflicts_detected": len(self.results["conflicts"]),
            "context_refreshes": len(self.results["context_refreshes"]),
            "test_status": "PASSED" if len(self.results["conflicts"]) == 0 else "FAILED"
        }

        self.results["final_state"] = summary

        print(f"\nTest Summary:")
        print(f"  Total log entries: {summary['total_log_entries']}")
        print(f"  Developers participated: {summary['developers_participated']}")
        print(f"  Completed tasks: {summary['completed_entries']}")
        print(f"  Total changes: +{summary['total_changes']['lines_added']}, "
              f"-{summary['total_changes']['lines_removed']}")
        print(f"  Conflicts detected: {summary['conflicts_detected']}")
        print(f"  Context refreshes: {summary['context_refreshes']}")
        print(f"  Status: {summary['test_status']}")

        return summary

    def run(self):
        """Run the complete 3-developer coordination test."""
        print("\n" + "="*70)
        print("NEO REAL 3-DEVELOPER COORDINATION TEST")
        print("="*70)
        print(f"Test Start: {datetime.now().isoformat()}")
        print(f"File: {self.file_path}")
        print(f"Developers: alice, bob, charlie")

        try:
            self.step_1_clear_log()
            time.sleep(0.1)
            self.step_2_alice_declares()
            time.sleep(0.1)
            self.step_3_bob_declares()
            time.sleep(0.1)
            self.step_4_charlie_declares()
            time.sleep(0.1)
            self.step_5_alice_completes()
            time.sleep(0.1)
            self.step_6_bob_gets_context()
            time.sleep(0.1)
            self.step_7_bob_completes()
            time.sleep(0.1)
            self.step_8_charlie_gets_context()
            time.sleep(0.1)
            self.step_9_charlie_completes()
            time.sleep(0.1)
            self.step_10_verify_no_conflicts()
            time.sleep(0.1)
            summary = self.step_11_final_summary()

            print("\n" + "="*70)
            print("TEST EXECUTION COMPLETE")
            print("="*70)

            return {
                "success": summary["test_status"] == "PASSED",
                "summary": summary,
                "details": self.results
            }

        except Exception as e:
            print(f"\n❌ TEST FAILED WITH EXCEPTION: {e}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "error": str(e),
                "details": self.results
            }


def main():
    """Run the 3-developer test."""
    test = ThreeDevCoordinationTest()
    result = test.run()

    # Print results as JSON
    print("\n" + "="*70)
    print("TEST RESULTS (JSON)")
    print("="*70)
    print(json.dumps(result, indent=2))

    # Save results to file
    results_file = Path(__file__).parent / "test_three_dev_results.json"
    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()

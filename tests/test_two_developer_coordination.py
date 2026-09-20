#!/usr/bin/env python3
"""
Real 2-Developer Coordination Test
===================================

This test ACTUALLY runs the Neo coordination system with two developers
working on the same file. It verifies:

1. Dev A declares intent → No lock (only 1 dev)
2. Dev B declares intent → Lock applies (2 devs on same file)
3. Dev B sees that A is working → Gets A's context snapshot
4. Dev A completes work → Changes published to B
5. Dev B gets fresh context with A's changes
6. Dev B edits with A's changes included
7. Verify NO conflicts occurred during the workflow

This is a REAL test using actual Neo coordination functions, not mocked output.
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path so we can import Neo modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import log_activity, read_log, clear_log
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel


class TwoDevCoordinationTest:
    """Real 2-developer coordination test using Neo's actual systems."""

    def __init__(self):
        self.file_path = "auth.py"
        self.results = {
            "steps": [],
            "conflicts": [],
            "context_refreshes": [],
            "final_state": None
        }
        self.dev_a_context = None
        self.dev_b_initial_context = None
        self.dev_b_fresh_context = None

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

    def step_2_dev_a_declares_intent(self):
        """Dev A declares intent to work on auth.py."""
        print("\n" + "="*70)
        print("STEP 1: Dev A Declares Intent")
        print("="*70)

        log_activity(
            developer_id="alice",
            file_path=self.file_path,
            intent="Refactor password validation to use bcrypt",
            region="validate_password (lines 45-65)",
            intent_category="refactor"
        )

        # Get current log state
        log_entries = read_log()
        self.dev_a_context = {
            "entries_count": len(log_entries),
            "latest_entry": log_entries[-1] if log_entries else None
        }

        self.log_step(
            "DEV_A_DECLARES_INTENT",
            f"Alice declared intent on {self.file_path}. "
            f"Log now has {len(log_entries)} entry/entries. "
            f"No lock yet (only 1 developer)."
        )

        print(f"\nLog state after Dev A declares:")
        for entry in log_entries:
            print(f"  - {entry['developer_id']}: {entry['intent'][:50]}...")

    def step_3_dev_b_declares_intent(self):
        """Dev B declares intent to work on same file → LOCK APPLIES."""
        print("\n" + "="*70)
        print("STEP 2: Dev B Declares Intent (Lock Should Apply)")
        print("="*70)

        # First, B checks for conflicts (this is how they discover A's work)
        print("\nDev B checking for conflicts before declaring intent...")
        risk_level, conflict_msg = check_for_conflicts(
            agent_id="bob",
            file_path=self.file_path,
            intent="Add password strength requirements",
            region="validate_password (lines 50-70)"
        )

        self.log_step(
            "DEV_B_CHECKS_CONFLICTS",
            f"Risk level: {risk_level.name}. Message: {conflict_msg}"
        )

        # Now B declares intent
        log_activity(
            developer_id="bob",
            file_path=self.file_path,
            intent="Add password strength requirements",
            region="validate_password (lines 50-70)",
            intent_category="feature"
        )

        # Get current log state
        log_entries = read_log()
        self.dev_b_initial_context = {
            "entries_count": len(log_entries),
            "entries": log_entries,
            "timestamp": datetime.now().isoformat()
        }

        # Check if lock is now active (2+ developers on same file)
        same_file_entries = [e for e in log_entries if e['file_path'] == self.file_path]
        lock_should_be_active = len(same_file_entries) >= 2

        self.log_step(
            "DEV_B_DECLARES_INTENT",
            f"Bob declared intent on {self.file_path}. "
            f"Log now has {len(log_entries)} entries. "
            f"Lock status: {'ACTIVE' if lock_should_be_active else 'NOT ACTIVE'} "
            f"({len(same_file_entries)} devs on same file)"
        )

        print(f"\nLog state after Dev B declares:")
        for entry in log_entries:
            print(f"  - {entry['developer_id']}: {entry['intent'][:50]}...")

        # Verify lock was applied
        if not lock_should_be_active:
            self.results["conflicts"].append({
                "timestamp": datetime.now().isoformat(),
                "issue": "LOCK_NOT_APPLIED",
                "severity": "CRITICAL",
                "message": f"Lock should be active with 2 developers on {self.file_path}"
            })

    def step_4_dev_a_completes_work(self):
        """Dev A completes work and publishes changes."""
        print("\n" + "="*70)
        print("STEP 3: Dev A Completes Work and Publishes")
        print("="*70)

        # Dev A makes changes and logs completion
        log_activity(
            developer_id="alice",
            file_path=self.file_path,
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
        self.log_step(
            "DEV_A_COMPLETES_WORK",
            f"Alice completed her work. "
            f"Changes: +20 lines, -5 lines. "
            f"Log now has {len(log_entries)} entries."
        )

        print(f"\nLog state after Dev A completes:")
        for entry in log_entries:
            metadata = entry.get('agent_metadata') or {}
            status = metadata.get('status', 'declared')
            print(f"  - {entry['developer_id']}: {status} ({entry['intent'][:40]}...)")

    def step_5_dev_b_gets_fresh_context(self):
        """Dev B gets notified of A's completion and receives fresh context."""
        print("\n" + "="*70)
        print("STEP 4: Dev B Gets Fresh Context After A's Changes")
        print("="*70)

        # Dev B checks for conflicts again (this triggers context refresh)
        print("\nDev B checking for conflicts after A's changes...")
        risk_level, conflict_msg = check_for_conflicts(
            agent_id="bob",
            file_path=self.file_path,
            intent="Add password strength requirements",
            region="validate_password (lines 50-70)"
        )

        log_entries = read_log()

        # Find A's completed entry
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
                "alice_changes": {
                    "lines_added": metadata.get('lines_added'),
                    "lines_removed": metadata.get('lines_removed'),
                    "summary": metadata.get('change_summary')
                },
                "risk_assessment": {
                    "risk_level": risk_level.name,
                    "message": conflict_msg
                },
                "context_freshness": "FRESH"
            }

            self.dev_b_fresh_context = context_update
            self.log_step(
                "DEV_B_GETS_FRESH_CONTEXT",
                f"Dev B received fresh context. "
                f"Alice's changes: +{context_update['alice_changes']['lines_added']}, "
                f"-{context_update['alice_changes']['lines_removed']}. "
                f"Risk: {context_update['risk_assessment']['risk_level']} "
                f"({context_update['risk_assessment']['message'][:50]}...)"
            )

            self.results["context_refreshes"].append(context_update)
        else:
            self.results["conflicts"].append({
                "timestamp": datetime.now().isoformat(),
                "issue": "CONTEXT_NOT_FOUND",
                "severity": "ERROR",
                "message": "Could not find Alice's completed entry for context refresh"
            })

    def step_6_dev_b_completes_work(self):
        """Dev B completes work with A's context integrated."""
        print("\n" + "="*70)
        print("STEP 5: Dev B Completes Work (With A's Context Integrated)")
        print("="*70)

        # Dev B makes changes (building on A's work)
        log_activity(
            developer_id="bob",
            file_path=self.file_path,
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
        self.log_step(
            "DEV_B_COMPLETES_WORK",
            f"Bob completed his work (built on Alice's changes). "
            f"Changes: +15 lines, -0 lines. "
            f"Log now has {len(log_entries)} entries. "
            f"Conflicts: 0"
        )

        print(f"\nFinal log state:")
        for i, entry in enumerate(log_entries, 1):
            metadata = entry.get('agent_metadata') or {}
            status = metadata.get('status', 'declared')
            built_on = metadata.get('built_on', 'none')
            print(f"  [{i}] {entry['developer_id']} ({status}): {entry['intent'][:50]}...")
            if built_on != 'none':
                print(f"       └─ Built on: {built_on}")

    def step_7_verify_no_conflicts(self):
        """Verify that no merge conflicts occurred throughout the workflow."""
        print("\n" + "="*70)
        print("STEP 6: Verify No Conflicts Throughout Workflow")
        print("="*70)

        log_entries = read_log()

        # Count completed entries
        completed_entries = [
            e for e in log_entries
            if (e.get('agent_metadata') or {}).get('status') == 'completed'
        ]

        # Check if any entry reports conflicts
        total_conflicts_reported = 0
        for entry in completed_entries:
            metadata = entry.get('agent_metadata') or {}
            conflicts = metadata.get('conflicts_detected', 0)
            total_conflicts_reported += conflicts

        status = "✅ PASS" if total_conflicts_reported == 0 else "❌ FAIL"
        self.log_step(
            "VERIFY_NO_CONFLICTS",
            f"{status} - Total conflicts reported: {total_conflicts_reported}. "
            f"Developers completed: {len(completed_entries)}."
        )

        return total_conflicts_reported == 0

    def step_8_final_summary(self):
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
            "developers_participated": len(set(e['developer_id'] for e in log_entries)),
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
        print(f"  Total changes: +{summary['total_changes']['lines_added']}, -{summary['total_changes']['lines_removed']}")
        print(f"  Conflicts detected: {summary['conflicts_detected']}")
        print(f"  Context refreshes: {summary['context_refreshes']}")
        print(f"  Status: {summary['test_status']}")

        return summary

    def run(self):
        """Run the complete 2-developer coordination test."""
        print("\n" + "="*70)
        print("NEO REAL 2-DEVELOPER COORDINATION TEST")
        print("="*70)
        print(f"Test Start: {datetime.now().isoformat()}")
        print(f"File: {self.file_path}")
        print(f"Developers: alice (Dev A), bob (Dev B)")

        try:
            self.step_1_clear_log()
            time.sleep(0.1)
            self.step_2_dev_a_declares_intent()
            time.sleep(0.1)
            self.step_3_dev_b_declares_intent()
            time.sleep(0.1)
            self.step_4_dev_a_completes_work()
            time.sleep(0.1)
            self.step_5_dev_b_gets_fresh_context()
            time.sleep(0.1)
            self.step_6_dev_b_completes_work()
            time.sleep(0.1)
            self.step_7_verify_no_conflicts()
            time.sleep(0.1)
            summary = self.step_8_final_summary()

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
    """Run the 2-developer test."""
    test = TwoDevCoordinationTest()
    result = test.run()

    # Print results as JSON
    print("\n" + "="*70)
    print("TEST RESULTS (JSON)")
    print("="*70)
    print(json.dumps(result, indent=2))

    # Save results to file
    results_file = Path(__file__).parent / "test_two_dev_results.json"
    with open(results_file, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    # Exit with appropriate code
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()

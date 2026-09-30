#!/usr/bin/env python3
"""
Comprehensive unit tests for Phase 2 fix:
Lock holder should not see waiting developers as conflicts
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
import shutil

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import clear_log, log_activity, read_log, get_active_entries
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel
from core.lock_manager import LockManager


class TestPhase2WaitingAgentFix:
    """Test suite for Phase 2: Lock holder doesn't see waiting developers as conflicts"""

    def __init__(self):
        self.test_results = []
        self.test_count = 0
        self.passed_count = 0

    def setup(self):
        """Clean up before each test"""
        clear_log()
        log_dir = Path(".devsync")
        if log_dir.exists():
            shutil.rmtree(log_dir)

    def teardown(self):
        """Clean up after each test"""
        pass

    def log_result(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        self.test_count += 1
        if passed:
            self.passed_count += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"

        result = f"{status}: {test_name}"
        if details:
            result += f" | {details}"

        self.test_results.append(result)
        print(result)

    def assert_equal(self, actual, expected, msg=""):
        """Assert equality"""
        if actual == expected:
            return True
        else:
            print(f"   ❌ Expected {expected}, got {actual}. {msg}")
            return False

    def assert_is_none(self, value, msg=""):
        """Assert value is None"""
        if value is None:
            return True
        else:
            print(f"   ❌ Expected None, got {value}. {msg}")
            return False

    def assert_is_not_none(self, value, msg=""):
        """Assert value is not None"""
        if value is not None:
            return True
        else:
            print(f"   ❌ Expected not None. {msg}")
            return False

    # =========== TESTS ===========

    def test_basic_lock_holder_no_conflict_from_waiting(self):
        """Test 1: Lock holder doesn't see waiting developers as conflicts"""
        self.setup()

        # Alice declares intent first
        log_activity(
            developer_id="alice",
            file_path="auth.py",
            intent="Add authentication",
            intent_category="feature"
        )
        risk1, msg1, lock_info1 = check_for_conflicts("alice", "auth.py", "Add authentication")

        # Bob declares intent (should be queued)
        log_activity(
            developer_id="bob",
            file_path="auth.py",
            intent="Add JWT support",
            intent_category="feature"
        )
        risk2, msg2, lock_info2 = check_for_conflicts("bob", "auth.py", "Add JWT support")

        # Alice checks conflicts again (should NOT see bob as conflict anymore)
        risk3, msg3, lock_info3 = check_for_conflicts("alice", "auth.py", "Add authentication")

        passed = (
            self.assert_equal(risk3, RiskLevel.LOW, "Alice should see LOW risk after Bob is queued") and
            self.assert_is_none(lock_info3, "Alice should have no lock_info (no conflict)")
        )

        self.log_result("Lock holder doesn't see waiting developers as conflicts", passed,
                       f"risk3={risk3.value}, has_lock_info={lock_info3 is not None}")

    def test_waiting_developer_still_sees_conflict(self):
        """Test 2: Waiting developer still sees lock holder as conflict"""
        self.setup()

        # Alice declares first
        log_activity(
            developer_id="alice",
            file_path="auth.py",
            intent="Add authentication",
            intent_category="feature"
        )
        check_for_conflicts("alice", "auth.py", "Add authentication")

        # Bob declares (gets queued)
        log_activity(
            developer_id="bob",
            file_path="auth.py",
            intent="Add JWT support",
            intent_category="feature"
        )
        risk_bob, msg_bob, lock_info_bob = check_for_conflicts("bob", "auth.py", "Add JWT support")

        passed = (
            self.assert_equal(risk_bob, RiskLevel.MEDIUM, "Bob should see MEDIUM risk (waiting)") and
            self.assert_is_not_none(lock_info_bob, "Bob should have lock_info (queued)")
        )

        self.log_result("Waiting developer still sees conflict with lock holder", passed,
                       f"risk_bob={risk_bob.value}, queue_pos={lock_info_bob.get('queue_position') if lock_info_bob else None}")

    def test_three_dev_scenario(self):
        """Test 3: Three developer scenario - alice holds lock, bob and charlie wait"""
        self.setup()

        # Alice declares first (gets lock)
        log_activity("alice", "auth.py", "Add authentication", "feature")
        risk_a1, msg_a1, lock_a1 = check_for_conflicts("alice", "auth.py", "Add authentication")

        # Bob declares (gets queued)
        log_activity("bob", "auth.py", "Add JWT support", "feature")
        risk_b1, msg_b1, lock_b1 = check_for_conflicts("bob", "auth.py", "Add JWT support")
        bob_queue_pos = lock_b1.get('queue_position') if lock_b1 else None

        # Charlie declares (gets queued behind bob)
        log_activity("charlie", "auth.py", "Add oauth", "feature")
        risk_c1, msg_c1, lock_c1 = check_for_conflicts("charlie", "auth.py", "Add oauth")
        charlie_queue_pos = lock_c1.get('queue_position') if lock_c1 else None

        # Alice checks again (should NOT see bob or charlie as conflicts)
        risk_a2, msg_a2, lock_a2 = check_for_conflicts("alice", "auth.py", "Add authentication")

        passed = (
            self.assert_equal(risk_a1, RiskLevel.LOW, "Alice first should be LOW") and
            self.assert_equal(risk_b1, RiskLevel.MEDIUM, "Bob should be MEDIUM") and
            self.assert_equal(risk_c1, RiskLevel.MEDIUM, "Charlie should be MEDIUM") and
            self.assert_equal(bob_queue_pos, 0, "Bob should be queue_position 0 (first waiting)") and
            self.assert_equal(charlie_queue_pos, 1, "Charlie should be queue_position 1 (second waiting)") and
            self.assert_equal(risk_a2, RiskLevel.LOW, "Alice second check should be LOW (no conflict)")
        )

        self.log_result("3-dev scenario - lock holder sees LOW risk, waiters see MEDIUM", passed,
                       f"alice: {risk_a1.value}→{risk_a2.value}, bob: queue={bob_queue_pos}, charlie: queue={charlie_queue_pos}")

    def test_lock_release_and_queue_promotion(self):
        """Test 4: After lock holder releases, next developer promoted"""
        self.setup()

        # Alice declares and gets lock
        log_activity("alice", "auth.py", "Add authentication", "feature")
        check_for_conflicts("alice", "auth.py", "Add authentication")

        # Bob declares and gets queued
        log_activity("bob", "auth.py", "Add JWT support", "feature")
        risk_b1, msg_b1, lock_b1 = check_for_conflicts("bob", "auth.py", "Add JWT support")
        bob_queue_before = lock_b1.get('queue_position') if lock_b1 else None

        # Alice completes and releases lock
        lock_manager = LockManager()
        lock_manager.release_lock("auth.py", None, "alice")

        # Check bob's status after promotion (should now have the lock)
        risk_b2, msg_b2, lock_b2 = check_for_conflicts("bob", "auth.py", "Add JWT support")
        bob_queue_after = lock_b2.get('queue_position') if lock_b2 else None
        bob_lock_holder = lock_b2.get('lock_holder') if lock_b2 else None

        passed = (
            self.assert_equal(bob_queue_before, 0, "Bob should be queue 0 before alice releases") and
            self.assert_equal(bob_lock_holder, "bob", "Bob should hold lock after alice releases")
        )

        self.log_result("Lock release and queue promotion", passed,
                       f"bob: queue {bob_queue_before}→{bob_queue_after}, holder={bob_lock_holder}")

    def test_no_waiting_developers_no_change(self):
        """Test 5: If no waiting developers, behavior unchanged"""
        self.setup()

        # Only alice on file
        log_activity("alice", "auth.py", "Add authentication", "feature")
        risk1, msg1, lock1 = check_for_conflicts("alice", "auth.py", "Add authentication")

        # Alice checks again (should still be LOW, no one waiting)
        risk2, msg2, lock2 = check_for_conflicts("alice", "auth.py", "Add authentication")

        passed = (
            self.assert_equal(risk1, RiskLevel.LOW, "Alice alone should be LOW") and
            self.assert_equal(risk2, RiskLevel.LOW, "Alice alone still should be LOW")
        )

        self.log_result("No waiting developers - no change in behavior", passed,
                       f"risk: {risk1.value}→{risk2.value}")

    def test_different_files_no_conflict(self):
        """Test 6: Different files - developers don't block each other"""
        self.setup()

        # Alice on auth.py
        log_activity("alice", "auth.py", "Add authentication", "feature")
        risk_a, msg_a, lock_a = check_for_conflicts("alice", "auth.py", "Add authentication")

        # Bob on different file (database.py)
        log_activity("bob", "database.py", "Add migrations", "feature")
        risk_b, msg_b, lock_b = check_for_conflicts("bob", "database.py", "Add migrations")

        passed = (
            self.assert_equal(risk_a, RiskLevel.LOW, "Alice on auth.py should be LOW") and
            self.assert_equal(risk_b, RiskLevel.LOW, "Bob on database.py should be LOW (different file)")
        )

        self.log_result("Different files - no cross-file conflicts", passed,
                       f"alice: {risk_a.value}, bob: {risk_b.value}")

    def test_activity_log_captures_lock_state(self):
        """Test 7: Activity log correctly records lock state"""
        self.setup()

        # Alice declares
        log_activity("alice", "auth.py", "Add authentication", "feature")
        check_for_conflicts("alice", "auth.py", "Add authentication")

        # Bob declares
        log_activity("bob", "auth.py", "Add JWT support", "feature")
        check_for_conflicts("bob", "auth.py", "Add JWT support")

        # Read log
        entries = read_log()

        # Find alice and bob entries
        alice_entries = [e for e in entries if e.get('developer_id') == 'alice']
        bob_entries = [e for e in entries if e.get('developer_id') == 'bob']

        # Check lock states
        alice_has_lock = any(e.get('lock_state') == 'ACQUIRED' for e in alice_entries)
        bob_is_waiting = any(e.get('lock_state') == 'WAITING' for e in bob_entries)

        passed = (
            alice_has_lock and bob_is_waiting
        )

        self.log_result("Activity log captures lock state correctly", passed,
                       f"alice_acquired={alice_has_lock}, bob_waiting={bob_is_waiting}")

    def test_rapid_declarations(self):
        """Test 8: Rapid declarations (edge case) - alice checks first"""
        self.setup()

        # Alice declares and checks FIRST (before others declare)
        log_activity("alice", "auth.py", "alice feature", "feature")
        risk_a, msg_a, lock_a = check_for_conflicts("alice", "auth.py", "alice feature")

        # Others declare and check AFTER alice
        risks = {'alice': (risk_a, lock_a)}
        for dev in ['bob', 'charlie', 'diana']:
            log_activity(dev, "auth.py", f"{dev} feature", "feature")
            risk, msg, lock_info = check_for_conflicts(dev, "auth.py", f"{dev} feature")
            risks[dev] = (risk, lock_info)

        # Alice should be LOW (first, gets lock)
        # Others should be MEDIUM (waiting)
        passed = (
            self.assert_equal(risks['alice'][0], RiskLevel.LOW, "Alice should be LOW") and
            self.assert_equal(risks['bob'][0], RiskLevel.MEDIUM, "Bob should be MEDIUM") and
            self.assert_equal(risks['charlie'][0], RiskLevel.MEDIUM, "Charlie should be MEDIUM") and
            self.assert_equal(risks['diana'][0], RiskLevel.MEDIUM, "Diana should be MEDIUM")
        )

        self.log_result("Rapid declarations - correct queueing", passed,
                       f"alice={risks['alice'][0].value}, bob={risks['bob'][0].value}")

    def test_alice_second_check_no_warnings(self):
        """Test 9: Alice holds lock, bob waits, alice checks again (main use case)"""
        self.setup()

        # Alice declares first
        log_activity("alice", "auth.py", "Add authentication", "feature")
        risk_a1, msg_a1, _ = check_for_conflicts("alice", "auth.py", "Add authentication")
        print(f"   Alice first check: {risk_a1.value}")

        # Bob declares (gets queued)
        log_activity("bob", "auth.py", "Add JWT support", "feature")
        risk_b1, msg_b1, lock_b1 = check_for_conflicts("bob", "auth.py", "Add JWT support")
        print(f"   Bob declares: {risk_b1.value}, queue_pos={lock_b1.get('queue_position') if lock_b1 else None}")

        # Charlie declares (gets queued)
        log_activity("charlie", "auth.py", "Add oauth", "feature")
        risk_c1, msg_c1, lock_c1 = check_for_conflicts("charlie", "auth.py", "Add oauth")
        print(f"   Charlie declares: {risk_c1.value}, queue_pos={lock_c1.get('queue_position') if lock_c1 else None}")

        # Alice checks AGAIN while holding lock with bob and charlie waiting
        risk_a2, msg_a2, lock_a2 = check_for_conflicts("alice", "auth.py", "Add authentication")
        print(f"   Alice second check: {risk_a2.value} (should be LOW, no warnings)")

        passed = (
            self.assert_equal(risk_a1, RiskLevel.LOW, "Alice first check LOW") and
            self.assert_equal(risk_b1, RiskLevel.MEDIUM, "Bob gets MEDIUM") and
            self.assert_equal(risk_c1, RiskLevel.MEDIUM, "Charlie gets MEDIUM") and
            self.assert_equal(risk_a2, RiskLevel.LOW, "Alice second check should be LOW (no conflict from waiters)")
        )

        self.log_result("Alice 2nd check: no warnings from bob/charlie waiting", passed,
                       f"a1={risk_a1.value}, b1={risk_b1.value}, c1={risk_c1.value}, a2={risk_a2.value}")

    def run_all_tests(self):
        """Run all tests"""
        print("\n" + "="*70)
        print("PHASE 2 COMPREHENSIVE TEST SUITE")
        print("Lock holder should not see waiting developers as conflicts")
        print("="*70 + "\n")

        self.test_basic_lock_holder_no_conflict_from_waiting()
        self.test_waiting_developer_still_sees_conflict()
        self.test_three_dev_scenario()
        self.test_lock_release_and_queue_promotion()
        self.test_no_waiting_developers_no_change()
        self.test_different_files_no_conflict()
        self.test_activity_log_captures_lock_state()
        self.test_rapid_declarations()
        self.test_alice_second_check_no_warnings()

        # Print summary
        print("\n" + "="*70)
        print(f"TEST SUMMARY: {self.passed_count}/{self.test_count} passed")
        print("="*70)

        for result in self.test_results:
            print(result)

        print("="*70)

        return self.passed_count == self.test_count


if __name__ == "__main__":
    tester = TestPhase2WaitingAgentFix()
    all_passed = tester.run_all_tests()
    sys.exit(0 if all_passed else 1)

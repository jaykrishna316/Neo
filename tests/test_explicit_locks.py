#!/usr/bin/env python3
"""Comprehensive tests for explicit lock mechanism in Neo.

Tests lock acquisition, queue tracking, auto-promotion, expiration, and
backward compatibility with RiskLevel classification.
"""

import os
import time
import json
import tempfile
from pathlib import Path

# Add parent to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import clear_log, read_log, log_activity, DEFAULT_TENANT_ID
from core.lock_manager import LockManager
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel


def test_lock_acquisition_when_free():
    """Test acquiring a lock when it's available."""
    clear_log()
    manager = LockManager()

    result = manager.acquire_lock(
        file_path="auth.py",
        region="validate_password",
        developer_id="alice",
        reason="MEDIUM_CONFLICT",
        scope="region",
    )

    assert result["success"] is True
    assert result["lock_holder"] == "alice"
    assert result["queue_position"] is None
    assert result["lock_acquired_at"] is not None
    print("✓ test_lock_acquisition_when_free PASSED")


def test_lock_blocking_when_held():
    """Test that lock blocks second developer."""
    clear_log()
    manager = LockManager()

    # Alice acquires
    result1 = manager.acquire_lock(
        file_path="auth.py",
        region="validate_password",
        developer_id="alice",
        reason="MEDIUM_CONFLICT",
        scope="region",
    )
    assert result1["success"] is True

    # Bob tries to acquire (blocked)
    result2 = manager.acquire_lock(
        file_path="auth.py",
        region="validate_password",
        developer_id="bob",
        reason="MEDIUM_CONFLICT",
        scope="region",
    )
    assert result2["success"] is False
    assert result2["lock_holder"] == "alice"
    assert result2["queue_position"] == 0
    assert result2["waiting_for"] == "alice"
    print("✓ test_lock_blocking_when_held PASSED")


def test_lock_queue_tracking():
    """Test queue position tracking with 3 developers."""
    clear_log()
    manager = LockManager()

    # Alice acquires
    r1 = manager.acquire_lock(
        file_path="auth.py", region="validate_password",
        developer_id="alice", reason="MEDIUM_CONFLICT", scope="region"
    )
    assert r1["success"] is True

    # Bob queued (position 0 = next)
    r2 = manager.acquire_lock(
        file_path="auth.py", region="validate_password",
        developer_id="bob", reason="MEDIUM_CONFLICT", scope="region"
    )
    assert r2["queue_position"] == 0

    # Charlie queued (position 1)
    r3 = manager.acquire_lock(
        file_path="auth.py", region="validate_password",
        developer_id="charlie", reason="MEDIUM_CONFLICT", scope="region"
    )
    assert r3["queue_position"] == 1

    # Verify queue order
    state = manager.get_lock_state("auth.py", "validate_password", "region")
    assert state["queue_list"] == ["bob", "charlie"]
    print("✓ test_lock_queue_tracking PASSED")


def test_lock_auto_promotion():
    """Test automatic promotion when lock is released."""
    clear_log()
    manager = LockManager()

    # Alice acquires
    manager.acquire_lock(
        file_path="auth.py", region="validate_password",
        developer_id="alice", reason="MEDIUM_CONFLICT", scope="region"
    )

    # Bob and Charlie queue
    manager.acquire_lock(
        file_path="auth.py", region="validate_password",
        developer_id="bob", reason="MEDIUM_CONFLICT", scope="region"
    )
    manager.acquire_lock(
        file_path="auth.py", region="validate_password",
        developer_id="charlie", reason="MEDIUM_CONFLICT", scope="region"
    )

    # Alice releases
    result = manager.release_lock(
        file_path="auth.py", region="validate_password",
        developer_id="alice", scope="region"
    )
    assert result["success"] is True
    assert result["next_lock_holder"] == "bob"

    # Verify Bob now holds lock
    state = manager.get_lock_state("auth.py", "validate_password", "region")
    assert state["lock_holder"] == "bob"
    assert state["queue_list"] == ["charlie"]
    print("✓ test_lock_auto_promotion PASSED")


def test_lock_expiration():
    """Test lock timeout and expiration detection."""
    clear_log()
    manager = LockManager()

    # Alice acquires with 1-second timeout
    manager.acquire_lock(
        file_path="auth.py", region="validate_password",
        developer_id="alice", reason="MEDIUM_CONFLICT",
        scope="region", duration_seconds=1
    )

    # Not expired yet
    assert manager.check_expired("auth.py", "validate_password", "region") is False

    # Wait for expiration
    time.sleep(1.1)
    assert manager.check_expired("auth.py", "validate_password", "region") is True
    print("✓ test_lock_expiration PASSED")


def test_backward_compatibility_with_risk_level():
    """Test that RiskLevel classification still works alongside explicit locks."""
    clear_log()
    manager = LockManager()

    # Alice declares intent and acquires lock
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Add bcrypt hashing to validate_password",
        region="validate_password",
        tenant_id=DEFAULT_TENANT_ID,
    )

    # Alice acquires explicit lock
    manager.acquire_lock(
        file_path="auth.py",
        region="validate_password",
        developer_id="alice",
        reason="MEDIUM_CONFLICT",
        scope="region",
    )

    # Bob tries to work on same file (should detect conflict)
    risk_level, msg, lock_info = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Refactor validate_password",
        region="validate_password",
    )

    # Should be MEDIUM risk and explicit lock should be created
    assert risk_level == RiskLevel.MEDIUM
    assert lock_info is not None
    assert lock_info["success"] is False  # Bob gets queued, not immediate lock
    assert lock_info["lock_holder"] == "alice"
    print("✓ test_backward_compatibility_with_risk_level PASSED")


def test_2dev_workflow_with_explicit_locks():
    """Test 2-dev workflow with full explicit lock tracking."""
    clear_log()
    manager = LockManager()

    # Dev A declares intent and acquires lock
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Add authentication module",
        region="login_user",
    )

    lock_a = manager.acquire_lock(
        file_path="auth.py", region="login_user",
        developer_id="alice", reason="MEDIUM_CONFLICT", scope="region"
    )
    assert lock_a["success"] is True

    # Dev B declares intent (should be queued)
    log_activity(
        developer_id="bob",
        file_path="auth.py",
        intent="Add password validation",
        region="login_user",
    )

    lock_b = manager.acquire_lock(
        file_path="auth.py", region="login_user",
        developer_id="bob", reason="MEDIUM_CONFLICT", scope="region"
    )
    assert lock_b["success"] is False
    assert lock_b["queue_position"] == 0

    # Dev A completes and releases
    result = manager.release_lock(
        file_path="auth.py", region="login_user",
        developer_id="alice", scope="region"
    )
    assert result["next_lock_holder"] == "bob"

    # Dev B now holds lock
    state = manager.get_lock_state("auth.py", "login_user", "region")
    assert state["lock_holder"] == "bob"
    print("✓ test_2dev_workflow_with_explicit_locks PASSED")


def test_3dev_workflow_with_queue():
    """Test 3-dev workflow with queue behavior."""
    clear_log()
    manager = LockManager()

    # Alice acquires
    manager.acquire_lock(
        file_path="auth.py", region="validate",
        developer_id="alice", reason="MEDIUM_CONFLICT", scope="region"
    )

    # Bob and Charlie queue
    manager.acquire_lock(
        file_path="auth.py", region="validate",
        developer_id="bob", reason="MEDIUM_CONFLICT", scope="region"
    )
    manager.acquire_lock(
        file_path="auth.py", region="validate",
        developer_id="charlie", reason="MEDIUM_CONFLICT", scope="region"
    )

    # Alice releases -> Bob promoted
    manager.release_lock(
        file_path="auth.py", region="validate",
        developer_id="alice", scope="region"
    )
    state = manager.get_lock_state("auth.py", "validate", "region")
    assert state["lock_holder"] == "bob"

    # Bob releases -> Charlie promoted
    manager.release_lock(
        file_path="auth.py", region="validate",
        developer_id="bob", scope="region"
    )
    state = manager.get_lock_state("auth.py", "validate", "region")
    assert state["lock_holder"] == "charlie"
    print("✓ test_3dev_workflow_with_queue PASSED")


def test_lock_activity_log_entries():
    """Verify lock state is persisted in activity log."""
    clear_log()
    manager = LockManager()

    manager.acquire_lock(
        file_path="auth.py", region="validate",
        developer_id="alice", reason="MEDIUM_CONFLICT", scope="region"
    )

    log = read_log()
    assert len(log) > 0

    entry = log[-1]
    assert entry["lock_state"] == "ACQUIRED"
    assert entry["lock_holder"] == "alice"
    assert entry["lock_scope"] == "region"
    assert entry["lock_reason"] == "MEDIUM_CONFLICT"
    print("✓ test_lock_activity_log_entries PASSED")


# ==================== MAIN TEST RUNNER ====================

def run_all_tests():
    """Execute all explicit lock tests."""
    print("=" * 70)
    print("NEO 4.0: EXPLICIT LOCK TESTS")
    print("=" * 70)
    print()

    tests = [
        test_lock_acquisition_when_free,
        test_lock_blocking_when_held,
        test_lock_queue_tracking,
        test_lock_auto_promotion,
        test_lock_expiration,
        test_backward_compatibility_with_risk_level,
        test_2dev_workflow_with_explicit_locks,
        test_3dev_workflow_with_queue,
        test_lock_activity_log_entries,
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test_func.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} ERROR: {e}")
            failed += 1

    print()
    print("=" * 70)
    print(f"TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    print()

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)

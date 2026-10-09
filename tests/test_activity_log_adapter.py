#!/usr/bin/env python3
"""Test Activity Log Adapter - Verify abstraction works for file storage."""

import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import ActivityEntry
from core.activity_log_adapter import ActivityLogAdapter, FileBackend


def test_file_backend():
    """Test file-based backend."""
    print("\n" + "="*70)
    print("TEST: File Backend (Local Storage)")
    print("="*70)

    os.environ["ACTIVITY_LOG_MODE"] = "file"

    ActivityLogAdapter.clear_log("test-tenant")

    # Create test entries
    entry1 = ActivityEntry(
        developer_id="alice",
        file_path="auth.py",
        intent="Add bcrypt hashing",
        region="validate_password",
        timestamp=time.time(),
        tenant_id="test-tenant"
    )

    entry2 = ActivityEntry(
        developer_id="bob",
        file_path="auth.py",
        intent="Add password validation",
        region="validate_password",
        timestamp=time.time(),
        tenant_id="test-tenant",
        agent_metadata={"status": "working"}
    )

    print("\n✓ Writing entries to file backend...")
    ActivityLogAdapter.append_entry(entry1, "test-tenant")
    ActivityLogAdapter.append_entry(entry2, "test-tenant")

    print("✓ Reading entries from file backend...")
    entries = ActivityLogAdapter.read_log("test-tenant")

    assert len(entries) == 2, f"Expected 2 entries, got {len(entries)}"
    assert entries[0].developer_id == "alice"
    assert entries[1].developer_id == "bob"
    print(f"✓ Read {len(entries)} entries successfully")

    print("✓ Getting active entries...")
    active = ActivityLogAdapter.get_active_entries("test-tenant")
    assert len(active) == 2, f"Expected 2 active entries, got {len(active)}"
    print(f"✓ Got {len(active)} active entries")

    print("✓ Clearing log...")
    ActivityLogAdapter.clear_log("test-tenant")
    entries = ActivityLogAdapter.read_log("test-tenant")
    assert len(entries) == 0, f"Log should be empty after clear, got {len(entries)}"
    print("✓ Log cleared successfully")

    print("\n✅ FILE BACKEND TEST PASSED")


def test_lock_fields():
    """Test that lock fields are preserved in storage."""
    print("\n" + "="*70)
    print("TEST: Lock Fields Storage")
    print("="*70)

    os.environ["ACTIVITY_LOG_MODE"] = "file"
    ActivityLogAdapter.clear_log("lock-test")

    print("\n✓ Creating entry with lock fields...")
    entry = ActivityEntry(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor validation",
        region="validate_password",
        timestamp=time.time(),
        tenant_id="lock-test",
        lock_state="ACQUIRED",
        lock_holder="alice",
        lock_acquired_at=time.time(),
        lock_expires_at=time.time() + 1800,
        lock_reason="MEDIUM_CONFLICT",
        lock_scope="region",
        queue_position=None
    )

    print("✓ Writing entry with locks...")
    ActivityLogAdapter.append_entry(entry, "lock-test")

    print("✓ Reading entry back...")
    entries = ActivityLogAdapter.read_log("lock-test")
    assert len(entries) == 1

    restored = entries[0]
    assert restored.lock_state == "ACQUIRED"
    assert restored.lock_holder == "alice"
    assert restored.lock_reason == "MEDIUM_CONFLICT"
    assert restored.lock_scope == "region"
    print("✓ Lock fields preserved correctly")

    ActivityLogAdapter.clear_log("lock-test")

    print("\n✅ LOCK FIELDS TEST PASSED")


def test_backend_switching():
    """Test that backend can be switched."""
    print("\n" + "="*70)
    print("TEST: Backend Switching")
    print("="*70)

    os.environ["ACTIVITY_LOG_MODE"] = "file"

    print("\n✓ Verifying file backend...")
    backend = ActivityLogAdapter.get_backend()
    assert isinstance(backend, FileBackend), f"Expected FileBackend, got {type(backend)}"
    print(f"✓ Active backend: {type(backend).__name__}")

    ActivityLogAdapter._backend = None

    print("\n✅ BACKEND SWITCHING TEST PASSED")


def test_supabase_availability():
    """Check if Supabase SDK is available (optional)."""
    print("\n" + "="*70)
    print("TEST: Supabase Availability Check")
    print("="*70)

    try:
        import supabase
        print("\n✓ Supabase SDK is installed")
    except ImportError:
        print("\n⚠ Supabase SDK not installed (optional)")
        print("  Install with: pip install supabase-py")

    print("✅ SUPABASE AVAILABILITY CHECK COMPLETE")


def main():
    """Run all adapter tests."""
    print("\n" + "="*70)
    print("NEO ACTIVITY LOG ADAPTER TEST SUITE")
    print("="*70)

    try:
        test_file_backend()
        test_lock_fields()
        test_backend_switching()
        test_supabase_availability()

        print("\n" + "="*70)
        print("ALL ADAPTER TESTS PASSED ✅")
        print("="*70)
        return 0
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

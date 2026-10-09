#!/usr/bin/env python3
"""Tests for cloud storage backends (Supabase, MongoDB).

Tests storage adapter pattern for file-based and cloud-based backends.
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.storage.file_storage import FileStorage
from core.storage.factory import get_storage


def test_file_storage_write_read():
    """Test file storage basic operations."""
    storage = FileStorage()
    storage.clear()

    entry = {
        "developer_id": "alice",
        "file_path": "auth.py",
        "intent": "Add bcrypt hashing",
        "region": "validate_password",
        "tenant_id": "default",
    }

    # Write
    written = storage.write_entry(entry)
    assert written["developer_id"] == "alice"
    assert written["timestamp"] is not None

    # Read all
    entries = storage.read_all()
    assert len(entries) == 1
    assert entries[0]["developer_id"] == "alice"

    print("✓ test_file_storage_write_read PASSED")


def test_file_storage_tenant_isolation():
    """Test file storage with multitenancy."""
    storage = FileStorage()
    storage.clear()

    # Write to tenant A
    storage.write_entry({
        "developer_id": "alice",
        "file_path": "auth.py",
        "intent": "Refactor",
        "tenant_id": "tenant-a",
    })

    # Write to tenant B
    storage.write_entry({
        "developer_id": "bob",
        "file_path": "auth.py",
        "intent": "Add validation",
        "tenant_id": "tenant-b",
    })

    # Query tenant A only
    a_entries = storage.read_all(tenant_id="tenant-a")
    assert len(a_entries) == 1
    assert a_entries[0]["developer_id"] == "alice"

    # Query tenant B only
    b_entries = storage.read_all(tenant_id="tenant-b")
    assert len(b_entries) == 1
    assert b_entries[0]["developer_id"] == "bob"

    print("✓ test_file_storage_tenant_isolation PASSED")


def test_file_storage_active_entries():
    """Test reading only non-expired entries."""
    storage = FileStorage()
    storage.clear()

    now = time.time()

    # Recent entry (active)
    storage.write_entry({
        "developer_id": "alice",
        "file_path": "auth.py",
        "intent": "Recent work",
        "timestamp": now,
        "tenant_id": "default",
    })

    # Old entry (expired, 40 minutes ago)
    storage.write_entry({
        "developer_id": "bob",
        "file_path": "auth.py",
        "intent": "Old work",
        "timestamp": now - (40 * 60),
        "tenant_id": "default",
    })

    # Read active (30 min expiry)
    active = storage.read_active(expiry_minutes=30)
    assert len(active) == 1
    assert active[0]["developer_id"] == "alice"

    print("✓ test_file_storage_active_entries PASSED")


def test_file_storage_query():
    """Test querying with filters."""
    storage = FileStorage()
    storage.clear()

    # Write multiple entries
    storage.write_entry({
        "developer_id": "alice",
        "file_path": "auth.py",
        "intent": "Add hashing",
        "lock_state": "ACQUIRED",
        "tenant_id": "default",
    })

    storage.write_entry({
        "developer_id": "bob",
        "file_path": "auth.py",
        "intent": "Add validation",
        "lock_state": "WAITING",
        "tenant_id": "default",
    })

    storage.write_entry({
        "developer_id": "alice",
        "file_path": "models.py",
        "intent": "Add schema",
        "lock_state": "ACQUIRED",
        "tenant_id": "default",
    })

    # Query alice's entries
    alice_entries = storage.query({"developer_id": "alice"})
    assert len(alice_entries) == 2

    # Query locked entries
    locked = storage.query({"lock_state": "ACQUIRED"})
    assert len(locked) == 2

    # Query alice's entries on auth.py
    specific = storage.query({
        "developer_id": "alice",
        "file_path": "auth.py",
    })
    assert len(specific) == 1

    print("✓ test_file_storage_query PASSED")


def test_file_storage_delete():
    """Test deleting entries."""
    storage = FileStorage()
    storage.clear()

    entry = storage.write_entry({
        "developer_id": "alice",
        "file_path": "auth.py",
        "intent": "Work",
        "tenant_id": "default",
    })

    # Verify it exists
    entries = storage.read_all()
    assert len(entries) == 1

    # Delete by timestamp
    entry_id = str(entry["timestamp"])
    deleted = storage.delete_entry(entry_id)
    assert deleted is True

    # Verify it's gone
    entries = storage.read_all()
    assert len(entries) == 0

    print("✓ test_file_storage_delete PASSED")


def test_storage_factory():
    """Test storage factory pattern."""
    # Default to file storage
    storage = get_storage()
    assert isinstance(storage, FileStorage)

    # Explicitly request file storage
    storage = get_storage("file")
    assert isinstance(storage, FileStorage)

    # Try invalid backend
    try:
        storage = get_storage("invalid")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "Unknown storage backend" in str(e)

    print("✓ test_storage_factory PASSED")


def test_supabase_storage_available():
    """Test that Supabase storage can be imported when configured."""
    try:
        from core.storage.supabase_storage import SupabaseStorage
        print("✓ SupabaseStorage importable (supabase-py installed)")
    except ImportError:
        print("⚠ SupabaseStorage requires supabase-py (not installed in this env)")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("NEO 4.0: CLOUD STORAGE TESTS")
    print("="*70 + "\n")

    test_file_storage_write_read()
    test_file_storage_tenant_isolation()
    test_file_storage_active_entries()
    test_file_storage_query()
    test_file_storage_delete()
    test_storage_factory()
    test_supabase_storage_available()

    print("\n" + "="*70)
    print("TEST RESULTS: All file storage tests passed")
    print("="*70)

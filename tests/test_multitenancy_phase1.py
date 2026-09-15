#!/usr/bin/env python3
"""Unit tests for Phase 1: Multitenancy infrastructure in activity_log.py"""

import json
import os
import shutil
import pytest
from pathlib import Path
from unittest import mock

# Note: Tests need to reload module after env var changes
import importlib


@pytest.fixture(autouse=True)
def cleanup_devsync():
    """Clean up .devsync directory before and after each test."""
    if Path(".devsync").exists():
        shutil.rmtree(".devsync")
    yield
    if Path(".devsync").exists():
        shutil.rmtree(".devsync")


class TestSingleTenantMode:
    """Test backward compatibility with single-tenant (legacy) mode."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up single-tenant mode before each test."""
        os.environ["NEO_MULTITENANCY"] = "false"
        # Reload module to pick up env vars
        import core.activity_log
        importlib.reload(core.activity_log)

    def test_legacy_path_used(self):
        """Verify legacy .devsync/activity-log.json path is used."""
        from core.activity_log import get_tenant_log_path

        path = get_tenant_log_path()
        assert path == Path(".devsync/activity-log.json")

    def test_log_activity_single_tenant(self):
        """Verify log_activity works in single-tenant mode."""
        from core.activity_log import log_activity, get_active_entries

        entry = log_activity("agent-a", "src/auth.py", "Add OAuth2")

        assert entry.developer_id == "agent-a"
        assert entry.file_path == "src/auth.py"
        assert entry.tenant_id == "default"

        # Verify entry is stored
        active = get_active_entries()
        assert len(active) == 1
        assert active[0]["developer_id"] == "agent-a"

    def test_log_file_location_single_tenant(self):
        """Verify log file is created at legacy location."""
        from core.activity_log import log_activity

        log_activity("agent-a", "src/auth.py", "Add OAuth2")

        legacy_path = Path(".devsync/activity-log.json")
        assert legacy_path.exists()
        assert legacy_path.read_text()  # Has content


class TestMultiTenantMode:
    """Test multitenancy infrastructure."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up multi-tenant mode before each test."""
        os.environ["NEO_MULTITENANCY"] = "true"
        # Reload module to pick up env vars
        import core.activity_log
        importlib.reload(core.activity_log)

    def test_tenant_log_path_isolation(self):
        """Verify get_tenant_log_path() creates isolated paths."""
        from core.activity_log import get_tenant_log_path

        path_a = get_tenant_log_path("acme-corp")
        path_b = get_tenant_log_path("startup-ai-lab")

        assert "acme-corp" in str(path_a)
        assert "startup-ai-lab" in str(path_b)
        assert path_a != path_b

    def test_tenant_directory_created(self):
        """Verify tenant directories are created on access."""
        from core.activity_log import get_tenant_log_path

        path = get_tenant_log_path("acme-corp")

        assert path.parent.exists()
        assert (path.parent / ".tenant_id").exists()
        assert (path.parent / ".tenant_id").read_text() == "acme-corp"

    def test_ensure_tenant_isolation_validation(self):
        """Verify ensure_tenant_isolation() validates tenant markers."""
        from core.activity_log import ensure_tenant_isolation

        # First call creates marker
        ensure_tenant_isolation("acme-corp")

        # Second call with same tenant succeeds
        ensure_tenant_isolation("acme-corp")  # Should not raise

        # Call with different tenant should raise
        tenant_dir = Path(".devsync/tenants/acme-corp")
        marker = tenant_dir / ".tenant_id"
        assert marker.read_text() == "acme-corp"

        # Manually corrupt the marker to test validation
        marker.write_text("different-tenant")
        with pytest.raises(ValueError, match="Tenant mismatch"):
            ensure_tenant_isolation("acme-corp")

    def test_log_activity_multitenancy(self):
        """Verify log_activity isolates entries per tenant."""
        from core.activity_log import log_activity, get_active_entries

        # Company A logs intent
        entry_a = log_activity(
            "alice",
            "src/auth.py",
            "Add OAuth2",
            tenant_id="acme-corp"
        )
        assert entry_a.tenant_id == "acme-corp"

        # Company B logs intent on same file
        entry_b = log_activity(
            "bob",
            "src/auth.py",
            "Add SAML",
            tenant_id="startup-ai-lab"
        )
        assert entry_b.tenant_id == "startup-ai-lab"

        # Company A should only see their entries
        active_a = get_active_entries(tenant_id="acme-corp")
        assert len(active_a) == 1
        assert active_a[0]["developer_id"] == "alice"

        # Company B should only see their entries
        active_b = get_active_entries(tenant_id="startup-ai-lab")
        assert len(active_b) == 1
        assert active_b[0]["developer_id"] == "bob"

    def test_no_cross_tenant_leakage(self):
        """Verify entries from one tenant don't leak to another."""
        from core.activity_log import log_activity, get_active_entries

        # Log entries for multiple tenants
        log_activity("alice", "src/auth.py", "Add OAuth2", tenant_id="acme-corp")
        log_activity("bob", "src/auth.py", "Add SAML", tenant_id="startup-ai-lab")
        log_activity("charlie", "src/db.py", "Add migration", tenant_id="google-cloud")

        # Company A can only see their entries
        active_a = get_active_entries(tenant_id="acme-corp")
        assert len(active_a) == 1
        assert all(e["tenant_id"] == "acme-corp" for e in active_a)
        assert not any(e["developer_id"] in ["bob", "charlie"] for e in active_a)

        # Company B can only see their entries
        active_b = get_active_entries(tenant_id="startup-ai-lab")
        assert len(active_b) == 1
        assert all(e["tenant_id"] == "startup-ai-lab" for e in active_b)
        assert not any(e["developer_id"] in ["alice", "charlie"] for e in active_b)

    def test_tenant_directory_cleanup(self):
        """Verify clear_log() cleans up empty tenant directories."""
        from core.activity_log import log_activity, clear_log

        log_activity("alice", "src/auth.py", "Add OAuth2", tenant_id="acme-corp")

        tenant_dir = Path(".devsync/tenants/acme-corp")
        assert tenant_dir.exists()

        clear_log(tenant_id="acme-corp")

        # Directory should be cleaned up if empty
        # (marker file deletion happens during clear)
        log_file = tenant_dir / "activity-log.json"
        assert log_file.exists()  # Log file exists (cleared, not deleted)
        assert log_file.read_text() == "[]"

    def test_read_log_tenant_isolation(self):
        """Verify read_log() returns only tenant-specific entries."""
        from core.activity_log import log_activity, read_log

        log_activity("alice", "src/auth.py", "Add OAuth2", tenant_id="acme-corp")
        log_activity("bob", "src/api.py", "Add endpoints", tenant_id="startup-ai-lab")

        # Read Company A's log
        entries_a = read_log(tenant_id="acme-corp")
        assert len(entries_a) == 1
        assert entries_a[0]["developer_id"] == "alice"

        # Read Company B's log
        entries_b = read_log(tenant_id="startup-ai-lab")
        assert len(entries_b) == 1
        assert entries_b[0]["developer_id"] == "bob"

    def test_default_tenant_from_env_var(self):
        """Verify DEFAULT_TENANT_ID is used when tenant_id not specified."""
        os.environ["CLAUDE_TENANT_ID"] = "my-company"

        import core.activity_log
        importlib.reload(core.activity_log)

        from core.activity_log import log_activity, get_active_entries

        # Log without specifying tenant_id
        entry = log_activity("agent", "src/auth.py", "Add OAuth2")
        assert entry.tenant_id == "my-company"

        # Get active entries without specifying tenant_id
        active = get_active_entries()
        assert len(active) == 1
        assert active[0]["tenant_id"] == "my-company"


class TestTenantFiltering:
    """Test tenant-based filtering in get_active_entries()."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up multi-tenant mode."""
        os.environ["NEO_MULTITENANCY"] = "true"
        import core.activity_log
        importlib.reload(core.activity_log)

    def test_filter_by_file_path(self):
        """Verify file_path filtering works within same tenant."""
        from core.activity_log import log_activity, get_active_entries

        log_activity("alice", "src/auth.py", "Add OAuth2", tenant_id="acme-corp")
        log_activity("bob", "src/db.py", "Add migration", tenant_id="acme-corp")

        # Filter by file_path
        auth_entries = get_active_entries(
            file_path="src/auth.py",
            tenant_id="acme-corp"
        )
        assert len(auth_entries) == 1
        assert auth_entries[0]["file_path"] == "src/auth.py"

    def test_filter_by_developer_id(self):
        """Verify developer_id filtering works within same tenant."""
        from core.activity_log import log_activity, get_active_entries

        log_activity("alice", "src/auth.py", "Add OAuth2", tenant_id="acme-corp")
        log_activity("bob", "src/auth.py", "Add SAML", tenant_id="acme-corp")

        # Filter by developer_id
        alice_entries = get_active_entries(
            developer_id="alice",
            tenant_id="acme-corp"
        )
        assert len(alice_entries) == 1
        assert alice_entries[0]["developer_id"] == "alice"

    def test_combined_filters(self):
        """Verify multiple filters work together."""
        from core.activity_log import log_activity, get_active_entries

        log_activity("alice", "src/auth.py", "Add OAuth2", tenant_id="acme-corp")
        log_activity("alice", "src/db.py", "Add migration", tenant_id="acme-corp")
        log_activity("bob", "src/auth.py", "Add SAML", tenant_id="acme-corp")

        # Filter by file AND developer
        entries = get_active_entries(
            file_path="src/auth.py",
            developer_id="alice",
            tenant_id="acme-corp"
        )
        assert len(entries) == 1
        assert entries[0]["file_path"] == "src/auth.py"
        assert entries[0]["developer_id"] == "alice"


class TestBackwardCompatibility:
    """Test backward compatibility between single and multi-tenant modes."""

    def test_enable_multitenancy_dynamically(self):
        """Verify switching multitenancy mode works."""
        # Start in single-tenant
        os.environ["NEO_MULTITENANCY"] = "false"
        import core.activity_log
        importlib.reload(core.activity_log)

        from core.activity_log import log_activity, get_active_entries

        log_activity("agent", "src/auth.py", "Add OAuth2")
        assert Path(".devsync/activity-log.json").exists()

        # Switch to multi-tenant
        if Path(".devsync").exists():
            shutil.rmtree(".devsync")

        os.environ["NEO_MULTITENANCY"] = "true"
        os.environ["CLAUDE_TENANT_ID"] = "company-a"
        importlib.reload(core.activity_log)

        from core.activity_log import log_activity as log_a, get_active_entries as get_a

        log_a("agent", "src/auth.py", "Add OAuth2")
        assert Path(".devsync/tenants/company-a/activity-log.json").exists()
        assert not Path(".devsync/activity-log.json").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

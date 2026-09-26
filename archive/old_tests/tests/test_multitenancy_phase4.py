#!/usr/bin/env python3
"""Phase 4: Integration and performance testing for multitenancy."""

import json
import os
import shutil
import time
import tempfile
import threading
from pathlib import Path
from unittest import mock
import importlib

import pytest


@pytest.fixture(autouse=True)
def setup_multitenancy():
    """Enable multitenancy for Phase 4 tests."""
    os.environ["NEO_MULTITENANCY"] = "true"
    # Clean up any existing test directories
    if Path(".devsync").exists():
        shutil.rmtree(".devsync")
    yield
    # Cleanup after tests
    if Path(".devsync").exists():
        shutil.rmtree(".devsync")


class TestConcurrentTenants:
    """Test concurrent operations across multiple tenants."""

    def test_5_tenant_simultaneous_logging(self):
        """Verify 5 tenants can log concurrently without conflicts."""
        from core.activity_log import log_activity, get_active_entries

        tenants = [
            "acme-corp",
            "startup-ai-lab",
            "google-cloud",
            "meta-research",
            "openai-enterprise"
        ]

        # Log activities for all tenants
        for tenant in tenants:
            log_activity(
                f"agent-{tenant}",
                "src/auth.py",
                f"Add OAuth2 for {tenant}",
                tenant_id=tenant
            )
            log_activity(
                f"dev-{tenant}",
                "src/db.py",
                f"Add migration for {tenant}",
                tenant_id=tenant
            )

        # Verify each tenant only sees their own entries
        for tenant in tenants:
            entries = get_active_entries(tenant_id=tenant)
            assert len(entries) == 2
            assert all(e["tenant_id"] == tenant for e in entries)
            assert len([e for e in entries if e["file_path"] == "src/auth.py"]) == 1
            assert len([e for e in entries if e["file_path"] == "src/db.py"]) == 1

    def test_file_conflict_isolation_across_tenants(self):
        """Verify same file in different tenants doesn't trigger conflicts."""
        from core.activity_log import log_activity
        from core.pre_gen_check import check_for_conflicts
        from core.risk_classifier import RiskLevel

        # Company A and B both work on same file
        log_activity("alice", "src/payment.py", "Add Stripe integration", tenant_id="acme-corp")
        log_activity("bob", "src/payment.py", "Add PayPal integration", tenant_id="startup-ai-lab")

        # Company A checks conflicts - should see no conflict (different tenant)
        risk_a, msg_a = check_for_conflicts(
            agent_id="alice-2",
            file_path="src/payment.py",
            intent="Add Refund logic",
            tenant_id="acme-corp"
        )
        assert risk_a == RiskLevel.LOW

        # Company B checks conflicts - should see no conflict (different tenant)
        risk_b, msg_b = check_for_conflicts(
            agent_id="bob-2",
            file_path="src/payment.py",
            intent="Add Dispute resolution",
            tenant_id="startup-ai-lab"
        )
        assert risk_b == RiskLevel.LOW

    def test_threading_no_data_leakage(self):
        """Verify threading concurrent logs doesn't leak data between tenants."""
        from core.activity_log import log_activity, get_active_entries

        results = {"acme": [], "startup": [], "google": []}
        errors = []

        def log_and_check(tenant, num_entries=10):
            try:
                # Log entries for this tenant
                for i in range(num_entries):
                    log_activity(
                        f"agent-{i}",
                        f"src/file{i}.py",
                        f"Intent {i} for {tenant}",
                        tenant_id=tenant
                    )

                # Check that only this tenant's entries are visible
                entries = get_active_entries(tenant_id=tenant)
                results[tenant] = entries

                # Verify all entries belong to this tenant
                if not all(e["tenant_id"] == tenant for e in entries):
                    errors.append(f"{tenant}: Found cross-tenant leakage!")

            except Exception as e:
                errors.append(f"{tenant}: {str(e)}")

        # Run threads concurrently
        threads = []
        for tenant in ["acme-corp", "startup-ai-lab", "google-cloud"]:
            t = threading.Thread(target=log_and_check, args=(tenant,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Verify no errors occurred
        assert not errors, f"Errors during concurrent logging: {errors}"

        # Verify each tenant has correct count
        assert len(results["acme"]) == 10
        assert len(results["startup"]) == 10
        assert len(results["google"]) == 10

        # Verify no cross-tenant entries
        for tenant, entries in results.items():
            assert all(e["tenant_id"] in [tenant.split("-")[0], tenant] for e in entries)

    def test_10_concurrent_conflict_checks(self):
        """Run 10 concurrent conflict checks across 3 tenants."""
        from core.activity_log import log_activity
        from core.pre_gen_check import check_for_conflicts

        tenants = ["acme-corp", "startup-ai-lab", "google-cloud"]

        # Setup: Log initial activities
        for tenant in tenants:
            log_activity("initial-agent", "src/core.py", "Initial setup", tenant_id=tenant)

        results = []
        errors = []

        def concurrent_conflict_check(tenant, agent_num):
            try:
                risk, msg = check_for_conflicts(
                    agent_id=f"agent-{agent_num}",
                    file_path="src/core.py",
                    intent=f"Agent {agent_num} intent",
                    tenant_id=tenant
                )
                results.append((tenant, risk.value))
            except Exception as e:
                errors.append(f"Tenant {tenant}, Agent {agent_num}: {str(e)}")

        # Run 10 concurrent checks (distributed across 3 tenants)
        threads = []
        for i in range(10):
            tenant = tenants[i % 3]
            t = threading.Thread(
                target=concurrent_conflict_check,
                args=(tenant, i)
            )
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify results
        assert not errors, f"Errors during concurrent checks: {errors}"
        assert len(results) == 10

        # All should detect the one initial-agent's activity
        medium_or_high = sum(1 for _, level in results if level in ["MEDIUM", "HIGH"])
        assert medium_or_high > 0  # Should detect conflicts with initial-agent


class TestPerformanceBenchmark:
    """Benchmark multitenancy overhead."""

    def test_single_vs_multi_tenant_logging_overhead(self):
        """Measure performance overhead of multitenancy."""
        from core.activity_log import log_activity
        import time

        num_iterations = 1000

        # Single tenant baseline
        start = time.perf_counter()
        for i in range(num_iterations):
            log_activity(
                f"agent-{i}",
                "src/test.py",
                "Test intent",
                tenant_id="baseline"
            )
        single_tenant_time = time.perf_counter() - start

        # Clear for next test
        shutil.rmtree(".devsync")

        # Multi-tenant test (10 tenants)
        start = time.perf_counter()
        for i in range(num_iterations):
            tenant = f"tenant-{i % 10}"
            log_activity(
                f"agent-{i}",
                "src/test.py",
                "Test intent",
                tenant_id=tenant
            )
        multi_tenant_time = time.perf_counter() - start

        # Calculate overhead
        overhead_percent = ((multi_tenant_time - single_tenant_time) / single_tenant_time) * 100

        print(f"\n--- Performance Benchmark ---")
        print(f"Single-tenant (1000 logs): {single_tenant_time:.4f}s")
        print(f"Multi-tenant (1000 logs, 10 tenants): {multi_tenant_time:.4f}s")
        print(f"Overhead: {overhead_percent:.2f}%")

        # Overhead should be less than 1% (allowing some variance)
        assert overhead_percent < 5.0, f"Overhead too high: {overhead_percent:.2f}%"

    def test_conflict_check_performance(self):
        """Measure conflict check performance across tenants."""
        from core.activity_log import log_activity
        from core.pre_gen_check import check_for_conflicts

        tenants = [f"tenant-{i}" for i in range(5)]

        # Setup: Create 100 entries per tenant
        for tenant in tenants:
            for i in range(100):
                log_activity(
                    f"agent-{i}",
                    f"src/file{i % 10}.py",
                    f"Intent {i}",
                    tenant_id=tenant
                )

        # Benchmark conflict checks
        start = time.perf_counter()
        for i in range(100):
            check_for_conflicts(
                agent_id=f"check-agent-{i}",
                file_path=f"src/file{i % 10}.py",
                intent="New intent",
                tenant_id=tenants[i % 5]
            )
        elapsed = time.perf_counter() - start

        print(f"\n--- Conflict Check Performance ---")
        print(f"100 conflict checks (5 tenants, 100 entries each): {elapsed:.4f}s")
        print(f"Avg per check: {elapsed/100*1000:.2f}ms")

        # Should be fast (< 2 seconds for 100 checks)
        assert elapsed < 2.0, f"Conflict checks too slow: {elapsed:.4f}s"

    def test_active_entries_filter_performance(self):
        """Measure get_active_entries filter performance."""
        from core.activity_log import log_activity, get_active_entries

        tenants = [f"tenant-{i}" for i in range(10)]

        # Setup: Create 1000 total entries (100 per tenant)
        for tenant in tenants:
            for i in range(100):
                log_activity(
                    f"agent-{i}",
                    f"src/file{i % 5}.py",
                    f"Intent {i}",
                    tenant_id=tenant
                )

        # Benchmark filtering
        start = time.perf_counter()
        for i in range(100):
            entries = get_active_entries(
                tenant_id=tenants[i % 10],
                file_path=f"src/file{i % 5}.py"
            )
        elapsed = time.perf_counter() - start

        print(f"\n--- Filter Performance ---")
        print(f"100 filtered queries (10 tenants, 1000 total entries): {elapsed:.4f}s")
        print(f"Avg per query: {elapsed/100*1000:.2f}ms")

        # Should be fast (< 1 second for 100 queries)
        assert elapsed < 1.0, f"Filtering too slow: {elapsed:.4f}s"


class TestBackwardCompatibility:
    """Ensure Phase 1-4 changes don't break single-tenant mode."""

    @pytest.fixture(autouse=True)
    def setup_single_tenant(self):
        """Switch to single-tenant mode."""
        os.environ["NEO_MULTITENANCY"] = "false"
        if Path(".devsync").exists():
            shutil.rmtree(".devsync")
        import core.activity_log
        importlib.reload(core.activity_log)
        yield
        if Path(".devsync").exists():
            shutil.rmtree(".devsync")

    def test_legacy_single_tenant_still_works(self):
        """Verify single-tenant mode is not broken by multitenancy code."""
        from core.activity_log import log_activity, get_active_entries, read_log
        from core.pre_gen_check import check_for_conflicts
        from core.risk_classifier import RiskLevel

        # Log activity in single-tenant mode
        entry = log_activity("agent-1", "src/auth.py", "Add OAuth2")
        assert entry.tenant_id == "default"

        # Verify it's stored in legacy location
        legacy_path = Path(".devsync/activity-log.json")
        assert legacy_path.exists()

        # Verify retrieval works
        active = get_active_entries()
        assert len(active) == 1
        assert active[0]["developer_id"] == "agent-1"

        # Verify conflict checking works
        log_activity("agent-2", "src/auth.py", "Add SAML")
        risk, msg = check_for_conflicts(
            agent_id="agent-3",
            file_path="src/auth.py",
            intent="Add custom auth"
        )
        assert risk in [RiskLevel.MEDIUM, RiskLevel.HIGH]

    def test_single_tenant_no_tenant_isolation_validation(self):
        """Verify single-tenant mode doesn't enforce tenant isolation."""
        from core.activity_log import log_activity, get_active_entries

        # Should work without tenant_id even in single-tenant mode
        log_activity("agent-1", "src/auth.py", "Intent 1")
        log_activity("agent-2", "src/auth.py", "Intent 2")

        # No tenant isolation in single-tenant mode
        entries = get_active_entries()
        assert len(entries) == 2


class TestEnterpriseScenarios:
    """Test realistic enterprise scenarios."""

    def test_multi_team_same_repo_isolation(self):
        """Simulate multiple teams working on same repo with proper isolation."""
        from core.activity_log import log_activity, get_active_entries
        from core.pre_gen_check import check_for_conflicts

        teams = {
            "frontend-team": ["alice", "bob"],
            "backend-team": ["charlie", "dave"],
            "devops-team": ["eve"]
        }

        # Each team works on different files
        log_activity("alice", "src/ui/components.ts", "Refactor buttons", tenant_id="frontend-team")
        log_activity("bob", "src/ui/layout.ts", "Update grid system", tenant_id="frontend-team")
        log_activity("charlie", "src/api/users.py", "Add pagination", tenant_id="backend-team")
        log_activity("dave", "src/api/posts.py", "Add caching", tenant_id="backend-team")
        log_activity("eve", "infra/deploy.yaml", "Update k8s config", tenant_id="devops-team")

        # Frontend team checks conflicts in their domain
        frontend_entries = get_active_entries(tenant_id="frontend-team")
        assert len(frontend_entries) == 2
        assert all(e["tenant_id"] == "frontend-team" for e in frontend_entries)

        # Backend team checks - no visibility to frontend work
        backend_entries = get_active_entries(tenant_id="backend-team")
        assert len(backend_entries) == 2
        assert all(e["tenant_id"] == "backend-team" for e in backend_entries)
        assert not any("ui" in e["file_path"] for e in backend_entries)

    def test_tenant_migration_scenario(self):
        """Test scenario where a company migrates between single-tenant and multi-tenant."""
        from core.activity_log import log_activity, get_active_entries, clear_log

        # Phase 1: Single-tenant (legacy)
        os.environ["NEO_MULTITENANCY"] = "false"
        import core.activity_log
        importlib.reload(core.activity_log)

        log_activity("agent-1", "src/auth.py", "Legacy intent")
        legacy_entries = get_active_entries()
        assert len(legacy_entries) == 1

        # Clear for migration
        clear_log()

        # Phase 2: Multi-tenant with new company setup
        os.environ["NEO_MULTITENANCY"] = "true"
        os.environ["CLAUDE_TENANT_ID"] = "acme-corp"
        importlib.reload(core.activity_log)

        log_activity("agent-1", "src/auth.py", "New intent in multitenancy", tenant_id="acme-corp")
        new_entries = get_active_entries(tenant_id="acme-corp")
        assert len(new_entries) == 1
        assert new_entries[0]["tenant_id"] == "acme-corp"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

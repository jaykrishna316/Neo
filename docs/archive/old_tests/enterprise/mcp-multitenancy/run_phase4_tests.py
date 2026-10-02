#!/usr/bin/env python3
"""Phase 4 testing without pytest - standalone runner."""

import sys
import os
import shutil
import time
import threading
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable multitenancy
os.environ["NEO_MULTITENANCY"] = "true"

# Cleanup
if Path(".devsync").exists():
    shutil.rmtree(".devsync")


def cleanup():
    """Cleanup after tests."""
    if Path(".devsync").exists():
        shutil.rmtree(".devsync")


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def add_pass(self, test_name):
        self.passed += 1
        print(f"  ✓ {test_name}")

    def add_fail(self, test_name, error):
        self.failed += 1
        self.errors.append((test_name, str(error)))
        print(f"  ✗ {test_name}")
        print(f"    Error: {error}")

    def summary(self):
        print(f"\n{'='*60}")
        print(f"Results: {self.passed} passed, {self.failed} failed")
        print(f"{'='*60}\n")
        return self.failed == 0


results = TestResults()


# ============================================================================
# CONCURRENT TENANT TESTS
# ============================================================================

def test_5_tenant_simultaneous_logging():
    """Verify 5 tenants can log concurrently without conflicts."""
    try:
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
            log_activity(f"agent-{tenant}", "src/auth.py", f"Add OAuth2 for {tenant}", tenant_id=tenant)
            log_activity(f"dev-{tenant}", "src/db.py", f"Add migration for {tenant}", tenant_id=tenant)

        # Verify each tenant only sees their own entries
        for tenant in tenants:
            entries = get_active_entries(tenant_id=tenant)
            assert len(entries) == 2, f"Expected 2 entries, got {len(entries)}"
            assert all(e["tenant_id"] == tenant for e in entries), "Cross-tenant entries found"

        results.add_pass("5 tenant simultaneous logging")
    except Exception as e:
        results.add_fail("5 tenant simultaneous logging", e)


def test_file_conflict_isolation():
    """Verify same file in different tenants doesn't trigger conflicts."""
    try:
        from core.activity_log import log_activity
        from core.pre_gen_check import check_for_conflicts
        from core.risk_classifier import RiskLevel

        log_activity("alice", "src/payment.py", "Add Stripe integration", tenant_id="acme-corp")
        log_activity("bob", "src/payment.py", "Add PayPal integration", tenant_id="startup-ai-lab")

        risk_a, msg_a = check_for_conflicts(
            agent_id="alice-2",
            file_path="src/payment.py",
            intent="Add Refund logic",
            tenant_id="acme-corp"
        )
        assert risk_a == RiskLevel.LOW, f"Company A should see LOW risk, got {risk_a.value}"

        risk_b, msg_b = check_for_conflicts(
            agent_id="bob-2",
            file_path="src/payment.py",
            intent="Add Dispute resolution",
            tenant_id="startup-ai-lab"
        )
        assert risk_b == RiskLevel.LOW, f"Company B should see LOW risk, got {risk_b.value}"

        results.add_pass("File conflict isolation across tenants")
    except Exception as e:
        results.add_fail("File conflict isolation across tenants", e)


def test_threading_no_data_leakage():
    """Verify threading concurrent logs doesn't leak data."""
    try:
        from core.activity_log import log_activity, get_active_entries

        results_data = {}
        errors = []

        def log_and_check(tenant, num_entries=10):
            try:
                for i in range(num_entries):
                    log_activity(f"agent-{i}", f"src/file{i}.py", f"Intent {i}", tenant_id=tenant)

                entries = get_active_entries(tenant_id=tenant)
                results_data[tenant] = entries

                if not all(e["tenant_id"] == tenant for e in entries):
                    errors.append(f"{tenant}: Found cross-tenant leakage")
            except Exception as e:
                errors.append(f"{tenant}: {str(e)}")

        threads = []
        for tenant in ["acme-corp", "startup-ai-lab", "google-cloud"]:
            t = threading.Thread(target=log_and_check, args=(tenant,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert not errors, f"Errors during concurrent logging: {errors}"
        assert len(results_data.get("acme-corp", [])) == 10
        assert len(results_data.get("startup-ai-lab", [])) == 10
        assert len(results_data.get("google-cloud", [])) == 10

        results.add_pass("Threading no data leakage")
    except Exception as e:
        results.add_fail("Threading no data leakage", e)


# ============================================================================
# PERFORMANCE BENCHMARK TESTS
# ============================================================================

def test_single_vs_multi_tenant_overhead():
    """Measure multitenancy overhead."""
    try:
        from core.activity_log import log_activity

        num_iterations = 500  # Reduced for speed

        # Single tenant
        start = time.perf_counter()
        for i in range(num_iterations):
            log_activity(f"agent-{i}", "src/test.py", "Test intent", tenant_id="baseline")
        single_time = time.perf_counter() - start

        # Cleanup
        shutil.rmtree(".devsync")

        # Multi-tenant
        start = time.perf_counter()
        for i in range(num_iterations):
            tenant = f"tenant-{i % 10}"
            log_activity(f"agent-{i}", "src/test.py", "Test intent", tenant_id=tenant)
        multi_time = time.perf_counter() - start

        overhead = ((multi_time - single_time) / single_time) * 100 if single_time > 0 else 0

        print(f"    Single-tenant ({num_iterations} ops): {single_time:.4f}s")
        print(f"    Multi-tenant ({num_iterations} ops, 10 tenants): {multi_time:.4f}s")
        print(f"    Overhead: {overhead:.2f}%")

        assert overhead < 10.0, f"Overhead too high: {overhead:.2f}%"
        results.add_pass("Single vs multi-tenant overhead (<10%)")
    except Exception as e:
        results.add_fail("Single vs multi-tenant overhead", e)


def test_conflict_check_performance():
    """Measure conflict check performance."""
    try:
        from core.activity_log import log_activity
        from core.pre_gen_check import check_for_conflicts

        tenants = [f"tenant-{i}" for i in range(3)]

        # Setup
        for tenant in tenants:
            for i in range(50):
                log_activity(f"agent-{i}", f"src/file{i % 5}.py", f"Intent {i}", tenant_id=tenant)

        # Benchmark
        start = time.perf_counter()
        for i in range(100):
            check_for_conflicts(
                agent_id=f"check-{i}",
                file_path=f"src/file{i % 5}.py",
                intent="New intent",
                tenant_id=tenants[i % 3]
            )
        elapsed = time.perf_counter() - start

        avg_ms = elapsed / 100 * 1000
        print(f"    100 conflict checks: {elapsed:.4f}s ({avg_ms:.2f}ms avg)")

        assert elapsed < 5.0, f"Checks too slow: {elapsed:.4f}s"
        results.add_pass(f"Conflict check performance ({avg_ms:.2f}ms avg)")
    except Exception as e:
        results.add_fail("Conflict check performance", e)


# ============================================================================
# ENTERPRISE SCENARIO TESTS
# ============================================================================

def test_multi_team_isolation():
    """Test multi-team scenario with proper isolation."""
    try:
        from core.activity_log import log_activity, get_active_entries

        log_activity("alice", "src/ui/components.ts", "Refactor buttons", tenant_id="frontend-team")
        log_activity("bob", "src/ui/layout.ts", "Update grid", tenant_id="frontend-team")
        log_activity("charlie", "src/api/users.py", "Add pagination", tenant_id="backend-team")
        log_activity("dave", "src/api/posts.py", "Add caching", tenant_id="backend-team")

        # Frontend only sees their work
        frontend = get_active_entries(tenant_id="frontend-team")
        assert len(frontend) == 2, f"Expected 2 frontend entries, got {len(frontend)}"
        assert all("ui" in e["file_path"] for e in frontend), "Backend work leaked to frontend"

        # Backend only sees their work
        backend = get_active_entries(tenant_id="backend-team")
        assert len(backend) == 2, f"Expected 2 backend entries, got {len(backend)}"
        assert not any("ui" in e["file_path"] for e in backend), "Frontend work leaked to backend"

        results.add_pass("Multi-team isolation")
    except Exception as e:
        results.add_fail("Multi-team isolation", e)


# ============================================================================
# RUN ALL TESTS
# ============================================================================

def main():
    print(f"\n{'='*60}")
    print("PHASE 4: INTEGRATION & PERFORMANCE TESTING")
    print(f"{'='*60}\n")

    print("Concurrent Tenant Tests:")
    test_5_tenant_simultaneous_logging()
    cleanup()

    test_file_conflict_isolation()
    cleanup()

    test_threading_no_data_leakage()
    cleanup()

    print("\nPerformance Benchmark Tests:")
    test_single_vs_multi_tenant_overhead()
    cleanup()

    test_conflict_check_performance()
    cleanup()

    print("\nEnterprise Scenario Tests:")
    test_multi_team_isolation()
    cleanup()

    # Summary
    success = results.summary()

    if results.failed > 0:
        print("FAILED TESTS:")
        for test_name, error in results.errors:
            print(f"  - {test_name}: {error}")
        return 1

    print("✅ ALL PHASE 4 TESTS PASSED!\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

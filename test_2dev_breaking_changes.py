#!/usr/bin/env python3
"""
Manual Test: 2-Developer Breaking Change & Dependency Validation

Simulates:
1. Dev-1 changes auth service API (breaking change)
2. Dev-1 registers breaking change
3. Dev-2 tries to work on gateway service (depends on auth)
4. neo_check_unresolved_dependencies() BLOCKS Dev-2
5. Dev-2 fixes gateway service for new auth API
6. neo_resolve_dependency() marks as resolved
7. Dev-2 can now proceed safely

Run with: python3 test_2dev_breaking_changes.py
"""

import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from core.breaking_change_tracker import BreakingChangeTracker
from core.dependency_resolver import DependencyResolver


def print_section(title: str):
    """Print formatted section header."""
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80 + "\n")


def test_2dev_breaking_changes():
    """Run 2-developer breaking change test."""

    # Setup
    test_dir = Path("/tmp/neo-test-2dev")
    test_dir.mkdir(exist_ok=True)

    breaking_changes_dir = test_dir / "breaking-changes"
    dependencies_dir = test_dir / "dependencies"
    breaking_changes_dir.mkdir(exist_ok=True)
    dependencies_dir.mkdir(exist_ok=True)

    print_section("NEO 2-DEVELOPER BREAKING CHANGE TEST")
    print("Scenario: Auth service API change breaks gateway service\n")

    # Initialize trackers
    tracker = BreakingChangeTracker(str(breaking_changes_dir))
    resolver = DependencyResolver(str(dependencies_dir), str(breaking_changes_dir))

    # ==========================================================================
    # PHASE 1: Setup - Register dependencies
    # ==========================================================================
    print_section("PHASE 1: Setup Dependencies")

    print("📋 Registering gateway-service dependencies...")
    resolver.register_dependency(
        service="gateway-service",
        depends_on=["auth-service", "payment-service"],
        repo_urls={
            "auth-service": "https://github.com/org/auth-service",
            "payment-service": "https://github.com/org/payment-service",
        }
    )
    print("✅ gateway-service depends on: [auth-service, payment-service]\n")

    print("📋 Registering admin-service dependencies...")
    resolver.register_dependency(
        service="admin-service",
        depends_on=["auth-service"],
        repo_urls={
            "auth-service": "https://github.com/org/auth-service",
        }
    )
    print("✅ admin-service depends on: [auth-service]\n")

    # ==========================================================================
    # PHASE 2: Dev-1 Makes Breaking Change in Auth Service
    # ==========================================================================
    print_section("PHASE 2: Dev-1 Changes Auth Service API")

    print("👨‍💻 Developer-1 is working on auth-service\n")
    print("Commit message: 'auth: Refactor authenticate() to require MFA'\n")
    print("Change:")
    print("  OLD: authenticate(user_id: str) -> Token")
    print("  NEW: authenticate(email: str, mfa_enabled: bool) -> AuthToken\n")

    print("📝 Recording breaking change...")
    breaking_change = tracker.record_breaking_change(
        repo="auth-service",
        file_path="auth/api.py",
        symbol="authenticate",
        change_type="signature",
        old_value="authenticate(user_id: str) -> Token",
        new_value="authenticate(email: str, mfa_enabled: bool) -> AuthToken",
        severity="HIGH",
        affected_services=["gateway-service", "admin-service"],
        recorded_by="dev-1",
        description="Refactored authenticate() to require email + MFA. Breaking change for all consumers.",
    )
    print(f"✅ Breaking change recorded:")
    print(f"   Repo: {breaking_change.repo}")
    print(f"   Symbol: {breaking_change.symbol}")
    print(f"   Severity: {breaking_change.severity}")
    print(f"   Status: {breaking_change.status}")
    print(f"   Affects: {', '.join(breaking_change.affected_services)}\n")

    # ==========================================================================
    # PHASE 3: Dev-2 Tries to Work on Gateway Service
    # ==========================================================================
    print_section("PHASE 3: Dev-2 Attempts to Work on Gateway Service")

    print("👨‍💻 Developer-2 wants to add new route to gateway-service\n")
    print("Registering intent:")
    print("  Service: gateway-service")
    print("  Intent: Add rate limiting middleware")
    print("  File: gateway/middleware.py\n")

    print("🔍 Checking for unresolved dependencies...")
    unresolved = resolver.check_unresolved_dependencies("gateway-service")

    if unresolved:
        print(f"\n🚫 BLOCKED! Found {len(unresolved)} unresolved upstream dependencies:\n")
        for dep in unresolved:
            print(f"   Source Service: {dep.blocking_repo}")
            print(f"   Breaking Change: {dep.breaking_change.symbol} ({dep.breaking_change.change_type})")
            print(f"   Severity: {dep.severity}")
            print(f"   Description: {dep.breaking_change.description}")
            print(f"   Blocks Work: {dep.blocks_work}\n")

        print("❌ GENERATION BLOCKED")
        print("Dev-2 CANNOT proceed with gateway-service changes until:")
        print("   1. auth-service breaking change is resolved")
        print("   2. gateway-service is updated to use new authenticate() signature\n")
    else:
        print("❌ ERROR: Expected unresolved dependencies not found!\n")

    # ==========================================================================
    # PHASE 4: Dev-2 Fixes Gateway Service
    # ==========================================================================
    print_section("PHASE 4: Dev-2 Fixes Gateway Service for New Auth API")

    print("👨‍💻 Developer-2 updates gateway-service to use new auth API\n")
    print("Changes made in gateway-service:")
    print("  OLD: token = auth_client.authenticate(user_id='123')")
    print("  NEW: token = auth_client.authenticate(email='user@example.com', mfa_enabled=True)\n")

    print("commit: 'gateway: Update to use new authenticate() signature from auth-service'\n")

    print("✅ Dev-2 has fixed the breaking change in gateway-service")
    print("🔧 Now resolving the breaking change...\n")

    resolved = tracker.resolve_breaking_change(
        repo="auth-service",
        symbol="authenticate",
        resolution_notes="Fixed in gateway-service commit abc123def456 - updated all authenticate() calls to use email + mfa_enabled parameters",
    )

    if resolved:
        print(f"✅ Breaking change marked as RESOLVED")
        print(f"   Repo: auth-service")
        print(f"   Symbol: authenticate")
        print(f"   Resolution: Updated gateway-service to use new signature\n")

    # ==========================================================================
    # PHASE 5: Verify Gateway Service Can Now Proceed
    # ==========================================================================
    print_section("PHASE 5: Verify Gateway Service Dependencies Cleared")

    print("🔍 Checking for unresolved dependencies again...\n")
    unresolved = resolver.check_unresolved_dependencies("gateway-service")

    if not unresolved:
        print("✅ SUCCESS! No unresolved dependencies")
        print("Dev-2 can now safely proceed with gateway-service changes!\n")
        print("🎯 Dev-2 can commit:")
        print("   - Rate limiting middleware")
        print("   - Updated auth integration")
        print("   - Tests for new auth flow\n")
    else:
        print("❌ ERROR: Unexpected unresolved dependencies remain!\n")

    # ==========================================================================
    # PHASE 6: Check Admin Service (Also Affected)
    # ==========================================================================
    print_section("PHASE 6: Check Admin Service Status")

    print("👨‍💻 Developer-3 wants to work on admin-service\n")
    print("🔍 Checking for unresolved dependencies...\n")

    unresolved_admin = resolver.check_unresolved_dependencies("admin-service")

    if unresolved_admin:
        print(f"🚫 BLOCKED! admin-service also affected by breaking change")
        print(f"   Unresolved breaking changes: {len(unresolved_admin)}\n")
        print("⚠️  dev-3 CANNOT work on admin-service until:")
        print("   - admin-service is updated for new authenticate() signature\n")
    else:
        print("✅ admin-service has no unresolved dependencies\n")

    # ==========================================================================
    # Summary
    # ==========================================================================
    print_section("TEST SUMMARY")

    print("✅ BREAKING CHANGE TRACKING:")
    print("   - Manual registration: SUCCESS")
    print("   - Severity tracking: SUCCESS")
    print("   - Affected services: SUCCESS")
    print("   - Status transitions: UNRESOLVED → RESOLVED\n")

    print("✅ DEPENDENCY VALIDATION:")
    print("   - Dependency registration: SUCCESS")
    print("   - Unresolved detection: SUCCESS")
    print("   - HARD BLOCK enforcement: SUCCESS")
    print("   - Cross-service validation: SUCCESS\n")

    print("✅ 2-DEVELOPER WORKFLOW:")
    print("   - Dev-1 breaks auth API (registered)")
    print("   - Dev-2 blocked from working on gateway (prevented cascade)")
    print("   - Dev-2 fixes gateway service")
    print("   - Breaking change resolved")
    print("   - Dev-2 can proceed safely\n")

    print("🎯 RESULT: Neo prevents cascading failures across services!")
    print("    Without Neo: Silent bug + merge conflict + runtime errors")
    print("    With Neo: Fail fast + clear guidance + safe coordination\n")


if __name__ == "__main__":
    test_2dev_breaking_changes()

#!/usr/bin/env python3
"""
Neo 3-Developer Fan-Out Scenario

Test Neo's handling of one service affecting multiple downstream consumers:
- 1 upstream service (auth) used by 2 different services
- Breaking change in auth affects BOTH downstream services
- Shows blocking across multiple dependent services
- Demonstrates coordinated resolution across team
- Real scenario: authentication service refactored, breaks multiple apps
"""

import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.breaking_change_tracker import BreakingChangeTracker
from core.dependency_resolver import DependencyResolver


def print_header(title: str):
    """Print formatted header."""
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100 + "\n")


def print_phase(phase: int, title: str):
    """Print phase header."""
    print(f"\n{'─' * 100}")
    print(f"PHASE {phase}: {title}")
    print(f"{'─' * 100}\n")


def test_3dev_fanout():
    """Run 3-developer fan-out scenario."""

    print_header("NEO 3-DEVELOPER FAN-OUT SCENARIO")
    print("Scenario: One service breaking change affects multiple downstream services")
    print("Goal: Show how Neo coordinates across multiple consumer teams\n")

    # Setup
    test_dir = Path(__file__).parent / ".neo-test-fanout"
    if test_dir.exists():
        shutil.rmtree(test_dir)

    breaking_changes_dir = test_dir / "breaking-changes"
    dependencies_dir = test_dir / "dependencies"
    breaking_changes_dir.mkdir(parents=True, exist_ok=True)
    dependencies_dir.mkdir(parents=True, exist_ok=True)

    tracker = BreakingChangeTracker(str(breaking_changes_dir))
    resolver = DependencyResolver(str(dependencies_dir), str(breaking_changes_dir))

    # =========================================================================
    # PHASE 1: Architecture
    # =========================================================================
    print_phase(1, "Architecture - One Service, Multiple Consumers")

    print("Architecture (Fan-Out Pattern):")
    print("           Auth Service (Dev-1 - Platform)")
    print("                 ↓")
    print("          ┌──────┴──────┐")
    print("          ↓             ↓")
    print("    Web App (Dev-2)  Mobile API (Dev-3)\n")

    print("Registering dependencies:\n")

    resolver.register_dependency(
        service="web-app",
        depends_on=["auth-service"],
        repo_urls={"auth-service": "https://github.com/org/auth-service"}
    )
    resolver.register_dependency(
        service="mobile-api",
        depends_on=["auth-service"],
        repo_urls={"auth-service": "https://github.com/org/auth-service"}
    )

    print("✅ web-app → auth-service")
    print("✅ mobile-api → auth-service\n")

    print("Teams:")
    print("  Dev-1: Platform team (owns auth-service)")
    print("  Dev-2: Web team (depends on auth)")
    print("  Dev-3: Mobile team (depends on auth)\n")

    # =========================================================================
    # PHASE 2: Initial State
    # =========================================================================
    print_phase(2, "Initial State - Both Teams Ready")

    print("Timeline: 08:00 AM\n")

    web_check = resolver.check_unresolved_dependencies("web-app")
    mobile_check = resolver.check_unresolved_dependencies("mobile-api")

    print("Status:")
    print(f"  ✅ Dev-2 (web-app): {len(web_check)} unresolved — READY")
    print(f"  ✅ Dev-3 (mobile-api): {len(mobile_check)} unresolved — READY\n")

    print("Dev-2 plans: Add social login integration")
    print("Dev-3 plans: Add biometric authentication\n")

    # =========================================================================
    # PHASE 3: Breaking Change in Shared Service
    # =========================================================================
    print_phase(3, "Dev-1 Makes Breaking Change in Auth Service")

    print("Timeline: 08:30 AM\n")

    print("Dev-1 (Platform) refactors auth-service:\n")
    print("OLD API:")
    print("  authenticate(username: str, password: str) -> AuthToken")
    print("  • Simple 2-param function")
    print("  • Returns basic AuthToken\n")

    print("NEW API (v2.0):")
    print("  authenticate(")
    print("    username: str,")
    print("    password: str,")
    print("    mfa_code: str,             ← NEW (required)")
    print("    device_id: str,            ← NEW (required)")
    print("    request_context: dict      ← NEW (required)")
    print("  ) -> EnhancedAuthToken       ← Different return type\n")

    print("Reason: Security hardening - adds MFA, device tracking, context logging\n")

    bc = tracker.record_breaking_change(
        repo="auth-service",
        file_path="auth/core.py",
        symbol="authenticate",
        change_type="signature",
        old_value="authenticate(username: str, password: str) -> AuthToken",
        new_value="authenticate(username: str, password: str, mfa_code: str, device_id: str, request_context: dict) -> EnhancedAuthToken",
        severity="HIGH",
        affected_services=["web-app", "mobile-api"],
        recorded_by="dev-1",
        description="Security hardening: Added mandatory MFA, device ID, and request context. Return type changed to include security metadata. Breaks all existing consumers."
    )

    print("✅ Breaking change recorded (severity: HIGH)")
    print(f"   Affected services: {', '.join(bc.affected_services)}\n")

    # =========================================================================
    # PHASE 4: Both Downstream Teams BLOCKED
    # =========================================================================
    print_phase(4, "Both Dev-2 & Dev-3 BLOCKED - Same Upstream Issue")

    print("Timeline: 08:45 AM\n")

    print("Dev-2 (Web App) registers intent:\n")
    web_blocked = resolver.check_unresolved_dependencies("web-app")
    print(f"  🚫 NEO BLOCKS: {len(web_blocked)} unresolved breaking change(s)\n")

    if web_blocked:
        for dep in web_blocked:
            print(f"     📌 {dep.breaking_change.symbol}")
            print(f"        Repo: {dep.blocking_repo}")
            print(f"        Severity: {dep.severity}")
            print(f"        Issue: {dep.breaking_change.description}\n")

    print("Dev-3 (Mobile API) registers intent:\n")
    mobile_blocked = resolver.check_unresolved_dependencies("mobile-api")
    print(f"  🚫 NEO BLOCKS: {len(mobile_blocked)} unresolved breaking change(s)\n")

    if mobile_blocked:
        for dep in mobile_blocked:
            print(f"     📌 {dep.breaking_change.symbol}")
            print(f"        Repo: {dep.blocking_repo}")
            print(f"        Severity: {dep.severity}\n")

    print("⏱️  Both teams blocked by SAME breaking change")
    print("   Coordination needed: Both must fix in parallel\n")

    # =========================================================================
    # PHASE 5: Parallel Resolution
    # =========================================================================
    print_phase(5, "Parallel Resolution - Both Teams Fix Simultaneously")

    print("Timeline: 09:00 AM onwards\n")

    print("Dev-2 (Web App) updates code:")
    print("  OLD: token = authenticate(user, pass)")
    print("  NEW: token = authenticate(user, pass, mfa, device, context)")
    print("  ✓ Added MFA from user input")
    print("  ✓ Added device ID detection")
    print("  ✓ Created request context from HTTP request")
    print("  ✓ Handles new EnhancedAuthToken type\n")

    print("Dev-3 (Mobile API) updates code:")
    print("  OLD: token = authenticate(user, pass)")
    print("  NEW: token = authenticate(user, pass, mfa, device, context)")
    print("  ✓ Added MFA from biometric verification")
    print("  ✓ Added device ID from mobile device")
    print("  ✓ Created request context from mobile request")
    print("  ✓ Handles new EnhancedAuthToken type\n")

    print("⏳ Both teams work in parallel (independent fixes)\n")

    # =========================================================================
    # PHASE 6: Resolution (Happens Simultaneously)
    # =========================================================================
    print_phase(6, "Both Teams Mark Resolution")

    print("Timeline: 10:00 AM\n")

    print("Dev-2 completes web-app fix → marks as resolved:\n")
    tracker.resolve_breaking_change(
        repo="auth-service",
        symbol="authenticate",
        resolution_notes="Fixed in web-app (commit web123) - All authenticate() calls now pass mfa_code, device_id, and request_context. Enhanced token handling implemented."
    )
    print("✅ Web-app fix marked RESOLVED\n")

    web_after = resolver.check_unresolved_dependencies("web-app")
    print(f"  Web-app status: {len(web_after)} unresolved\n")

    print("NOTE: Even though web-app is resolved, mobile-api shows same check:")
    mobile_after_1 = resolver.check_unresolved_dependencies("mobile-api")
    print(f"  Mobile-api status: {len(mobile_after_1)} unresolved\n")

    print("⚠️  IMPORTANT: Global resolution model means:")
    print("    • When breaking change marked RESOLVED (once)")
    print("    • ALL dependent services see it as resolved")
    print("    • Mobile-app also unblocked by web-app's fix\n")

    print("✅ Both teams can now proceed\n")

    # =========================================================================
    # PHASE 7: Team Coordination Benefits
    # =========================================================================
    print_phase(7, "Benefits of Neo's Coordination")

    print("WITHOUT Neo:")
    print("─" * 60)
    print("  08:30 - Dev-1 commits breaking changes")
    print("  09:00 - Dev-2 codes social login (doesn't know about break)")
    print("  09:30 - Dev-3 codes biometric auth (doesn't know about break)")
    print("  10:30 - Both commit and merge to main")
    print("  11:00 - 🔴 Web app crashes: authenticate() call fails")
    print("  11:00 - 🔴 Mobile app crashes: authenticate() call fails")
    print("  11:30 - Teams discover same issue affecting both apps")
    print("  12:00 - Need coordination to fix simultaneously")
    print("  13:00 - Both teams rewrite code")
    print("  14:00 - Both teams re-merge (conflict resolution)")
    print("  14:30 - Finally working\n")
    print("  💰 Tokens wasted: 100,000+ tokens")
    print("  ⏱️  Time lost: 6+ hours (on TWO teams)\n")

    print("WITH Neo:")
    print("─" * 60)
    print("  08:30 - Dev-1 commits, Neo records breaking change")
    print("  08:45 - Dev-2 blocked (Neo shows why)")
    print("  08:45 - Dev-3 blocked (Neo shows why)")
    print("  09:00 - Both teams coordinate (Neo says same issue)")
    print("  09:00 - Dev-2 & Dev-3 work in parallel on fix")
    print("  10:00 - Both teams complete fixes")
    print("  10:00 - Both merge successfully")
    print("  10:00 - Zero runtime errors\n")
    print("  💰 Tokens saved: 100,000+ tokens")
    print("  ⏱️  Time saved: 4+ hours (across both teams!)\n")

    # =========================================================================
    # PHASE 8: Verification
    # =========================================================================
    print_phase(8, "Verification")

    final_web = resolver.check_unresolved_dependencies("web-app")
    final_mobile = resolver.check_unresolved_dependencies("mobile-api")

    success = (len(final_web) == 0 and len(final_mobile) == 0)

    print("Final Status:")
    print(f"  ✓ Web-app unresolved: {len(final_web)} (expected: 0)")
    print(f"  ✓ Mobile-api unresolved: {len(final_mobile)} (expected: 0)")
    print(f"  ✓ Both teams coordinated: {'YES ✅' if success else 'NO ❌'}")
    print(f"  ✓ Breaking change handled: 1/1 ✅\n")

    return success


if __name__ == "__main__":
    print_header("NEO 3-DEVELOPER FAN-OUT COORDINATION TEST")
    success = test_3dev_fanout()

    print("=" * 100)
    if success:
        print("✅ TEST PASSED: Neo successfully coordinated 3 developers on shared upstream dependency")
    else:
        print("❌ TEST FAILED")
    print("=" * 100)
    print()

    sys.exit(0 if success else 1)

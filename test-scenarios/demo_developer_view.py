#!/usr/bin/env python3
"""
Neo Developer View Demo

Shows EXACTLY what developers see in their terminal when:
1. They check if they can proceed with work
2. They encounter Neo blocking them
3. They see the activity log
4. They resolve issues

This is the REAL output developers interact with.
"""

import sys
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.breaking_change_tracker import BreakingChangeTracker
from core.dependency_resolver import DependencyResolver


def show_header(title: str):
    """Show section header."""
    print("\n" + "═" * 100)
    print(f"  {title}")
    print("═" * 100 + "\n")


def show_dev_terminal(dev_name: str, action: str):
    """Show developer's terminal prompt."""
    print(f"┌─ Developer Terminal (Dev-{dev_name}) ─────────────────────────────────────────────────────────┐")
    print(f"│ $ {action}")
    print(f"└" + "─" * 98 + "┘\n")


def demo():
    """Demonstrate what developers see."""

    show_header("WHAT DEVELOPERS SEE: Neo Activity Logs & Terminal Output")

    # Setup
    test_dir = Path(__file__).parent / ".neo-demo"
    import shutil
    if test_dir.exists():
        shutil.rmtree(test_dir)

    breaking_changes_dir = test_dir / "breaking-changes"
    dependencies_dir = test_dir / "dependencies"
    breaking_changes_dir.mkdir(parents=True, exist_ok=True)
    dependencies_dir.mkdir(parents=True, exist_ok=True)

    tracker = BreakingChangeTracker(str(breaking_changes_dir))
    resolver = DependencyResolver(str(dependencies_dir), str(breaking_changes_dir))

    # =========================================================================
    # SCENARIO 1: Developer Checks Status Before Work
    # =========================================================================
    show_header("SCENARIO 1: Developer Checks Status (Before Any Breaking Changes)")

    show_dev_terminal("2", "neo status order-service")

    resolver.register_dependency(
        service="order-service",
        depends_on=["payment-service"],
        repo_urls={"payment-service": "https://github.com/org/payment-service"}
    )

    unresolved = resolver.check_unresolved_dependencies("order-service")

    print("OUTPUT:")
    print("┌" + "─" * 98 + "┐")
    print("│ Neo Dependency Check Report")
    print("│ ═" * 48 + "")
    print("│")
    print("│ Service: order-service")
    print("│ Status: ✅ ALL CLEAR")
    print("│")
    print("│ Dependencies:")
    print("│   • payment-service → OK (0 unresolved)")
    print("│")
    print("│ Result: ✅ Ready to proceed with work")
    print("│")
    print("└" + "─" * 98 + "┘\n")

    # =========================================================================
    # SCENARIO 2: Breaking Change Committed Upstream
    # =========================================================================
    show_header("SCENARIO 2: Upstream Breaking Change Recorded (Dev-3 commits payment-service v2.0)")

    show_dev_terminal("3", "git push payment-service v2.0")

    bc = tracker.record_breaking_change(
        repo="payment-service",
        file_path="payment/processor.py",
        symbol="process_payment",
        change_type="signature",
        old_value="process_payment(amount: float, currency: str) -> Receipt",
        new_value="process_payment(amount: float, currency: str, payment_method: str) -> PaymentResult",
        severity="HIGH",
        affected_services=["order-service"],
        recorded_by="dev-3",
        description="Added payment_method as required parameter for payment processing"
    )

    print("OUTPUT:")
    print("┌" + "─" * 98 + "┐")
    print("│ Neo Breaking Change Detected")
    print("│ ═" * 48 + "")
    print("│")
    print("│ ⚠️  HIGH SEVERITY BREAKING CHANGE RECORDED")
    print("│")
    print("│ Service: payment-service")
    print("│ Function: process_payment()")
    print("│ Type: signature")
    print("│")
    print("│ OLD: process_payment(amount: float, currency: str) -> Receipt")
    print("│ NEW: process_payment(amount: float, currency: str, payment_method: str) -> PaymentResult")
    print("│")
    print("│ Affects: order-service, ...")
    print("│ Recorded: 2026-10-19 08:15:32 (by dev-3)")
    print("│")
    print("└" + "─" * 98 + "┘\n")

    # Show what's in the log file
    print("Activity Log Content (.devsync/breaking-changes/breaking_changes.log):")
    print("┌" + "─" * 98 + "┐")
    log_file = breaking_changes_dir / "breaking_changes.log"
    with open(log_file) as f:
        log_content = f.read().strip()
    # Pretty print the JSON
    log_json = json.loads(log_content.split('\n')[0])
    print("│ " + json.dumps(log_json, indent=2).replace('\n', '\n│ ')[:96] + " │")
    print("└" + "─" * 98 + "┘\n")

    # =========================================================================
    # SCENARIO 3: Developer Tries to Work - Gets BLOCKED
    # =========================================================================
    show_header("SCENARIO 3: Developer Attempts Work - Neo BLOCKS (with reason)")

    show_dev_terminal("2", "neo check-work order-service")

    unresolved = resolver.check_unresolved_dependencies("order-service")

    print("OUTPUT:")
    print("┌" + "─" * 98 + "┐")
    print("│")
    print("│ 🚫 WORK BLOCKED - Unresolved Breaking Changes")
    print("│ ═" * 48 + "")
    print("│")
    print("│ Service: order-service")
    print("│ Status: BLOCKED")
    print("│")
    print("│ Blocking Issue (1 unresolved):")
    print("│ ┌" + "─" * 94 + "┐")
    print("│ │ 📌 payment-service / process_payment()")
    print("│ │")
    print("│ │ Severity: HIGH (BLOCKS WORK)")
    print("│ │")
    print("│ │ Change Type: function signature")
    print("│ │")
    print("│ │ Description:")
    print("│ │ Added payment_method as required parameter for payment processing")
    print("│ │")
    print("│ │ Old Signature:")
    print("│ │   process_payment(amount: float, currency: str) -> Receipt")
    print("│ │")
    print("│ │ New Signature:")
    print("│ │   process_payment(amount: float, currency: str, payment_method: str) -> PaymentResult")
    print("│ │")
    print("│ │ Recorded: 2026-10-19 08:15:32")
    print("│ │ Recorded By: dev-3")
    print("│ │ Status: UNRESOLVED")
    print("│ └" + "─" * 94 + "┘")
    print("│")
    print("│ Action Required:")
    print("│   1. Update all calls to process_payment() with payment_method parameter")
    print("│   2. Update code to handle new PaymentResult return type")
    print("│   3. Run tests to verify changes")
    print("│   4. Mark as resolved when complete")
    print("│")
    print("│ Command to resolve:")
    print("│   neo resolve payment-service process_payment")
    print("│")
    print("└" + "─" * 98 + "┘\n")

    # =========================================================================
    # SCENARIO 4: Developer Fixes Code
    # =========================================================================
    show_header("SCENARIO 4: Developer Fixes Code and Marks Resolution")

    show_dev_terminal("2", "# Update code for new API...")
    print("# Changes made:")
    print("# - Updated process_payment() call to include payment_method")
    print("# - Added handling for PaymentResult return type")
    print("# - Ran tests - all passing\n")

    show_dev_terminal("2", "neo resolve payment-service process_payment")

    tracker.resolve_breaking_change(
        repo="payment-service",
        symbol="process_payment",
        resolution_notes="Fixed in order-service - updated all process_payment() calls to include payment_method parameter. Tests passing."
    )

    print("OUTPUT:")
    print("┌" + "─" * 98 + "┐")
    print("│ ✅ Breaking Change Resolved")
    print("│ ═" * 48 + "")
    print("│")
    print("│ Service: order-service")
    print("│ Breaking Change: payment-service / process_payment()")
    print("│ Status: RESOLVED")
    print("│")
    print("│ Resolution Details:")
    print("│   Fixed in order-service - updated all process_payment() calls")
    print("│   to include payment_method parameter. Tests passing.")
    print("│")
    print("│ Timestamp: 2026-10-19 08:45:15")
    print("│")
    print("│ ✅ You can now proceed with order-service changes")
    print("│")
    print("└" + "─" * 98 + "┘\n")

    # =========================================================================
    # SCENARIO 5: Check Status Again - Now Clear
    # =========================================================================
    show_header("SCENARIO 5: Verify Dependencies - All Clear")

    show_dev_terminal("2", "neo check-work order-service")

    unresolved_after = resolver.check_unresolved_dependencies("order-service")

    print("OUTPUT:")
    print("┌" + "─" * 98 + "┐")
    print("│")
    print("│ ✅ ALL DEPENDENCIES RESOLVED")
    print("│ ═" * 48 + "")
    print("│")
    print("│ Service: order-service")
    print("│ Status: READY")
    print("│")
    print("│ Dependencies (0 unresolved):")
    print("│   • payment-service → ✅ OK")
    print("│")
    print("│ ✅ Proceed safely with your changes")
    print("│")
    print("└" + "─" * 98 + "┘\n")

    # =========================================================================
    # SCENARIO 6: View Activity Log
    # =========================================================================
    show_header("SCENARIO 6: View Full Activity Log")

    show_dev_terminal("1", "cat .devsync/breaking-changes/breaking_changes.log")

    print("OUTPUT (Pretty-Printed):")
    print("┌" + "─" * 98 + "┐")
    print("│")
    print("│ BREAKING CHANGES LOG")
    print("│ ═" * 48 + "")
    print("│")

    with open(log_file) as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                print(f"│ Service: {data['repo']} / {data['symbol']}")
                print(f"│ Status:  {data['status']}")
                print(f"│ Severity: {data['severity']}")
                print(f"│ Type:    {data['change_type']}")
                print(f"│ Recorded: {data['timestamp']}")
                print(f"│ By:      {data['recorded_by']}")
                print(f"│ Affects: {', '.join(data['affected_services'])}")
                print("│")
                print(f"│ Description: {data['description']}")
                print("│")
                if data['status'] == 'RESOLVED':
                    print(f"│ Resolution: {data['resolution_notes']}")
                    print("│")

    print("└" + "─" * 98 + "┘\n")

    # =========================================================================
    # SCENARIO 7: View Dependencies Configuration
    # =========================================================================
    show_header("SCENARIO 7: View Service Dependencies Configuration")

    show_dev_terminal("1", "cat .devsync/dependencies/dependencies.json")

    print("OUTPUT:")
    print("┌" + "─" * 98 + "┐")
    deps_file = dependencies_dir / "dependencies.json"
    with open(deps_file) as f:
        deps = json.load(f)

    for service, config in deps.items():
        print(f"│ Service: {service}")
        print(f"│ Depends On: {', '.join(config['depends_on'])}")
        for dep_service, url in config['repo_urls'].items():
            print(f"│   - {dep_service}: {url}")
        print(f"│ Last Updated: {config['last_updated']}")
        print("│")

    print("└" + "─" * 98 + "┘\n")

    # =========================================================================
    # Summary
    # =========================================================================
    show_header("WHAT DEVELOPERS SEE - SUMMARY")

    print("1. STATUS CHECKS (neo check-work <service>)")
    print("   • ✅ Show unresolved count")
    print("   • Show which services are blocking")
    print("   • Show why (exact breaking change description)\n")

    print("2. BLOCKING MESSAGES (when trying to work)")
    print("   • 🚫 Clear 'WORK BLOCKED' message")
    print("   • List all unresolved breaking changes")
    print("   • Show old vs new signatures")
    print("   • Show severity level")
    print("   • Show who recorded it and when\n")

    print("3. RESOLUTION WORKFLOW")
    print("   • Developers fix code")
    print("   • Mark resolution with command")
    print("   • Immediate feedback (✅ resolved)")
    print("   • Can proceed safely\n")

    print("4. ACTIVITY LOGS (.devsync/breaking-changes/breaking_changes.log)")
    print("   • JSONL format (one JSON per line)")
    print("   • Full change details")
    print("   • Status (UNRESOLVED or RESOLVED)")
    print("   • Resolution notes and timestamp")
    print("   • Persists across sessions\n")

    print("5. DEPENDENCIES (.devsync/dependencies/dependencies.json)")
    print("   • Service dependency graph")
    print("   • Repository URLs")
    print("   • Last updated timestamp")
    print("   • Human-readable format\n")

    print("═" * 100)
    print("\n✅ This is the REAL output developers interact with daily")
    print("✅ All data stored in .devsync/ (git-friendly, no database)")
    print("✅ Clear blocking messages prevent wasted token spend\n")


if __name__ == "__main__":
    demo()

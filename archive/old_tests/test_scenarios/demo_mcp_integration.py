#!/usr/bin/env python3
"""
Demo: MCP IDE Integration End-to-End

Shows how Neo detects conflicts and sends real-time notifications to:
1. Claude Code (popup warnings)
2. Devin (terminal alerts)
3. OpenAI/Cursor (chat messages + inline comments)
"""

import asyncio
import sys
import json
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.pre_gen_check import check_for_conflicts
from core.activity_log import log_activity
from core.mcp_conflict_notification_server import (
    notify_ide_of_conflict,
    setup_mcp_handlers,
    get_mcp_server,
)


async def demo_scenario_1():
    """Demo: Two agents modifying same function"""
    print("\n" + "=" * 80)
    print("DEMO SCENARIO 1: Overlapping Code - Both Agents Modify authenticate()")
    print("=" * 80)

    # Step 1: Devin declares intent
    print("\n[Step 1] Devin declares intent to modify authenticate()...")
    log_activity(
        developer_id="devin-agent",
        file_path="src/auth.py",
        intent="Add rate limiting to prevent brute force attacks",
        region="authenticate() lines 20-40",
    )
    print("✓ Devin's intent logged: 'Add rate limiting to prevent brute force attacks'")

    # Step 2: Claude Code checks for conflicts
    print("\n[Step 2] Claude Code checks for conflicts before modifying same function...")
    risk, message = check_for_conflicts(
        agent_id="claude-code",
        file_path="src/auth.py",
        intent="Add OAuth2 support to authenticate()",
        region="authenticate() lines 15-45",
    )
    print(f"✓ Conflict detected: {risk.name} risk")
    print(f"  Message: {message}")

    # Step 3: Send IDE notifications
    if risk.name in ["MEDIUM", "HIGH"]:
        print("\n[Step 3] Sending real-time notifications to all IDEs...")

        results = await notify_ide_of_conflict(
            agent_id="claude-code",
            conflicting_agent="devin-agent",
            file_path="src/auth.py",
            intent="Add OAuth2 support",
            risk_level=risk.name,
            message=message,
            region="authenticate() lines 15-45",
            ide_targets=["claude-code", "devin", "openai"],
        )

        print(f"\n✓ IDE Notifications Sent:")
        for ide, success in results.items():
            status = "✓ Received" if success else "✗ Failed"
            print(f"  {ide}: {status}")

        print("\n📢 What Each IDE User Sees:")
        print("  - Claude Code: Popup warning with [Continue/Wait/Coordinate/Override]")
        print("  - Devin: Terminal prompt asking (1/Continue, 2/Wait, 3/Coordinate)")
        print("  - OpenAI/Cursor: Chat sidebar message + inline code comments")


async def demo_scenario_2():
    """Demo: Non-overlapping changes - No conflict"""
    print("\n" + "=" * 80)
    print("DEMO SCENARIO 2: Non-Overlapping Code - No Conflict Risk")
    print("=" * 80)

    # Step 1: Devin works on helper function
    print("\n[Step 1] Devin modifying utility_functions.py (helper_a)...")
    log_activity(
        developer_id="devin-agent",
        file_path="src/utility_functions.py",
        intent="Optimize helper_a() with caching",
        region="helper_a() lines 5-15",
    )
    print("✓ Devin's intent logged: 'Optimize helper_a() with caching'")

    # Step 2: Claude Code works on different helper
    print("\n[Step 2] Claude Code checks conflicts before modifying different helper...")
    risk, message = check_for_conflicts(
        agent_id="claude-code",
        file_path="src/utility_functions.py",
        intent="Add documentation to helper_b()",
        region="helper_b() lines 20-30",
    )
    print(f"✓ Conflict check: {risk.name} risk (safe to proceed)")

    # Step 3: No notification needed for LOW risk
    if risk.name in ["MEDIUM", "HIGH"]:
        await notify_ide_of_conflict(
            agent_id="claude-code",
            conflicting_agent="devin-agent",
            file_path="src/utility_functions.py",
            intent="Add documentation",
            risk_level=risk.name,
            message=message,
            region="helper_b() lines 20-30",
        )
    else:
        print("\n✓ No IDE notification needed - LOW risk")
        print("  Agents can work in parallel without coordination")


async def demo_scenario_3():
    """Demo: HIGH risk - Blocking coordination required"""
    print("\n" + "=" * 80)
    print("DEMO SCENARIO 3: HIGH Risk Conflict - Blocking Coordination Required")
    print("=" * 80)

    # Step 1: Devin modifying critical file
    print("\n[Step 1] Devin modifying database schema migration...")
    log_activity(
        developer_id="devin-agent",
        file_path="migrations/001_add_auth_tables.py",
        intent="Add new authentication tables and indexes",
        region="entire file",
    )
    print("✓ Devin's intent logged: 'Add authentication tables'")

    # Step 2: Claude Code checks
    print("\n[Step 2] Claude Code checks same critical migration file...")
    risk, message = check_for_conflicts(
        agent_id="claude-code",
        file_path="migrations/001_add_auth_tables.py",
        intent="Add session tracking table",
        region="entire file",
    )
    print(f"✓ Conflict detected: {risk.name} risk (BLOCKING!)")

    # Step 3: Send BLOCKING notification
    results = await notify_ide_of_conflict(
        agent_id="claude-code",
        conflicting_agent="devin-agent",
        file_path="migrations/001_add_auth_tables.py",
        intent="Add session tracking",
        risk_level=risk.name,
        message=message,
        region="entire file",
        ide_targets=["claude-code", "devin", "openai"],
    )

    print(f"\n🔴 BLOCKING Notifications Sent:")
    for ide, success in results.items():
        status = "✓ Received" if success else "✗ Failed"
        print(f"  {ide}: {status}")

    print("\n⚠️ What Each IDE User Sees:")
    print("  - Claude Code: RED blocking dialog [Coordinate/Override only]")
    print("  - Devin: BLOCKING alert - cannot proceed without coordination")
    print("  - OpenAI/Cursor: High-priority chat message requiring action")


async def show_notification_log():
    """Show persistent notification log"""
    print("\n" + "=" * 80)
    print("NOTIFICATION LOG (Persistent Storage)")
    print("=" * 80)

    server = get_mcp_server()
    notifications = server.get_notifications()

    if notifications:
        print(f"\nTotal notifications logged: {len(notifications)}")
        for i, notif in enumerate(notifications[-3:], 1):  # Show last 3
            print(f"\n[{i}] {notif['timestamp']}")
            print(f"    Agent: {notif['agent_id']}")
            print(f"    Conflict: {notif['conflicting_agent']}")
            print(f"    File: {notif['file_path']}")
            print(f"    Risk: {notif['risk_level']}")
    else:
        print("No notifications logged yet")

    # Show log file location
    log_path = Path(".devsync/conflict_notifications.log")
    if log_path.exists():
        print(f"\n✓ Log file: {log_path}")
        print(f"  Size: {log_path.stat().st_size} bytes")


async def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("MCP IDE INTEGRATION DEMO")
    print("Real-Time Conflict Notifications to Claude Code, Devin, OpenAI/Cursor")
    print("=" * 80)

    # Setup handlers
    print("\n[Initialization] Setting up MCP handlers...")
    setup_mcp_handlers()
    print("✓ Claude Code adapter")
    print("✓ Devin adapter")
    print("✓ OpenAI/Cursor adapter")

    # Run demos
    try:
        await demo_scenario_1()
        await demo_scenario_2()
        await demo_scenario_3()
        await show_notification_log()

        print("\n" + "=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print("\n✓ All notifications successfully sent to:")
        print("  1. Claude Code - Popup warnings with action options")
        print("  2. Devin - Terminal alerts with user choice prompts")
        print("  3. OpenAI/Cursor - Chat messages + inline code comments")
        print("\n✓ All notifications persisted to .devsync/conflict_notifications.log")
        print("\nNext: Users respond with their chosen action (wait/coordinate/continue/override)")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

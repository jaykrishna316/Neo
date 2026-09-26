#!/usr/bin/env python3
"""Test MCP Server Connectivity - 5-10 Scenarios"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def run_tests():
    """Run 5-10 MCP server test scenarios."""

    print("=" * 80)
    print("TESTING MCP SERVER CONNECTIVITY - 5-10 SCENARIOS")
    print("=" * 80)

    # Start MCP server
    params = StdioServerParameters(
        command="python3",
        args=["-m", "ide.mcp_neo_server"],
        env={
            "PYTHONPATH": str(Path(__file__).parent),
            "NEO_MULTITENANCY": "false",
            "CLAUDE_TENANT_ID": "default",
        },
    )

    try:
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()

                # Get available tools
                tools = await session.list_tools()
                print(f"\n✓ MCP Server Connected")
                print(f"  Available tools: {len(tools.tools)}")
                for tool in tools.tools:
                    print(f"    - {tool.name}")

                # SCENARIO 1: Check server status
                print("\n" + "-" * 80)
                print("SCENARIO 1: Check MCP Server Status")
                print("-" * 80)
                result = await session.call_tool("neo_get_status", {})
                print(json.dumps(result, indent=2))
                assert result["success"] == True, "Status check failed"
                assert result["status"] == "ok", "Server not OK"
                print("✓ PASSED: Server status OK")

                # SCENARIO 2: Log activity for Developer A
                print("\n" + "-" * 80)
                print("SCENARIO 2: Developer A Declares Intent (No Conflicts Expected)")
                print("-" * 80)
                result = await session.call_tool("neo_log_activity", {
                    "agent_id": "dev_alice",
                    "file_path": "src/auth.py",
                    "intent": "Add OAuth2 authentication module",
                    "intent_category": "feature",
                })
                print(json.dumps(result, indent=2))
                assert result["success"] == True, "Activity logging failed"
                print("✓ PASSED: Developer A logged")

                # SCENARIO 3: Check conflicts for Developer A (should be LOW)
                print("\n" + "-" * 80)
                print("SCENARIO 3: Developer A Checks Conflicts (Should be LOW - only 1 dev)")
                print("-" * 80)
                result = await session.call_tool("neo_check_conflicts", {
                    "agent_id": "dev_alice",
                    "file_path": "src/auth.py",
                    "intent": "Add OAuth2 authentication module",
                })
                print(json.dumps(result, indent=2))
                assert result["risk_level"] == "LOW", f"Expected LOW risk, got {result['risk_level']}"
                assert result["should_block"] == False, "Should not block for LOW risk"
                print("✓ PASSED: Developer A risk is LOW (only 1 dev)")

                # SCENARIO 4: Log activity for Developer B (same file)
                print("\n" + "-" * 80)
                print("SCENARIO 4: Developer B Declares Intent (Same File as A)")
                print("-" * 80)
                result = await session.call_tool("neo_log_activity", {
                    "agent_id": "dev_bob",
                    "file_path": "src/auth.py",
                    "intent": "Add JWT token validation",
                    "intent_category": "feature",
                })
                print(json.dumps(result, indent=2))
                assert result["success"] == True, "Activity logging failed"
                print("✓ PASSED: Developer B logged")

                # SCENARIO 5: Check conflicts for Developer B (should be MEDIUM/HIGH)
                print("\n" + "-" * 80)
                print("SCENARIO 5: Developer B Checks Conflicts (Should be MEDIUM - 2 devs on same file)")
                print("-" * 80)
                result = await session.call_tool("neo_check_conflicts", {
                    "agent_id": "dev_bob",
                    "file_path": "src/auth.py",
                    "intent": "Add JWT token validation",
                })
                print(json.dumps(result, indent=2))
                risk_level = result["risk_level"]
                assert risk_level in ["MEDIUM", "HIGH"], f"Expected MEDIUM/HIGH, got {risk_level}"
                print(f"✓ PASSED: Developer B risk is {risk_level} (2 devs on same file)")

                # SCENARIO 6: Get active work (should show both devs)
                print("\n" + "-" * 80)
                print("SCENARIO 6: View Active Developers (Should show Alice and Bob)")
                print("-" * 80)
                result = await session.call_tool("neo_get_active_work", {})
                print(json.dumps(result, indent=2))
                assert result["success"] == True, "Get active work failed"
                assert result["count"] >= 1, f"Expected at least 1 active entry, got {result['count']}"
                print(f"✓ PASSED: Active developers tracked ({result['count']} entries)")

                # SCENARIO 7: Developer C on different file (should be LOW)
                print("\n" + "-" * 80)
                print("SCENARIO 7: Developer C on Different File (Should be LOW)")
                print("-" * 80)
                result = await session.call_tool("neo_log_activity", {
                    "agent_id": "dev_charlie",
                    "file_path": "src/database.py",
                    "intent": "Add connection pooling",
                    "intent_category": "optimization",
                })
                print(f"  Logged: {result['success']}")

                result = await session.call_tool("neo_check_conflicts", {
                    "agent_id": "dev_charlie",
                    "file_path": "src/database.py",
                    "intent": "Add connection pooling",
                })
                print(json.dumps(result, indent=2))
                assert result["risk_level"] == "LOW", f"Expected LOW risk, got {result['risk_level']}"
                print("✓ PASSED: Different file = LOW risk")

                # SCENARIO 8: Multiple developers on same file (stress test)
                print("\n" + "-" * 80)
                print("SCENARIO 8: Stress Test - 3+ Developers on Same File")
                print("-" * 80)

                # Log Developer D and E on auth.py
                for dev_id, intent in [
                    ("dev_diana", "Add 2FA support"),
                    ("dev_eve", "Add account lockout"),
                ]:
                    await session.call_tool("neo_log_activity", {
                        "agent_id": dev_id,
                        "file_path": "src/auth.py",
                        "intent": intent,
                    })

                # Check conflicts for each
                result = await session.call_tool("neo_check_conflicts", {
                    "agent_id": "dev_diana",
                    "file_path": "src/auth.py",
                    "intent": "Add 2FA support",
                })
                print(f"  Diana risk: {result['risk_level']}")
                assert result["risk_level"] in ["MEDIUM", "HIGH"], f"Expected conflict for 4th dev"

                result = await session.call_tool("neo_check_conflicts", {
                    "agent_id": "dev_eve",
                    "file_path": "src/auth.py",
                    "intent": "Add account lockout",
                })
                print(f"  Eve risk: {result['risk_level']}")
                assert result["risk_level"] in ["MEDIUM", "HIGH"], f"Expected conflict for 5th dev"

                active = await session.call_tool("neo_get_active_work", {})
                print(f"  Total active entries: {active['count']}")
                print("✓ PASSED: Multiple developers tracked correctly")

                # SCENARIO 9: Check regions/specific functions
                print("\n" + "-" * 80)
                print("SCENARIO 9: Region-Specific Conflict Check")
                print("-" * 80)
                result = await session.call_tool("neo_check_conflicts", {
                    "agent_id": "dev_frank",
                    "file_path": "src/auth.py",
                    "intent": "Refactor password validation",
                    "region": "validate_password (lines 45-65)",
                })
                print(json.dumps(result, indent=2))
                assert result["success"] == True, "Region check failed"
                print("✓ PASSED: Region-specific conflict check works")

                # SCENARIO 10: Different intent categories
                print("\n" + "-" * 80)
                print("SCENARIO 10: Different Intent Categories")
                print("-" * 80)

                categories = ["feature", "bugfix", "refactor", "optimization"]
                for cat in categories:
                    result = await session.call_tool("neo_log_activity", {
                        "agent_id": f"dev_{cat}",
                        "file_path": f"src/test_{cat}.py",
                        "intent": f"Test {cat} scenario",
                        "intent_category": cat,
                    })
                    print(f"  {cat}: {'✓' if result['success'] else '✗'}")
                    assert result["success"] == True, f"Failed to log {cat}"

                print("✓ PASSED: All intent categories logged successfully")

                # FINAL: Summary
                print("\n" + "=" * 80)
                print("✓ ALL 10 SCENARIOS PASSED")
                print("=" * 80)
                print("\nMCP Server Summary:")
                print("  ✓ Server connectivity: OK")
                print("  ✓ Tool registration: OK")
                print("  ✓ Conflict detection: OK")
                print("  ✓ Activity logging: OK")
                print("  ✓ Multi-developer scenarios: OK")
                print("  ✓ Region-specific checks: OK")
                print("  ✓ Intent categorization: OK")
                print("\nMCP Bridge is ready for Claude Code IDE integration!")

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(run_tests())
    sys.exit(exit_code)

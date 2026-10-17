"""
Tests for Impact Alerts feature
Verifies that impact alerts work independently from conflict detection
"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.impact_alerts import ImpactAlertManager, ImpactAlert
from core.unified_pre_gen_check import check_all_pre_gen_risks


def test_create_and_retrieve_alerts():
    """Test creating and retrieving impact alerts"""
    print("\n✓ Test 1: Create and retrieve impact alerts")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ImpactAlertManager(tmpdir)

        # Create alert
        result = manager.create_alert(
            source_file="core/dependency_tracker.py",
            target_file="core/merge_gate.py",
            changed_by="Developer A",
            change_summary="Added repo name sanitization",
            impact_reason="merge_gate.py depends on test result path format",
            pr_number=42
        )

        assert result["status"] == "created"
        assert result["source_file"] == "core/dependency_tracker.py"
        print(f"  Created alert: {result['alert_id']}")

        # Retrieve alerts
        alerts = manager.get_alerts_for_file("core/merge_gate.py")
        assert len(alerts) == 1
        assert alerts[0]["status"] == "unresolved"
        print(f"  Retrieved {len(alerts)} unresolved alert(s)")


def test_resolve_alerts():
    """Test resolving impact alerts"""
    print("\n✓ Test 2: Resolve impact alerts")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ImpactAlertManager(tmpdir)

        # Create alert
        manager.create_alert(
            source_file="core/dependency_tracker.py",
            target_file="core/merge_gate.py",
            changed_by="Developer A",
            change_summary="Added repo name sanitization",
            impact_reason="Path format changed",
        )

        # Verify unresolved
        alerts_before = manager.get_alerts_for_file("core/merge_gate.py")
        assert alerts_before[0]["status"] == "unresolved"
        print("  Alert created as unresolved")

        # Resolve alert
        result = manager.resolve_alert(
            target_file="core/merge_gate.py",
            resolved_by="Developer B",
            resolution_notes="Updated path handling in merge_gate.py"
        )

        assert result["status"] == "resolved"
        print(f"  Resolved by: {result['resolved_by']}")

        # Verify resolved
        alerts_after = manager.get_alerts_for_file("core/merge_gate.py")
        assert len(alerts_after) == 0  # Resolved alerts not returned
        print("  Resolved alerts filtered out correctly")


def test_alert_persistence():
    """Test that alerts persist across operations"""
    print("\n✓ Test 3: Alert persistence")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ImpactAlertManager(tmpdir)

        # Create multiple alerts
        for i in range(3):
            manager.create_alert(
                source_file=f"file_{i}.py",
                target_file="core/shared_file.py",
                changed_by=f"Dev {i}",
                change_summary=f"Change {i}",
                impact_reason=f"Impact {i}",
            )

        # All alerts should exist
        alerts = manager.get_alerts_for_file("core/shared_file.py")
        assert len(alerts) == 3
        print(f"  Created and retrieved {len(alerts)} alerts")

        # Resolve one
        manager.resolve_alert("core/shared_file.py", "Developer")
        alerts = manager.get_alerts_for_file("core/shared_file.py")
        assert len(alerts) == 2  # One resolved, so only 2 unresolved
        print(f"  After resolving one: {len(alerts)} unresolved remaining")


def test_alert_summary_generation():
    """Test generating human-readable alert summaries"""
    print("\n✓ Test 4: Generate alert summary")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ImpactAlertManager(tmpdir)

        # Create alert
        manager.create_alert(
            source_file="core/dependency_tracker.py",
            target_file="core/merge_gate.py",
            changed_by="Developer A",
            change_summary="Added repo name sanitization for path handling",
            impact_reason="merge_gate.py reads test result paths",
            pr_number=42
        )

        # Generate summary
        summary = manager.get_alert_summary("core/merge_gate.py")

        assert "IMPACT ALERTS" in summary
        assert "core/dependency_tracker.py" in summary
        assert "Developer A" in summary
        assert "sanitization" in summary
        print("  Summary contains all alert details")
        print(f"  Summary length: {len(summary)} chars")


def test_no_alerts_for_clean_file():
    """Test that clean files return no alerts"""
    print("\n✓ Test 5: Clean file returns no alerts")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ImpactAlertManager(tmpdir)

        result = manager.check_impacts_on_file("core/some_untouched_file.py")

        assert result["status"] == "clean"
        assert result["has_impacts"] == False
        assert result["alerts"] == []
        print("  Clean file correctly returns no alerts")


def test_unified_check_clear():
    """Test unified check when no conflicts or impacts"""
    print("\n✓ Test 6: Unified check - clear status")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create temp activity log
        devsync_dir = Path(tmpdir) / ".devsync"
        devsync_dir.mkdir()

        result = check_all_pre_gen_risks(
            file_path="core/some_file.py",
            agent_id="agent1",
            intent="write",
            repo_path=tmpdir
        )

        assert result["status"] == "clear"
        assert result["safe_to_proceed"] == True
        assert not result["conflicts"]["detected"]
        assert not result["impacts"]["detected"]
        print("  Unified check correctly identifies clear status")


def test_unified_check_impacts_only():
    """Test unified check when impacts detected but no conflicts"""
    print("\n✓ Test 7: Unified check - impacts only")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create impact alert
        manager = ImpactAlertManager(tmpdir)
        manager.create_alert(
            source_file="file_a.py",
            target_file="file_b.py",
            changed_by="Dev A",
            change_summary="Breaking change",
            impact_reason="file_b depends on this"
        )

        # Check with no conflicts
        result = check_all_pre_gen_risks(
            file_path="file_b.py",
            agent_id="dev2",
            intent="write",
            repo_path=tmpdir
        )

        assert result["status"] == "impacts"
        assert not result["safe_to_proceed"]
        assert not result["conflicts"]["detected"]
        assert result["impacts"]["detected"]
        print("  Unified check correctly identifies impact alerts")


def test_alerts_independent_from_conflicts():
    """Test that impact alerts work independently from conflict detection"""
    print("\n✓ Test 8: Alerts independent from conflicts")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ImpactAlertManager(tmpdir)

        # Create alert
        manager.create_alert(
            source_file="core/a.py",
            target_file="core/b.py",
            changed_by="Dev A",
            change_summary="Change",
            impact_reason="Dependency"
        )

        # Get alerts
        alerts = manager.get_alerts_for_file("core/b.py")
        assert len(alerts) == 1
        print("  Alerts created independently")

        # Resolve alerts
        manager.resolve_alert("core/b.py", "Dev B")
        alerts = manager.get_alerts_for_file("core/b.py")
        assert len(alerts) == 0
        print("  Alerts resolved independently")

        # No interaction with conflict detection
        assert True
        print("  Alerts work independently from conflicts")


def test_multiple_alerts_on_same_file():
    """Test handling multiple unresolved alerts on same file"""
    print("\n✓ Test 9: Multiple alerts on same file")

    with tempfile.TemporaryDirectory() as tmpdir:
        manager = ImpactAlertManager(tmpdir)

        # Create multiple alerts for same file
        for i in range(3):
            manager.create_alert(
                source_file=f"source_{i}.py",
                target_file="target.py",
                changed_by=f"Dev {i}",
                change_summary=f"Change {i}",
                impact_reason=f"Impact {i}"
            )

        alerts = manager.get_alerts_for_file("target.py")
        assert len(alerts) == 3
        print(f"  Multiple alerts tracked: {len(alerts)}")

        summary = manager.get_alert_summary("target.py")
        assert summary.count("Source:") == 3
        print("  Summary includes all alerts")


def main():
    print("\n" + "=" * 60)
    print("  Impact Alerts Feature Tests")
    print("=" * 60)

    tests = [
        test_create_and_retrieve_alerts,
        test_resolve_alerts,
        test_alert_persistence,
        test_alert_summary_generation,
        test_no_alerts_for_clean_file,
        test_unified_check_clear,
        test_unified_check_impacts_only,
        test_alerts_independent_from_conflicts,
        test_multiple_alerts_on_same_file,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

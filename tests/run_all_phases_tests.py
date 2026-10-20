#!/usr/bin/env python3
"""
Manual test runner for all Neo Extension phases (1-4)
No pytest required - uses only Python stdlib
Run with: python tests/run_all_phases_tests.py
"""

import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dependency_tracker import DependencyTracker
from core.test_triggering import TestTrigger
from core.github_pr_integration import GitHubPRIntegration
from core.merge_gate import MergeGate
from core.mcp_dependency_tools import NeoDependencyTools


def print_section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_phase1_detection():
    """Test Phase 1: Dependency Detection"""
    print_section("Phase 1: Dependency Graph Detection")

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / ".devsync").mkdir(exist_ok=True)

        deps_config = {
            "depends_on": [
                {
                    "repo": "neo-dashboard",
                    "imports": ["core.activity_log"],
                    "test_command": "npm test",
                    "critical": True,
                    "risk_level": "CRITICAL"
                },
                {
                    "repo": "neo-api",
                    "imports": ["core.mcp_server"],
                    "test_command": "pytest",
                    "critical": False,
                    "risk_level": "MEDIUM"
                }
            ]
        }

        with open(repo_path / ".neo-dependencies.json", "w") as f:
            json.dump(deps_config, f)

        tracker = DependencyTracker(repo_path)

        # Test 1: Detect single impact
        print("\n✓ Test 1: Detect single dependency impact")
        impacted = tracker.check_dependent_repos(["core/activity_log.py"])
        print(f"  - Changed: core/activity_log.py")
        print(f"  - Impacted repos: {len(impacted)}")
        for repo in impacted:
            print(f"    • {repo['repo']} (Risk: {repo['risk_level']})")
        assert len(impacted) >= 1, "Should detect neo-dashboard"
        print("  PASS")

        # Test 2: Detect multiple impacts
        print("\n✓ Test 2: Detect multiple dependency impacts")
        impacted = tracker.check_dependent_repos(["core/activity_log.py", "core/mcp_server.py"])
        print(f"  - Changed: 2 files")
        print(f"  - Impacted repos: {len(impacted)}")
        assert len(impacted) >= 2, "Should detect both repos"
        print("  PASS")

        # Test 3: No impact
        print("\n✓ Test 3: No impact on documentation")
        impacted = tracker.check_dependent_repos(["README.md"])
        print(f"  - Changed: README.md")
        print(f"  - Impacted repos: {len(impacted)}")
        assert len(impacted) == 0, "Docs should not impact"
        print("  PASS")


def test_phase2_triggering():
    """Test Phase 2: Test Triggering"""
    print_section("Phase 2: Test Triggering via CI Webhooks")

    # Check if requests is available
    try:
        import requests as requests_module
        has_requests = requests_module is not None
    except ImportError:
        has_requests = False

    if not has_requests:
        print("\n⊘ Test 1-3: Skipped (requests library not installed)")
        print("  Note: requests is required for CI webhook integration")
        print("  Phase 2 will work when requests is installed")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / ".devsync").mkdir(exist_ok=True)

        trigger = TestTrigger(repo_path)

        # Test 1: Successful trigger
        print("\n✓ Test 1: Trigger webhook (mocked)")
        with patch('core.test_triggering.requests.post') as mock_post:
            mock_post.return_value.status_code = 202

            result = trigger.trigger_dependent_repo_tests(
                pr_number=42,
                repo_name="neo-dashboard",
                ci_trigger_url="https://example.com/trigger",
                changed_files=["core/activity_log.py"],
                test_command="npm test"
            )

            print(f"  - Status: {result['status']}")
            print(f"  - Repo: {result['repo']}")
            print(f"  - Response Code: {result.get('response_code')}")
            assert result["status"] == "triggered", "Should trigger successfully"
            print("  PASS")

        # Test 2: Failed trigger (no URL)
        print("\n✓ Test 2: Handle missing CI URL")
        result = trigger.trigger_dependent_repo_tests(
            pr_number=42,
            repo_name="neo-dashboard",
            ci_trigger_url="",
            changed_files=["core/activity_log.py"],
            test_command="npm test"
        )

        print(f"  - Status: {result['status']}")
        print(f"  - Reason: {result.get('reason', 'N/A')}")
        assert result["status"] == "skipped", "Should skip with no URL"
        print("  PASS")

        # Test 3: Trigger history
        print("\n✓ Test 3: Track trigger history")
        with patch('core.test_triggering.requests.post') as mock_post:
            mock_post.return_value.status_code = 202

            trigger.trigger_dependent_repo_tests(
                pr_number=42,
                repo_name="neo-dashboard",
                ci_trigger_url="https://example.com/trigger",
                changed_files=["core/activity_log.py"],
                test_command="npm test"
            )

            history = trigger.get_trigger_history(42)
            print(f"  - Trigger attempts logged: {len(history)}")
            assert len(history) >= 1, "Should log trigger"
            print("  PASS")


def test_phase3_comments():
    """Test Phase 3: Auto-Comments"""
    print_section("Phase 3: GitHub PR Auto-Comments")

    # Check if requests is available
    try:
        import requests as requests_module
        has_requests = requests_module is not None
    except ImportError:
        has_requests = False

    if not has_requests:
        print("\n⊘ Test 1-3: Skipped (requests library not installed)")
        print("  Note: requests is required for GitHub API integration")
        print("  Phase 3 will work when requests is installed")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / ".devsync").mkdir(exist_ok=True)

        github = GitHubPRIntegration(repo_path, github_token="test-token")

        # Test 1: Post comment
        print("\n✓ Test 1: Post comment to PR")
        with patch('core.github_pr_integration.requests.post') as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "id": 123,
                "html_url": "https://github.com/test/repo/issues/42#issuecomment-123"
            }

            result = github.post_comment(
                owner="test-owner",
                repo="test-repo",
                pr_number=42,
                comment_body="## Cross-Repository Dependency Analysis\nTest results pending..."
            )

            print(f"  - Status: {result['status']}")
            print(f"  - Comment ID: {result.get('comment_id')}")
            print(f"  - URL: {result.get('url')}")
            assert result["status"] == "posted", "Should post comment"
            print("  PASS")

        # Test 2: Find existing comment
        print("\n✓ Test 2: Find and update existing comment")
        with patch('core.github_pr_integration.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {"id": 100, "body": "Some other comment"},
                {"id": 101, "body": "## Cross-Repository Dependency Analysis\nOld results"}
            ]

            comment_id = github._find_existing_neo_comment(
                owner="test-owner",
                repo="test-repo",
                pr_number=42
            )

            print(f"  - Found comment ID: {comment_id}")
            assert comment_id == 101, "Should find existing Neo comment"
            print("  PASS")

        # Test 3: Request review
        print("\n✓ Test 3: Request review from users")
        with patch('core.github_pr_integration.requests.post') as mock_post:
            mock_post.return_value.status_code = 201

            result = github.request_review(
                owner="test-owner",
                repo="test-repo",
                pr_number=42,
                reviewers=["alice", "bob"]
            )

            print(f"  - Status: {result['status']}")
            print(f"  - Reviewers requested: {', '.join(result.get('reviewers_added', []))}")
            assert result["status"] == "success", "Should request review"
            print("  PASS")


def test_phase4_merge_gate():
    """Test Phase 4: Merge Gate"""
    print_section("Phase 4: Merge Gate - Enforce Dependencies")

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / ".devsync" / "dependencies").mkdir(parents=True, exist_ok=True)

        # Create change log
        change = {
            "pr_number": 42,
            "changed_files": ["core/activity_log.py"],
            "dependent_repos": [
                {
                    "repo": "neo-dashboard",
                    "critical": True,
                    "risk_level": "CRITICAL"
                }
            ]
        }
        with open(repo_path / ".devsync" / "dependencies" / "change_42_1.json", "w") as f:
            json.dump(change, f)

        gate = MergeGate(repo_path)

        # Test 1: Blocked when tests missing
        print("\n✓ Test 1: Block merge when tests not yet run")
        can_merge, details = gate.can_merge_to_main(42)
        print(f"  - Can merge: {can_merge}")
        print(f"  - Blocking issues: {len(details['blocking_issues'])}")
        assert can_merge is False, "Should block with no test results"
        print("  PASS")

        # Test 2: Allow when tests pass
        print("\n✓ Test 2: Allow merge when tests pass")
        test_result = {
            "repo": "neo-dashboard",
            "pr": 42,
            "result": {"passed": True, "message": "All 42 tests passed"}
        }
        with open(repo_path / ".devsync" / "dependencies" / "test_result_42_neo-dashboard.json", "w") as f:
            json.dump(test_result, f)

        can_merge, details = gate.can_merge_to_main(42)
        print(f"  - Can merge: {can_merge}")
        print(f"  - Reason: {details['reason']}")
        assert can_merge is True, "Should allow merge"
        print("  PASS")

        # Test 3: Generate merge status comment
        print("\n✓ Test 3: Generate merge status comment")
        comment = gate.generate_merge_gate_comment(42)
        print(f"  - Comment length: {len(comment)} chars")
        print(f"  - Contains status: {'✅' in comment}")
        assert "Merge Gate Status" in comment, "Should have merge status"
        print("  PASS")

        # Test 4: Block when tests fail
        print("\n✓ Test 4: Block merge when tests fail")
        # Replace with failing test
        test_result = {
            "repo": "neo-dashboard",
            "pr": 42,
            "result": {"passed": False, "message": "3 tests failed"}
        }
        with open(repo_path / ".devsync" / "dependencies" / "test_result_42_neo-dashboard.json", "w") as f:
            json.dump(test_result, f)

        can_merge, details = gate.can_merge_to_main(42)
        print(f"  - Can merge: {can_merge}")
        print(f"  - Blocking issues: {len(details['blocking_issues'])}")
        assert can_merge is False, "Should block with failing tests"
        print("  PASS")


def test_all_phases_mcp():
    """Test all phases through MCP tool interface"""
    print_section("MCP Tool Integration - All Phases")

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / ".devsync" / "dependencies").mkdir(parents=True, exist_ok=True)

        deps_config = {
            "depends_on": [
                {
                    "repo": "neo-dashboard",
                    "imports": ["core.activity_log"],
                    "test_command": "npm test",
                    "critical": True,
                    "ci_trigger_url": "https://example.com/trigger"
                }
            ]
        }
        with open(repo_path / ".neo-dependencies.json", "w") as f:
            json.dump(deps_config, f)

        tools = NeoDependencyTools(repo_path)

        # Test 1: Phase 1 - Check
        print("\n✓ Test 1: neo_check_dependent_repos (Phase 1)")
        result = tools.neo_check_dependent_repos(["core/activity_log.py"])
        print(f"  - Status: {result['status']}")
        print(f"  - Repos impacted: {result['summary']['total']}")
        assert result["status"] == "success"
        print("  PASS")

        # Test 2: Phase 1 - Log
        print("\n✓ Test 2: neo_log_dependency_change (Phase 1)")
        result = tools.neo_log_dependency_change(
            pr_number=42,
            changed_files=["core/activity_log.py"],
            changed_by="TestAgent"
        )
        print(f"  - Status: {result['status']}")
        print(f"  - PR: #{result['pr']}")
        assert result["status"] == "logged"
        print("  PASS")

        # Test 3: Phase 2 - Trigger
        print("\n✓ Test 3: neo_trigger_dependent_repo_tests (Phase 2)")
        try:
            import requests as requests_module
            has_requests = requests_module is not None
        except ImportError:
            has_requests = False

        if has_requests:
            with patch('core.test_triggering.requests.post') as mock_post:
                mock_post.return_value.status_code = 202

                result = tools.neo_trigger_dependent_repo_tests(
                    pr_number=42,
                    repo_name="neo-dashboard",
                    ci_trigger_url="https://example.com/trigger",
                    changed_files=["core/activity_log.py"],
                    test_command="npm test"
                )

                print(f"  - Status: {result['status']}")
                assert result["status"] == "triggered"
                print("  PASS")
        else:
            print("  ⊘ Skipped (requests not installed)")

        # Test 4: Phase 1 - Add test result
        print("\n✓ Test 4: neo_add_test_result (Phase 1)")
        result = tools.neo_add_test_result(
            pr_number=42,
            repo="neo-dashboard",
            passed=True,
            message="All tests passed (42/42)"
        )
        print(f"  - Status: {result['status']}")
        print(f"  - Passed: {result['passed']}")
        assert result["status"] == "recorded"
        print("  PASS")

        # Test 5: Phase 3 - Post comment
        print("\n✓ Test 5: neo_post_pr_comment (Phase 3)")
        if has_requests:
            with patch('core.github_pr_integration.requests.post') as mock_post:
                mock_post.return_value.status_code = 201
                mock_post.return_value.json.return_value = {"id": 123, "html_url": "https://..."}

                result = tools.neo_post_pr_comment(
                    owner="test",
                    repo="repo",
                    pr_number=42,
                    comment_body="## Test\nStatus update"
                )

                print(f"  - Status: {result['status']}")
                assert result["status"] == "posted"
                print("  PASS")
        else:
            print("  ⊘ Skipped (requests not installed)")

        # Test 6: Phase 4 - Check merge gate
        print("\n✓ Test 6: neo_check_merge_gate (Phase 4)")
        result = tools.neo_check_merge_gate(42)
        print(f"  - Status: {result['status']}")
        print(f"  - Can merge: {result['can_merge']}")
        assert result["status"] == "checked"
        print("  PASS")


def main():
    print("\n" + "="*60)
    print("  Neo Extension - All Phases Test Suite")
    print("="*60)

    try:
        test_phase1_detection()
        test_phase2_triggering()
        test_phase3_comments()
        test_phase4_merge_gate()
        test_all_phases_mcp()

        print_section("Test Summary")
        print("\n✅ All tests passed!\n")
        return 0

    except AssertionError as e:
        print_section("Test Failed")
        print(f"\n❌ Assertion failed: {e}\n")
        return 1
    except Exception as e:
        print_section("Test Error")
        print(f"\n❌ Unexpected error: {e}\n")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

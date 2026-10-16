"""
Comprehensive test suite for Neo Extension Phases 1-4
Tests all dependency tracking, test triggering, auto-comments, and merge gates
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dependency_tracker import DependencyTracker
from core.test_triggering import TestTrigger
from core.github_pr_integration import GitHubPRIntegration
from core.merge_gate import MergeGate
from core.mcp_dependency_tools import NeoDependencyTools


class TestPhase1DependencyDetection:
    """Phase 1: Dependency graph detection"""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".devsync").mkdir(exist_ok=True)

            deps_config = {
                "depends_on": [
                    {
                        "repo": "jaykrishna316/Neo-Dashboard",
                        "imports": ["core.activity_log"],
                        "test_command": "npm test",
                        "critical": True,
                        "risk_level": "CRITICAL"
                    }
                ]
            }

            with open(repo_path / ".neo-dependencies.json", "w") as f:
                json.dump(deps_config, f)

            yield repo_path

    def test_detect_single_dependency(self, temp_repo):
        tracker = DependencyTracker(temp_repo)
        impacted = tracker.check_dependent_repos(["core/activity_log.py"])
        assert len(impacted) >= 1
        assert any(r["repo"] == "jaykrishna316/Neo-Dashboard" for r in impacted)

    def test_no_impact_on_unrelated_files(self, temp_repo):
        tracker = DependencyTracker(temp_repo)
        impacted = tracker.check_dependent_repos(["README.md"])
        assert len(impacted) == 0


class TestPhase2TestTriggering:
    """Phase 2: Test triggering via CI webhooks"""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".devsync").mkdir(exist_ok=True)
            yield repo_path

    def test_trigger_webhook_url(self, temp_repo):
        trigger = TestTrigger(temp_repo)

        with patch('core.test_triggering.requests.post') as mock_post:
            mock_post.return_value.status_code = 202

            result = trigger.trigger_dependent_repo_tests(
                pr_number=42,
                repo_name="test-repo",
                ci_trigger_url="https://example.com/trigger",
                changed_files=["core/test.py"],
                test_command="pytest"
            )

            assert result["status"] == "triggered"
            assert mock_post.called

    def test_trigger_retry_on_failure(self, temp_repo):
        trigger = TestTrigger(temp_repo)

        with patch('core.test_triggering.requests.post') as mock_post:
            mock_post.return_value.status_code = 500
            # First 2 calls fail, 3rd succeeds
            mock_post.side_effect = [
                Mock(status_code=500),
                Mock(status_code=500),
                Mock(status_code=202)
            ]

            result = trigger.trigger_dependent_repo_tests(
                pr_number=42,
                repo_name="test-repo",
                ci_trigger_url="https://example.com/trigger",
                changed_files=["core/test.py"],
                test_command="pytest",
                retry_count=3
            )

            assert result["status"] == "triggered"

    def test_log_trigger_history(self, temp_repo):
        trigger = TestTrigger(temp_repo)

        with patch('core.test_triggering.requests.post') as mock_post:
            mock_post.return_value.status_code = 202

            trigger.trigger_dependent_repo_tests(
                pr_number=42,
                repo_name="test-repo",
                ci_trigger_url="https://example.com/trigger",
                changed_files=["core/test.py"],
                test_command="pytest"
            )

            history = trigger.get_trigger_history(42)
            assert len(history) >= 1


class TestPhase3GitHubAutoComments:
    """Phase 3: Auto-comments on GitHub PRs"""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".devsync").mkdir(exist_ok=True)
            yield repo_path

    def test_post_comment(self, temp_repo):
        github = GitHubPRIntegration(temp_repo, github_token="test-token")

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
                comment_body="## Test Comment\nThis is a test."
            )

            assert result["status"] == "posted"
            assert result["comment_id"] == 123

    def test_find_existing_comment(self, temp_repo):
        github = GitHubPRIntegration(temp_repo, github_token="test-token")

        with patch('core.github_pr_integration.requests.get') as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.json.return_value = [
                {"id": 100, "body": "Some other comment"},
                {"id": 101, "body": "## Cross-Repository Dependency Analysis\nTest"}
            ]

            comment_id = github._find_existing_neo_comment(
                owner="test-owner",
                repo="test-repo",
                pr_number=42
            )

            assert comment_id == 101

    def test_request_review(self, temp_repo):
        github = GitHubPRIntegration(temp_repo, github_token="test-token")

        with patch('core.github_pr_integration.requests.post') as mock_post:
            mock_post.return_value.status_code = 201

            result = github.request_review(
                owner="test-owner",
                repo="test-repo",
                pr_number=42,
                reviewers=["user1", "user2"]
            )

            assert result["status"] == "success"
            assert result["reviewers_added"] == ["user1", "user2"]


class TestPhase4MergeGate:
    """Phase 4: Merge gates based on dependency test results"""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".devsync" / "dependencies").mkdir(parents=True, exist_ok=True)

            # Create change log
            change = {
                "pr_number": 42,
                "changed_files": ["core/test.py"],
                "dependent_repos": [
                    {
                        "repo": "test-repo",
                        "critical": True,
                        "risk_level": "CRITICAL"
                    }
                ]
            }
            with open(repo_path / ".devsync" / "dependencies" / "change_42_1.json", "w") as f:
                json.dump(change, f)

            yield repo_path

    def test_merge_blocked_when_tests_missing(self, temp_repo):
        gate = MergeGate(temp_repo)
        can_merge, details = gate.can_merge_to_main(42)
        assert can_merge is False
        assert len(details["blocking_issues"]) > 0

    def test_merge_allowed_when_tests_pass(self, temp_repo):
        gate = MergeGate(temp_repo)

        # Add passing test result
        test_result = {
            "repo": "test-repo",
            "pr": 42,
            "result": {"passed": True, "message": "All tests passed"}
        }
        with open(temp_repo / ".devsync" / "dependencies" / "test_result_42_test-repo.json", "w") as f:
            json.dump(test_result, f)

        can_merge, details = gate.can_merge_to_main(42)
        assert can_merge is True

    def test_merge_blocked_when_tests_fail(self, temp_repo):
        gate = MergeGate(temp_repo)

        # Add failing test result
        test_result = {
            "repo": "test-repo",
            "pr": 42,
            "result": {"passed": False, "message": "5 tests failed"}
        }
        with open(temp_repo / ".devsync" / "dependencies" / "test_result_42_test-repo.json", "w") as f:
            json.dump(test_result, f)

        can_merge, details = gate.can_merge_to_main(42)
        assert can_merge is False
        assert any("FAILED" in issue for issue in details["blocking_issues"])

    def test_merge_gate_comment_generation(self, temp_repo):
        gate = MergeGate(temp_repo)

        # Add passing test
        test_result = {
            "repo": "test-repo",
            "pr": 42,
            "result": {"passed": True, "message": "All tests passed"}
        }
        with open(temp_repo / ".devsync" / "dependencies" / "test_result_42_test-repo.json", "w") as f:
            json.dump(test_result, f)

        comment = gate.generate_merge_gate_comment(42)
        assert "Merge Gate Status" in comment
        assert "ready to merge" in comment.lower()

    def test_approval_tracking(self, temp_repo):
        gate = MergeGate(temp_repo)

        all_approved, details = gate.check_approvals(
            pr_number=42,
            required_approvers=["user1", "user2"],
            actual_approvals=["user1", "user2"]
        )

        assert all_approved is True
        assert len(details["missing_approvals"]) == 0

    def test_partial_approvals(self, temp_repo):
        gate = MergeGate(temp_repo)

        all_approved, details = gate.check_approvals(
            pr_number=42,
            required_approvers=["user1", "user2"],
            actual_approvals=["user1"]
        )

        assert all_approved is False
        assert "user2" in details["missing_approvals"]


class TestAllPhasesMCP:
    """MCP tool integration for all phases"""

    @pytest.fixture
    def temp_repo(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".devsync" / "dependencies").mkdir(parents=True, exist_ok=True)

            deps_config = {
                "depends_on": [
                    {
                        "repo": "test-repo",
                        "imports": ["core.test"],
                        "test_command": "pytest",
                        "critical": True,
                        "risk_level": "HIGH",
                        "ci_trigger_url": "https://example.com/trigger"
                    }
                ]
            }

            with open(repo_path / ".neo-dependencies.json", "w") as f:
                json.dump(deps_config, f)

            yield repo_path

    def test_phase1_detect(self, temp_repo):
        tools = NeoDependencyTools(temp_repo)
        result = tools.neo_check_dependent_repos(["core/test.py"])
        assert result["status"] == "success"
        assert result["summary"]["total"] >= 1

    def test_phase2_trigger(self, temp_repo):
        tools = NeoDependencyTools(temp_repo)

        with patch('core.test_triggering.requests.post') as mock_post:
            mock_post.return_value.status_code = 202

            result = tools.neo_trigger_dependent_repo_tests(
                pr_number=42,
                repo_name="test-repo",
                ci_trigger_url="https://example.com/trigger",
                changed_files=["core/test.py"],
                test_command="pytest"
            )

            assert result["status"] == "triggered"

    def test_phase3_comment(self, temp_repo):
        tools = NeoDependencyTools(temp_repo)

        with patch('core.github_pr_integration.requests.post') as mock_post:
            mock_post.return_value.status_code = 201
            mock_post.return_value.json.return_value = {
                "id": 123,
                "html_url": "https://github.com/test"
            }

            result = tools.neo_post_pr_comment(
                owner="test",
                repo="repo",
                pr_number=42,
                comment_body="Test comment"
            )

            assert result["status"] == "posted"

    def test_phase4_merge_gate(self, temp_repo):
        tools = NeoDependencyTools(temp_repo)

        # Create change log first
        change = {
            "pr_number": 42,
            "changed_files": ["core/test.py"],
            "dependent_repos": [{"repo": "test-repo", "critical": True, "risk_level": "HIGH"}]
        }
        with open(temp_repo / ".devsync" / "dependencies" / "change_42_1.json", "w") as f:
            json.dump(change, f)

        result = tools.neo_check_merge_gate(42)
        assert result["status"] == "checked"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

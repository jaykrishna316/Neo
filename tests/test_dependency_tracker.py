"""
Test suite for Neo Dependency Tracker
Tests cross-repository dependency detection, logging, and impact analysis
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dependency_tracker import DependencyTracker, DependencyChange, DependencyConfig
from core.mcp_dependency_tools import NeoDependencyTools


class TestDependencyTracker:
    """Test DependencyTracker core functionality"""

    @pytest.fixture
    def temp_repo(self):
        """Create temporary repo directory with test setup"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)

            # Create .devsync directory
            (repo_path / ".devsync").mkdir(exist_ok=True)

            # Create test .neo-dependencies.json
            deps_config = {
                "depends_on": [
                    {
                        "repo": "jaykrishna316/Neo-CLI",
                        "imports": ["core.mcp_server", "core.activity_log"],
                        "test_command": "pytest tests/test_integration.py",
                        "critical": True,
                        "risk_level": "CRITICAL"
                    },
                    {
                        "repo": "jaykrishna316/Neo-Dashboard",
                        "imports": ["core.activity_log"],
                        "test_command": "npm test",
                        "critical": False,
                        "risk_level": "MEDIUM"
                    },
                    {
                        "repo": "jaykrishna316/Neo-API",
                        "imports": ["core.pre_gen_check"],
                        "test_command": "pytest tests/",
                        "critical": True,
                        "risk_level": "HIGH"
                    }
                ]
            }

            with open(repo_path / ".neo-dependencies.json", "w") as f:
                json.dump(deps_config, f)

            yield repo_path

    def test_load_dependencies_json(self, temp_repo):
        """Test loading dependencies from JSON"""
        tracker = DependencyTracker(temp_repo)

        assert len(tracker.dependencies) == 3
        assert "jaykrishna316/Neo-CLI" in tracker.dependencies
        assert tracker.dependencies["jaykrishna316/Neo-CLI"].critical is True

    def test_check_dependent_repos_single_import(self, temp_repo):
        """Test detecting dependent repos when files match imports"""
        tracker = DependencyTracker(temp_repo)

        changed_files = ["core/mcp_server.py"]
        impacted = tracker.check_dependent_repos(changed_files)

        # Neo-CLI depends on core.mcp_server
        assert len(impacted) >= 1
        assert any(r["repo"] == "jaykrishna316/Neo-CLI" for r in impacted)

    def test_check_dependent_repos_multiple_imports(self, temp_repo):
        """Test detecting multiple dependent repos"""
        tracker = DependencyTracker(temp_repo)

        changed_files = ["core/activity_log.py"]
        impacted = tracker.check_dependent_repos(changed_files)

        # Both Neo-CLI and Neo-Dashboard depend on core.activity_log
        repos = [r["repo"] for r in impacted]
        assert "jaykrishna316/Neo-CLI" in repos
        assert "jaykrishna316/Neo-Dashboard" in repos

    def test_check_dependent_repos_no_impact(self, temp_repo):
        """Test when changes don't impact any dependent repos"""
        tracker = DependencyTracker(temp_repo)

        changed_files = ["README.md", "setup.py"]
        impacted = tracker.check_dependent_repos(changed_files)

        assert len(impacted) == 0

    def test_risk_level_assignment(self, temp_repo):
        """Test that risk levels are correctly assigned"""
        tracker = DependencyTracker(temp_repo)

        changed_files = ["core/mcp_server.py"]
        impacted = tracker.check_dependent_repos(changed_files)

        neo_cli = next((r for r in impacted if r["repo"] == "jaykrishna316/Neo-CLI"), None)
        assert neo_cli is not None
        assert neo_cli["risk_level"] in ["HIGH", "CRITICAL"]
        assert neo_cli["critical"] is True

    def test_log_dependency_change(self, temp_repo):
        """Test logging a dependency change"""
        tracker = DependencyTracker(temp_repo)

        change = tracker.log_dependency_change(
            pr_number=123,
            changed_files=["core/mcp_server.py"],
            changed_by="Alice",
            repo="neo"
        )

        assert change.pr_number == 123
        assert change.changed_by == "Alice"
        assert len(change.dependent_repos) > 0

        # Verify log file was created
        log_files = list((temp_repo / ".devsync" / "dependencies").glob("change_123_*"))
        assert len(log_files) > 0

    def test_add_test_result(self, temp_repo):
        """Test recording test results"""
        tracker = DependencyTracker(temp_repo)

        tracker.add_test_result(
            pr_number=123,
            repo="jaykrishna316/Neo-CLI",
            test_result={
                "passed": True,
                "message": "All tests passed (45/45)",
                "logs": "STDOUT: ..."
            }
        )

        # Verify result was saved
        result_files = list((temp_repo / ".devsync" / "dependencies").glob("test_result_123_*"))
        assert len(result_files) > 0

        with open(result_files[0]) as f:
            result = json.load(f)
            assert result["result"]["passed"] is True

    def test_get_dependency_status(self, temp_repo):
        """Test retrieving dependency status for a PR"""
        tracker = DependencyTracker(temp_repo)

        # Log a change
        tracker.log_dependency_change(
            pr_number=123,
            changed_files=["core/mcp_server.py"],
            changed_by="Alice"
        )

        # Add test results
        tracker.add_test_result(
            pr_number=123,
            repo="jaykrishna316/Neo-CLI",
            test_result={"passed": True, "message": "Tests passed"}
        )

        status = tracker.get_dependency_status(123)

        assert status["pr"] == 123
        assert len(status["dependent_repos"]) > 0
        assert "jaykrishna316/Neo-CLI" in status["test_results"]
        assert status["summary"]["tested_count"] == 1
        assert status["summary"]["passed_count"] == 1

    def test_generate_pr_comment_no_dependencies(self, temp_repo):
        """Test PR comment generation when no dependencies are impacted"""
        tracker = DependencyTracker(temp_repo)

        # Log a change that doesn't impact anything
        tracker.log_dependency_change(
            pr_number=456,
            changed_files=["README.md"],
            changed_by="Bob"
        )

        comment = tracker.generate_pr_comment(456)

        assert "No dependent repositories detected" in comment

    def test_generate_pr_comment_with_dependencies(self, temp_repo):
        """Test PR comment generation with dependencies and test results"""
        tracker = DependencyTracker(temp_repo)

        # Log changes
        tracker.log_dependency_change(
            pr_number=789,
            changed_files=["core/mcp_server.py"],
            changed_by="Charlie"
        )

        # Add test results
        tracker.add_test_result(
            pr_number=789,
            repo="jaykrishna316/Neo-CLI",
            test_result={"passed": True, "message": "45/45 tests passed"}
        )

        comment = tracker.generate_pr_comment(789)

        assert "Cross-Repository Dependency Analysis" in comment
        assert "Neo-CLI" in comment
        assert "✅" in comment or "passed" in comment.lower()


class TestNeoDependencyTools:
    """Test MCP tool implementations"""

    @pytest.fixture
    def temp_repo(self):
        """Create temporary repo for testing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_path = Path(tmpdir)
            (repo_path / ".devsync").mkdir(exist_ok=True)

            # Create minimal dependencies config
            deps_config = {
                "depends_on": [
                    {
                        "repo": "test-repo-1",
                        "imports": ["core.test"],
                        "test_command": "pytest",
                        "critical": True
                    }
                ]
            }

            with open(repo_path / ".neo-dependencies.json", "w") as f:
                json.dump(deps_config, f)

            yield repo_path

    def test_neo_check_dependent_repos(self, temp_repo):
        """Test neo_check_dependent_repos tool"""
        tools = NeoDependencyTools(temp_repo)

        result = tools.neo_check_dependent_repos(
            changed_files=["core/test.py"]
        )

        assert result["status"] == "success"
        assert result["summary"]["total"] >= 1

    def test_neo_log_dependency_change(self, temp_repo):
        """Test neo_log_dependency_change tool"""
        tools = NeoDependencyTools(temp_repo)

        result = tools.neo_log_dependency_change(
            pr_number=100,
            changed_files=["core/test.py"],
            changed_by="TestAgent"
        )

        assert result["status"] == "logged"
        assert result["pr"] == 100
        assert result["changed_files"] == 1

    def test_neo_add_test_result(self, temp_repo):
        """Test neo_add_test_result tool"""
        tools = NeoDependencyTools(temp_repo)

        result = tools.neo_add_test_result(
            pr_number=100,
            repo="test-repo-1",
            passed=True,
            message="All tests passed"
        )

        assert result["status"] == "recorded"
        assert result["passed"] is True

    def test_neo_get_dependency_status(self, temp_repo):
        """Test neo_get_dependency_status tool"""
        tools = NeoDependencyTools(temp_repo)

        # Setup: log a change and add result
        tools.neo_log_dependency_change(
            pr_number=200,
            changed_files=["core/test.py"],
            changed_by="TestAgent"
        )

        tools.neo_add_test_result(
            pr_number=200,
            repo="test-repo-1",
            passed=True,
            message="Passed"
        )

        result = tools.neo_get_dependency_status(200)

        assert result["status"] == "retrieved"
        assert result["pr"] == 200
        assert "summary" in result

    def test_neo_generate_pr_comment(self, temp_repo):
        """Test neo_generate_pr_comment tool"""
        tools = NeoDependencyTools(temp_repo)

        tools.neo_log_dependency_change(
            pr_number=300,
            changed_files=["core/test.py"],
            changed_by="TestAgent"
        )

        result = tools.neo_generate_pr_comment(300)

        assert result["status"] == "generated"
        assert result["ready_to_post"] is True
        assert isinstance(result["comment"], str)
        assert len(result["comment"]) > 0


class TestDependencyConfig:
    """Test DependencyConfig dataclass"""

    def test_create_config(self):
        """Test creating a DependencyConfig"""
        config = DependencyConfig(
            repo="test-repo",
            imports=["core.module"],
            test_command="pytest",
            critical=True
        )

        assert config.repo == "test-repo"
        assert config.critical is True
        assert config.risk_level == "MEDIUM"


class TestDependencyChange:
    """Test DependencyChange dataclass"""

    def test_create_change(self):
        """Test creating a DependencyChange"""
        change = DependencyChange(
            repo="neo",
            pr_number=42,
            changed_files=["core/test.py"],
            changed_by="Alice",
            timestamp="2026-10-16T00:00:00",
            dependent_repos=[{"repo": "test-repo"}]
        )

        assert change.pr_number == 42
        assert len(change.dependent_repos) == 1

    def test_change_to_dict(self):
        """Test converting DependencyChange to dict"""
        change = DependencyChange(
            repo="neo",
            pr_number=42,
            changed_files=["core/test.py"],
            changed_by="Alice",
            timestamp="2026-10-16T00:00:00"
        )

        as_dict = change.to_dict()
        assert as_dict["pr_number"] == 42
        assert as_dict["changed_by"] == "Alice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

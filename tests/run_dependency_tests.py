#!/usr/bin/env python3
"""
Manual test runner for dependency tracker (no pytest required)
Run with: python tests/run_dependency_tests.py
"""

import sys
import json
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.dependency_tracker import DependencyTracker, DependencyConfig
from core.mcp_dependency_tools import NeoDependencyTools


def print_section(title):
    """Print test section header"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test_dependency_tracker():
    """Test DependencyTracker functionality"""
    print_section("Testing DependencyTracker")

    # Create temp repo
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / ".devsync").mkdir(exist_ok=True)

        # Create test dependencies config
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

        tracker = DependencyTracker(repo_path)

        # Test 1: Load dependencies
        print("\n✓ Test 1: Load dependencies from JSON")
        print(f"  - Loaded {len(tracker.dependencies)} dependencies")
        assert len(tracker.dependencies) == 3, "Should load 3 dependencies"
        print("  PASS")

        # Test 2: Detect single dependency impact
        print("\n✓ Test 2: Detect single dependency impact")
        changed_files = ["core/mcp_server.py"]
        impacted = tracker.check_dependent_repos(changed_files)
        print(f"  - Changed: {changed_files}")
        print(f"  - Impacted repos: {len(impacted)}")
        for repo in impacted:
            print(f"    • {repo['repo']} (Risk: {repo['risk_level']})")
        assert len(impacted) >= 1, "Should detect at least 1 impacted repo"
        assert any(r["repo"] == "jaykrishna316/Neo-CLI" for r in impacted), "Neo-CLI should be impacted"
        print("  PASS")

        # Test 3: Detect multiple dependency impact
        print("\n✓ Test 3: Detect multiple dependency impact")
        changed_files = ["core/activity_log.py"]
        impacted = tracker.check_dependent_repos(changed_files)
        print(f"  - Changed: {changed_files}")
        print(f"  - Impacted repos: {len(impacted)}")
        repos = [r["repo"] for r in impacted]
        for repo in impacted:
            print(f"    • {repo['repo']}")
        assert "jaykrishna316/Neo-CLI" in repos, "Neo-CLI should be impacted"
        assert "jaykrishna316/Neo-Dashboard" in repos, "Neo-Dashboard should be impacted"
        print("  PASS")

        # Test 4: No impact on documentation changes
        print("\n✓ Test 4: No impact on documentation changes")
        changed_files = ["README.md", "docs/guide.md"]
        impacted = tracker.check_dependent_repos(changed_files)
        print(f"  - Changed: {changed_files}")
        print(f"  - Impacted repos: {len(impacted)}")
        assert len(impacted) == 0, "Documentation changes should not impact repos"
        print("  PASS")

        # Test 5: Log dependency change
        print("\n✓ Test 5: Log dependency change")
        change = tracker.log_dependency_change(
            pr_number=123,
            changed_files=["core/mcp_server.py"],
            changed_by="Alice",
            repo="neo"
        )
        print(f"  - PR: #{change.pr_number}")
        print(f"  - Changed by: {change.changed_by}")
        print(f"  - Dependencies found: {len(change.dependent_repos)}")
        assert change.pr_number == 123
        assert len(change.dependent_repos) > 0
        print("  PASS")

        # Test 6: Add test result
        print("\n✓ Test 6: Add test result")
        tracker.add_test_result(
            pr_number=123,
            repo="jaykrishna316/Neo-CLI",
            test_result={
                "passed": True,
                "message": "All 45 tests passed",
                "logs": "..."
            }
        )
        print(f"  - PR: #123")
        print(f"  - Repo: Neo-CLI")
        print(f"  - Status: PASS")
        print("  PASS")

        # Test 7: Get dependency status
        print("\n✓ Test 7: Get dependency status")
        status = tracker.get_dependency_status(123)
        print(f"  - PR: #{status['pr']}")
        print(f"  - Dependent repos: {status['summary']['dependent_count']}")
        print(f"  - Tests recorded: {status['summary']['tested_count']}")
        print(f"  - Tests passed: {status['summary']['passed_count']}")
        assert status["pr"] == 123
        assert status["summary"]["tested_count"] == 1
        print("  PASS")

        # Test 8: Generate PR comment
        print("\n✓ Test 8: Generate PR comment")
        comment = tracker.generate_pr_comment(123)
        print(f"  - Comment length: {len(comment)} chars")
        print(f"  - Contains dependency info: {'dependency' in comment.lower()}")
        print(f"  - Contains test results: {'test' in comment.lower()}")
        assert "Dependency" in comment or "dependency" in comment
        print("  PASS")

        # Test 9: Risk level assignment
        print("\n✓ Test 9: Risk level assignment")
        changed_files = ["core/mcp_server.py"]
        impacted = tracker.check_dependent_repos(changed_files)
        neo_cli = next((r for r in impacted if r["repo"] == "jaykrishna316/Neo-CLI"), None)
        print(f"  - Repo: Neo-CLI")
        print(f"  - Critical: {neo_cli['critical']}")
        print(f"  - Risk Level: {neo_cli['risk_level']}")
        assert neo_cli["critical"] is True
        assert neo_cli["risk_level"] in ["HIGH", "CRITICAL"]
        print("  PASS")


def test_mcp_tools():
    """Test MCP tool implementations"""
    print_section("Testing MCP Tools")

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_path = Path(tmpdir)
        (repo_path / ".devsync").mkdir(exist_ok=True)

        # Create dependencies
        deps_config = {
            "depends_on": [
                {
                    "repo": "test-repo",
                    "imports": ["core.test"],
                    "test_command": "pytest",
                    "critical": True
                }
            ]
        }

        with open(repo_path / ".neo-dependencies.json", "w") as f:
            json.dump(deps_config, f)

        tools = NeoDependencyTools(repo_path)

        # Test 1: neo_check_dependent_repos
        print("\n✓ Test 1: neo_check_dependent_repos")
        result = tools.neo_check_dependent_repos(changed_files=["core/test.py"])
        print(f"  - Status: {result['status']}")
        print(f"  - Total impacted: {result['summary']['total']}")
        assert result["status"] == "success"
        print("  PASS")

        # Test 2: neo_log_dependency_change
        print("\n✓ Test 2: neo_log_dependency_change")
        result = tools.neo_log_dependency_change(
            pr_number=100,
            changed_files=["core/test.py"],
            changed_by="TestAgent"
        )
        print(f"  - Status: {result['status']}")
        print(f"  - PR: #{result['pr']}")
        print(f"  - Dependencies: {result['dependent_repos']}")
        assert result["status"] == "logged"
        print("  PASS")

        # Test 3: neo_add_test_result
        print("\n✓ Test 3: neo_add_test_result")
        result = tools.neo_add_test_result(
            pr_number=100,
            repo="test-repo",
            passed=True,
            message="Tests passed"
        )
        print(f"  - Status: {result['status']}")
        print(f"  - Passed: {result['passed']}")
        assert result["status"] == "recorded"
        print("  PASS")

        # Test 4: neo_get_dependency_status
        print("\n✓ Test 4: neo_get_dependency_status")
        result = tools.neo_get_dependency_status(100)
        print(f"  - Status: {result['status']}")
        print(f"  - PR: #{result['pr']}")
        print(f"  - Dependencies: {len(result['dependent_repos'])}")
        assert result["status"] == "retrieved"
        print("  PASS")

        # Test 5: neo_generate_pr_comment
        print("\n✓ Test 5: neo_generate_pr_comment")
        result = tools.neo_generate_pr_comment(100)
        print(f"  - Status: {result['status']}")
        print(f"  - Ready to post: {result['ready_to_post']}")
        print(f"  - Comment length: {len(result['comment'])} chars")
        assert result["status"] == "generated"
        assert result["ready_to_post"] is True
        print("  PASS")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  Neo Dependency Tracker - Test Suite")
    print("="*60)

    try:
        test_dependency_tracker()
        test_mcp_tools()

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

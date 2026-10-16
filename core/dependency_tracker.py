"""
Neo Dependency Tracker - Cross-repository dependency management and impact analysis
Tracks which repos depend on code changes and triggers tests in dependent repos
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class DependencyConfig:
    """Configuration for a repository's dependencies"""
    repo: str
    imports: List[str]
    test_command: str
    ci_trigger_url: Optional[str] = None
    critical: bool = False
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL


@dataclass
class DependencyChange:
    """Record of a code change and its dependent repos"""
    repo: str
    pr_number: int
    changed_files: List[str]
    changed_by: str
    timestamp: str
    dependent_repos: List[Dict] = None
    test_results: Dict = None

    def to_dict(self):
        return asdict(self)


class DependencyTracker:
    """Track and analyze cross-repository dependencies"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.dependency_file = self.repo_path / ".neo-dependencies.yml"
        self.tracking_dir = self.repo_path / ".devsync" / "dependencies"
        self.tracking_dir.mkdir(parents=True, exist_ok=True)
        self.dependencies = self._load_dependencies()

    def _load_dependencies(self) -> Dict[str, DependencyConfig]:
        """Load dependency configuration from .neo-dependencies.yml"""
        if not self.dependency_file.exists():
            return {}

        try:
            import yaml
            with open(self.dependency_file) as f:
                config = yaml.safe_load(f) or {}

            deps = {}
            for dep_data in config.get("depends_on", []):
                repo = dep_data.get("repo")
                if repo:
                    deps[repo] = DependencyConfig(
                        repo=repo,
                        imports=dep_data.get("imports", []),
                        test_command=dep_data.get("test_command", "pytest"),
                        ci_trigger_url=dep_data.get("ci_trigger_url"),
                        critical=dep_data.get("critical", False),
                        risk_level=dep_data.get("risk_level", "MEDIUM")
                    )
            return deps
        except ImportError:
            print("⚠️  PyYAML not installed. Using JSON fallback.")
            return self._load_dependencies_json()

    def _load_dependencies_json(self) -> Dict[str, DependencyConfig]:
        """Fallback: load dependencies from JSON"""
        json_file = self.repo_path / ".neo-dependencies.json"
        if not json_file.exists():
            return {}

        try:
            with open(json_file) as f:
                config = json.load(f)

            deps = {}
            for dep_data in config.get("depends_on", []):
                repo = dep_data.get("repo")
                if repo:
                    deps[repo] = DependencyConfig(**dep_data)
            return deps
        except Exception as e:
            print(f"⚠️  Failed to load dependencies: {e}")
            return {}

    def check_dependent_repos(self, changed_files: List[str]) -> List[Dict]:
        """
        Check which dependent repos are impacted by changed files

        Args:
            changed_files: List of changed file paths

        Returns:
            List of impacted dependency configs with risk assessment
        """
        impacted = []

        for repo_name, dep_config in self.dependencies.items():
            risk_score = 0
            matched_imports = []

            # Check if any imports match changed files
            for import_path in dep_config.imports:
                # Convert import path to file paths (e.g., core.mcp_server → core/mcp_server.py)
                possible_files = [
                    import_path.replace(".", "/") + ".py",
                    import_path.replace(".", "/"),
                    f"{import_path.replace('.', '/')}.py"
                ]

                for changed_file in changed_files:
                    if any(changed_file.endswith(pf) for pf in possible_files):
                        matched_imports.append(import_path)
                        risk_score += 10

            # Calculate risk level
            if matched_imports:
                risk_level = "HIGH" if dep_config.critical else "MEDIUM"
                if risk_score >= 20:
                    risk_level = "CRITICAL" if dep_config.critical else "HIGH"

                impacted.append({
                    "repo": repo_name,
                    "imports": matched_imports,
                    "test_command": dep_config.test_command,
                    "critical": dep_config.critical,
                    "risk_level": risk_level,
                    "ci_trigger_url": dep_config.ci_trigger_url,
                })

        return sorted(impacted, key=lambda x: x["critical"], reverse=True)

    def log_dependency_change(self,
                             pr_number: int,
                             changed_files: List[str],
                             changed_by: str,
                             repo: str = "neo") -> DependencyChange:
        """
        Log a code change and identify dependent repos

        Args:
            pr_number: PR number
            changed_files: Files changed in this PR
            changed_by: Developer/agent name
            repo: Repository name

        Returns:
            DependencyChange record with identified dependencies
        """
        dependent_repos = self.check_dependent_repos(changed_files)

        change = DependencyChange(
            repo=repo,
            pr_number=pr_number,
            changed_files=changed_files,
            changed_by=changed_by,
            timestamp=datetime.utcnow().isoformat(),
            dependent_repos=dependent_repos
        )

        # Save to tracking log
        log_file = self.tracking_dir / f"change_{pr_number}_{int(datetime.utcnow().timestamp())}.json"
        with open(log_file, "w") as f:
            json.dump(change.to_dict(), f, indent=2)

        return change

    def add_test_result(self, pr_number: int, repo: str, test_result: Dict):
        """
        Record test results from a dependent repo

        Args:
            pr_number: PR number
            repo: Dependent repo name
            test_result: Test result data {passed: bool, message: str, logs: str}
        """
        log_file = self.tracking_dir / f"test_result_{pr_number}_{repo}.json"
        with open(log_file, "w") as f:
            json.dump({
                "repo": repo,
                "pr": pr_number,
                "result": test_result,
                "timestamp": datetime.utcnow().isoformat()
            }, f, indent=2)

    def get_dependency_status(self, pr_number: int) -> Dict:
        """
        Get current dependency test status for a PR

        Args:
            pr_number: PR number

        Returns:
            Dict with dependency status, test results, and summary
        """
        # Find change log for this PR
        change_logs = list(self.tracking_dir.glob(f"change_{pr_number}_*.json"))
        if not change_logs:
            return {"status": "no_changes_logged", "pr": pr_number}

        with open(change_logs[0]) as f:
            change = json.load(f)

        # Get test results
        test_results = {}
        for test_file in self.tracking_dir.glob(f"test_result_{pr_number}_*.json"):
            with open(test_file) as f:
                result = json.load(f)
                test_results[result["repo"]] = result["result"]

        # Summary
        dependent_count = len(change.get("dependent_repos", []))
        test_count = len(test_results)
        passed_count = sum(1 for r in test_results.values() if r.get("passed"))

        return {
            "pr": pr_number,
            "dependent_repos": change.get("dependent_repos", []),
            "test_results": test_results,
            "summary": {
                "dependent_count": dependent_count,
                "tested_count": test_count,
                "passed_count": passed_count,
                "failed_count": test_count - passed_count,
                "all_passed": test_count == passed_count and test_count > 0
            }
        }

    def generate_pr_comment(self, pr_number: int) -> str:
        """Generate markdown comment for PR with dependency status"""
        status = self.get_dependency_status(pr_number)

        if status.get("status") == "no_changes_logged":
            return "No dependency analysis available yet."

        comment = "## 🔗 Cross-Repository Dependency Analysis\n\n"

        deps = status.get("dependent_repos", [])
        if not deps:
            comment += "✅ No dependent repositories detected\n"
            return comment

        comment += f"This PR impacts **{len(deps)} dependent repo(s)**:\n\n"

        for dep in deps:
            risk_emoji = "🔴" if dep["critical"] else "🟡"
            comment += f"{risk_emoji} **{dep['repo']}** (Risk: {dep['risk_level']})\n"
            comment += f"   - Imports: `{', '.join(dep['imports'])}`\n"

        comment += "\n### Test Results\n\n"

        test_results = status.get("test_results", {})
        if not test_results:
            comment += "⏳ Tests pending...\n"
        else:
            for repo, result in test_results.items():
                status_icon = "✅" if result.get("passed") else "❌"
                comment += f"{status_icon} **{repo}**: {result.get('message', 'No message')}\n"

        summary = status.get("summary", {})
        comment += f"\n**Summary**: {summary.get('passed_count')}/{summary.get('tested_count')} tests passing\n"

        if not summary.get("all_passed") and test_results:
            comment += "⚠️ **Some tests are failing. Please review before merging.**\n"

        return comment

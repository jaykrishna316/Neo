"""
Phase 4: Merge Gate - Enforce dependency test requirements before merge
Blocks or warns about merging when dependent repo tests haven't passed
"""

import json
from typing import Dict, List, Tuple, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class MergeGateResult:
    """Result of merge gate check"""
    can_merge: bool
    reason: str
    blocking_issues: List[str]
    warnings: List[str]
    summary: Dict[str, Any]


class MergeGate:
    """Enforce dependency test requirements for merges"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.tracking_dir = self.repo_path / ".devsync" / "dependencies"

    def can_merge_to_main(self,
                         pr_number: int,
                         allow_missing_tests: bool = False) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if PR can be merged to main based on dependent repo tests

        Args:
            pr_number: PR number to check
            allow_missing_tests: Allow merge if tests haven't run yet

        Returns:
            Tuple of (can_merge: bool, details: Dict)
        """
        # Find dependency change log
        change_logs = list(self.tracking_dir.glob(f"change_{pr_number}_*.json"))
        if not change_logs:
            return True, {
                "reason": "No dependencies detected",
                "pr": pr_number
            }

        with open(change_logs[0]) as f:
            change = json.load(f)

        dependent_repos = change.get("dependent_repos", [])
        if not dependent_repos:
            return True, {
                "reason": "No dependent repositories found",
                "pr": pr_number
            }

        # Check test results
        test_results = {}
        for test_file in self.tracking_dir.glob(f"test_result_{pr_number}_*.json"):
            with open(test_file) as f:
                result = json.load(f)
                test_results[result["repo"]] = result["result"]

        # Analyze merge readiness
        blocking_issues = []
        warnings = []

        for dep in dependent_repos:
            repo_name = dep["repo"]
            is_critical = dep.get("critical", False)
            risk_level = dep.get("risk_level", "MEDIUM")

            if repo_name not in test_results:
                msg = f"{repo_name}: Tests not yet run (Risk: {risk_level})"
                if is_critical or risk_level in ["HIGH", "CRITICAL"]:
                    if not allow_missing_tests:
                        blocking_issues.append(msg)
                    else:
                        warnings.append(msg)
                else:
                    warnings.append(msg)
            else:
                test_result = test_results[repo_name]
                if not test_result.get("passed", False):
                    msg = f"{repo_name}: Tests FAILED - {test_result.get('message', 'Unknown error')}"
                    if is_critical or risk_level in ["HIGH", "CRITICAL"]:
                        blocking_issues.append(msg)
                    else:
                        warnings.append(msg)

        can_merge = len(blocking_issues) == 0

        return can_merge, {
            "pr": pr_number,
            "can_merge": can_merge,
            "dependent_repos": len(dependent_repos),
            "tested_repos": len(test_results),
            "blocking_issues": blocking_issues,
            "warnings": warnings,
            "reason": self._format_reason(can_merge, blocking_issues, warnings)
        }

    def get_merge_status(self, pr_number: int) -> Dict[str, Any]:
        """Get detailed merge gate status for a PR"""
        can_merge, details = self.can_merge_to_main(pr_number)
        return {
            "pr": pr_number,
            "status": "ready" if can_merge else "blocked",
            "can_merge": can_merge,
            **details
        }

    def generate_merge_gate_comment(self, pr_number: int) -> str:
        """Generate markdown comment showing merge gate status"""
        can_merge, details = self.can_merge_to_main(pr_number)

        comment = "## 🚪 Merge Gate Status\n\n"

        if can_merge:
            comment += "✅ **All dependency tests passed - ready to merge**\n\n"
        else:
            comment += "🚫 **Merge blocked - dependency tests must pass**\n\n"

        blocking = details.get("blocking_issues", [])
        warnings = details.get("warnings", [])

        if blocking:
            comment += "### ❌ Blocking Issues\n"
            for issue in blocking:
                comment += f"- {issue}\n"
            comment += "\n"

        if warnings:
            comment += "### ⚠️ Warnings\n"
            for warning in warnings:
                comment += f"- {warning}\n"
            comment += "\n"

        summary = details.get("reason", "")
        if summary:
            comment += f"**Summary:** {summary}\n"

        return comment

    def _format_reason(self, can_merge: bool, blocking: List[str], warnings: List[str]) -> str:
        """Format merge readiness reason"""
        if can_merge:
            if warnings:
                return f"Ready to merge ({len(warnings)} warning(s))"
            else:
                return "All checks passed"
        else:
            return f"{len(blocking)} critical issue(s) must be resolved"

    def require_approval_from(self,
                             pr_number: int,
                             required_approvers: List[str]) -> Dict[str, Any]:
        """
        Specify approvers required based on dependency risk

        Args:
            pr_number: PR number
            required_approvers: List of GitHub usernames who must approve

        Returns:
            Dict with approval requirements
        """
        return {
            "pr": pr_number,
            "required_approvers": required_approvers,
            "approval_count": len(required_approvers),
            "status": "awaiting_approval"
        }

    def check_approvals(self,
                       pr_number: int,
                       required_approvers: List[str],
                       actual_approvals: List[str]) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if required approvals are satisfied

        Args:
            pr_number: PR number
            required_approvers: List of required approvers
            actual_approvals: List of users who have approved

        Returns:
            Tuple of (all_approved: bool, details: Dict)
        """
        missing = set(required_approvers) - set(actual_approvals)

        return len(missing) == 0, {
            "pr": pr_number,
            "required_approvers": required_approvers,
            "actual_approvals": actual_approvals,
            "missing_approvals": list(missing),
            "approval_percentage": len(actual_approvals) / len(required_approvers) * 100 if required_approvers else 100
        }

"""
Git Activity Log Bridge - Connects Git workflow with Activity Log
Automatically adds required approvers to PRs based on conflicts
"""

import json
import os
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from datetime import datetime


class GitActivityLogBridge:
    """Bridge between Git workflow and Activity Log"""

    def __init__(self, repo_path: str = ".", github_token: Optional[str] = None):
        self.repo_path = Path(repo_path)
        self.activity_log_dir = self.repo_path / ".activity_log"
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.github_api = self._init_github_api()

    def _init_github_api(self):
        """Initialize GitHub API client"""
        try:
            # Try importing requests for GitHub API calls
            import requests
            return requests
        except ImportError:
            print("⚠️  requests library not installed. GitHub integration disabled.")
            print("   Install with: pip install requests")
            return None

    def get_repo_info(self) -> Dict:
        """Get repo info from git remote"""
        try:
            # Get origin URL
            origin = subprocess.check_output(
                ["git", "config", "--get", "remote.origin.url"],
                cwd=self.repo_path,
                text=True
            ).strip()

            # Parse owner/repo from URL
            if "github.com" in origin:
                # Format: git@github.com:owner/repo.git or https://github.com/owner/repo.git
                parts = origin.split(":")[-1].replace(".git", "").split("/")
                owner = parts[-2]
                repo = parts[-1]

                return {
                    "owner": owner,
                    "repo": repo,
                    "origin": origin
                }
        except Exception as e:
            print(f"⚠️  Could not parse git repo info: {e}")

        return None

    def find_high_conflicts_in_pr(self, base_branch: str = "main",
                                  head_branch: str = None) -> List[Dict]:
        """
        Find all HIGH conflicts between branches
        Returns list of conflicting functions with involved developers
        """

        if not head_branch:
            # Get current branch
            head_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                text=True
            ).strip()

        high_conflicts = []

        # Scan activity log for HIGH conflicts
        changes_dir = self.activity_log_dir / "changes"
        if not changes_dir.exists():
            return []

        # Group changes by function
        functions = {}

        for change_file in changes_dir.glob("*.json"):
            try:
                with open(change_file) as f:
                    change = json.load(f)

                key = f"{change['file']}::{change['function']}"

                if key not in functions:
                    functions[key] = []

                functions[key].append(change)
            except:
                continue

        # Find HIGH conflicts
        for func_key, changes in functions.items():
            if len(changes) >= 2:  # Multiple developers touched it
                # Check if any are HIGH severity
                high_changes = [c for c in changes if c.get("conflict_severity") == "high"]

                if high_changes:
                    file_path, function_name = func_key.split("::")

                    conflict = {
                        "file": file_path,
                        "function": function_name,
                        "severity": "HIGH",
                        "developers_involved": [c["developer"] for c in changes],
                        "descriptions": [c["description"] for c in changes],
                        "changes_count": len(changes),
                        "downstream_impacts": high_changes[-1].get("downstream_impacts", {})
                    }

                    high_conflicts.append(conflict)

        return high_conflicts

    def get_required_approvers(self, base_branch: str = "main",
                              head_branch: str = None) -> List[str]:
        """
        Get list of developers who MUST approve based on HIGH conflicts
        These become required reviewers in the PR
        """

        conflicts = self.find_high_conflicts_in_pr(base_branch, head_branch)

        approvers = set()

        for conflict in conflicts:
            # All developers involved in HIGH conflicts must approve
            for dev in conflict["developers_involved"]:
                approvers.add(dev)

        return sorted(list(approvers))

    def get_pr_number_from_branch(self, head_branch: str) -> Optional[int]:
        """Find PR number for a given branch"""

        if not self.github_api or not self.github_token:
            return None

        try:
            repo_info = self.get_repo_info()
            if not repo_info:
                return None

            # GitHub API: GET /repos/{owner}/{repo}/pulls
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/pulls"
            params = {"head": f"{repo_info['owner']}:{head_branch}", "state": "open"}

            response = self.github_api.get(url, headers=headers, params=params)

            if response.status_code == 200:
                prs = response.json()
                if prs:
                    return prs[0]["number"]
        except Exception as e:
            print(f"⚠️  Could not find PR: {e}")

        return None

    def add_required_reviewers_to_pr(self, pr_number: int,
                                     reviewers: List[str]) -> Dict:
        """
        Add required reviewers to a PR
        These developers will see a "Review required" notification
        """

        if not self.github_api or not self.github_token:
            print("⚠️  GitHub API not configured")
            return {"success": False, "reason": "No GitHub token"}

        try:
            repo_info = self.get_repo_info()
            if not repo_info:
                return {"success": False, "reason": "Could not parse repo info"}

            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            # GitHub API: POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers
            url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/pulls/{pr_number}/requested_reviewers"

            data = {
                "reviewers": reviewers
            }

            response = self.github_api.post(url, headers=headers, json=data)

            if response.status_code == 201:
                return {
                    "success": True,
                    "reviewers_added": reviewers,
                    "pr_number": pr_number
                }
            else:
                return {
                    "success": False,
                    "reason": response.text,
                    "status_code": response.status_code
                }

        except Exception as e:
            return {"success": False, "reason": str(e)}

    def set_pr_approval_requirement(self, pr_number: int,
                                    required_approvals: int = 1) -> Dict:
        """
        Set PR to require approval from all added reviewers
        Uses branch protection rules
        """

        if not self.github_api or not self.github_token:
            return {"success": False, "reason": "No GitHub token"}

        try:
            repo_info = self.get_repo_info()
            if not repo_info:
                return {"success": False, "reason": "Could not parse repo info"}

            # Note: This requires admin access to set branch protection rules
            # For now, just return info about what would be required

            return {
                "success": True,
                "message": "Branch protection rules must be configured in GitHub Settings",
                "instructions": [
                    "1. Go to repo Settings > Branches",
                    "2. Select 'main' branch",
                    "3. Enable 'Require pull request reviews before merging'",
                    "4. Set 'Require approvals: 1' (or number of required developers)",
                    "5. Enable 'Dismiss stale pull request approvals when new commits'",
                    "6. Enable 'Restrict who can dismiss pull request reviews'"
                ],
                "pr_number": pr_number,
                "required_approvals": required_approvals
            }

        except Exception as e:
            return {"success": False, "reason": str(e)}

    def auto_add_approvers_to_mr(self, head_branch: str = None) -> Dict:
        """
        Automatically add required approvers to PR
        Called when MR is created
        """

        if not head_branch:
            head_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                text=True
            ).strip()

        # Find HIGH conflicts
        conflicts = self.find_high_conflicts_in_pr("main", head_branch)

        if not conflicts:
            return {
                "success": True,
                "high_conflicts": 0,
                "message": "No HIGH conflicts - standard approval flow"
            }

        # Get required approvers
        approvers = self.get_required_approvers("main", head_branch)

        # Find PR number
        pr_number = self.get_pr_number_from_branch(head_branch)

        if not pr_number:
            return {
                "success": False,
                "reason": "Could not find PR number",
                "approvers": approvers,
                "instructions": f"Manually add these as reviewers: {', '.join(approvers)}"
            }

        # Add reviewers to PR
        result = self.add_required_reviewers_to_pr(pr_number, approvers)

        if result["success"]:
            return {
                "success": True,
                "pr_number": pr_number,
                "approvers_added": approvers,
                "conflicts": conflicts
            }
        else:
            return {
                "success": False,
                "pr_number": pr_number,
                "reason": result.get("reason"),
                "approvers": approvers
            }

    def sync_approvals_with_github(self, pr_number: int) -> Dict:
        """
        Sync approvals from activity log with GitHub PR approvals
        Marks PR as approved in GitHub when all developers approve
        """

        if not self.github_api or not self.github_token:
            return {"success": False, "reason": "No GitHub token"}

        # This would check activity log approvals and update GitHub PR status
        # Implementation depends on GitHub App permissions

        return {
            "success": False,
            "note": "Requires GitHub App with 'write:pull_requests' scope"
        }

    def create_activity_log_summary_comment(self, pr_number: int) -> Dict:
        """
        Post activity log summary as PR comment
        Shows conflicts, involved developers, approvals needed
        """

        if not self.github_api or not self.github_token:
            return {"success": False, "reason": "No GitHub token"}

        try:
            repo_info = self.get_repo_info()
            if not repo_info:
                return {"success": False}

            # Get HIGH conflicts
            conflicts = self.find_high_conflicts_in_pr()

            if not conflicts:
                return {"already_approved": True}

            # Build comment
            comment = "## 🔴 Activity Log: HIGH Conflicts Detected\n\n"
            comment += "This PR involves HIGH conflicts that require approval from all developers:\n\n"

            for conflict in conflicts:
                comment += f"### {conflict['file']}::{conflict['function']}\n"
                comment += f"**Developers involved:**\n"
                for dev in conflict['developers_involved']:
                    comment += f"- {dev}\n"
                comment += f"\n**Changes:**\n"
                for desc in conflict['descriptions']:
                    comment += f"- {desc}\n"
                comment += "\n"

            # Post comment
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }

            url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/issues/{pr_number}/comments"

            response = self.github_api.post(
                url,
                headers=headers,
                json={"body": comment}
            )

            if response.status_code == 201:
                return {
                    "success": True,
                    "pr_number": pr_number,
                    "comment_id": response.json()["id"]
                }
            else:
                return {
                    "success": False,
                    "reason": response.text
                }

        except Exception as e:
            return {"success": False, "reason": str(e)}


# ========== GIT HOOK INTEGRATION ==========

def setup_git_hooks(repo_path: str = "."):
    """Setup git hooks to integrate activity log with workflow"""

    git_dir = Path(repo_path) / ".git" / "hooks"

    # 1. Pre-commit hook: Record change to activity log
    pre_commit = git_dir / "pre-commit"
    pre_commit.write_text("""#!/bin/bash
# Record change to activity log before commit

python3 .claude/activity_log_hook.py \\
  "$(git config user.name)" \\
  "$(git diff --cached --name-only | head -1)" \\
  "function_name" \\
  "$(git rev-parse --abbrev-ref HEAD)" \\
  "Commit message"
""")
    pre_commit.chmod(0o755)

    # 2. Pre-push hook: Check merge gate
    pre_push = git_dir / "pre-push"
    pre_push.write_text("""#!/bin/bash
# Enforce merge gate before push to main

while IFS=' ' read -r local_ref local_sha remote_ref remote_sha; do
    if [[ "$remote_ref" == "refs/heads/main" ]]; then
        python3 .claude/merge_gate_check.py
        if [ $? -ne 0 ]; then
            exit 1
        fi
    fi
done
""")
    pre_push.chmod(0o755)

    # 3. Post-merge hook: Auto-add approvers to PR
    post_merge = git_dir / "post-merge"
    post_merge.write_text("""#!/bin/bash
# Auto-add required approvers when PR created

GITHUB_TOKEN="${GITHUB_TOKEN:-}"
if [ ! -z "$GITHUB_TOKEN" ]; then
    python3 .claude/git_activity_log_bridge.py --auto-add-approvers
fi
""")
    post_merge.chmod(0o755)

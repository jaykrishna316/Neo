"""
Phase 3: GitHub PR Auto-Comments - Post dependency analysis and test results to PRs
Integrates with GitHub API to automatically comment on PRs with dependency status
"""

import json
import os
from typing import Dict, List, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    import requests
except ImportError:
    requests = None


class GitHubPRIntegration:
    """GitHub PR integration for auto-commenting with dependency results"""

    def __init__(self, repo_path: str = ".", github_token: str = None):
        self.repo_path = Path(repo_path)
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.api_base = "https://api.github.com"
        self.comment_log_dir = self.repo_path / ".devsync" / "pr_comments"
        self.comment_log_dir.mkdir(parents=True, exist_ok=True)

    def get_pr_for_branch(self,
                         owner: str,
                         repo: str,
                         branch: str) -> Optional[Dict[str, Any]]:
        """
        Find PR number for a given branch

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name to find PR for

        Returns:
            PR dict with number, url, etc. or None if not found
        """
        if not requests or not self.github_token:
            return None

        url = f"{self.api_base}/repos/{owner}/{repo}/pulls"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            response = requests.get(url, headers=headers, params={"state": "open"}, timeout=30)
            if response.status_code == 200:
                prs = response.json()
                for pr in prs:
                    if pr["head"]["ref"] == branch:
                        return pr
            return None
        except requests.RequestException:
            return None

    def post_comment(self,
                    owner: str,
                    repo: str,
                    pr_number: int,
                    comment_body: str,
                    update_existing: bool = True) -> Dict[str, Any]:
        """
        Post or update comment on PR

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            comment_body: Markdown comment body
            update_existing: Update existing Neo comment if found

        Returns:
            Dict with comment status, ID, and URL
        """
        if not requests:
            return {
                "status": "failed",
                "error": "requests library not installed"
            }

        if not self.github_token:
            return {
                "status": "failed",
                "error": "GITHUB_TOKEN not configured"
            }

        url = f"{self.api_base}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Check for existing Neo comment if updating
        if update_existing:
            existing_comment_id = self._find_existing_neo_comment(owner, repo, pr_number)
            if existing_comment_id:
                return self._update_comment(owner, repo, existing_comment_id, comment_body)

        # Post new comment
        try:
            response = requests.post(
                url,
                json={"body": comment_body},
                headers=headers,
                timeout=30
            )

            if response.status_code == 201:
                comment_data = response.json()
                result = {
                    "status": "posted",
                    "comment_id": comment_data["id"],
                    "url": comment_data["html_url"],
                    "pr": pr_number,
                    "timestamp": datetime.utcnow().isoformat()
                }
                self._log_comment(pr_number, result)
                return result
            else:
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}"
                }

        except requests.RequestException as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def _find_existing_neo_comment(self,
                                   owner: str,
                                   repo: str,
                                   pr_number: int) -> Optional[int]:
        """Find existing Neo dependency comment on PR"""
        if not requests or not self.github_token:
            return None

        url = f"{self.api_base}/repos/{owner}/{repo}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                comments = response.json()
                for comment in comments:
                    if "Cross-Repository Dependency Analysis" in comment["body"]:
                        return comment["id"]
            return None
        except requests.RequestException:
            return None

    def _update_comment(self,
                       owner: str,
                       repo: str,
                       comment_id: int,
                       comment_body: str) -> Dict[str, Any]:
        """Update existing comment"""
        url = f"{self.api_base}/repos/{owner}/{repo}/issues/comments/{comment_id}"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            response = requests.patch(
                url,
                json={"body": comment_body},
                headers=headers,
                timeout=30
            )

            if response.status_code == 200:
                comment_data = response.json()
                return {
                    "status": "updated",
                    "comment_id": comment_data["id"],
                    "url": comment_data["html_url"],
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}"
                }

        except requests.RequestException as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def post_dependency_comment(self,
                               owner: str,
                               repo: str,
                               pr_number: int,
                               comment_body: str) -> Dict[str, Any]:
        """Post or update dependency analysis comment on PR"""
        return self.post_comment(owner, repo, pr_number, comment_body, update_existing=True)

    def _log_comment(self, pr_number: int, result: Dict):
        """Log comment posting to tracking file"""
        log_file = self.comment_log_dir / f"comment_{pr_number}_{int(datetime.utcnow().timestamp())}.json"
        with open(log_file, "w") as f:
            json.dump(result, f, indent=2)

    def get_comment_history(self, pr_number: int) -> List[Dict]:
        """Get all comment posting attempts for a PR"""
        comments = []
        for comment_file in self.comment_log_dir.glob(f"comment_{pr_number}_*.json"):
            with open(comment_file) as f:
                comments.append(json.load(f))
        return sorted(comments, key=lambda x: x.get("timestamp", ""), reverse=True)

    def request_review(self,
                      owner: str,
                      repo: str,
                      pr_number: int,
                      reviewers: List[str]) -> Dict[str, Any]:
        """
        Request review from specific users on PR

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            reviewers: List of GitHub usernames to request review from

        Returns:
            Dict with request status
        """
        if not self.github_token:
            return {
                "status": "failed",
                "error": "GITHUB_TOKEN not configured"
            }

        url = f"{self.api_base}/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers"
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        try:
            response = requests.post(
                url,
                json={"reviewers": reviewers},
                headers=headers,
                timeout=30
            )

            if response.status_code == 201:
                return {
                    "status": "success",
                    "reviewers_added": reviewers,
                    "pr": pr_number,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}"
                }

        except requests.RequestException as e:
            return {
                "status": "failed",
                "error": str(e)
            }

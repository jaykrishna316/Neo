"""
Phase 2: Test Triggering - Auto-trigger tests in dependent repositories
Handles CI integration for dependent repos via webhooks and GitHub Actions
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    requests = None


class TestTrigger:
    """Trigger tests in dependent repositories via CI webhooks"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.trigger_log_dir = self.repo_path / ".devsync" / "triggers"
        self.trigger_log_dir.mkdir(parents=True, exist_ok=True)

    def trigger_dependent_repo_tests(self,
                                     pr_number: int,
                                     repo_name: str,
                                     ci_trigger_url: str,
                                     changed_files: List[str],
                                     test_command: str,
                                     branch: str = "main",
                                     retry_count: int = 3) -> Dict[str, Any]:
        """
        Trigger tests in a dependent repository via CI webhook

        Args:
            pr_number: PR number that triggered this
            repo_name: Dependent repo name
            ci_trigger_url: Webhook URL for CI trigger
            changed_files: Files changed in parent repo
            test_command: Command to run tests
            branch: Branch to test against
            retry_count: Number of retries on failure

        Returns:
            Dict with trigger status, timestamp, and result
        """
        if not ci_trigger_url:
            return {
                "status": "skipped",
                "reason": "No CI trigger URL configured",
                "repo": repo_name
            }

        if not requests:
            return {
                "status": "skipped",
                "reason": "requests library not installed",
                "repo": repo_name
            }

        payload = {
            "trigger_source": "neo-dependency-tracker",
            "pr_number": pr_number,
            "parent_repo": "neo",
            "dependent_repo": repo_name,
            "changed_files": changed_files,
            "test_command": test_command,
            "branch": branch,
            "timestamp": datetime.utcnow().isoformat()
        }

        for attempt in range(retry_count):
            try:
                response = requests.post(
                    ci_trigger_url,
                    json=payload,
                    timeout=30
                )

                if response.status_code in [200, 201, 202]:
                    trigger_result = {
                        "status": "triggered",
                        "repo": repo_name,
                        "url": ci_trigger_url,
                        "pr": pr_number,
                        "response_code": response.status_code,
                        "timestamp": datetime.utcnow().isoformat(),
                        "attempt": attempt + 1
                    }

                    self._log_trigger(pr_number, repo_name, trigger_result)
                    return trigger_result

                elif attempt < retry_count - 1:
                    continue
                else:
                    return {
                        "status": "failed",
                        "repo": repo_name,
                        "error": f"HTTP {response.status_code}",
                        "timestamp": datetime.utcnow().isoformat()
                    }

            except requests.RequestException as e:
                if attempt < retry_count - 1:
                    continue
                else:
                    return {
                        "status": "failed",
                        "repo": repo_name,
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }

    def trigger_github_actions(self,
                              repo_owner: str,
                              repo_name: str,
                              workflow_file: str,
                              ref: str = "main",
                              github_token: str = None,
                              inputs: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Trigger GitHub Actions workflow in dependent repo

        Args:
            repo_owner: Owner of dependent repo
            repo_name: Name of dependent repo
            workflow_file: GitHub Actions workflow filename
            ref: Branch/tag to trigger on
            github_token: GitHub API token
            inputs: Workflow input parameters

        Returns:
            Dict with trigger status and run ID
        """
        import os
        if not requests:
            return {
                "status": "failed",
                "error": "requests library not installed"
            }

        if not github_token:
            github_token = os.getenv("GITHUB_TOKEN")

        if not github_token:
            return {
                "status": "failed",
                "error": "GITHUB_TOKEN not configured"
            }

        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_file}/dispatches"

        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        payload = {
            "ref": ref,
            "inputs": inputs or {}
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)

            if response.status_code == 204:
                return {
                    "status": "triggered",
                    "repo": f"{repo_owner}/{repo_name}",
                    "workflow": workflow_file,
                    "ref": ref,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "failed",
                    "error": f"HTTP {response.status_code}: {response.text}"
                }

        except requests.RequestException as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def _log_trigger(self, pr_number: int, repo_name: str, result: Dict):
        """Log trigger attempt to tracking file"""
        log_file = self.trigger_log_dir / f"trigger_{pr_number}_{repo_name.replace('/', '_')}.json"
        with open(log_file, "w") as f:
            json.dump(result, f, indent=2)

    def get_trigger_history(self, pr_number: int) -> List[Dict]:
        """Get all trigger attempts for a PR"""
        triggers = []
        for trigger_file in self.trigger_log_dir.glob(f"trigger_{pr_number}_*.json"):
            with open(trigger_file) as f:
                triggers.append(json.load(f))
        return sorted(triggers, key=lambda x: x.get("timestamp", ""), reverse=True)

    def get_trigger_status(self, pr_number: int, repo_name: str) -> Optional[Dict]:
        """Get latest trigger status for a specific repo"""
        log_file = self.trigger_log_dir / f"trigger_{pr_number}_{repo_name.replace('/', '_')}.json"
        if log_file.exists():
            with open(log_file) as f:
                return json.load(f)
        return None

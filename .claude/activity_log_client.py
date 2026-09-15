#!/usr/bin/env python3
"""
Activity Log Client - Communicates with Activity Log Server via REST API
Use this when testing with multiple developers
"""

import requests
from typing import Dict, List, Tuple, Optional


class ActivityLogClient:
    """Client for remote activity log server"""

    def __init__(self, server_url: str):
        """
        Initialize client

        Args:
            server_url: Base URL of activity log server (e.g., https://xyz.ngrok.io)
        """
        self.server_url = server_url.rstrip("/")
        self._verify_connection()

    def _verify_connection(self):
        """Verify server is reachable"""
        try:
            response = requests.get(f"{self.server_url}/health", timeout=5)
            response.raise_for_status()
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to activity log server at {self.server_url}: {e}"
            )

    def log_change(
        self,
        developer: str,
        file_path: str,
        function_name: str,
        old_code: str,
        new_code: str,
        feature_branch: str,
        verbal_description: str,
    ) -> Dict:
        """Log a code change"""
        payload = {
            "developer": developer,
            "file_path": file_path,
            "function_name": function_name,
            "old_code": old_code,
            "new_code": new_code,
            "feature_branch": feature_branch,
            "verbal_description": verbal_description,
        }

        response = requests.post(
            f"{self.server_url}/api/log_change", json=payload, timeout=10
        )
        response.raise_for_status()
        return response.json()

    def record_approval(
        self, developer: str, file_path: str, function_name: str, approval_status: str = "approved"
    ) -> Dict:
        """Record developer approval"""
        payload = {
            "developer": developer,
            "file_path": file_path,
            "function_name": function_name,
            "approval_status": approval_status,
        }

        response = requests.post(
            f"{self.server_url}/api/record_approval", json=payload, timeout=10
        )
        response.raise_for_status()
        return response.json()

    def get_conflicts(
        self, base_branch: str = "main", head_branch: str = None
    ) -> List[Dict]:
        """Get HIGH conflicts"""
        params = {"base_branch": base_branch}
        if head_branch:
            params["head_branch"] = head_branch

        response = requests.get(
            f"{self.server_url}/api/conflicts", params=params, timeout=10
        )
        response.raise_for_status()
        return response.json().get("conflicts", [])

    def can_merge_to_main(self, file_path: str, function_name: str) -> Tuple[bool, Dict]:
        """Check if merge to main is allowed"""
        params = {"file_path": file_path, "function_name": function_name}

        response = requests.get(
            f"{self.server_url}/api/can_merge", params=params, timeout=10
        )
        response.raise_for_status()
        data = response.json()
        return data.get("can_merge", False), data.get("status", {})

    def record_rollback(
        self, merge_commit_sha: str, file_path: str, function_name: str, reason: str
    ) -> Dict:
        """Record a rollback"""
        payload = {
            "merge_commit_sha": merge_commit_sha,
            "file_path": file_path,
            "function_name": function_name,
            "reason": reason,
        }

        response = requests.post(
            f"{self.server_url}/api/record_rollback", json=payload, timeout=10
        )
        response.raise_for_status()
        return response.json()

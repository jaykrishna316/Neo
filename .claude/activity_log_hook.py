#!/usr/bin/env python3
"""
Activity Log Hook for Neo
Integrates with Claude Code to track changes
Uses full activity_log_manager for conflict detection and merge gate
Can be triggered on: agent commit, file save, branch push
"""

import sys
from pathlib import Path
from activity_log_manager import ActivityLogManager, MergeGate

class ActivityLogHook:
    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.manager = ActivityLogManager(repo_root)
        self.merge_gate = MergeGate(repo_root)

    def log_change(self, developer: str, file_path: str, function_name: str,
                   old_code: str, new_code: str, branch: str, verbal_description: str):
        """Log a change with full conflict detection and auto-push"""
        change = self.manager.log_change(
            developer=developer,
            file_path=file_path,
            function_name=function_name,
            old_code=old_code,
            new_code=new_code,
            feature_branch=branch,
            verbal_description=verbal_description
        )
        return change

    def check_merge_status(self, file_path: str, function_name: str):
        """Check if changes can be merged to main"""
        status = self.merge_gate.get_merge_status(file_path, function_name)
        return status

    def record_approval(self, developer: str, file_path: str, function_name: str):
        """Record developer approval for merge"""
        approvals = self.merge_gate.record_approval(developer, file_path, function_name)
        return approvals

if __name__ == "__main__":
    # Can be called from Claude Code hooks
    if len(sys.argv) < 6:
        print("Usage: activity_log_hook.py <developer> <file> <function> <branch> <description> <old_code> <new_code>")
        sys.exit(1)

    hook = ActivityLogHook()

    developer = sys.argv[1]
    file_path = sys.argv[2]
    function_name = sys.argv[3]
    branch = sys.argv[4]
    description = sys.argv[5]
    old_code = sys.argv[6] if len(sys.argv) > 6 else ""
    new_code = sys.argv[7] if len(sys.argv) > 7 else ""

    change = hook.log_change(
        developer=developer,
        file_path=file_path,
        function_name=function_name,
        old_code=old_code,
        new_code=new_code,
        branch=branch,
        verbal_description=description
    )

    print(f"✅ Logged change by {developer} to {function_name}")

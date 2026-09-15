#!/usr/bin/env python3
"""
Activity Log Hook for Neo
Integrates with Claude Code to track changes
Can be triggered on: agent commit, file save, branch push
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict

@dataclass
class Change:
    developer: str
    file_path: str
    function_name: str
    branch: str
    timestamp: str
    verbal_description: str  # What the developer is trying to accomplish
    conflict_severity: str
    related_changes: list = None

class ActivityLogHook:
    def __init__(self, repo_root: str = "."):
        self.repo_root = Path(repo_root)
        self.activity_log_dir = self.repo_root / ".activity_log"
        self.activity_log_dir.mkdir(exist_ok=True)

        # Create .gitignore for activity log
        gitignore = self.activity_log_dir / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("*.json\n")

    def log_change(self, developer: str, file_path: str, function_name: str,
                   branch: str, verbal_description: str,
                   conflict_severity: str = "unknown",
                   related_changes: list = None):
        """Log a change to activity log"""

        timestamp = datetime.now().isoformat()

        change = Change(
            developer=developer,
            file_path=file_path,
            function_name=function_name,
            branch=branch,
            timestamp=timestamp,
            verbal_description=verbal_description,
            conflict_severity=conflict_severity,
            related_changes=related_changes or []
        )

        # Save to JSON
        log_file = self.activity_log_dir / f"{timestamp.replace(':', '-')}__{developer.replace(' ', '_')}__change.json"
        log_file.write_text(json.dumps(asdict(change), indent=2))

        return change

if __name__ == "__main__":
    # Can be called from Claude Code hooks
    if len(sys.argv) < 5:
        print("Usage: activity_log_hook.py <developer> <file> <function> <branch> <description> [severity] [related]")
        sys.exit(1)

    hook = ActivityLogHook()

    developer = sys.argv[1]
    file_path = sys.argv[2]
    function_name = sys.argv[3]
    branch = sys.argv[4]
    description = sys.argv[5]
    severity = sys.argv[6] if len(sys.argv) > 6 else "unknown"
    related = sys.argv[7].split(",") if len(sys.argv) > 7 else []

    change = hook.log_change(
        developer=developer,
        file_path=file_path,
        function_name=function_name,
        branch=branch,
        verbal_description=description,
        conflict_severity=severity,
        related_changes=related
    )

    print(f"✅ Logged change by {developer} to {function_name}")

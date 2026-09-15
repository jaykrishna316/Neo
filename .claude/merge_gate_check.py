#!/usr/bin/env python3
"""
Merge Gate Check - Called by pre-push hook
Prevents pushing to main if HIGH conflicts exist without approval
"""

import sys
import json
from pathlib import Path
from activity_log_manager import MergeGate

def check_merge_gate(repo_path: str = ".") -> bool:
    """
    Check if all HIGH conflicts have approval
    Returns True if merge is allowed, False otherwise
    """
    repo_path = Path(repo_path)
    merge_gate = MergeGate(str(repo_path))
    log_dir = repo_path / ".activity_log"

    if not log_dir.exists():
        return True  # No activity log, allow merge

    # Find all changes with HIGH conflicts
    changes = list(log_dir.glob("*.json"))
    if not changes:
        return True

    high_conflicts = []
    for change_file in changes:
        if change_file.name.startswith("push_"):
            continue
        try:
            with open(change_file) as f:
                change = json.load(f)
                if change.get("conflict_severity") == "high":
                    high_conflicts.append(change)
        except:
            continue

    if not high_conflicts:
        return True  # No HIGH conflicts, allow merge

    # For each HIGH conflict, check if all developers approved
    for conflict in high_conflicts:
        file_path = conflict["file"]
        function_name = conflict["function"]

        status = merge_gate.get_merge_status(file_path, function_name)
        if not status["can_merge"]:
            print(f"\n❌ MERGE BLOCKED: HIGH CONFLICT IN {file_path}::{function_name}")
            print(f"   Reason: {status['reason']}")
            print(f"   Developers involved: {', '.join(status['developers_involved'])}")
            print(f"   Approved by: {', '.join(status['approved_by']) if status['approved_by'] else 'None'}")
            print(f"   Still need approval from: {', '.join(status['approvals_needed'])}")
            print(f"\n   Fix: Have each developer run:")
            print(f"   $ neo-approve {file_path} {function_name}")
            return False

    return True

if __name__ == "__main__":
    if not check_merge_gate():
        sys.exit(1)
    sys.exit(0)

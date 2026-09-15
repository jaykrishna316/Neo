"""
Activity Log Manager - POC Implementation
Stores activity log in Git (.activity_log/ directory as JSON)
Auto-pushes on HIGH conflicts
Verbal change descriptions for UI preview
Merge approval gate
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from enum import Enum
import difflib

class ConflictSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ActivityLogManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.log_dir = self.repo_path / ".activity_log"
        self.log_dir.mkdir(exist_ok=True)

        # Ensure .activity_log is tracked but .activity_log/*.json is not (use .gitignore)
        self._setup_gitignore()

    def _setup_gitignore(self):
        """Setup .gitignore for activity log"""
        gitignore_path = self.log_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("*.json\n")

    def log_change(self, developer: str, file_path: str, function_name: str,
                   old_code: str, new_code: str, feature_branch: str,
                   verbal_description: str):
        """
        Log a code change
        verbal_description: What the developer is trying to accomplish (not just diff)
        """

        change_id = datetime.now().isoformat()

        # Calculate conflict severity with existing changes
        conflict_severity, related_changes = self._detect_conflicts(
            file_path, function_name, old_code, new_code
        )

        # Create change record
        change_record = {
            "id": change_id,
            "developer": developer,
            "file": file_path,
            "function": function_name,
            "branch": feature_branch,
            "timestamp": change_id,
            "description": verbal_description,
            "conflict_severity": conflict_severity.value,
            "related_changes": related_changes,
            "old_lines": len(old_code.split('\n')),
            "new_lines": len(new_code.split('\n')),
            "line_changes": self._calculate_changes(old_code, new_code),
        }

        # Save to activity log
        log_file = self.log_dir / f"{file_path.replace('/', '_')}_{function_name}_{change_id.replace(':', '-')}.json"
        log_file.write_text(json.dumps(change_record, indent=2))

        # Print to console
        self._print_change(change_record)

        # HIGH CONFLICT: Auto-push immediately
        if conflict_severity == ConflictSeverity.HIGH:
            print(f"\n🔴 HIGH CONFLICT DETECTED - Auto-pushing to feature branch")
            self._auto_push(feature_branch, change_record)

        return change_record

    def _detect_conflicts(self, file_path: str, function_name: str,
                         old_code: str, new_code: str) -> tuple:
        """Detect conflicts with previous changes to same function"""

        # Find all changes to this function
        pattern = f"*{file_path.replace('/', '_')}_{function_name}_*.json"
        existing_changes = list(self.log_dir.glob(pattern))

        if not existing_changes:
            return ConflictSeverity.LOW, []

        # Load latest change
        latest = sorted(existing_changes)[-1]
        with open(latest) as f:
            prev_change = json.load(f)

        # Analyze overlap
        old_lines = old_code.split('\n')
        new_lines = new_code.split('\n')

        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
        changes = [l for l in diff if l.startswith('+') or l.startswith('-')]

        # Count overlap with previous
        prev_lines_changed = prev_change.get("line_changes", 0)
        current_lines_changed = len(changes) // 2
        overlap_ratio = min(prev_lines_changed, current_lines_changed) / max(prev_lines_changed, current_lines_changed) if max(prev_lines_changed, current_lines_changed) > 0 else 0

        if overlap_ratio == 0:
            severity = ConflictSeverity.LOW
        elif overlap_ratio < 0.5:
            severity = ConflictSeverity.MEDIUM
        else:
            severity = ConflictSeverity.HIGH

        return severity, [prev_change["developer"]]

    def _calculate_changes(self, old_code: str, new_code: str) -> int:
        """Calculate number of lines changed"""
        old_lines = old_code.split('\n')
        new_lines = new_code.split('\n')
        diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=''))
        return len([l for l in diff if l.startswith('+') or l.startswith('-')])

    def _print_change(self, record: dict):
        """Print change to console with formatting"""
        severity = record["conflict_severity"]
        severity_icon = "🔴" if severity == "high" else "🟡" if severity == "medium" else "✅"

        print(f"\n{severity_icon} CHANGE LOGGED")
        print(f"   Developer: {record['developer']}")
        print(f"   File: {record['file']}")
        print(f"   Function: {record['function']}")
        print(f"   Branch: {record['branch']}")
        print(f"   Description: {record['description']}")
        print(f"   Lines changed: {record['line_changes']}")
        if record["related_changes"]:
            print(f"   Conflicts with: {', '.join(record['related_changes'])}")

    def _auto_push(self, branch_name: str, change_record: dict):
        """Auto-push to feature branch on HIGH conflict"""
        try:
            # This is simulated - in real implementation would actually git push
            push_log = {
                "timestamp": datetime.now().isoformat(),
                "branch": branch_name,
                "change_id": change_record["id"],
                "status": "QUEUED_FOR_PUSH",
                "auto_triggered_by": "HIGH_CONFLICT"
            }

            push_file = self.log_dir / f"push_{branch_name.replace('/', '_')}_{datetime.now().isoformat().replace(':', '-')}.json"
            push_file.write_text(json.dumps(push_log, indent=2))

            print(f"   ✅ Queued: git push -u origin {branch_name}")
            print(f"   📝 Push log: {push_file.relative_to(self.repo_path)}")
        except Exception as e:
            print(f"   ⚠️  Push failed: {e}")

    def get_diff_preview(self, file_path: str, function_name: str) -> str:
        """Get a readable diff preview for UI"""
        pattern = f"*{file_path.replace('/', '_')}_{function_name}_*.json"
        changes = list(self.log_dir.glob(pattern))

        if not changes:
            return "No changes recorded"

        latest = sorted(changes)[-1]
        with open(latest) as f:
            change = json.load(f)

        # Create UI-friendly preview
        preview = f"""
📄 Recent Change: {file_path}::{function_name}

👤 Developer: {change['developer']}
🌳 Branch: {change['branch']}
⏰ Time: {change['timestamp']}

📝 What Changed:
   {change['description']}

📊 Impact:
   • Lines modified: {change['line_changes']}
   • Related changes: {', '.join(change['related_changes']) if change['related_changes'] else 'None'}
   • Conflict severity: {change['conflict_severity'].upper()}
"""
        return preview.strip()

    def get_all_activity(self) -> list:
        """Get all recorded activity"""
        activities = []
        for log_file in sorted(self.log_dir.glob("*.json")):
            if log_file.name.startswith("push_"):
                continue
            with open(log_file) as f:
                activities.append(json.load(f))
        return activities


class MergeGate:
    """Prevents merge to main until all related developers approve"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.approvals_dir = self.repo_path / ".activity_log" / "approvals"
        self.approvals_dir.mkdir(exist_ok=True)

    def can_merge_to_main(self, feature_branch: str, file_path: str, function_name: str) -> bool:
        """Check if merge to main is allowed"""

        # Find all related changes
        log_dir = self.repo_path / ".activity_log"
        pattern = f"*{file_path.replace('/', '_')}_{function_name}_*.json"
        changes = list(log_dir.glob(pattern))

        if not changes:
            return True  # No conflicts

        # Check if all developers have approved
        developers_involved = set()
        has_high_conflict = False

        for change_file in changes:
            with open(change_file) as f:
                change = json.load(f)
                developers_involved.add(change["developer"])
                if change["conflict_severity"] == "high":
                    has_high_conflict = True

        if not has_high_conflict:
            return True  # Low/Medium conflicts, can auto-merge

        # For HIGH conflicts, require all developers to approve
        approval_file = self.approvals_dir / f"{file_path.replace('/', '_')}_{function_name}_approvals.json"

        if not approval_file.exists():
            return False

        with open(approval_file) as f:
            approvals = json.load(f)

        # Check if all developers have approved
        approved_by = set(approvals.get("approved_by", []))
        return len(approved_by) == len(developers_involved)

    def record_approval(self, developer: str, file_path: str, function_name: str):
        """Record developer approval for merge"""
        approval_file = self.approvals_dir / f"{file_path.replace('/', '_')}_{function_name}_approvals.json"

        approvals = {}
        if approval_file.exists():
            with open(approval_file) as f:
                approvals = json.load(f)

        if "approved_by" not in approvals:
            approvals["approved_by"] = []

        if developer not in approvals["approved_by"]:
            approvals["approved_by"].append(developer)

        approvals["last_approval"] = datetime.now().isoformat()

        approval_file.write_text(json.dumps(approvals, indent=2))

        return approvals

    def get_merge_status(self, file_path: str, function_name: str) -> dict:
        """Get merge readiness status"""
        log_dir = self.repo_path / ".activity_log"
        pattern = f"*{file_path.replace('/', '_')}_{function_name}_*.json"
        changes = list(log_dir.glob(pattern))

        if not changes:
            return {
                "can_merge": True,
                "reason": "No conflicts detected",
                "approvals_needed": []
            }

        # Get all involved developers
        developers_involved = set()
        has_high_conflict = False

        for change_file in changes:
            with open(change_file) as f:
                change = json.load(f)
                developers_involved.add(change["developer"])
                if change["conflict_severity"] == "high":
                    has_high_conflict = True

        if not has_high_conflict:
            return {
                "can_merge": True,
                "reason": "Only low/medium conflicts",
                "approvals_needed": []
            }

        # Check approvals
        approval_file = self.approvals_dir / f"{file_path.replace('/', '_')}_{function_name}_approvals.json"
        approved_by = set()

        if approval_file.exists():
            with open(approval_file) as f:
                approvals = json.load(f)
                approved_by = set(approvals.get("approved_by", []))

        approvals_needed = developers_involved - approved_by

        return {
            "can_merge": len(approvals_needed) == 0,
            "reason": f"HIGH conflict: waiting on {len(approvals_needed)} approval(s)",
            "developers_involved": list(developers_involved),
            "approved_by": list(approved_by),
            "approvals_needed": list(approvals_needed)
        }


if __name__ == "__main__":
    # Demo
    print("="*80)
    print("ACTIVITY LOG MANAGER - POC DEMO")
    print("="*80)

    # Create manager
    log_mgr = ActivityLogManager()
    merge_gate = MergeGate()

    # Developer 1 makes a change
    print("\n1️⃣  Developer1 makes changes...")
    log_mgr.log_change(
        developer="Developer1 (Agent)",
        file_path="auth.py",
        function_name="validate_user",
        old_code="def validate_user(username, password):\n    if not username or not password:\n        return False\n    user = db.find_user(username)\n    if user and user.check_password(password):\n        return True\n    return False",
        new_code="def validate_user(username, password):\n    if not username or not password:\n        return False\n    user = db.find_user(username)\n    if user:\n        return user.check_password(password)\n    return False",
        feature_branch="feature/dev1-auth-refactor",
        verbal_description="Refactored validation logic for clarity and maintainability"
    )

    # Developer 2 makes conflicting change (HIGH)
    print("\n\n2️⃣  Developer2 makes conflicting changes...")
    log_mgr.log_change(
        developer="Developer2 (Human)",
        file_path="auth.py",
        function_name="validate_user",
        old_code="def validate_user(username, password):\n    if not username or not password:\n        return False\n    user = db.find_user(username)\n    if user and user.check_password(password):\n        return True\n    return False",
        new_code="def validate_user(username, password, email_required=False):\n    if not username or not password:\n        return False\n    if email_required:\n        user = db.find_user(username)\n        if user and user.email:\n            return user.check_password(password)\n        return False\n    user = db.find_user(username)\n    if user and user.check_password(password):\n        return True\n    return False",
        feature_branch="feature/dev2-auth-email",
        verbal_description="Added optional email validation for enhanced security"
    )

    # Check merge status
    print("\n\n" + "="*80)
    print("MERGE GATE STATUS")
    print("="*80)
    status = merge_gate.get_merge_status("auth.py", "validate_user")
    print(f"\n📋 Status for auth.py::validate_user")
    print(f"   Can merge to main: {status['can_merge']}")
    print(f"   Reason: {status['reason']}")
    print(f"   Developers involved: {', '.join(status['developers_involved'])}")
    print(f"   Approved by: {', '.join(status['approved_by']) if status['approved_by'] else 'None'}")
    print(f"   Approvals needed from: {', '.join(status['approvals_needed'])}")

    # Record approval
    print("\n\n" + "="*80)
    print("APPROVAL PROCESS")
    print("="*80)
    print("\n📝 Developer1 approves merge...")
    merge_gate.record_approval("Developer1 (Agent)", "auth.py", "validate_user")

    status = merge_gate.get_merge_status("auth.py", "validate_user")
    print(f"   Approved by: {', '.join(status['approved_by'])}")
    print(f"   Still need approval from: {', '.join(status['approvals_needed'])}")
    print(f"   Can merge now? {status['can_merge']}")

    print("\n📝 Developer2 approves merge...")
    merge_gate.record_approval("Developer2 (Human)", "auth.py", "validate_user")

    status = merge_gate.get_merge_status("auth.py", "validate_user")
    print(f"   Approved by: {', '.join(status['approved_by'])}")
    print(f"   Still need approval from: {', '.join(status['approvals_needed'])}")
    print(f"   Can merge now? {status['can_merge']}")

    # Show diff preview for UI
    print("\n\n" + "="*80)
    print("UI DIFF PREVIEW")
    print("="*80)
    preview = log_mgr.get_diff_preview("auth.py", "validate_user")
    print("\n" + preview)

    # Show activity log
    print("\n\n" + "="*80)
    print("COMPLETE ACTIVITY LOG")
    print("="*80)
    activities = log_mgr.get_all_activity()
    for activity in activities:
        print(f"\n[{activity['id'][:19]}] {activity['developer']}")
        print(f"   {activity['description']}")
        print(f"   Severity: {activity['conflict_severity']}")

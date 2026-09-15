"""
Enhanced Activity Log Manager - Full implementation with all features
Integrates: locking, downstream detection, merge strategies, approval tracking, escalation
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
import difflib
from typing import Dict, List, Optional, Tuple

from lock_manager import LockManager
from downstream_detector import DownstreamDetector
from merge_strategy import MergeStrategy


class ConflictSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class EnhancedActivityLogManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.log_dir = self.repo_path / ".activity_log"
        self.log_dir.mkdir(exist_ok=True)

        # Initialize sub-managers
        self.lock_manager = LockManager(repo_path)
        self.downstream_detector = DownstreamDetector(repo_path)
        self.merge_strategy = MergeStrategy(repo_path)

        self._setup_gitignore()
        self._ensure_directories()

    def _ensure_directories(self):
        """Ensure all required directories exist"""
        (self.log_dir / "changes").mkdir(exist_ok=True)
        (self.log_dir / "approvals").mkdir(exist_ok=True)
        (self.log_dir / "locks").mkdir(exist_ok=True)
        (self.log_dir / "escalations").mkdir(exist_ok=True)
        (self.log_dir / "rollbacks").mkdir(exist_ok=True)

    def _setup_gitignore(self):
        """Setup .gitignore for activity log"""
        gitignore_path = self.log_dir / ".gitignore"
        if not gitignore_path.exists():
            gitignore_path.write_text("*.json\n")

    def start_editing(self, file_path: str, function_name: str, developer: str,
                     severity: str = "high", timeout_minutes: int = 30) -> Dict:
        """
        Developer starts editing a function
        Acquires lock on HIGH conflicts
        Returns lock status
        """

        lock_result = self.lock_manager.acquire_lock(
            file_path, function_name, developer, severity, timeout_minutes
        )
        return lock_result

    def log_change(self, developer: str, file_path: str, function_name: str,
                   old_code: str, new_code: str, feature_branch: str,
                   verbal_description: str) -> Dict:
        """
        Log a code change with full analysis
        Returns change record with conflict detection, downstream impacts, merge strategies
        """

        change_id = datetime.now().isoformat()

        # Detect conflict severity
        conflict_severity, related_changes = self._detect_conflicts(
            file_path, function_name, old_code, new_code
        )

        # Calculate line changes
        line_changes = self._calculate_changes(old_code, new_code)

        # Detect downstream impacts
        downstream_analysis = self.downstream_detector.flag_downstream_impacts(
            file_path, function_name, verbal_description
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
            "line_changes": line_changes,
            "downstream_impacts": downstream_analysis
        }

        # Save to activity log
        log_file = self.log_dir / "changes" / f"{file_path.replace('/', '_')}_{function_name}_{change_id.replace(':', '-')}.json"
        log_file.write_text(json.dumps(change_record, indent=2))

        # On HIGH conflict: Auto-push and offer merge strategies
        if conflict_severity == ConflictSeverity.HIGH:
            self._handle_high_conflict(change_record, related_changes)

        # Release lock after change is logged
        if conflict_severity != ConflictSeverity.LOW:
            self.lock_manager.release_lock(file_path, function_name)

        return change_record

    def _handle_high_conflict(self, change_record: Dict, related_developers: List[str]):
        """Handle HIGH conflict: auto-push, suggest merge strategies, track escalation"""

        # Log auto-push
        push_log = {
            "timestamp": datetime.now().isoformat(),
            "branch": change_record["branch"],
            "change_id": change_record["id"],
            "status": "QUEUED_FOR_PUSH",
            "auto_triggered_by": "HIGH_CONFLICT"
        }

        push_file = self.log_dir / f"push_{change_record['branch'].replace('/', '_')}_{datetime.now().isoformat().replace(':', '-')}.json"
        push_file.write_text(json.dumps(push_log, indent=2))

        # Track escalation timeout
        escalation = {
            "file": change_record["file"],
            "function": change_record["function"],
            "created_at": datetime.now().isoformat(),
            "timeout_minutes": 30,
            "timeout_at": (datetime.now() + timedelta(minutes=30)).isoformat(),
            "developers_involved": [change_record["developer"]] + related_developers,
            "approvals_needed": related_developers + [change_record["developer"]],
            "status": "PENDING"
        }

        escalation_file = self.log_dir / "escalations" / f"{change_record['file'].replace('/', '_')}_{change_record['function']}_escalation.json"
        escalation_file.write_text(json.dumps(escalation, indent=2))

    def get_merge_strategies(self, file_path: str, function_name: str) -> Dict:
        """
        Get suggested merge strategies for a HIGH conflict
        Surfaces both auto-merge (recommended) and manual options
        """

        # Load latest changes to this function
        pattern = f"*{file_path.replace('/', '_')}_{function_name}_*.json"
        changes_dir = self.log_dir / "changes"

        if not changes_dir.exists():
            return {"error": "No changes found"}

        changes = sorted(changes_dir.glob(pattern))
        if len(changes) < 2:
            return {"error": "Less than 2 changes (no conflict)"}

        # Load last two changes
        with open(changes[-1]) as f:
            change1 = json.load(f)
        with open(changes[-2]) as f:
            change2 = json.load(f)

        # Calculate overlap for confidence
        overlap = min(change1["line_changes"], change2["line_changes"]) / \
                  max(change1["line_changes"], change2["line_changes"]) if max(change1["line_changes"], change2["line_changes"]) > 0 else 0

        # Get strategies
        strategies = self.merge_strategy.suggest_merge_strategy(
            file_path, function_name,
            change1["developer"], change2["developer"],
            change1["description"], change2["description"],
            overlap
        )

        return strategies

    def record_approval(self, developer: str, file_path: str, function_name: str,
                       approval_status: str = "approved") -> Dict:
        """
        Record developer approval for merge (Option A: single approval per developer)
        """

        approval_file = self.log_dir / "approvals" / f"{file_path.replace('/', '_')}_{function_name}_approvals.json"

        approvals = {}
        if approval_file.exists():
            with open(approval_file) as f:
                approvals = json.load(f)

        if "approved_by" not in approvals:
            approvals["approved_by"] = []
        if "rejected_by" not in approvals:
            approvals["rejected_by"] = []

        if approval_status == "approved":
            if developer not in approvals["approved_by"]:
                approvals["approved_by"].append(developer)
            if developer in approvals["rejected_by"]:
                approvals["rejected_by"].remove(developer)

        else:
            if developer not in approvals["rejected_by"]:
                approvals["rejected_by"].append(developer)
            if developer in approvals["approved_by"]:
                approvals["approved_by"].remove(developer)

        approvals["last_update"] = datetime.now().isoformat()
        approval_file.write_text(json.dumps(approvals, indent=2))

        return approvals

    def can_merge_to_main(self, file_path: str, function_name: str) -> Tuple[bool, Dict]:
        """
        Check if merge to main is allowed
        Returns: (can_merge, status_dict)
        """

        changes_dir = self.log_dir / "changes"
        if not changes_dir.exists():
            return True, {"reason": "No activity log (auto-merge allowed)"}

        # Find changes to this function
        pattern = f"*{file_path.replace('/', '_')}_{function_name}_*.json"
        changes = list(changes_dir.glob(pattern))

        if not changes:
            return True, {"reason": "No conflicts detected"}

        # Check if any HIGH conflict
        has_high_conflict = False
        for change_file in changes:
            with open(change_file) as f:
                change = json.load(f)
                if change.get("conflict_severity") == "high":
                    has_high_conflict = True
                    break

        if not has_high_conflict:
            return True, {"reason": "Only LOW/MEDIUM conflicts (auto-merge allowed)"}

        # For HIGH conflicts, check all developers approved
        approval_file = self.log_dir / "approvals" / f"{file_path.replace('/', '_')}_{function_name}_approvals.json"

        if not approval_file.exists():
            return False, {
                "reason": "HIGH conflict requires approval",
                "status": "APPROVAL_PENDING",
                "missing_approvals": "All developers"
            }

        with open(approval_file) as f:
            approvals = json.load(f)

        # Get all developers involved
        developers_involved = set()
        for change_file in changes:
            with open(change_file) as f:
                change = json.load(f)
                developers_involved.add(change["developer"])

        approved_by = set(approvals.get("approved_by", []))
        rejected_by = set(approvals.get("rejected_by", []))

        # If any developer rejected, merge is blocked
        if rejected_by:
            return False, {
                "reason": "Merge REJECTED by developers",
                "rejected_by": list(rejected_by),
                "approved_by": list(approved_by),
                "status": "REJECTED"
            }

        # Check if all approved
        if len(approved_by) == len(developers_involved):
            return True, {
                "reason": "All developers approved",
                "approved_by": list(approved_by),
                "status": "APPROVED"
            }

        missing = developers_involved - approved_by
        return False, {
            "reason": "Waiting for approvals",
            "approved_by": list(approved_by),
            "waiting_for": list(missing),
            "status": "PENDING_APPROVAL"
        }

    def record_rollback(self, merge_commit_sha: str, file_path: str,
                       function_name: str, reason: str) -> Dict:
        """
        Record a rollback of a merged change
        Tracks why merge was reverted for learning
        """

        rollback_record = {
            "timestamp": datetime.now().isoformat(),
            "merge_commit": merge_commit_sha,
            "file": file_path,
            "function": function_name,
            "reason": reason,
            "status": "ROLLED_BACK"
        }

        rollback_file = self.log_dir / "rollbacks" / f"{file_path.replace('/', '_')}_{function_name}_{datetime.now().isoformat().replace(':', '-')}.json"
        rollback_file.write_text(json.dumps(rollback_record, indent=2))

        return rollback_record

    # ========== Helper Methods ==========

    def _detect_conflicts(self, file_path: str, function_name: str,
                         old_code: str, new_code: str) -> Tuple[ConflictSeverity, List[str]]:
        """Detect conflicts with previous changes"""

        changes_dir = self.log_dir / "changes"
        if not changes_dir.exists():
            return ConflictSeverity.LOW, []

        pattern = f"*{file_path.replace('/', '_')}_{function_name}_*.json"
        existing_changes = list(changes_dir.glob(pattern))

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

        # Calculate overlap ratio
        prev_lines_changed = prev_change.get("line_changes", 0)
        current_lines_changed = len(changes) // 2

        if max(prev_lines_changed, current_lines_changed) == 0:
            overlap_ratio = 0
        else:
            overlap_ratio = min(prev_lines_changed, current_lines_changed) / max(prev_lines_changed, current_lines_changed)

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


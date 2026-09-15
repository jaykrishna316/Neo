#!/usr/bin/env python3
"""
Activity Log Server - REST API for distributed activity log management
Run this server locally and expose via ngrok for multi-dev testing
"""

from flask import Flask, request, jsonify
from pathlib import Path
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import difflib
import threading

from workflow_state_machine import WorkflowStateMachine, WorkflowState
from notification_manager import NotificationManager, NotificationType, NotificationChannel

app = Flask(__name__)
STORAGE_DIR = Path("./activity_log_storage")
LOCK = threading.Lock()  # Prevent concurrent writes

# Global managers
state_machines = {}  # file::function -> WorkflowStateMachine
notification_manager = NotificationManager()

# Ensure storage directory exists
STORAGE_DIR.mkdir(exist_ok=True)
(STORAGE_DIR / "changes").mkdir(exist_ok=True)
(STORAGE_DIR / "approvals").mkdir(exist_ok=True)
(STORAGE_DIR / "escalations").mkdir(exist_ok=True)
(STORAGE_DIR / "rollbacks").mkdir(exist_ok=True)


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "service": "activity-log-server"}), 200


# ========== PHASE 3: Notification Endpoints ==========


@app.route("/api/subscribe", methods=["POST"])
def subscribe_notifications():
    """Subscribe to notifications"""
    try:
        data = request.json
        developer = data.get("developer")
        channel = data.get("channel", "webhook")  # webhook, email, slack, polling
        endpoint = data.get("endpoint", "")
        notify_on = data.get("notify_on")  # List of notification types or None for all

        if not developer:
            return jsonify({"error": "Missing developer"}), 400

        result = notification_manager.subscribe(
            developer, NotificationChannel[channel.upper()], endpoint, notify_on
        )
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Poll for notifications (for developers using polling channel)"""
    try:
        developer = request.args.get("developer")
        since = request.args.get("since")  # ISO timestamp

        if not developer:
            return jsonify({"error": "Missing developer"}), 400

        notifications = notification_manager.get_notifications(developer, since)
        return jsonify({"notifications": notifications}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/workflow/state", methods=["GET"])
def get_workflow_state():
    """Get current workflow state for a function"""
    try:
        file_path = request.args.get("file_path")
        function_name = request.args.get("function_name")

        if not all([file_path, function_name]):
            return jsonify({"error": "Missing file_path or function_name"}), 400

        key = f"{file_path}::{function_name}"

        if key not in state_machines:
            return jsonify({"state": "available", "message": "No active workflow"}), 200

        state = state_machines[key].get_state()
        return jsonify(state), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== PHASE 4: Workflow State Machine Endpoints ==========


@app.route("/api/start_editing", methods=["POST"])
def start_editing_endpoint():
    """
    Developer starts editing - REQUIRED before any coding
    Acquires lock and notifies other developers
    """
    try:
        data = request.json
        developer = data.get("developer")
        file_path = data.get("file_path")
        function_name = data.get("function_name")

        if not all([developer, file_path, function_name]):
            return jsonify({"error": "Missing required fields"}), 400

        key = f"{file_path}::{function_name}"

        # Get or create state machine
        if key not in state_machines:
            state_machines[key] = WorkflowStateMachine(file_path, function_name)

        machine = state_machines[key]

        # Try to start editing
        allowed, message, new_state = machine.start_editing(developer)

        if allowed:
            # Notify others if this is first developer
            if new_state == WorkflowState.EDITING:
                notification_manager.notify(
                    "all",
                    NotificationType.LOCK_ACQUIRED,
                    {
                        "developer": developer,
                        "file": file_path,
                        "function": function_name,
                        "message": message,
                    },
                    file_path,
                    function_name,
                )

            return (
                jsonify(
                    {
                        "success": True,
                        "message": message,
                        "lock_acquired": True,
                        "state": new_state.value,
                        "developer": developer,
                    }
                ),
                200,
            )
        else:
            # Notify waiting developer
            blocked_devs = machine.waiting_developers
            notification_manager.notify(
                developer,
                NotificationType.LOCK_BLOCKED,
                {
                    "blocking_developer": machine.current_editor,
                    "file": file_path,
                    "function": function_name,
                    "message": message,
                    "queue_position": blocked_devs.index(developer) + 1
                    if developer in blocked_devs
                    else 0,
                },
                file_path,
                function_name,
            )

            return (
                jsonify(
                    {
                        "success": False,
                        "message": message,
                        "lock_acquired": False,
                        "state": new_state.value,
                        "blocking_developer": machine.current_editor,
                        "waiting_in_queue": blocked_devs.index(developer) + 1
                        if developer in blocked_devs
                        else 0,
                    }
                ),
                200,
            )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/finish_editing", methods=["POST"])
def finish_editing_endpoint():
    """
    Developer finishes editing and releases lock
    Notifies next waiting developer
    """
    try:
        data = request.json
        developer = data.get("developer")
        file_path = data.get("file_path")
        function_name = data.get("function_name")

        if not all([developer, file_path, function_name]):
            return jsonify({"error": "Missing required fields"}), 400

        key = f"{file_path}::{function_name}"

        if key not in state_machines:
            return jsonify({"error": "No active workflow"}), 400

        machine = state_machines[key]
        success, message, new_state = machine.finish_editing(developer)

        if success:
            # Notify that lock is released
            notification_manager.notify(
                "all",
                NotificationType.LOCK_RELEASED,
                {
                    "developer": developer,
                    "file": file_path,
                    "function": function_name,
                    "message": message,
                },
                file_path,
                function_name,
            )

            # If someone was waiting, notify them specifically
            if machine.waiting_developers:
                next_dev = machine.waiting_developers[0]
                notification_manager.notify(
                    next_dev,
                    NotificationType.REVIEW_REQUESTED,
                    {
                        "from_developer": developer,
                        "file": file_path,
                        "function": function_name,
                        "action": "Review my changes, then you can edit",
                        "branch": data.get("branch", "unknown"),
                        "pr_link": data.get("pr_link"),
                    },
                    file_path,
                    function_name,
                )

            return (
                jsonify(
                    {
                        "success": True,
                        "message": message,
                        "state": new_state.value,
                        "next_developer": machine.waiting_developers[0]
                        if machine.waiting_developers
                        else None,
                    }
                ),
                200,
            )
        else:
            return jsonify({"success": False, "message": message}), 400

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/log_change", methods=["POST"])
def log_change():
    """Log a code change with conflict detection"""
    try:
        data = request.json
        developer = data.get("developer")
        file_path = data.get("file_path")
        function_name = data.get("function_name")
        old_code = data.get("old_code", "")
        new_code = data.get("new_code", "")
        feature_branch = data.get("feature_branch")
        verbal_description = data.get("verbal_description")

        if not all([developer, file_path, function_name, feature_branch]):
            return jsonify({"error": "Missing required fields"}), 400

        change_id = datetime.now().isoformat()

        # Detect conflicts
        conflict_severity, related_changes = _detect_conflicts(
            file_path, function_name, old_code, new_code
        )

        # Calculate line changes
        line_changes = _calculate_changes(old_code, new_code)

        # Create change record
        change_record = {
            "id": change_id,
            "developer": developer,
            "file": file_path,
            "function": function_name,
            "branch": feature_branch,
            "timestamp": change_id,
            "description": verbal_description,
            "conflict_severity": conflict_severity,
            "related_changes": related_changes,
            "old_lines": len(old_code.split("\n")),
            "new_lines": len(new_code.split("\n")),
            "line_changes": line_changes,
        }

        # Save to storage
        with LOCK:
            log_file = (
                STORAGE_DIR
                / "changes"
                / f"{file_path.replace('/', '_')}_{function_name}_{change_id.replace(':', '-')}.json"
            )
            log_file.write_text(json.dumps(change_record, indent=2))

        # Handle HIGH conflict
        if conflict_severity == "high":
            _create_escalation(change_record, related_changes)

        return jsonify(change_record), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/record_approval", methods=["POST"])
def record_approval():
    """Record developer approval for a change"""
    try:
        data = request.json
        developer = data.get("developer")
        file_path = data.get("file_path")
        function_name = data.get("function_name")
        approval_status = data.get("approval_status", "approved")

        if not all([developer, file_path, function_name]):
            return jsonify({"error": "Missing required fields"}), 400

        with LOCK:
            approval_file = (
                STORAGE_DIR
                / "approvals"
                / f"{file_path.replace('/', '_')}_{function_name}_approvals.json"
            )

            approvals = {}
            if approval_file.exists():
                approvals = json.loads(approval_file.read_text())

            if "approved_by" not in approvals:
                approvals["approved_by"] = []
            if "rejected_by" not in approvals:
                approvals["rejected_by"] = []

            if approval_status == "approved":
                if developer not in approvals["approved_by"]:
                    approvals["approved_by"].append(developer)
                if developer in approvals["rejected_by"]:
                    approvals["rejected_by"].remove(developer)
            else:  # rejected
                if developer not in approvals["rejected_by"]:
                    approvals["rejected_by"].append(developer)
                if developer in approvals["approved_by"]:
                    approvals["approved_by"].remove(developer)

            approvals["last_update"] = datetime.now().isoformat()
            approval_file.write_text(json.dumps(approvals, indent=2))

        return jsonify(approvals), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/conflicts", methods=["GET"])
def get_conflicts():
    """Find HIGH conflicts between branches"""
    try:
        base_branch = request.args.get("base_branch", "main")
        head_branch = request.args.get("head_branch")

        high_conflicts = []
        changes_dir = STORAGE_DIR / "changes"

        if not changes_dir.exists():
            return jsonify({"conflicts": []}), 200

        # Group changes by function
        functions = {}
        for change_file in changes_dir.glob("*.json"):
            with open(change_file) as f:
                change = json.load(f)

            key = f"{change['file']}::{change['function']}"
            if key not in functions:
                functions[key] = []
            functions[key].append(change)

        # Find HIGH conflicts
        for func_key, changes in functions.items():
            if len(changes) >= 2:
                high_changes = [
                    c for c in changes if c.get("conflict_severity") == "high"
                ]

                if high_changes:
                    file_path, function_name = func_key.split("::")
                    conflict = {
                        "file": file_path,
                        "function": function_name,
                        "severity": "HIGH",
                        "developers_involved": list(
                            set([c["developer"] for c in changes])
                        ),
                        "descriptions": [c["description"] for c in changes],
                        "changes_count": len(changes),
                    }
                    high_conflicts.append(conflict)

        return jsonify({"conflicts": high_conflicts}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/can_merge", methods=["GET"])
def can_merge():
    """Check if merge to main is allowed"""
    try:
        file_path = request.args.get("file_path")
        function_name = request.args.get("function_name")

        if not all([file_path, function_name]):
            return jsonify({"error": "Missing file_path or function_name"}), 400

        changes_dir = STORAGE_DIR / "changes"
        if not changes_dir.exists():
            return (
                jsonify(
                    {
                        "can_merge": True,
                        "status": {"reason": "No activity log (auto-merge allowed)"},
                    }
                ),
                200,
            )

        # Find changes to this function
        pattern = f"*{file_path.replace('/', '_')}_{function_name}_*.json"
        changes = list(changes_dir.glob(pattern))

        if not changes:
            return (
                jsonify(
                    {
                        "can_merge": True,
                        "status": {"reason": "No conflicts detected"},
                    }
                ),
                200,
            )

        # Check if any HIGH conflict
        has_high_conflict = False
        for change_file in changes:
            with open(change_file) as f:
                change = json.load(f)
                if change.get("conflict_severity") == "high":
                    has_high_conflict = True
                    break

        if not has_high_conflict:
            return (
                jsonify(
                    {
                        "can_merge": True,
                        "status": {
                            "reason": "Only LOW/MEDIUM conflicts (auto-merge allowed)"
                        },
                    }
                ),
                200,
            )

        # For HIGH conflicts, check all developers approved
        approval_file = (
            STORAGE_DIR
            / "approvals"
            / f"{file_path.replace('/', '_')}_{function_name}_approvals.json"
        )

        if not approval_file.exists():
            return (
                jsonify(
                    {
                        "can_merge": False,
                        "status": {
                            "reason": "HIGH conflict requires approval",
                            "status": "APPROVAL_PENDING",
                            "missing_approvals": "All developers",
                        },
                    }
                ),
                200,
            )

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
            return (
                jsonify(
                    {
                        "can_merge": False,
                        "status": {
                            "reason": "Merge REJECTED by developers",
                            "rejected_by": list(rejected_by),
                            "approved_by": list(approved_by),
                            "status": "REJECTED",
                        },
                    }
                ),
                200,
            )

        # Check if all approved
        if len(approved_by) == len(developers_involved):
            return (
                jsonify(
                    {
                        "can_merge": True,
                        "status": {
                            "reason": "All developers approved",
                            "approved_by": list(approved_by),
                            "status": "APPROVED",
                        },
                    }
                ),
                200,
            )

        missing = developers_involved - approved_by
        return (
            jsonify(
                {
                    "can_merge": False,
                    "status": {
                        "reason": "Waiting for approvals",
                        "approved_by": list(approved_by),
                        "waiting_for": list(missing),
                        "status": "PENDING_APPROVAL",
                    },
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/record_rollback", methods=["POST"])
def record_rollback():
    """Record a rollback of a merged change"""
    try:
        data = request.json
        merge_commit_sha = data.get("merge_commit_sha")
        file_path = data.get("file_path")
        function_name = data.get("function_name")
        reason = data.get("reason")

        if not all([merge_commit_sha, file_path, function_name, reason]):
            return jsonify({"error": "Missing required fields"}), 400

        rollback_record = {
            "timestamp": datetime.now().isoformat(),
            "merge_commit": merge_commit_sha,
            "file": file_path,
            "function": function_name,
            "reason": reason,
            "status": "ROLLED_BACK",
        }

        with LOCK:
            rollback_file = (
                STORAGE_DIR
                / "rollbacks"
                / f"{file_path.replace('/', '_')}_{function_name}_{datetime.now().isoformat().replace(':', '-')}.json"
            )
            rollback_file.write_text(json.dumps(rollback_record, indent=2))

        return jsonify(rollback_record), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== PHASE 5: PR Management & Auto-Approver Assignment ==========


@app.route("/api/create_pr", methods=["POST"])
def create_pr_endpoint():
    """
    Developer creates a PR after finishing edits
    Records PR in activity log and prepares for next developer review
    """
    try:
        data = request.json
        developer = data.get("developer")
        file_path = data.get("file_path")
        function_name = data.get("function_name")
        pr_number = data.get("pr_number")
        pr_link = data.get("pr_link")
        branch = data.get("branch")

        if not all([developer, file_path, function_name, pr_number]):
            return jsonify({"error": "Missing required fields"}), 400

        key = f"{file_path}::{function_name}"

        if key not in state_machines:
            return jsonify({"error": "No active workflow"}), 400

        machine = state_machines[key]

        # Record PR creation
        pr_record = {
            "timestamp": datetime.now().isoformat(),
            "developer": developer,
            "file_path": file_path,
            "function_name": function_name,
            "pr_number": pr_number,
            "pr_link": pr_link,
            "branch": branch,
            "status": "OPEN",
        }

        with LOCK:
            pr_file = (
                STORAGE_DIR
                / f"pr_{file_path.replace('/', '_')}_{function_name}_{pr_number}.json"
            )
            pr_file.write_text(json.dumps(pr_record, indent=2))

        # Update state machine
        machine.create_pr(int(pr_number))

        # Notify next developer about PR
        if machine.waiting_developers:
            next_dev = machine.waiting_developers[0]
            notification_manager.notify(
                next_dev,
                NotificationType.APPROVAL_NEEDED,
                {
                    "from_developer": developer,
                    "file": file_path,
                    "function": function_name,
                    "pr_number": pr_number,
                    "pr_link": pr_link,
                    "branch": branch,
                    "action": "review_pull_merge",
                },
                file_path,
                function_name,
            )

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"PR {pr_number} created and recorded",
                    "pr_number": pr_number,
                    "state": machine.current_state.value,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/review_options", methods=["GET"])
def review_options_endpoint():
    """
    Get options for next developer to review and handle PR
    Returns: pull (get code), review (review changes), merge (merge PR), discard
    """
    try:
        developer = request.args.get("developer")
        file_path = request.args.get("file_path")
        function_name = request.args.get("function_name")

        if not all([developer, file_path, function_name]):
            return jsonify({"error": "Missing required fields"}), 400

        key = f"{file_path}::{function_name}"

        if key not in state_machines:
            return jsonify({"error": "No active workflow"}), 400

        machine = state_machines[key]

        # Check if this developer is next in queue
        if not machine.waiting_developers or machine.waiting_developers[0] != developer:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": f"Not your turn yet. Current editor: {machine.current_editor}",
                    }
                ),
                200,
            )

        # Get latest PR for this function
        with LOCK:
            changes_dir = STORAGE_DIR
            pattern = f"pr_{file_path.replace('/', '_')}_{function_name}_*.json"
            pr_files = sorted(list(changes_dir.glob(pattern)))

            latest_pr = None
            if pr_files:
                with open(pr_files[-1]) as f:
                    latest_pr = json.load(f)

        return (
            jsonify(
                {
                    "success": True,
                    "developer": developer,
                    "file_path": file_path,
                    "function_name": function_name,
                    "latest_pr": latest_pr,
                    "options": {
                        "pull": {
                            "action": "pull",
                            "description": "Pull and review the code changes",
                            "next_step": "You can review, then merge or discard",
                        },
                        "review": {
                            "action": "review",
                            "description": "View code diff for this PR",
                            "next_step": "Decide to merge or discard",
                        },
                        "merge": {
                            "action": "merge",
                            "description": "Merge this PR to your branch and continue editing",
                            "next_step": "You acquire lock and can make more changes",
                        },
                        "discard": {
                            "action": "discard",
                            "description": "Discard these changes and start fresh",
                            "next_step": "You acquire lock with clean state",
                        },
                    },
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/complete_review", methods=["POST"])
def complete_review_endpoint():
    """
    Developer completes review and chooses action: merge or discard
    Then acquires lock to continue editing
    """
    try:
        data = request.json
        developer = data.get("developer")
        file_path = data.get("file_path")
        function_name = data.get("function_name")
        action = data.get("action")  # "merge" or "discard"

        if not all([developer, file_path, function_name, action]):
            return jsonify({"error": "Missing required fields"}), 400

        if action not in ["merge", "discard"]:
            return jsonify({"error": "Invalid action. Must be 'merge' or 'discard'"}), 400

        key = f"{file_path}::{function_name}"

        if key not in state_machines:
            return jsonify({"error": "No active workflow"}), 400

        machine = state_machines[key]

        # Record the review action
        review_record = {
            "timestamp": datetime.now().isoformat(),
            "developer": developer,
            "file_path": file_path,
            "function_name": function_name,
            "action": action,
            "status": "REVIEWED",
        }

        with LOCK:
            review_file = (
                STORAGE_DIR
                / "changes"
                / f"review_{file_path.replace('/', '_')}_{function_name}_{datetime.now().isoformat().replace(':', '-')}.json"
            )
            review_file.write_text(json.dumps(review_record, indent=2))

        # Notify about review completion
        notification_manager.notify(
            "all",
            NotificationType.APPROVED,
            {
                "developer": developer,
                "file": file_path,
                "function": function_name,
                "action": action,
            },
            file_path,
            function_name,
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Review completed. Action: {action}",
                    "action": action,
                    "next_step": f"You can now acquire lock to continue editing",
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/merge_to_main", methods=["POST"])
def merge_to_main_endpoint():
    """
    Merge PR to main branch
    Automatically adds all developers who touched the file as approvers
    """
    try:
        data = request.json
        developer = data.get("developer")
        file_path = data.get("file_path")
        function_name = data.get("function_name")
        pr_number = data.get("pr_number")
        merge_commit_sha = data.get("merge_commit_sha", "unknown")

        if not all([developer, file_path, function_name, pr_number]):
            return jsonify({"error": "Missing required fields"}), 400

        key = f"{file_path}::{function_name}"

        if key not in state_machines:
            return jsonify({"error": "No active workflow"}), 400

        machine = state_machines[key]

        # Get all developers who participated
        all_developers = list(machine.all_developers)

        # Record merge
        merge_record = {
            "timestamp": datetime.now().isoformat(),
            "developer": developer,
            "file_path": file_path,
            "function_name": function_name,
            "pr_number": pr_number,
            "merged_to": "main",
            "all_approvers": all_developers,
            "merge_commit_sha": merge_commit_sha,
            "status": "MERGED",
        }

        with LOCK:
            merge_file = (
                STORAGE_DIR
                / f"merge_{file_path.replace('/', '_')}_{function_name}_{pr_number}.json"
            )
            merge_file.write_text(json.dumps(merge_record, indent=2))

        # Update state machine
        machine.merge_to_main(merge_commit_sha)

        # Notify all developers that merge happened
        notification_manager.notify(
            "all",
            NotificationType.MERGED,
            {
                "file": file_path,
                "function": function_name,
                "pr_number": pr_number,
                "merged_by": developer,
                "all_approvers": all_developers,
            },
            file_path,
            function_name,
        )

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"PR {pr_number} merged to main",
                    "pr_number": pr_number,
                    "merged_to": "main",
                    "all_approvers_required": all_developers,
                    "state": machine.current_state.value,
                }
            ),
            200,
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== Helper Functions ==========


def _detect_conflicts(
    file_path: str, function_name: str, old_code: str, new_code: str
) -> Tuple[str, List[str]]:
    """Detect conflicts with previous changes"""

    changes_dir = STORAGE_DIR / "changes"
    if not changes_dir.exists():
        return "low", []

    pattern = f"*{file_path.replace('/', '_')}_{function_name}_*.json"
    existing_changes = sorted(list(changes_dir.glob(pattern)))

    if not existing_changes:
        return "low", []

    # Load latest change
    with open(existing_changes[-1]) as f:
        prev_change = json.load(f)

    # Analyze overlap
    old_lines = old_code.split("\n")
    new_lines = new_code.split("\n")

    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    changes = [l for l in diff if l.startswith("+") or l.startswith("-")]

    prev_lines_changed = prev_change.get("line_changes", 0)
    current_lines_changed = len(changes) // 2

    if max(prev_lines_changed, current_lines_changed) == 0:
        overlap_ratio = 0
    else:
        overlap_ratio = min(prev_lines_changed, current_lines_changed) / max(
            prev_lines_changed, current_lines_changed
        )

    if overlap_ratio == 0:
        severity = "low"
    elif overlap_ratio < 0.5:
        severity = "medium"
    else:
        severity = "high"

    return severity, [prev_change["developer"]]


def _calculate_changes(old_code: str, new_code: str) -> int:
    """Calculate number of lines changed"""
    old_lines = old_code.split("\n")
    new_lines = new_code.split("\n")
    diff = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))
    return len([l for l in diff if l.startswith("+") or l.startswith("-")])


def _create_escalation(change_record: Dict, related_developers: List[str]):
    """Create escalation record for HIGH conflict"""
    escalation = {
        "file": change_record["file"],
        "function": change_record["function"],
        "created_at": datetime.now().isoformat(),
        "timeout_minutes": 30,
        "timeout_at": (datetime.now() + timedelta(minutes=30)).isoformat(),
        "developers_involved": [change_record["developer"]] + related_developers,
        "status": "PENDING",
    }

    with LOCK:
        escalation_file = (
            STORAGE_DIR
            / "escalations"
            / f"{change_record['file'].replace('/', '_')}_{change_record['function']}_escalation.json"
        )
        escalation_file.write_text(json.dumps(escalation, indent=2))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

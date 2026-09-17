#!/usr/bin/env python3
"""
Workflow State Machine - Manages complete lifecycle of collaborative edits
Tracks state from intent to merge, prevents invalid transitions
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import json


class WorkflowState(Enum):
    """Complete workflow states"""
    AVAILABLE = "available"  # No one editing
    EDITING = "editing"  # Dev editing, lock held
    CONFLICT_WAITING = "conflict_waiting"  # Another dev waiting
    PENDING_REVIEW = "pending_review"  # First dev done, second reviewing
    BOTH_DONE = "both_done"  # Both finished edits
    HANDOFF_PENDING = "handoff_pending"  # Work completed, awaiting MR/consumption (Neo 2.0)
    IN_PR = "in_pr"  # Pull request created
    APPROVED = "approved"  # All developers approved
    MERGED = "merged"  # Merged to main
    ROLLED_BACK = "rolled_back"  # Reverted, tracking why


class WorkflowStateMachine:
    """Manages state transitions for collaborative workflow"""

    def __init__(self, file_path: str, function_name: str):
        self.file_path = file_path
        self.function_name = function_name
        self.state = WorkflowState.AVAILABLE
        self.state_history = []
        self.current_editor = None
        self.waiting_developers = []
        self.all_developers = set()

    def start_editing(self, developer: str) -> Tuple[bool, str, WorkflowState]:
        """
        Developer starts editing
        Returns: (allowed, message, current_state)
        """
        if self.state == WorkflowState.AVAILABLE:
            # No one editing, allow
            self.current_editor = developer
            self.all_developers.add(developer)
            self._transition_to(WorkflowState.EDITING, developer, "Started editing")
            return True, f"{developer} started editing", WorkflowState.EDITING

        elif self.state == WorkflowState.EDITING:
            if self.current_editor == developer:
                # Same dev, already editing
                return True, f"{developer} already editing", WorkflowState.EDITING
            else:
                # Different dev, add to waiting queue
                if developer not in self.waiting_developers:
                    self.waiting_developers.append(developer)
                    self.all_developers.add(developer)
                    self._transition_to(
                        WorkflowState.CONFLICT_WAITING,
                        developer,
                        f"Waiting for {self.current_editor}",
                    )
                return (
                    False,
                    f"BLOCKED: {self.current_editor} is editing. Waiting list: {self.waiting_developers}",
                    WorkflowState.CONFLICT_WAITING,
                )

        else:
            # Invalid state for start_editing
            return False, f"Cannot edit in {self.state.value} state", self.state

    def finish_editing(self, developer: str) -> Tuple[bool, str, WorkflowState]:
        """
        Developer finishes editing and releases lock
        Returns: (success, message, next_state)
        """
        if self.current_editor == developer and self.state in [
            WorkflowState.EDITING,
            WorkflowState.CONFLICT_WAITING,
        ]:
            self._transition_to(WorkflowState.BOTH_DONE, developer, "Finished editing")

            # If others waiting, notify them
            if self.waiting_developers:
                next_dev = self.waiting_developers.pop(0)
                self._transition_to(
                    WorkflowState.PENDING_REVIEW, next_dev, f"{next_dev} should review"
                )
                return (
                    True,
                    f"{developer} finished. {next_dev} notified to review and continue.",
                    WorkflowState.PENDING_REVIEW,
                )
            else:
                return True, f"{developer} finished editing", WorkflowState.BOTH_DONE

        else:
            return (
                False,
                f"Cannot finish: {developer} not currently editing",
                self.state,
            )

    def create_pr(self, pr_number: int) -> Tuple[bool, str, WorkflowState]:
        """
        PR created for this function
        Returns: (success, message, current_state)
        """
        if self.state in [WorkflowState.BOTH_DONE, WorkflowState.PENDING_REVIEW]:
            self._transition_to(WorkflowState.IN_PR, None, f"PR #{pr_number} created")
            return True, f"PR #{pr_number} created for review", WorkflowState.IN_PR
        else:
            return (
                False,
                f"Cannot create PR in {self.state.value} state",
                self.state,
            )

    def record_approval(
        self, developer: str, approval_status: str
    ) -> Tuple[bool, str, WorkflowState]:
        """
        Developer approves/rejects
        Returns: (success, message, current_state)
        """
        if self.state == WorkflowState.IN_PR:
            if approval_status == "approved":
                # Check if all developers approved
                # For now, transition to APPROVED when first developer approves
                # Real implementation would check all in approval list
                self._transition_to(
                    WorkflowState.APPROVED, developer, f"{developer} approved"
                )
                return True, f"{developer} approved", WorkflowState.APPROVED
            else:
                # Rejected - go back to BOTH_DONE
                self._transition_to(
                    WorkflowState.BOTH_DONE, developer, f"{developer} rejected"
                )
                return True, f"{developer} rejected - back to editing", WorkflowState.BOTH_DONE

        else:
            return False, f"Cannot approve in {self.state.value} state", self.state

    def merge_to_main(self, merge_commit_sha: str) -> Tuple[bool, str, WorkflowState]:
        """
        Merge to main completed
        Returns: (success, message, final_state)
        """
        if self.state == WorkflowState.APPROVED:
            self._transition_to(
                WorkflowState.MERGED, None, f"Merged with commit {merge_commit_sha}"
            )
            return True, "Successfully merged to main", WorkflowState.MERGED
        else:
            return (
                False,
                f"Cannot merge in {self.state.value} state",
                self.state,
            )

    def rollback(self, merge_commit_sha: str, reason: str) -> Tuple[bool, str, WorkflowState]:
        """
        Rollback after merge
        Returns: (success, message, final_state)
        """
        if self.state == WorkflowState.MERGED:
            self._transition_to(
                WorkflowState.ROLLED_BACK,
                None,
                f"Rolled back {merge_commit_sha}: {reason}",
            )
            return True, f"Rollback recorded: {reason}", WorkflowState.ROLLED_BACK
        else:
            return (
                False,
                f"Cannot rollback in {self.state.value} state",
                self.state,
            )

    def get_state(self) -> Dict:
        """Get current workflow state"""
        return {
            "file": self.file_path,
            "function": self.function_name,
            "current_state": self.state.value,
            "current_editor": self.current_editor,
            "waiting_developers": self.waiting_developers,
            "all_developers": list(self.all_developers),
            "state_history": self.state_history[-10:],  # Last 10 transitions
        }

    def _transition_to(self, new_state: WorkflowState, actor: Optional[str], reason: str):
        """Record state transition"""
        transition = {
            "timestamp": datetime.now().isoformat(),
            "from_state": self.state.value,
            "to_state": new_state.value,
            "actor": actor,
            "reason": reason,
        }
        self.state_history.append(transition)
        self.state = new_state

    def can_transition_to(self, target_state: WorkflowState) -> bool:
        """Check if transition is valid"""
        valid_transitions = {
            WorkflowState.AVAILABLE: [WorkflowState.EDITING],
            WorkflowState.EDITING: [
                WorkflowState.BOTH_DONE,
                WorkflowState.CONFLICT_WAITING,
            ],
            WorkflowState.CONFLICT_WAITING: [WorkflowState.PENDING_REVIEW],
            WorkflowState.PENDING_REVIEW: [WorkflowState.BOTH_DONE],
            WorkflowState.BOTH_DONE: [WorkflowState.IN_PR, WorkflowState.EDITING, WorkflowState.HANDOFF_PENDING],
            WorkflowState.HANDOFF_PENDING: [WorkflowState.IN_PR, WorkflowState.EDITING],
            WorkflowState.IN_PR: [WorkflowState.APPROVED, WorkflowState.BOTH_DONE],
            WorkflowState.APPROVED: [WorkflowState.MERGED],
            WorkflowState.MERGED: [WorkflowState.ROLLED_BACK],
            WorkflowState.ROLLED_BACK: [WorkflowState.EDITING, WorkflowState.AVAILABLE],
        }

        return target_state in valid_transitions.get(self.state, [])

    def to_dict(self) -> Dict:
        """Serialize state machine"""
        return {
            "file_path": self.file_path,
            "function_name": self.function_name,
            "state": self.state.value,
            "current_editor": self.current_editor,
            "waiting_developers": self.waiting_developers,
            "all_developers": list(self.all_developers),
            "state_history": self.state_history,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "WorkflowStateMachine":
        """Deserialize state machine"""
        machine = cls(data["file_path"], data["function_name"])
        machine.state = WorkflowState(data["state"])
        machine.current_editor = data.get("current_editor")
        machine.waiting_developers = data.get("waiting_developers", [])
        machine.all_developers = set(data.get("all_developers", []))
        machine.state_history = data.get("state_history", [])
        return machine

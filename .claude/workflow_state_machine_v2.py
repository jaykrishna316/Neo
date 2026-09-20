#!/usr/bin/env python3
"""
Workflow State Machine v2 - Scalable Multi-Developer Support
Supports N developers, per-resource locking, timeout recovery, and concurrent editing

Architecture:
- ResourceLock: Encapsulates per-resource state management
- QueueManager: Handles developer queuing with timeout + priority support
- WorkflowStateMachine: Orchestrator for multi-resource workflows
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json
from dataclasses import dataclass, field, asdict


class WorkflowState(Enum):
    """Complete workflow states - unchanged from v1 for compatibility"""
    AVAILABLE = "available"
    EDITING = "editing"
    CONFLICT_WAITING = "conflict_waiting"
    PENDING_REVIEW = "pending_review"
    BOTH_DONE = "both_done"
    HANDOFF_PENDING = "handoff_pending"
    IN_PR = "in_pr"
    APPROVED = "approved"
    MERGED = "merged"
    ROLLED_BACK = "rolled_back"


@dataclass
class QueuedDeveloper:
    """Developer in waiting queue with metadata"""
    developer: str
    resource: str
    queued_at: datetime = field(default_factory=datetime.now)
    priority: int = 0  # 0=normal, 1=urgent, 2=critical

    def time_waiting(self) -> timedelta:
        """Time spent waiting in queue"""
        return datetime.now() - self.queued_at

    def to_dict(self) -> Dict:
        """Serialize for storage"""
        data = asdict(self)
        data['queued_at'] = self.queued_at.isoformat()
        return data


class ResourceLock:
    """Per-resource lock state management"""

    def __init__(self, resource: str, timeout_seconds: int = 3600):
        self.resource = resource
        self.current_editor: Optional[str] = None
        self.state = WorkflowState.AVAILABLE
        self.state_history: List[Dict] = []
        self.lock_acquired_at: Optional[datetime] = None
        self.timeout_seconds = timeout_seconds
        self.all_developers: set = set()

    def acquire_lock(self, developer: str) -> Tuple[bool, str]:
        """Attempt to acquire lock for developer"""
        if self.is_timed_out():
            self.release_lock(force=True)

        if self.state == WorkflowState.AVAILABLE or self.current_editor == developer:
            self.current_editor = developer
            self.state = WorkflowState.EDITING
            self.lock_acquired_at = datetime.now()
            self.all_developers.add(developer)
            self._record_transition(developer, "Lock acquired")
            return True, f"{developer} acquired lock on {self.resource}"

        return False, f"Resource {self.resource} locked by {self.current_editor}"

    def release_lock(self, developer: str = None, force: bool = False) -> Tuple[bool, str]:
        """Release lock from developer"""
        if force or self.current_editor == developer:
            old_editor = self.current_editor
            self.current_editor = None
            self.lock_acquired_at = None

            if self.state != WorkflowState.AVAILABLE:
                self.state = WorkflowState.AVAILABLE
                self._record_transition(developer, f"Lock released (force={force})")

            return True, f"Lock released from {old_editor}"

        return False, f"Only {self.current_editor} can release lock"

    def is_locked(self) -> bool:
        """Check if resource is currently locked"""
        return self.current_editor is not None and self.state != WorkflowState.AVAILABLE

    def is_timed_out(self) -> bool:
        """Check if lock has exceeded timeout"""
        if not self.is_locked() or not self.lock_acquired_at:
            return False

        elapsed = (datetime.now() - self.lock_acquired_at).total_seconds()
        return elapsed > self.timeout_seconds

    def get_lock_age(self) -> Optional[timedelta]:
        """Get age of current lock"""
        if not self.lock_acquired_at:
            return None
        return datetime.now() - self.lock_acquired_at

    def transition_to(self, new_state: WorkflowState, actor: Optional[str], reason: str):
        """Record state transition"""
        self.state = new_state
        self._record_transition(actor, reason)

    def _record_transition(self, actor: Optional[str], reason: str):
        """Record state transition in history"""
        transition = {
            "timestamp": datetime.now().isoformat(),
            "from_state": self.state.value,
            "to_state": self.state.value,
            "actor": actor,
            "reason": reason,
        }
        self.state_history.append(transition)

    def to_dict(self) -> Dict:
        """Serialize lock state"""
        return {
            "resource": self.resource,
            "current_editor": self.current_editor,
            "state": self.state.value,
            "is_locked": self.is_locked(),
            "is_timed_out": self.is_timed_out(),
            "lock_age_seconds": self.get_lock_age().total_seconds() if self.get_lock_age() else None,
            "all_developers": list(self.all_developers),
            "state_history": self.state_history[-10:],
        }


class QueueManager:
    """Manages developer queues per resource with timeout + priority support"""

    def __init__(self):
        self.queues: Dict[str, List[QueuedDeveloper]] = {}
        self.timeout_seconds = 3600  # 1 hour default

    def add_to_queue(self, developer: str, resource: str, priority: int = 0):
        """Add developer to resource queue"""
        if resource not in self.queues:
            self.queues[resource] = []

        # Don't add if already in queue
        if any(q.developer == developer and q.resource == resource for q in self.queues[resource]):
            return

        queued_dev = QueuedDeveloper(developer, resource, priority=priority)
        self.queues[resource].append(queued_dev)
        # Sort by priority (higher first) then by queue time (older first)
        self.queues[resource].sort(key=lambda q: (-q.priority, q.queued_at))

    def pop_next(self, resource: str) -> Optional[str]:
        """Get next developer from queue"""
        if resource not in self.queues or not self.queues[resource]:
            return None

        next_dev = self.queues[resource].pop(0)
        return next_dev.developer

    def remove_from_queue(self, developer: str, resource: str) -> bool:
        """Remove developer from queue"""
        if resource not in self.queues:
            return False

        self.queues[resource] = [
            q for q in self.queues[resource]
            if not (q.developer == developer and q.resource == resource)
        ]
        return True

    def get_queue_for_resource(self, resource: str) -> List[str]:
        """Get all developers waiting for resource"""
        if resource not in self.queues:
            return []
        return [q.developer for q in self.queues[resource]]

    def queue_size(self, resource: str) -> int:
        """Get queue length for resource"""
        return len(self.queues.get(resource, []))

    def clear_queue(self, resource: str):
        """Clear queue for resource"""
        if resource in self.queues:
            self.queues[resource] = []

    def get_all_queues(self) -> Dict[str, List[str]]:
        """Get all queues"""
        return {
            resource: [q.developer for q in devs]
            for resource, devs in self.queues.items()
        }

    def to_dict(self) -> Dict:
        """Serialize queue state"""
        return {
            resource: [q.to_dict() for q in devs]
            for resource, devs in self.queues.items()
        }


class WorkflowStateMachine:
    """
    Scalable workflow state machine supporting N developers.

    Key improvements over v1:
    - Per-resource locking (dev1 on file1 + dev2 on file2)
    - Timeout + deadlock recovery
    - Priority queue support
    - Concurrent editing support
    - Backward compatible API
    """

    def __init__(self, file_path: str = None, function_name: str = None):
        """Initialize state machine. Supports single-resource (v1) or multi-resource mode"""
        self.file_path = file_path
        self.function_name = function_name
        self.default_resource = f"{file_path}::{function_name}" if file_path and function_name else None

        # Core data structures
        self.resource_locks: Dict[str, ResourceLock] = {}
        self.queue_manager = QueueManager()
        self.all_developers: set = set()
        self.all_resources: set = set()

    def start_editing(self, developer: str, resource: str = None) -> Tuple[bool, str, WorkflowState]:
        """
        Developer starts editing a resource.
        Returns: (allowed, message, current_state)
        """
        resource = resource or self.default_resource
        if not resource:
            return False, "Resource must be specified", WorkflowState.AVAILABLE

        self.all_developers.add(developer)
        self.all_resources.add(resource)

        # Initialize resource lock if needed
        if resource not in self.resource_locks:
            self.resource_locks[resource] = ResourceLock(resource)

        lock = self.resource_locks[resource]

        # Try to acquire lock
        success, msg = lock.acquire_lock(developer)
        if success:
            return True, msg, WorkflowState.EDITING

        # Lock held, add to queue
        self.queue_manager.add_to_queue(developer, resource)
        lock.transition_to(WorkflowState.CONFLICT_WAITING, developer, "Waiting in queue")

        queue_size = self.queue_manager.queue_size(resource)
        return (
            False,
            f"{developer} queued for {resource}. Queue position: {queue_size}",
            WorkflowState.CONFLICT_WAITING,
        )

    def finish_editing(self, developer: str, resource: str = None) -> Tuple[bool, str, WorkflowState]:
        """
        Developer finishes editing and releases lock.
        Returns: (success, message, next_state)
        """
        resource = resource or self.default_resource
        if not resource:
            return False, "Resource must be specified", WorkflowState.AVAILABLE

        if resource not in self.resource_locks:
            return False, f"No lock found for {resource}", WorkflowState.AVAILABLE

        lock = self.resource_locks[resource]

        # Check if this developer has the lock
        if lock.current_editor != developer:
            return (
                False,
                f"{developer} doesn't have lock (held by {lock.current_editor})",
                lock.state,
            )

        # Release lock
        success, msg = lock.release_lock(developer)
        if not success:
            return False, msg, lock.state

        next_state = WorkflowState.BOTH_DONE
        lock.transition_to(next_state, developer, "Finished editing")

        # Check if anyone is waiting
        next_dev = self.queue_manager.pop_next(resource)
        if next_dev:
            # Acquire lock for next developer
            lock.acquire_lock(next_dev)
            next_state = WorkflowState.PENDING_REVIEW
            lock.transition_to(WorkflowState.EDITING, next_dev, f"Lock passed to {next_dev}")
            return True, f"{developer} finished. {next_dev} now editing.", WorkflowState.PENDING_REVIEW

        return True, f"{developer} finished editing {resource}", WorkflowState.BOTH_DONE

    def create_pr(self, pr_number: int, resource: str = None) -> Tuple[bool, str, WorkflowState]:
        """Create PR for resource"""
        resource = resource or self.default_resource
        if not resource:
            return False, "Resource must be specified", WorkflowState.AVAILABLE

        if resource not in self.resource_locks:
            return False, f"No lock found for {resource}", WorkflowState.AVAILABLE

        lock = self.resource_locks[resource]

        if lock.state in [WorkflowState.BOTH_DONE, WorkflowState.PENDING_REVIEW]:
            lock.transition_to(WorkflowState.IN_PR, None, f"PR #{pr_number} created")
            return True, f"PR #{pr_number} created for {resource}", WorkflowState.IN_PR

        return False, f"Cannot create PR in {lock.state.value} state", lock.state

    def record_approval(
        self, developer: str, approval_status: str, resource: str = None
    ) -> Tuple[bool, str, WorkflowState]:
        """Record developer approval"""
        resource = resource or self.default_resource
        if not resource:
            return False, "Resource must be specified", WorkflowState.AVAILABLE

        if resource not in self.resource_locks:
            return False, f"No lock found for {resource}", WorkflowState.AVAILABLE

        lock = self.resource_locks[resource]

        if lock.state != WorkflowState.IN_PR:
            return False, f"Cannot approve in {lock.state.value} state", lock.state

        if approval_status == "approved":
            lock.transition_to(WorkflowState.APPROVED, developer, f"{developer} approved")
            return True, f"{developer} approved", WorkflowState.APPROVED
        else:
            lock.transition_to(WorkflowState.BOTH_DONE, developer, f"{developer} rejected")
            return True, f"{developer} rejected", WorkflowState.BOTH_DONE

    def merge_to_main(self, merge_commit_sha: str, resource: str = None) -> Tuple[bool, str, WorkflowState]:
        """Merge to main"""
        resource = resource or self.default_resource
        if not resource:
            return False, "Resource must be specified", WorkflowState.AVAILABLE

        if resource not in self.resource_locks:
            return False, f"No lock found for {resource}", WorkflowState.AVAILABLE

        lock = self.resource_locks[resource]

        if lock.state != WorkflowState.APPROVED:
            return False, f"Cannot merge in {lock.state.value} state", lock.state

        lock.transition_to(WorkflowState.MERGED, None, f"Merged {merge_commit_sha}")
        return True, "Successfully merged to main", WorkflowState.MERGED

    def rollback(self, merge_commit_sha: str, reason: str, resource: str = None) -> Tuple[bool, str, WorkflowState]:
        """Rollback merge"""
        resource = resource or self.default_resource
        if not resource:
            return False, "Resource must be specified", WorkflowState.AVAILABLE

        if resource not in self.resource_locks:
            return False, f"No lock found for {resource}", WorkflowState.AVAILABLE

        lock = self.resource_locks[resource]

        if lock.state != WorkflowState.MERGED:
            return False, f"Cannot rollback in {lock.state.value} state", lock.state

        lock.transition_to(WorkflowState.ROLLED_BACK, None, f"Rolled back: {reason}")
        return True, f"Rollback recorded: {reason}", WorkflowState.ROLLED_BACK

    def get_resource_state(self, resource: str = None) -> Dict:
        """Get current state for resource"""
        resource = resource or self.default_resource
        if not resource:
            return {"error": "Resource must be specified"}

        if resource not in self.resource_locks:
            return {
                "resource": resource,
                "state": WorkflowState.AVAILABLE.value,
                "current_editor": None,
                "queue": [],
            }

        lock = self.resource_locks[resource]
        return {
            "resource": resource,
            **lock.to_dict(),
            "queue": self.queue_manager.get_queue_for_resource(resource),
        }

    def get_state(self) -> Dict:
        """Get overall state machine state (for v1 compatibility)"""
        primary_resource = self.default_resource

        return {
            "file": self.file_path,
            "function": self.function_name,
            "primary_resource": primary_resource,
            "all_developers": list(self.all_developers),
            "all_resources": list(self.all_resources),
            "resource_states": {
                resource: self.resource_locks[resource].to_dict()
                for resource in self.all_resources
            },
            "queues": self.queue_manager.get_all_queues(),
        }

    def get_global_state(self) -> WorkflowState:
        """Get state of primary resource (v1 compatibility)"""
        if self.default_resource and self.default_resource in self.resource_locks:
            return self.resource_locks[self.default_resource].state
        return WorkflowState.AVAILABLE

    def can_transition_to(self, target_state: WorkflowState, resource: str = None) -> bool:
        """Check if state transition is valid"""
        resource = resource or self.default_resource
        if not resource or resource not in self.resource_locks:
            return False

        current_state = self.resource_locks[resource].state

        valid_transitions = {
            WorkflowState.AVAILABLE: [WorkflowState.EDITING],
            WorkflowState.EDITING: [WorkflowState.BOTH_DONE, WorkflowState.CONFLICT_WAITING],
            WorkflowState.CONFLICT_WAITING: [WorkflowState.PENDING_REVIEW],
            WorkflowState.PENDING_REVIEW: [WorkflowState.BOTH_DONE],
            WorkflowState.BOTH_DONE: [WorkflowState.IN_PR, WorkflowState.EDITING, WorkflowState.HANDOFF_PENDING],
            WorkflowState.HANDOFF_PENDING: [WorkflowState.IN_PR, WorkflowState.EDITING],
            WorkflowState.IN_PR: [WorkflowState.APPROVED, WorkflowState.BOTH_DONE],
            WorkflowState.APPROVED: [WorkflowState.MERGED],
            WorkflowState.MERGED: [WorkflowState.ROLLED_BACK],
            WorkflowState.ROLLED_BACK: [WorkflowState.EDITING, WorkflowState.AVAILABLE],
        }

        return target_state in valid_transitions.get(current_state, [])

    def detect_and_recover_deadlocks(self) -> Dict[str, bool]:
        """
        Detect and recover from deadlocks due to timeout.
        Returns: dict of resources that had locks released
        """
        recovered = {}

        for resource, lock in self.resource_locks.items():
            if lock.is_timed_out():
                old_editor = lock.current_editor
                lock.release_lock(force=True)
                recovered[resource] = True
                print(f"⚠️  Deadlock recovery: Released lock on {resource} from {old_editor}")
            else:
                recovered[resource] = False

        return recovered

    def to_dict(self) -> Dict:
        """Serialize state machine (for persistence)"""
        return {
            "file_path": self.file_path,
            "function_name": self.function_name,
            "default_resource": self.default_resource,
            "all_developers": list(self.all_developers),
            "all_resources": list(self.all_resources),
            "resource_locks": {
                resource: lock.to_dict()
                for resource, lock in self.resource_locks.items()
            },
            "queues": self.queue_manager.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "WorkflowStateMachine":
        """Deserialize state machine (for persistence)"""
        machine = cls(data.get("file_path"), data.get("function_name"))
        machine.all_developers = set(data.get("all_developers", []))
        machine.all_resources = set(data.get("all_resources", []))
        # Note: Full reconstruction of locks and queues would require more work
        return machine

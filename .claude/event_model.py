#!/usr/bin/env python3
"""
Neo 2.0 Event Model

Defines all event types that represent development lifecycle transitions.
Events form the foundation of Development Memory and enable temporal coordination.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime


class EventType(Enum):
    """All event types in Neo 2.0 development lifecycle"""

    # Developer Registration
    DEVELOPER_REGISTERED = "developer_registered"

    # Intent Lifecycle
    INTENT_DECLARED = "intent_declared"
    INTENT_UPDATED = "intent_updated"
    INTENT_AUTHORIZED = "intent_authorized"
    INTENT_BLOCKED = "intent_blocked"
    INTENT_EXPIRED = "intent_expired"
    INTENT_CANCELLED = "intent_cancelled"

    # Resource Coordination
    RESOURCE_CLAIMED = "resource_claimed"
    RESOURCE_RELEASED = "resource_released"
    RESOURCE_CONFLICT_DETECTED = "resource_conflict_detected"

    # Work Lifecycle
    WORK_STARTED = "work_started"
    WORK_PAUSED = "work_paused"
    WORK_RESUMED = "work_resumed"
    WORK_COMPLETED = "work_completed"

    # Context Management
    CONTEXT_SNAPSHOT_CREATED = "context_snapshot_created"
    CONTEXT_INVALIDATED = "context_invalidated"
    CONTEXT_SYNC_REQUIRED = "context_sync_required"
    CONTEXT_REVALIDATING = "context_revalidating"
    CONTEXT_REVALIDATED = "context_revalidated"

    # Handoff Coordination
    HANDOFF_CREATED = "handoff_created"
    HANDOFF_ACKNOWLEDGED = "handoff_acknowledged"
    HANDOFF_CONSUMED = "handoff_consumed"

    # Review & Integration
    REVIEW_REQUESTED = "review_requested"
    REVIEW_STARTED = "review_started"
    REVIEW_COMPLETED = "review_completed"

    # Git Integration
    BRANCH_CREATED = "branch_created"
    COMMIT_CREATED = "commit_created"
    PR_CREATED = "pr_created"
    PR_MERGED = "pr_merged"

    # System Events
    STATE_TRANSITION = "state_transition"
    ERROR_OCCURRED = "error_occurred"
    NOTIFICATION_SENT = "notification_sent"


class Event:
    """
    Single development event.

    Every significant action in Neo is captured as an Event to enable:
    - Development Memory queries
    - Temporal coordination
    - Audit trails
    - Provenance tracking
    """

    def __init__(
        self,
        event_type: EventType,
        actor: str,
        actor_type: str,  # "human" or "agent"
        resource: Optional[str] = None,  # file:function or branch or task
        task_id: Optional[str] = None,  # Jira ID, GitHub issue, etc.
        details: Optional[Dict[str, Any]] = None,
        severity: str = "info",  # info, warning, error
        correlation_id: Optional[str] = None,  # Links related events
    ):
        self.event_id = self._generate_id()
        self.event_type = event_type
        self.timestamp = datetime.now().isoformat()
        self.actor = actor
        self.actor_type = actor_type
        self.resource = resource
        self.task_id = task_id
        self.details = details or {}
        self.severity = severity
        self.correlation_id = correlation_id or self.event_id

    def _generate_id(self) -> str:
        """Generate unique event ID"""
        import uuid
        return f"evt_{uuid.uuid4().hex[:12]}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize event"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "resource": self.resource,
            "task_id": self.task_id,
            "details": self.details,
            "severity": self.severity,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Deserialize event"""
        event = cls(
            event_type=EventType(data["event_type"]),
            actor=data["actor"],
            actor_type=data["actor_type"],
            resource=data.get("resource"),
            task_id=data.get("task_id"),
            details=data.get("details", {}),
            severity=data.get("severity", "info"),
            correlation_id=data.get("correlation_id"),
        )
        event.event_id = data["event_id"]
        event.timestamp = data["timestamp"]
        return event


class EventFactory:
    """Factory for creating typed events"""

    @staticmethod
    def intent_declared(
        actor: str,
        actor_type: str,
        resource: str,
        task_id: Optional[str] = None,
        details: Optional[Dict] = None,
    ) -> Event:
        return Event(
            event_type=EventType.INTENT_DECLARED,
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            task_id=task_id,
            details=details or {},
        )

    @staticmethod
    def resource_claimed(
        actor: str,
        actor_type: str,
        resource: str,
        task_id: Optional[str] = None,
    ) -> Event:
        return Event(
            event_type=EventType.RESOURCE_CLAIMED,
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            task_id=task_id,
        )

    @staticmethod
    def work_completed(
        actor: str,
        actor_type: str,
        resource: str,
        summary: str,
        task_id: Optional[str] = None,
    ) -> Event:
        return Event(
            event_type=EventType.WORK_COMPLETED,
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            task_id=task_id,
            details={"summary": summary},
        )

    @staticmethod
    def context_invalidated(
        actor: str,
        actor_type: str,
        resource: str,
        changed_by: str,
        affected_symbol: str,
        reason: str,
    ) -> Event:
        return Event(
            event_type=EventType.CONTEXT_INVALIDATED,
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            details={
                "changed_by": changed_by,
                "affected_symbol": affected_symbol,
                "reason": reason,
            },
        )

    @staticmethod
    def state_transition(
        actor: str,
        actor_type: str,
        resource: str,
        from_state: str,
        to_state: str,
        reason: str,
    ) -> Event:
        return Event(
            event_type=EventType.STATE_TRANSITION,
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            details={
                "from_state": from_state,
                "to_state": to_state,
                "reason": reason,
            },
        )

#!/usr/bin/env python3
"""
Neo 2.0 Phase 2: Temporal Handoff Engine

Manages completed work handoffs and discovers temporal dependencies.
Enables developers to understand prior work even when no MR/PR exists.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
try:
    from .event_model import Event, EventType, EventFactory
    from .development_memory import DevelopmentMemory
except ImportError:
    from event_model import Event, EventType, EventFactory
    from development_memory import DevelopmentMemory


class HandoffRecord:
    """
    Represents completed work that may affect future developers.

    Independent of Git PR/MR creation—captures what was done,
    why, and what future developers should know.
    """

    def __init__(
        self,
        handoff_id: str,
        actor: str,
        actor_type: str,
        resource: str,
        task_id: Optional[str] = None,
        summary: Optional[str] = None,
        base_commit: Optional[str] = None,
        final_commit: Optional[str] = None,
        branch: Optional[str] = None,
    ):
        self.handoff_id = handoff_id
        self.actor = actor
        self.actor_type = actor_type
        self.resource = resource  # file:function
        self.task_id = task_id
        self.summary = summary
        self.base_commit = base_commit
        self.final_commit = final_commit
        self.branch = branch
        self.created_at = datetime.now().isoformat()
        self.acknowledged_by: List[str] = []
        self.consumed_by: Optional[str] = None
        self.consumed_at: Optional[str] = None
        self.status = "PENDING"  # PENDING, ACKNOWLEDGED, CONSUMED, EXPIRED
        self.expiration_hours = 24
        self.expires_at = (datetime.now() + timedelta(hours=self.expiration_hours)).isoformat()
        self.known_risks: List[str] = []
        self.follow_up_required = False
        self.follow_up_description: Optional[str] = None

    def to_dict(self) -> Dict:
        """Serialize handoff record"""
        return {
            "handoff_id": self.handoff_id,
            "actor": self.actor,
            "actor_type": self.actor_type,
            "resource": self.resource,
            "task_id": self.task_id,
            "summary": self.summary,
            "base_commit": self.base_commit,
            "final_commit": self.final_commit,
            "branch": self.branch,
            "created_at": self.created_at,
            "status": self.status,
            "acknowledged_by": self.acknowledged_by,
            "consumed_by": self.consumed_by,
            "consumed_at": self.consumed_at,
            "expires_at": self.expires_at,
            "known_risks": self.known_risks,
            "follow_up_required": self.follow_up_required,
            "follow_up_description": self.follow_up_description,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "HandoffRecord":
        """Deserialize handoff record"""
        record = cls(
            handoff_id=data["handoff_id"],
            actor=data["actor"],
            actor_type=data["actor_type"],
            resource=data["resource"],
            task_id=data.get("task_id"),
            summary=data.get("summary"),
            base_commit=data.get("base_commit"),
            final_commit=data.get("final_commit"),
            branch=data.get("branch"),
        )
        record.created_at = data.get("created_at", record.created_at)
        record.status = data.get("status", "PENDING")
        record.acknowledged_by = data.get("acknowledged_by", [])
        record.consumed_by = data.get("consumed_by")
        record.consumed_at = data.get("consumed_at")
        record.expires_at = data.get("expires_at", record.expires_at)
        record.known_risks = data.get("known_risks", [])
        record.follow_up_required = data.get("follow_up_required", False)
        record.follow_up_description = data.get("follow_up_description")
        return record


class TemporalHandoffEngine:
    """
    Manages handoff coordination and Next Intent Interception.

    Key responsibilities:
    1. Record completed work as handoff records
    2. Maintain pending handoff queue
    3. Intercept new intents that overlap prior work
    4. Provide handoff context to waiting developers
    5. Track handoff consumption
    """

    def __init__(self, development_memory: DevelopmentMemory):
        self.development_memory = development_memory
        self.handoff_queue: Dict[str, List[HandoffRecord]] = {}  # resource -> [handoffs]
        self.pending_handoffs: List[HandoffRecord] = []  # All unresolved handoffs
        self.expired_handoffs: List[HandoffRecord] = []  # Expired but tracked
        self.all_handoffs: Dict[str, HandoffRecord] = {}  # Comprehensive registry by ID

    def create_handoff(
        self,
        actor: str,
        actor_type: str,
        resource: str,
        task_id: Optional[str] = None,
        summary: Optional[str] = None,
        base_commit: Optional[str] = None,
        final_commit: Optional[str] = None,
        branch: Optional[str] = None,
        known_risks: Optional[List[str]] = None,
        follow_up_required: bool = False,
        follow_up_description: Optional[str] = None,
    ) -> HandoffRecord:
        """
        Create a handoff record when work is completed.

        This is called when finish_editing occurs and summary is provided.
        """
        import uuid
        handoff_id = f"handoff_{uuid.uuid4().hex[:12]}"

        record = HandoffRecord(
            handoff_id=handoff_id,
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            task_id=task_id,
            summary=summary,
            base_commit=base_commit,
            final_commit=final_commit,
            branch=branch,
        )

        if known_risks:
            record.known_risks = known_risks
        if follow_up_required:
            record.follow_up_required = follow_up_required
            record.follow_up_description = follow_up_description

        # Add to pending queue
        self.pending_handoffs.append(record)

        # Add to comprehensive registry
        self.all_handoffs[handoff_id] = record

        # Index by resource
        if resource not in self.handoff_queue:
            self.handoff_queue[resource] = []
        self.handoff_queue[resource].append(record)

        # Record event
        event = EventFactory.work_completed(
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            summary=summary or "Work completed",
            task_id=task_id
        )
        self.development_memory.record_event(event)

        # Create handoff event
        handoff_event = Event(
            event_type=EventType.HANDOFF_CREATED,
            actor=actor,
            actor_type=actor_type,
            resource=resource,
            task_id=task_id,
            details={
                "handoff_id": handoff_id,
                "summary": summary,
                "branch": branch,
                "known_risks": known_risks or [],
                "follow_up_required": follow_up_required,
            }
        )
        self.development_memory.record_event(handoff_event)

        return record

    def find_overlapping_handoffs(
        self, resource: str, hours_ago: int = 24
    ) -> List[HandoffRecord]:
        """
        Find handoffs that overlap with a resource (within time window).

        Used by Next Intent Interceptor to discover prior work.
        """
        if resource not in self.handoff_queue:
            return []

        cutoff = datetime.now() - timedelta(hours=hours_ago)
        cutoff_iso = cutoff.isoformat()

        overlapping = []
        for handoff in self.handoff_queue[resource]:
            # Check if handoff was created within time window
            if handoff.created_at > cutoff_iso:
                # Not yet expired
                if handoff.status != "EXPIRED":
                    overlapping.append(handoff)

        return overlapping

    def intercept_new_intent(
        self, new_actor: str, resource: str
    ) -> Tuple[bool, Optional[HandoffRecord], List[str]]:
        """
        Next Intent Interceptor: Detect when new developer's intent
        overlaps with recent handoff.

        Returns:
            (has_prior_work, primary_handoff, recommendations)
        """
        overlapping = self.find_overlapping_handoffs(resource, hours_ago=24)

        if not overlapping:
            return False, None, []

        # Get most recent handoff
        primary_handoff = overlapping[-1]

        # Determine if different developer
        if primary_handoff.actor == new_actor:
            # Same developer continuing own work
            return False, None, []

        # Generate recommendations
        recommendations = []
        if primary_handoff.summary:
            recommendations.append(f"Review prior changes: {primary_handoff.summary}")
        if primary_handoff.known_risks:
            for risk in primary_handoff.known_risks:
                recommendations.append(f"Known risk: {risk}")
        if primary_handoff.follow_up_required:
            recommendations.append(f"Follow-up needed: {primary_handoff.follow_up_description}")

        return True, primary_handoff, recommendations

    def acknowledge_handoff(
        self, acknowledging_actor: str, handoff_id: str
    ) -> Tuple[bool, str]:
        """
        Record that an actor acknowledged a pending handoff.
        """
        # Find handoff
        handoff = self._find_handoff_by_id(handoff_id)
        if not handoff:
            return False, "Handoff not found"

        if acknowledging_actor not in handoff.acknowledged_by:
            handoff.acknowledged_by.append(acknowledging_actor)
            handoff.status = "ACKNOWLEDGED"

            # Record event
            event = Event(
                event_type=EventType.HANDOFF_ACKNOWLEDGED,
                actor=acknowledging_actor,
                actor_type="human",  # Typically humans acknowledge
                resource=handoff.resource,
                task_id=handoff.task_id,
                details={"handoff_id": handoff_id, "original_actor": handoff.actor}
            )
            self.development_memory.record_event(event)

        return True, "Handoff acknowledged"

    def consume_handoff(
        self, consuming_actor: str, handoff_id: str
    ) -> Tuple[bool, str]:
        """
        Record that a developer/agent consumed a handoff and proceeded.
        """
        handoff = self._find_handoff_by_id(handoff_id)
        if not handoff:
            return False, "Handoff not found"

        if handoff.status == "EXPIRED":
            return False, "Handoff has expired"

        handoff.consumed_by = consuming_actor
        handoff.consumed_at = datetime.now().isoformat()
        handoff.status = "CONSUMED"

        # Remove from pending
        if handoff in self.pending_handoffs:
            self.pending_handoffs.remove(handoff)

        # Record event
        event = Event(
            event_type=EventType.HANDOFF_CONSUMED,
            actor=consuming_actor,
            actor_type="human",
            resource=handoff.resource,
            task_id=handoff.task_id,
            details={
                "handoff_id": handoff_id,
                "original_actor": handoff.actor,
                "time_to_consume": self._time_diff(handoff.created_at, handoff.consumed_at)
            }
        )
        self.development_memory.record_event(event)

        return True, "Handoff consumed"

    def get_pending_handoffs(self) -> List[Dict]:
        """Get all active pending handoffs."""
        # Clean expired
        self._cleanup_expired()

        return [h.to_dict() for h in self.pending_handoffs if h.status != "EXPIRED"]

    def get_handoff_for_resource(self, resource: str) -> Optional[Dict]:
        """Get most recent pending handoff for a resource."""
        if resource not in self.handoff_queue:
            return None

        handoffs = [h for h in self.handoff_queue[resource] if h.status != "CONSUMED"]
        if not handoffs:
            return None

        # Return most recent
        return handoffs[-1].to_dict()

    def get_handoff_summary_for_developer(
        self, new_actor: str, resource: str
    ) -> Optional[Dict]:
        """
        Get human-friendly handoff summary for a developer starting work.

        Used by UI/notifications to present context.
        """
        has_prior, primary_handoff, recommendations = self.intercept_new_intent(
            new_actor, resource
        )

        if not has_prior or not primary_handoff:
            return None

        return {
            "has_prior_work": True,
            "prior_actor": primary_handoff.actor,
            "prior_actor_type": primary_handoff.actor_type,
            "prior_summary": primary_handoff.summary,
            "prior_task": primary_handoff.task_id,
            "prior_branch": primary_handoff.branch,
            "prior_commit": primary_handoff.final_commit,
            "known_risks": primary_handoff.known_risks,
            "follow_up_required": primary_handoff.follow_up_required,
            "follow_up_description": primary_handoff.follow_up_description,
            "recommendations": recommendations,
            "handoff_id": primary_handoff.handoff_id,
            "time_since_completion": self._time_diff(primary_handoff.created_at, None),
        }

    # Helper methods

    def _find_handoff_by_id(self, handoff_id: str) -> Optional[HandoffRecord]:
        """Find handoff by ID from comprehensive registry."""
        return self.all_handoffs.get(handoff_id)

    def _cleanup_expired(self):
        """Move expired handoffs to expired list."""
        now = datetime.now()
        expired = []

        for handoff in list(self.pending_handoffs):
            if datetime.fromisoformat(handoff.expires_at) < now:
                handoff.status = "EXPIRED"
                self.expired_handoffs.append(handoff)
                self.pending_handoffs.remove(handoff)
                expired.append(handoff.handoff_id)

        # Record expiration events
        for handoff_id in expired:
            handoff = next((h for h in self.expired_handoffs if h.handoff_id == handoff_id), None)
            if handoff:
                event = Event(
                    event_type=EventType.INTENT_EXPIRED,
                    actor=handoff.actor,
                    actor_type=handoff.actor_type,
                    resource=handoff.resource,
                    details={"handoff_id": handoff_id}
                )
                self.development_memory.record_event(event)

    def _time_diff(self, start_iso: str, end_iso: Optional[str]) -> str:
        """Calculate readable time difference."""
        start = datetime.fromisoformat(start_iso)
        end = datetime.fromisoformat(end_iso) if end_iso else datetime.now()

        diff = end - start
        minutes = int(diff.total_seconds() / 60)

        if minutes < 60:
            return f"{minutes}m"
        elif minutes < 1440:
            hours = minutes / 60
            return f"{hours:.1f}h"
        else:
            days = minutes / 1440
            return f"{days:.1f}d"

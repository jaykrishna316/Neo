#!/usr/bin/env python3
"""
Neo 2.0 Development Memory

Persistent store and query interface for development events.
Transforms the activity log into queryable development history.
"""

from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime, timedelta
try:
    from .event_model import Event, EventType
except ImportError:
    from event_model import Event, EventType


class DevelopmentMemory:
    """
    In-memory event store with query interface.

    Phase 1: In-memory storage (suitable for demo/testing)
    Phase 2+: Extend with SQLite persistence
    """

    def __init__(self):
        self.events: List[Event] = []
        self.actor_index: Dict[str, List[Event]] = {}  # actor -> events
        self.resource_index: Dict[str, List[Event]] = {}  # resource -> events
        self.task_index: Dict[str, List[Event]] = {}  # task_id -> events
        self.correlation_index: Dict[str, List[Event]] = {}  # correlation_id -> events

    def record_event(self, event: Event) -> None:
        """Record an event to memory"""
        self.events.append(event)

        # Update indices for fast queries
        if event.actor:
            if event.actor not in self.actor_index:
                self.actor_index[event.actor] = []
            self.actor_index[event.actor].append(event)

        if event.resource:
            if event.resource not in self.resource_index:
                self.resource_index[event.resource] = []
            self.resource_index[event.resource].append(event)

        if event.task_id:
            if event.task_id not in self.task_index:
                self.task_index[event.task_id] = []
            self.task_index[event.task_id].append(event)

        if event.correlation_id:
            if event.correlation_id not in self.correlation_index:
                self.correlation_index[event.correlation_id] = []
            self.correlation_index[event.correlation_id].append(event)

    # Query Interfaces

    def get_actor_activity(self, actor: str, limit: int = 100) -> List[Dict]:
        """Get all activity for an actor"""
        events = self.actor_index.get(actor, [])
        return [e.to_dict() for e in events[-limit:]]

    def get_resource_history(self, resource: str, limit: int = 100) -> List[Dict]:
        """Get all activity for a resource (file:function, branch, etc)"""
        events = self.resource_index.get(resource, [])
        return [e.to_dict() for e in events[-limit:]]

    def get_task_activity(self, task_id: str, limit: int = 100) -> List[Dict]:
        """Get all activity for a Jira task or GitHub issue"""
        events = self.task_index.get(task_id, [])
        return [e.to_dict() for e in events[-limit:]]

    def get_events_by_type(self, event_type: EventType, limit: int = 100) -> List[Dict]:
        """Get all events of a specific type"""
        matching = [e for e in self.events if e.event_type == event_type]
        return [e.to_dict() for e in matching[-limit:]]

    def get_events_by_actor_and_type(
        self, actor: str, event_type: EventType, limit: int = 100
    ) -> List[Dict]:
        """Get events for an actor of a specific type"""
        events = self.actor_index.get(actor, [])
        matching = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in matching[-limit:]]

    def get_events_since(self, hours_ago: int, limit: int = 100) -> List[Dict]:
        """Get all events since N hours ago"""
        cutoff = datetime.now() - timedelta(hours=hours_ago)
        matching = [
            e for e in self.events
            if datetime.fromisoformat(e.timestamp) > cutoff
        ]
        return [e.to_dict() for e in matching[-limit:]]

    def get_recent_activity_for_resource(
        self, resource: str, hours_ago: int = 24
    ) -> List[Dict]:
        """Get recent activity for a resource"""
        events = self.resource_index.get(resource, [])
        cutoff = datetime.now() - timedelta(hours=hours_ago)
        recent = [
            e for e in events
            if datetime.fromisoformat(e.timestamp) > cutoff
        ]
        return [e.to_dict() for e in recent]

    def get_development_history(self, resource: str) -> Dict:
        """
        Get complete development history for a resource.

        Returns timeline of who worked on it, what they did, and current state.
        """
        events = self.resource_index.get(resource, [])
        if not events:
            return {"resource": resource, "history": []}

        actors_involved = set()
        timeline = []

        for event in events:
            actors_involved.add(event.actor)
            timeline.append({
                "timestamp": event.timestamp,
                "actor": event.actor,
                "actor_type": event.actor_type,
                "event_type": event.event_type.value,
                "details": event.details,
            })

        return {
            "resource": resource,
            "actors_involved": list(actors_involved),
            "total_events": len(events),
            "timeline": timeline,
        }

    def get_developer_participation(self, resource: str) -> Dict[str, int]:
        """Get count of events per developer for a resource"""
        events = self.resource_index.get(resource, [])
        participation = {}
        for event in events:
            if event.actor not in participation:
                participation[event.actor] = 0
            participation[event.actor] += 1
        return participation

    def find_recent_work_on_symbol(
        self, symbol: str, hours_ago: int = 24
    ) -> List[Dict]:
        """
        Find recent work on a symbol (for temporal handoff).

        Searches resource history for matching symbol patterns.
        """
        cutoff = datetime.now() - timedelta(hours=hours_ago)
        results = []

        for resource, events in self.resource_index.items():
            # Simple pattern matching: look for symbol in resource path
            if symbol in resource:
                recent_events = [
                    e for e in events
                    if datetime.fromisoformat(e.timestamp) > cutoff
                ]
                if recent_events:
                    results.append({
                        "resource": resource,
                        "events": [e.to_dict() for e in recent_events],
                    })

        return results

    def get_correlation_chain(self, correlation_id: str) -> List[Dict]:
        """Get all events in a correlation chain (related work session)"""
        events = self.correlation_index.get(correlation_id, [])
        return [e.to_dict() for e in events]

    def get_all_events(self, limit: int = 1000) -> List[Dict]:
        """Get all events (for debugging/audit)"""
        return [e.to_dict() for e in self.events[-limit:]]

    def get_statistics(self) -> Dict:
        """Get development memory statistics"""
        actor_event_count = {}
        resource_event_count = {}
        event_type_count = {}

        for event in self.events:
            # Count by actor
            if event.actor:
                actor_event_count[event.actor] = actor_event_count.get(event.actor, 0) + 1

            # Count by resource
            if event.resource:
                resource_event_count[event.resource] = resource_event_count.get(event.resource, 0) + 1

            # Count by event type
            et = event.event_type.value
            event_type_count[et] = event_type_count.get(et, 0) + 1

        return {
            "total_events": len(self.events),
            "unique_actors": len(self.actor_index),
            "unique_resources": len(self.resource_index),
            "unique_tasks": len(self.task_index),
            "event_type_distribution": event_type_count,
            "top_actors": sorted(
                actor_event_count.items(), key=lambda x: x[1], reverse=True
            )[:5],
            "top_resources": sorted(
                resource_event_count.items(), key=lambda x: x[1], reverse=True
            )[:5],
        }

    def clear(self) -> None:
        """Clear all events (for testing)"""
        self.events.clear()
        self.actor_index.clear()
        self.resource_index.clear()
        self.task_index.clear()
        self.correlation_index.clear()

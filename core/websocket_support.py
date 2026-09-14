"""WebSocket support for real-time conflict detection updates.

Enables agents to receive instant notifications instead of polling.
"""

from typing import Dict, List, Callable, Any, Optional
from dataclasses import dataclass
from enum import Enum
import json
import time


class EventType(Enum):
    """Types of real-time events."""
    ACTIVITY_LOGGED = "activity_logged"
    CONFLICT_DETECTED = "conflict_detected"
    CONFLICT_RESOLVED = "conflict_resolved"
    DEVELOPER_ONLINE = "developer_online"
    DEVELOPER_OFFLINE = "developer_offline"
    RISK_CHANGED = "risk_changed"
    AGENT_CHECK = "agent_check"
    COORDINATION_NEEDED = "coordination_needed"


@dataclass
class WebSocketEvent:
    """Real-time event for WebSocket delivery."""
    event_type: EventType
    timestamp: float
    data: Dict[str, Any]
    priority: str  # low/medium/high/critical
    requires_action: bool


class EventBroker:
    """In-memory event broker for real-time updates."""

    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = {}  # event_type -> callbacks
        self.event_history: List[WebSocketEvent] = []
        self.max_history = 1000

    def subscribe(self, event_type: str, callback: Callable) -> str:
        """
        Subscribe to events.

        Args:
            event_type: EventType or wildcard "*"
            callback: Function to call with (event: WebSocketEvent)

        Returns:
            Subscription ID
        """
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(callback)
        sub_id = f"{event_type}:{len(self.subscribers[event_type])}"
        return sub_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """Unsubscribe from events."""
        event_type = subscription_id.split(":")[0]
        if event_type in self.subscribers:
            self.subscribers[event_type] = [
                cb for cb in self.subscribers[event_type]
                if f"{event_type}:{id(cb)}" != subscription_id
            ]
            return True
        return False

    def publish(self, event: WebSocketEvent) -> None:
        """
        Publish an event to all subscribers.

        Args:
            event: WebSocketEvent to publish
        """
        # Store in history
        self.event_history.append(event)
        if len(self.event_history) > self.max_history:
            self.event_history.pop(0)

        # Notify subscribers
        event_type = event.event_type.value

        # Send to specific subscribers
        if event_type in self.subscribers:
            for callback in self.subscribers[event_type]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error calling callback: {e}")

        # Send to wildcard subscribers
        if "*" in self.subscribers:
            for callback in self.subscribers["*"]:
                try:
                    callback(event)
                except Exception as e:
                    print(f"Error calling wildcard callback: {e}")

    def get_recent_events(self, count: int = 10) -> List[WebSocketEvent]:
        """Get recent events."""
        return self.event_history[-count:]

    def get_events_by_type(self, event_type: str, count: int = 10) -> List[WebSocketEvent]:
        """Get recent events of a specific type."""
        matching = [
            e for e in self.event_history
            if e.event_type.value == event_type
        ]
        return matching[-count:]


# Global event broker instance
_event_broker = EventBroker()


def publish_activity_logged(developer_id: str, file_path: str, intent: str, region: str) -> None:
    """Publish when activity is logged."""
    event = WebSocketEvent(
        event_type=EventType.ACTIVITY_LOGGED,
        timestamp=time.time(),
        data={
            "developer_id": developer_id,
            "file_path": file_path,
            "intent": intent,
            "region": region,
        },
        priority="low",
        requires_action=False
    )
    _event_broker.publish(event)


def publish_conflict_detected(
    agent_id: str,
    file_path: str,
    risk_level: str,
    conflicting_developers: List[str],
) -> None:
    """Publish when conflict is detected."""
    event = WebSocketEvent(
        event_type=EventType.CONFLICT_DETECTED,
        timestamp=time.time(),
        data={
            "agent_id": agent_id,
            "file_path": file_path,
            "risk_level": risk_level,
            "conflicting_developers": conflicting_developers,
            "count": len(conflicting_developers),
        },
        priority="high" if risk_level == "HIGH" else "medium",
        requires_action=risk_level in ("HIGH", "MEDIUM")
    )
    _event_broker.publish(event)


def publish_conflict_resolved(file_path: str, reason: str) -> None:
    """Publish when conflict is resolved."""
    event = WebSocketEvent(
        event_type=EventType.CONFLICT_RESOLVED,
        timestamp=time.time(),
        data={
            "file_path": file_path,
            "reason": reason,
        },
        priority="medium",
        requires_action=True
    )
    _event_broker.publish(event)


def publish_coordination_needed(
    file_path: str,
    num_developers: int,
    suggested_order: List[str],
) -> None:
    """Publish when coordination is needed."""
    event = WebSocketEvent(
        event_type=EventType.COORDINATION_NEEDED,
        timestamp=time.time(),
        data={
            "file_path": file_path,
            "num_developers": num_developers,
            "suggested_order": suggested_order,
        },
        priority="high",
        requires_action=True
    )
    _event_broker.publish(event)


def publish_risk_changed(
    file_path: str,
    old_risk: str,
    new_risk: str,
    reason: str,
) -> None:
    """Publish when risk level changes."""
    event = WebSocketEvent(
        event_type=EventType.RISK_CHANGED,
        timestamp=time.time(),
        data={
            "file_path": file_path,
            "old_risk": old_risk,
            "new_risk": new_risk,
            "reason": reason,
        },
        priority="medium" if new_risk == "HIGH" else "low",
        requires_action=new_risk == "HIGH"
    )
    _event_broker.publish(event)


def subscribe_to_events(event_type: str, callback: Callable) -> str:
    """Subscribe to WebSocket events."""
    return _event_broker.subscribe(event_type, callback)


def unsubscribe_from_events(subscription_id: str) -> bool:
    """Unsubscribe from WebSocket events."""
    return _event_broker.unsubscribe(subscription_id)


def get_recent_events(count: int = 10) -> List[WebSocketEvent]:
    """Get recent events."""
    return _event_broker.get_recent_events(count)


def get_event_broker() -> EventBroker:
    """Get the global event broker."""
    return _event_broker


def event_to_json(event: WebSocketEvent) -> str:
    """Convert event to JSON for transmission."""
    return json.dumps({
        "type": event.event_type.value,
        "timestamp": event.timestamp,
        "data": event.data,
        "priority": event.priority,
        "requires_action": event.requires_action,
    })


def format_event_for_agent(event: WebSocketEvent) -> str:
    """Format event as readable message for agent."""
    if event.event_type == EventType.CONFLICT_DETECTED:
        data = event.data
        return (
            f"⚠️  CONFLICT DETECTED in {data['file_path']}\n"
            f"   Risk Level: {data['risk_level']}\n"
            f"   Conflicting: {', '.join(data['conflicting_developers'])}\n"
            f"   Action: Check before generating"
        )

    elif event.event_type == EventType.CONFLICT_RESOLVED:
        return f"✓ Conflict resolved in {event.data['file_path']} ({event.data['reason']})"

    elif event.event_type == EventType.COORDINATION_NEEDED:
        data = event.data
        order = " → ".join(data['suggested_order'])
        return (
            f"🔗 COORDINATION NEEDED in {data['file_path']}\n"
            f"   Suggested order: {order}"
        )

    elif event.event_type == EventType.RISK_CHANGED:
        data = event.data
        return (
            f"📊 Risk level changed: {data['old_risk']} → {data['new_risk']}\n"
            f"   File: {data['file_path']}\n"
            f"   Reason: {data['reason']}"
        )

    elif event.event_type == EventType.ACTIVITY_LOGGED:
        data = event.data
        return (
            f"📝 Activity logged: {data['developer_id']}\n"
            f"   File: {data['file_path']}\n"
            f"   Intent: {data['intent']}"
        )

    else:
        return f"Event: {event.event_type.value}"


if __name__ == "__main__":
    print("WebSocket Support - Real-Time Events")
    print("=" * 60)

    # Example: Subscribe and publish
    events_received = []

    def event_handler(event: WebSocketEvent):
        events_received.append(event)
        print(f"\n📨 Received: {format_event_for_agent(event)}")

    print("\n1. Subscribe to conflict detection:")
    sub_id = subscribe_to_events(EventType.CONFLICT_DETECTED.value, event_handler)
    print(f"   Subscription ID: {sub_id}")

    print("\n2. Publish conflict detected:")
    publish_conflict_detected(
        agent_id="claude-1",
        file_path="src/auth.py",
        risk_level="HIGH",
        conflicting_developers=["alice", "bob"]
    )

    print("\n3. Publish conflict resolved:")
    publish_conflict_resolved("src/auth.py", "Alice finished changes")

    print("\n4. Publish coordination needed:")
    publish_coordination_needed(
        file_path="src/payment.py",
        num_developers=3,
        suggested_order=["alice", "bob", "charlie"]
    )

    print("\n5. Recent events:")
    recent = get_recent_events(5)
    print(f"   Total events: {len(recent)}")
    for event in recent:
        print(f"   • {event.event_type.value} (priority: {event.priority})")

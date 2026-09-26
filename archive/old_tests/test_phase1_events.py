#!/usr/bin/env python3
"""
Test Neo 2.0 Phase 1: Event Model & Development Memory
Verifies event emission and queries work correctly
"""

import sys
import time
from event_model import Event, EventType, EventFactory
from development_memory import DevelopmentMemory


def test_event_creation():
    """Test basic event creation"""
    print("\n✓ Test: Event Creation")

    event = EventFactory.intent_declared(
        actor="dev1",
        actor_type="human",
        resource="test.py::main",
        task_id="JIRA-123",
        details={"file": "test.py", "function": "main"}
    )

    assert event.event_type == EventType.INTENT_DECLARED
    assert event.actor == "dev1"
    assert event.resource == "test.py::main"
    assert event.task_id == "JIRA-123"
    print(f"  Event ID: {event.event_id}")
    print(f"  Event Type: {event.event_type.value}")


def test_development_memory():
    """Test development memory recording and queries"""
    print("\n✓ Test: Development Memory")

    memory = DevelopmentMemory()

    # Record events simulating a development session
    events = [
        EventFactory.intent_declared(
            actor="dev1",
            actor_type="human",
            resource="payment.py::process_payment",
            task_id="JIRA-1001"
        ),
        EventFactory.resource_claimed(
            actor="dev1",
            actor_type="human",
            resource="payment.py::process_payment"
        ),
        EventFactory.work_completed(
            actor="dev1",
            actor_type="human",
            resource="payment.py::process_payment",
            summary="Added retry logic",
            task_id="JIRA-1001"
        ),
    ]

    for event in events:
        memory.record_event(event)

    # Test queries
    print("  Query 1: Actor activity (dev1)")
    activity = memory.get_actor_activity("dev1")
    assert len(activity) == 3
    print(f"    Found {len(activity)} events for dev1")

    print("  Query 2: Resource history (payment.py::process_payment)")
    history = memory.get_resource_history("payment.py::process_payment")
    assert len(history) == 3
    print(f"    Found {len(history)} events for resource")

    print("  Query 3: Events by type (WORK_COMPLETED)")
    completed = memory.get_events_by_type(EventType.WORK_COMPLETED)
    assert len(completed) == 1
    print(f"    Found {len(completed)} completion events")

    print("  Query 4: Development history")
    dev_history = memory.get_development_history("payment.py::process_payment")
    assert dev_history["resource"] == "payment.py::process_payment"
    assert "dev1" in dev_history["actors_involved"]
    print(f"    Actors involved: {dev_history['actors_involved']}")

    print("  Query 5: Developer participation")
    participation = memory.get_developer_participation("payment.py::process_payment")
    assert participation["dev1"] == 3
    print(f"    Dev1 participation count: {participation['dev1']}")

    print("  Query 6: Memory statistics")
    stats = memory.get_statistics()
    assert stats["total_events"] == 3
    assert stats["unique_actors"] == 1
    print(f"    Total events: {stats['total_events']}")
    print(f"    Unique actors: {stats['unique_actors']}")


def test_multi_developer_scenario():
    """Test scenario with multiple developers"""
    print("\n✓ Test: Multi-Developer Scenario")

    memory = DevelopmentMemory()

    # Dev1 works on order service
    event1 = EventFactory.intent_declared("dev1", "human", "order.py::process", "JIRA-201")
    event2 = EventFactory.resource_claimed("dev1", "human", "order.py::process")
    memory.record_event(event1)
    memory.record_event(event2)

    # Dev2 works on payment service (independent)
    event3 = EventFactory.intent_declared("dev2", "human", "payment.py::charge", "JIRA-202")
    event4 = EventFactory.resource_claimed("dev2", "human", "payment.py::charge")
    memory.record_event(event3)
    memory.record_event(event4)

    # Both complete
    event5 = EventFactory.work_completed("dev1", "human", "order.py::process", "Refactored", "JIRA-201")
    event6 = EventFactory.work_completed("dev2", "human", "payment.py::charge", "Added validation", "JIRA-202")
    memory.record_event(event5)
    memory.record_event(event6)

    # Queries
    print("  Query: Dev1 activity")
    dev1_activity = memory.get_actor_activity("dev1")
    assert len(dev1_activity) == 3
    print(f"    Dev1 events: {len(dev1_activity)}")

    print("  Query: Dev2 activity")
    dev2_activity = memory.get_actor_activity("dev2")
    assert len(dev2_activity) == 3
    print(f"    Dev2 events: {len(dev2_activity)}")

    print("  Query: Statistics")
    stats = memory.get_statistics()
    assert stats["unique_actors"] == 2
    assert stats["unique_resources"] == 2
    print(f"    Unique actors: {stats['unique_actors']}")
    print(f"    Unique resources: {stats['unique_resources']}")


def test_event_serialization():
    """Test event serialization/deserialization"""
    print("\n✓ Test: Event Serialization")

    event_orig = EventFactory.work_completed(
        actor="agent-1",
        actor_type="agent",
        resource="service.py::query",
        summary="Optimized database query",
        task_id="JIRA-500"
    )

    # Serialize
    event_dict = event_orig.to_dict()
    print(f"  Serialized: {event_dict['event_type']}")

    # Deserialize
    event_restored = Event.from_dict(event_dict)
    assert event_restored.event_type == event_orig.event_type
    assert event_restored.actor == event_orig.actor
    assert event_restored.resource == event_orig.resource
    print(f"  Deserialized: {event_restored.event_type.value}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Neo 2.0 Phase 1 Tests: Event Model & Development Memory")
    print("=" * 60)

    try:
        test_event_creation()
        test_development_memory()
        test_multi_developer_scenario()
        test_event_serialization()

        print("\n" + "=" * 60)
        print("✓ All Phase 1 tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

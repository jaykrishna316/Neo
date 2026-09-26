#!/usr/bin/env python3
"""
Test Neo 2.0 Phase 2: Temporal Handoff Engine
Verifies handoff creation, discovery, and consumption
"""

import sys
from event_model import EventType
from development_memory import DevelopmentMemory
from temporal_handoff_engine import TemporalHandoffEngine


def test_handoff_creation():
    """Test creating a handoff record"""
    print("\n✓ Test: Handoff Creation")

    memory = DevelopmentMemory()
    engine = TemporalHandoffEngine(memory)

    handoff = engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="payment.py::process",
        task_id="JIRA-123",
        summary="Added retry logic",
        branch="feature/payment-retry",
        known_risks=["Changed timeout behavior"],
        follow_up_required=True,
        follow_up_description="Verify with QA"
    )

    assert handoff.actor == "dev1"
    assert handoff.resource == "payment.py::process"
    assert handoff.status == "PENDING"
    assert len(engine.pending_handoffs) == 1
    print(f"  Handoff ID: {handoff.handoff_id}")
    print(f"  Status: {handoff.status}")
    print(f"  Known risks: {handoff.known_risks}")


def test_next_intent_interceptor():
    """Test discovering prior work when new intent arrives"""
    print("\n✓ Test: Next Intent Interceptor")

    memory = DevelopmentMemory()
    engine = TemporalHandoffEngine(memory)

    # Dev1 completes work
    handoff1 = engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="order.py::process_order",
        summary="Refactored order processing",
    )

    # Dev2 arrives with new intent on same resource
    has_prior, primary_handoff, recommendations = engine.intercept_new_intent(
        "dev2", "order.py::process_order"
    )

    assert has_prior == True
    assert primary_handoff is not None
    assert primary_handoff.actor == "dev1"
    assert len(recommendations) > 0
    print(f"  Prior work detected by: {primary_handoff.actor}")
    print(f"  Recommendations: {recommendations}")


def test_handoff_acknowledgment():
    """Test acknowledging a handoff"""
    print("\n✓ Test: Handoff Acknowledgment")

    memory = DevelopmentMemory()
    engine = TemporalHandoffEngine(memory)

    handoff = engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="service.py::query",
        summary="Optimized database query"
    )

    handoff_id = handoff.handoff_id

    # Acknowledge
    success, message = engine.acknowledge_handoff("dev2", handoff_id)
    assert success == True

    # Verify
    handoff_updated = engine._find_handoff_by_id(handoff_id)
    assert "dev2" in handoff_updated.acknowledged_by
    assert handoff_updated.status == "ACKNOWLEDGED"
    print(f"  Handoff acknowledged by: dev2")
    print(f"  Status: {handoff_updated.status}")


def test_handoff_consumption():
    """Test consuming a handoff"""
    print("\n✓ Test: Handoff Consumption")

    memory = DevelopmentMemory()
    engine = TemporalHandoffEngine(memory)

    handoff = engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="auth.py::validate",
        summary="Added MFA support"
    )

    handoff_id = handoff.handoff_id
    assert len(engine.pending_handoffs) == 1

    # Consume
    success, message = engine.consume_handoff("dev2", handoff_id)
    assert success == True

    # Verify removed from pending
    assert len(engine.pending_handoffs) == 0

    handoff_updated = engine._find_handoff_by_id(handoff_id)
    assert handoff_updated.consumed_by == "dev2"
    assert handoff_updated.status == "CONSUMED"
    print(f"  Handoff consumed by: {handoff_updated.consumed_by}")
    print(f"  Time to consume: {handoff_updated.created_at} → {handoff_updated.consumed_at}")


def test_handoff_summary_for_developer():
    """Test getting human-friendly handoff summary"""
    print("\n✓ Test: Handoff Summary for Developer")

    memory = DevelopmentMemory()
    engine = TemporalHandoffEngine(memory)

    # Create handoff with all details
    engine.create_handoff(
        actor="agent1",
        actor_type="agent",
        resource="ml.py::train_model",
        summary="Trained model with new dataset (87% accuracy)",
        branch="feature/ml-v2",
        final_commit="abc123def456",
        known_risks=[
            "Model requires 16GB GPU memory",
            "Training takes ~4 hours"
        ],
        follow_up_required=True,
        follow_up_description="Run validation tests before deploy"
    )

    # New developer queries
    summary = engine.get_handoff_summary_for_developer("dev1", "ml.py::train_model")

    assert summary is not None
    assert summary["prior_actor"] == "agent1"
    assert summary["prior_actor_type"] == "agent"
    assert summary["has_prior_work"] == True
    assert len(summary["recommendations"]) > 0
    assert summary["follow_up_required"] == True

    print(f"  Prior work by: {summary['prior_actor']} ({summary['prior_actor_type']})")
    print(f"  Branch: {summary['prior_branch']}")
    print(f"  Summary: {summary['prior_summary']}")
    print(f"  Known risks: {summary['known_risks']}")
    print(f"  Follow-up: {summary['follow_up_description']}")


def test_multi_resource_handoffs():
    """Test multiple handoffs on different resources"""
    print("\n✓ Test: Multiple Resource Handoffs")

    memory = DevelopmentMemory()
    engine = TemporalHandoffEngine(memory)

    # Multiple developers working on different resources
    h1 = engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="payment.py::charge",
        summary="Added payment validation"
    )

    h2 = engine.create_handoff(
        actor="dev2",
        actor_type="human",
        resource="order.py::create",
        summary="Refactored order creation"
    )

    h3 = engine.create_handoff(
        actor="dev3",
        actor_type="agent",
        resource="notification.py::send",
        summary="Added retry logic to notifications"
    )

    assert len(engine.pending_handoffs) == 3

    # Query specific resource
    payment_handoffs = engine.find_overlapping_handoffs("payment.py::charge")
    assert len(payment_handoffs) == 1
    assert payment_handoffs[0].actor == "dev1"

    print(f"  Total handoffs: {len(engine.pending_handoffs)}")
    print(f"  Handoffs on payment.py::charge: {len(payment_handoffs)}")


def test_same_developer_continuation():
    """Test that same developer doesn't trigger interceptor"""
    print("\n✓ Test: Same Developer Continuation")

    memory = DevelopmentMemory()
    engine = TemporalHandoffEngine(memory)

    # Dev1 creates handoff
    engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="service.py::query",
        summary="First iteration"
    )

    # Dev1 returns to same resource
    has_prior, handoff, recommendations = engine.intercept_new_intent(
        "dev1", "service.py::query"
    )

    # Should not trigger because it's same developer
    assert has_prior == False
    print(f"  Same developer continuation: No prior work flag (expected)")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Neo 2.0 Phase 2 Tests: Temporal Handoff Engine")
    print("=" * 60)

    try:
        test_handoff_creation()
        test_next_intent_interceptor()
        test_handoff_acknowledgment()
        test_handoff_consumption()
        test_handoff_summary_for_developer()
        test_multi_resource_handoffs()
        test_same_developer_continuation()

        print("\n" + "=" * 60)
        print("✓ All Phase 2 tests passed!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

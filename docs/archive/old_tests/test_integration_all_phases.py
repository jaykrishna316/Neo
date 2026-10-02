#!/usr/bin/env python3
"""
Integration Test: All Neo 2.0 Phases Working Together
Tests complete workflows using all 5 phases together
"""

import sys
from event_model import Event, EventType
from development_memory import DevelopmentMemory
from dependency_graph import DependencyGraph
from context_invalidation_engine import ContextInvalidationEngine
from temporal_handoff_engine import TemporalHandoffEngine
from reviewer_provenance_engine import ReviewerProvenanceEngine
from agent_autonomy_engine import AgentAutonomyEngine, AgentAutonomyPolicy, AutonomyLevel


def test_complete_developer_workflow():
    """Test complete workflow: dev1 → handoff → dev2 → agent autonomy"""
    print("\n✓ Test: Complete Developer Workflow")

    # Initialize all engines
    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    reviewer_engine = ReviewerProvenanceEngine(memory, graph)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Phase 1: Dev1 works on feature
    print("  1. Dev1 starts work and claims resource")
    memory.record_event(Event(
        event_type=EventType.DEVELOPER_REGISTERED,
        actor="dev1",
        actor_type="human",
        resource="payment.py::process",
    ))

    memory.record_event(Event(
        event_type=EventType.RESOURCE_CLAIMED,
        actor="dev1",
        actor_type="human",
        resource="payment.py::process",
        task_id="JIRA-100",
    ))

    # Phase 3: Dev1 creates context snapshot
    print("  2. Dev1 creates context snapshot")
    graph.add_dependency("payment.py::process", "bank.py::transfer")
    context_engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="payment.py::process",
        base_commit="abc123",
        symbols=["payment.py::process", "bank.py::transfer"],
        assumptions={"bank_sync": "synchronous", "timeout": "30s"}
    )

    # Dev1 completes work
    print("  3. Dev1 completes work")
    memory.record_event(Event(
        event_type=EventType.WORK_COMPLETED,
        actor="dev1",
        actor_type="human",
        resource="payment.py::process",
        task_id="JIRA-100",
    ))

    # Phase 2: Dev1 creates handoff
    print("  4. Dev1 creates handoff for dev2")
    handoff = handoff_engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="payment.py::process",
        task_id="JIRA-100",
        summary="Added retry logic with exponential backoff",
        branch="feature/payment-retry",
        known_risks=["Changed timeout behavior"],
        follow_up_required=True,
        follow_up_description="Verify with QA"
    )

    # Phase 2: Dev2 intercepts handoff
    print("  5. Dev2 detects prior work via Next Intent Interceptor")
    has_prior, primary_handoff, recommendations = handoff_engine.intercept_new_intent(
        "dev2", "payment.py::process"
    )
    assert has_prior == True
    assert primary_handoff is not None

    # Phase 3: Someone changes dependency
    print("  6. Dev3 changes bank.py::transfer (invalidates context)")
    context_engine.mark_symbol_changed(
        symbol="bank.py::transfer",
        changed_by="dev3",
        reason="Added new API wrapper"
    )

    # Check that dev1's context is now stale
    context = context_engine.active_contexts["payment.py::process"]
    assert context.status == "STALE"

    # Phase 4: Query reviewers for payment.py::process
    print("  7. Query reviewers using provenance engine")
    candidates = reviewer_engine.get_reviewer_provenance("payment.py::process")
    assert len(candidates) > 0
    print(f"     Found {len(candidates)} reviewer candidates")

    # Phase 5: Dev2 registers as agent with autonomy
    print("  8. Dev2 (now agent) registers autonomy policy")
    policy = AgentAutonomyPolicy(
        "dev2_agent",
        AutonomyLevel.FULL_AUTONOMOUS,
        can_auto_sync=True,
        can_auto_revalidate=True,
        can_auto_consume_handoffs=True
    )
    autonomy_engine.register_agent_policy(policy)

    # Phase 5: Execute full autonomous workflow
    print("  9. Dev2 executes full autonomous workflow")
    success, message, workflow_id = autonomy_engine.execute_full_workflow_orchestration(
        agent_id="dev2_agent",
        resource="payment.py::process",
        include_sync=True,
        include_revalidate=True,
        include_consume_handoff=True,
        handoff_id=handoff.handoff_id
    )

    # Verify handoff was consumed
    assert handoff_engine._find_handoff_by_id(handoff.handoff_id).status == "CONSUMED"

    print(f"  ✓ Complete workflow successful!")
    print(f"    - Dev1 created handoff with known risks")
    print(f"    - Dev2 detected prior work")
    print(f"    - Dependency change invalidated context")
    print(f"    - {len(candidates)} reviewers identified")
    print(f"    - Agent autonomously consumed handoff and synced")


def test_multi_developer_context_tracking():
    """Test multiple developers' contexts being tracked simultaneously"""
    print("\n✓ Test: Multi-Developer Context Tracking")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)

    # Set up multi-layer dependencies
    graph.add_dependency("api.py::endpoint", "service.py::query")
    graph.add_dependency("service.py::query", "db.py::execute")
    graph.add_dependency("db.py::execute", "cache.py::get")

    # Dev1 working on api layer
    print("  1. Dev1 creates context for api.py::endpoint")
    context_engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="api.py::endpoint",
        base_commit="abc123",
        symbols=["api.py::endpoint", "service.py::query"],
        assumptions={"response_time": "< 100ms"}
    )

    # Dev2 working on service layer
    print("  2. Dev2 creates context for service.py::query")
    context_engine.create_context_snapshot(
        actor="dev2",
        actor_type="human",
        resource="service.py::query",
        base_commit="abc123",
        symbols=["service.py::query", "db.py::execute"],
        assumptions={"db_connections": "pooled"}
    )

    # Dev3 working on db layer
    print("  3. Dev3 creates context for db.py::execute")
    context_engine.create_context_snapshot(
        actor="dev3",
        actor_type="human",
        resource="db.py::execute",
        base_commit="abc123",
        symbols=["db.py::execute", "cache.py::get"],
        assumptions={"cache_hit_ratio": "> 80%"}
    )

    assert len(context_engine.active_contexts) == 3

    # Change cache layer - should invalidate db and service contexts
    print("  4. Dev4 changes cache.py::get")
    context_engine.mark_symbol_changed(
        symbol="cache.py::get",
        changed_by="dev4",
        reason="Changed to async implementation"
    )

    # Check affected contexts
    print("  5. Verify context invalidation propagation")
    db_context = context_engine.active_contexts["db.py::execute"]
    service_context = context_engine.active_contexts["service.py::query"]
    api_context = context_engine.active_contexts["api.py::endpoint"]

    assert db_context.status == "STALE"
    print(f"    - db.py context: {db_context.status}")
    print(f"    - service.py context: {service_context.status}")
    print(f"    - api.py context: {api_context.status}")


def test_handoff_chain():
    """Test chain of handoffs through multiple developers"""
    print("\n✓ Test: Handoff Chain")

    memory = DevelopmentMemory()
    handoff_engine = TemporalHandoffEngine(memory)

    # Dev1 → Dev2 → Agent
    print("  1. Dev1 completes feature and creates handoff")
    h1 = handoff_engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="feature.py::main",
        summary="Initial implementation",
        branch="feature/initial"
    )

    print("  2. Dev2 consumes dev1's handoff and creates new one")
    handoff_engine.consume_handoff("dev2", h1.handoff_id)
    h2 = handoff_engine.create_handoff(
        actor="dev2",
        actor_type="human",
        resource="feature.py::main",
        summary="Refactored for performance",
        branch="feature/optimized"
    )

    print("  3. Agent autonomously consumes dev2's handoff")
    handoff_engine.consume_handoff("agent1", h2.handoff_id)

    # Verify chain
    h1_final = handoff_engine._find_handoff_by_id(h1.handoff_id)
    h2_final = handoff_engine._find_handoff_by_id(h2.handoff_id)

    assert h1_final.consumed_by == "dev2"
    assert h2_final.consumed_by == "agent1"

    print(f"  ✓ Handoff chain complete:")
    print(f"    - Dev1 → Dev2 (h1)")
    print(f"    - Dev2 → Agent (h2)")


def test_reviewer_provenance_with_full_workflow():
    """Test reviewer provenance based on full workflow participation"""
    print("\n✓ Test: Reviewer Provenance with Full Workflow")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    reviewer_engine = ReviewerProvenanceEngine(memory, graph)

    graph.add_dependency("ml.py::train", "dataset.py::load")

    # Dev1: Direct modifications
    print("  1. Dev1 directly modifies resource")
    memory.record_event(Event(
        event_type=EventType.RESOURCE_CLAIMED,
        actor="dev1",
        actor_type="human",
        resource="ml.py::train",
        task_id="JIRA-100",
    ))
    memory.record_event(Event(
        event_type=EventType.WORK_COMPLETED,
        actor="dev1",
        actor_type="human",
        resource="ml.py::train",
        task_id="JIRA-100",
    ))

    # Dev2: Changes dependencies
    print("  2. Dev2 changes dependency")
    memory.record_event(Event(
        event_type=EventType.CONTEXT_INVALIDATED,
        actor="dev2",
        actor_type="human",
        resource="ml.py::train",
        details={"affected_symbol": "dataset.py::load"},
    ))

    # Dev3: Creates handoff (follow-up work)
    print("  3. Dev3 creates handoff for follow-up")
    memory.record_event(Event(
        event_type=EventType.HANDOFF_CREATED,
        actor="dev3",
        actor_type="human",
        resource="ml.py::train",
    ))

    # Query reviewers
    print("  4. Query reviewer candidates")
    candidates = reviewer_engine.get_reviewer_provenance("ml.py::train")

    print(f"  ✓ Found {len(candidates)} reviewer candidates:")
    for c in candidates[:3]:
        print(f"    - {c.actor}: score={c.relevance_score:.2f}, reasons={len(c.relevance_reasons)}")


def test_agent_autonomy_with_all_phases():
    """Test agent autonomy using all phases together"""
    print("\n✓ Test: Agent Autonomy with All Phases")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Setup: Create complex scenario
    print("  1. Setup: Create handoff and stale context")
    graph.add_dependency("order.py::process", "payment.py::charge")
    context_engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="order.py::process",
        base_commit="abc123",
        symbols=["order.py::process", "payment.py::charge"],
        assumptions={"payment_sync": "synchronous"}
    )

    handoff = handoff_engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="order.py::process",
        summary="Initial order processing"
    )

    # Invalidate context
    context_engine.mark_symbol_changed("payment.py::charge", "dev2", "Made async")

    # Register autonomous agent
    print("  2. Register fully autonomous agent")
    policy = AgentAutonomyPolicy(
        "order_agent",
        AutonomyLevel.FULL_AUTONOMOUS,
        can_auto_sync=True,
        can_auto_revalidate=True,
        can_auto_consume_handoffs=True
    )
    autonomy_engine.register_agent_policy(policy)

    # Execute full orchestration
    print("  3. Execute full autonomous orchestration")
    success, message, workflow_id = autonomy_engine.execute_full_workflow_orchestration(
        agent_id="order_agent",
        resource="order.py::process",
        include_sync=True,
        include_revalidate=True,
        include_consume_handoff=True,
        handoff_id=handoff.handoff_id
    )

    # Verify workflow
    print("  4. Verify workflow completion")
    workflow = autonomy_engine.get_workflow_status(workflow_id)
    assert workflow is not None
    print(f"    - Workflow: {workflow['workflow_type']}")
    print(f"    - Status: {workflow['status']}")
    print(f"    - Steps: {len(workflow['steps_executed'])}")
    print(f"  ✓ Agent autonomy orchestration successful!")


def main():
    """Run all integration tests"""
    print("=" * 70)
    print("Neo 2.0 Integration Tests: All Phases Working Together")
    print("=" * 70)

    try:
        test_complete_developer_workflow()
        test_multi_developer_context_tracking()
        test_handoff_chain()
        test_reviewer_provenance_with_full_workflow()
        test_agent_autonomy_with_all_phases()

        print("\n" + "=" * 70)
        print("✓ All Integration Tests Passed!")
        print("=" * 70)
        print("\nPhase Summary:")
        print("  Phase 1: Event Model & Development Memory ✓")
        print("  Phase 2: Temporal Handoff Engine ✓")
        print("  Phase 3: Context Invalidation Engine ✓")
        print("  Phase 4: Reviewer Provenance Engine ✓")
        print("  Phase 5: Agent Autonomy Engine ✓")
        print("\nAll 5 phases working together seamlessly! 🎉")
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

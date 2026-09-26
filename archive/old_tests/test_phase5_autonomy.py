#!/usr/bin/env python3
"""
Test Neo 2.0 Phase 5: Agent Autonomy Engine
Verifies autonomous workflow execution and policy enforcement
"""

import sys
from event_model import Event, EventType
from development_memory import DevelopmentMemory
from dependency_graph import DependencyGraph
from context_invalidation_engine import ContextInvalidationEngine
from temporal_handoff_engine import TemporalHandoffEngine
from agent_autonomy_engine import (
    AgentAutonomyEngine,
    AgentAutonomyPolicy,
    AutonomyLevel
)


def test_agent_policy_registration():
    """Test registering agent autonomy policies"""
    print("\n✓ Test: Agent Policy Registration")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Register policies for different autonomy levels
    policies = [
        AgentAutonomyPolicy("agent1", AutonomyLevel.SYNC_ONLY),
        AgentAutonomyPolicy("agent2", AutonomyLevel.SYNC_AND_REVALIDATE),
        AgentAutonomyPolicy("agent3", AutonomyLevel.FULL_AUTONOMOUS, can_auto_consume_handoffs=True),
    ]

    for policy in policies:
        success, message = autonomy_engine.register_agent_policy(policy)
        assert success == True
        assert policy.agent_id in autonomy_engine.agent_policies

    print(f"  Registered {len(policies)} agent policies")
    for agent_id, policy in autonomy_engine.agent_policies.items():
        print(f"    {agent_id}: {policy.autonomy_level.value}")


def test_auto_sync_execution():
    """Test autonomous context sync"""
    print("\n✓ Test: Auto Sync Execution")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Register agent
    policy = AgentAutonomyPolicy("agent1", AutonomyLevel.SYNC_ONLY)
    autonomy_engine.register_agent_policy(policy)

    # Create stale context
    graph.add_dependency("service.py::query", "db.py::execute")
    context_engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="service.py::query",
        base_commit="abc123",
        symbols=["service.py::query", "db.py::execute"],
    )

    # Invalidate
    context_engine.mark_symbol_changed("db.py::execute", "dev2", "Added optimization")

    # Execute auto sync
    success, message, workflow_id = autonomy_engine.execute_auto_sync("agent1", "service.py::query")

    assert success == True
    assert workflow_id is not None
    assert workflow_id in autonomy_engine.workflow_history[-1].workflow_id

    print(f"  Workflow ID: {workflow_id}")
    print(f"  Status: {success}")
    print(f"  Message: {message}")


def test_auto_revalidate_execution():
    """Test autonomous context revalidation"""
    print("\n✓ Test: Auto Revalidate Execution")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Register agent
    policy = AgentAutonomyPolicy("agent1", AutonomyLevel.SYNC_AND_REVALIDATE)
    autonomy_engine.register_agent_policy(policy)

    # Create context with assumptions
    graph.add_dependency("ml.py::train", "dataset.py::load")
    context_engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="ml.py::train",
        base_commit="abc123",
        symbols=["ml.py::train", "dataset.py::load"],
        assumptions={"dataset_size": "10000 rows"}
    )

    # Sync first
    context_engine.sync_context("ml.py::train")

    # Execute auto revalidate
    success, message, workflow_id = autonomy_engine.execute_auto_revalidate("agent1", "ml.py::train")

    assert workflow_id is not None
    workflow = autonomy_engine.get_workflow_status(workflow_id)
    assert workflow is not None
    assert workflow["workflow_type"] == "revalidate"

    print(f"  Workflow ID: {workflow_id}")
    print(f"  Status: {workflow['status']}")
    print(f"  Steps executed: {len(workflow['steps_executed'])}")


def test_auto_consume_handoff():
    """Test autonomous handoff consumption"""
    print("\n✓ Test: Auto Consume Handoff")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Register agent with full autonomy
    policy = AgentAutonomyPolicy(
        "agent1",
        AutonomyLevel.FULL_AUTONOMOUS,
        can_auto_consume_handoffs=True
    )
    autonomy_engine.register_agent_policy(policy)

    # Create handoff
    handoff = handoff_engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="payment.py::process",
        summary="Added retry logic",
        branch="feature/retry"
    )

    # Execute auto consume
    success, message, workflow_id = autonomy_engine.execute_auto_consume_handoff(
        "agent1", handoff.handoff_id
    )

    assert success == True
    assert workflow_id is not None

    # Verify handoff was consumed
    consumed_handoff = handoff_engine._find_handoff_by_id(handoff.handoff_id)
    assert consumed_handoff.consumed_by == "agent1"
    assert consumed_handoff.status == "CONSUMED"

    print(f"  Handoff ID: {handoff.handoff_id}")
    print(f"  Consumed by: {consumed_handoff.consumed_by}")
    print(f"  Workflow ID: {workflow_id}")


def test_full_workflow_orchestration():
    """Test full autonomous workflow orchestration"""
    print("\n✓ Test: Full Workflow Orchestration")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Register fully autonomous agent
    policy = AgentAutonomyPolicy(
        "agent1",
        AutonomyLevel.FULL_AUTONOMOUS,
        can_auto_sync=True,
        can_auto_revalidate=True,
        can_auto_consume_handoffs=True
    )
    autonomy_engine.register_agent_policy(policy)

    # Create handoff
    handoff = handoff_engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="order.py::process",
        summary="Refactored processing"
    )

    # Create stale context
    graph.add_dependency("order.py::process", "payment.py::charge")
    context_engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="order.py::process",
        base_commit="abc123",
        symbols=["order.py::process", "payment.py::charge"],
        assumptions={"payment_sync": "synchronous"}
    )

    # Execute full orchestration
    success, message, workflow_id = autonomy_engine.execute_full_workflow_orchestration(
        agent_id="agent1",
        resource="order.py::process",
        include_sync=True,
        include_revalidate=True,
        include_consume_handoff=True,
        handoff_id=handoff.handoff_id
    )

    workflow = autonomy_engine.get_workflow_status(workflow_id)
    assert workflow is not None
    assert workflow["workflow_type"] == "full_orchestration"
    assert len(workflow["steps_executed"]) >= 2  # At least consume and sync

    print(f"  Workflow ID: {workflow_id}")
    print(f"  Status: {workflow['status']}")
    print(f"  Steps executed: {[s['step'] for s in workflow['steps_executed']]}")


def test_policy_enforcement():
    """Test that policies are properly enforced"""
    print("\n✓ Test: Policy Enforcement")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Register agent with limited permissions
    policy = AgentAutonomyPolicy("agent1", AutonomyLevel.SYNC_ONLY, can_auto_consume_handoffs=False)
    autonomy_engine.register_agent_policy(policy)

    # Create handoff
    handoff = handoff_engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="service.py::query",
        summary="Optimized query"
    )

    # Try to consume - should fail due to policy
    success, message, workflow_id = autonomy_engine.execute_auto_consume_handoff(
        "agent1", handoff.handoff_id
    )

    assert success == False
    assert "not authorized" in message.lower()

    print(f"  Policy check: {message}")
    print(f"  Authorization denied as expected")


def test_workflow_history_tracking():
    """Test that workflow history is tracked"""
    print("\n✓ Test: Workflow History Tracking")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Register agent
    policy = AgentAutonomyPolicy("agent1", AutonomyLevel.SYNC_ONLY)
    autonomy_engine.register_agent_policy(policy)

    # Create and execute multiple workflows
    graph.add_dependency("service1.py::query", "db.py::execute")
    context_engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="service1.py::query",
        base_commit="abc123",
        symbols=["service1.py::query", "db.py::execute"],
    )

    for i in range(3):
        autonomy_engine.execute_auto_sync("agent1", "service1.py::query")

    # Check history
    history = autonomy_engine.get_workflow_history("agent1")
    assert len(history) >= 3

    active = autonomy_engine.get_active_workflows("agent1")

    print(f"  Total workflows in history: {len(history)}")
    print(f"  Active workflows: {len(active)}")


def test_agent_disable_enable():
    """Test disabling and enabling agent autonomy"""
    print("\n✓ Test: Agent Disable/Enable")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    context_engine = ContextInvalidationEngine(memory, graph)
    handoff_engine = TemporalHandoffEngine(memory)
    autonomy_engine = AgentAutonomyEngine(memory, context_engine, handoff_engine, graph)

    # Register agent
    policy = AgentAutonomyPolicy("agent1", AutonomyLevel.SYNC_ONLY)
    autonomy_engine.register_agent_policy(policy)

    # Disable agent
    success, message = autonomy_engine.disable_agent_autonomy("agent1")
    assert success == True
    assert not autonomy_engine.agent_policies["agent1"].enabled

    # Try to execute - should fail
    graph.add_dependency("service.py::query", "db.py::execute")
    context_engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="service.py::query",
        base_commit="abc123",
        symbols=["service.py::query", "db.py::execute"],
    )

    success, msg, _ = autonomy_engine.execute_auto_sync("agent1", "service.py::query")
    assert success == False

    # Re-enable
    success, message = autonomy_engine.enable_agent_autonomy("agent1")
    assert success == True
    assert autonomy_engine.agent_policies["agent1"].enabled

    print(f"  Agent disabled and re-enabled successfully")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Neo 2.0 Phase 5 Tests: Agent Autonomy Engine")
    print("=" * 60)

    try:
        test_agent_policy_registration()
        test_auto_sync_execution()
        test_auto_revalidate_execution()
        test_auto_consume_handoff()
        test_full_workflow_orchestration()
        test_policy_enforcement()
        test_workflow_history_tracking()
        test_agent_disable_enable()

        print("\n" + "=" * 60)
        print("✓ All Phase 5 tests passed!")
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

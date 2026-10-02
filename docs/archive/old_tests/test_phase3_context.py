#!/usr/bin/env python3
"""
Test Neo 2.0 Phase 3: Context Invalidation Engine
Verifies context snapshots and invalidation detection
"""

import sys
from development_memory import DevelopmentMemory
from dependency_graph import DependencyGraph, ContextSnapshot
from context_invalidation_engine import ContextInvalidationEngine


def test_dependency_graph():
    """Test dependency graph operations"""
    print("\n✓ Test: Dependency Graph")

    graph = DependencyGraph()

    # Build a dependency graph
    graph.add_dependency("order.py::process", "payment.py::charge")
    graph.add_dependency("order.py::process", "notification.py::send")
    graph.add_dependency("payment.py::charge", "bank.py::transfer")

    # Test transitive dependencies
    deps = graph.get_all_dependencies("order.py::process")
    assert "payment.py::charge" in deps
    assert "bank.py::transfer" in deps
    assert "notification.py::send" in deps

    # Test dependents
    dependents = graph.get_all_dependents("payment.py::charge")
    assert "order.py::process" in dependents

    print(f"  Dependencies of order.py::process: {deps}")
    print(f"  Dependents of payment.py::charge: {dependents}")


def test_context_snapshot():
    """Test creating context snapshots"""
    print("\n✓ Test: Context Snapshot Creation")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ContextInvalidationEngine(memory, graph)

    # Build dependencies first
    graph.add_dependency("order.py::process_order", "payment.py::charge")

    # Dev1 starts work with context
    snapshot = engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="order.py::process_order",
        base_commit="abc123",
        task_id="JIRA-100",
        files=["order.py", "payment.py"],
        symbols=["order.py::process_order", "payment.py::charge"],
        assumptions={
            "payment_sync": "payment.charge() is synchronous",
            "timeout": "charge completes within 30 seconds",
        },
        api_signatures={
            "payment.py::charge": "charge(amount: float) -> bool"
        }
    )

    assert snapshot.actor == "dev1"
    assert snapshot.status == "CURRENT"
    assert "payment.py" in snapshot.files_involved
    assert len(snapshot.dependencies) > 0

    print(f"  Snapshot created for: {snapshot.resource}")
    print(f"  Status: {snapshot.status}")
    print(f"  Dependencies tracked: {snapshot.dependencies}")


def test_context_invalidation():
    """Test context invalidation detection"""
    print("\n✓ Test: Context Invalidation Detection")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ContextInvalidationEngine(memory, graph)

    # Build dependencies (must match symbols in snapshot)
    graph.add_dependency("order.py::process_order", "payment.py::charge")
    graph.add_dependency("payment.py::charge", "bank.py::transfer")

    # Dev1 creates context snapshot
    snapshot = engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="order.py::process_order",
        base_commit="abc123",
        files=["order.py", "payment.py"],
        symbols=["order.py::process_order", "payment.py::charge"],
        assumptions={
            "sync": "payment.charge() is synchronous"
        }
    )

    # Dev2 changes payment.charge (invalidates dev1's context)
    engine.mark_symbol_changed(
        symbol="payment.py::charge",
        changed_by="dev2",
        reason="Changed to async/await pattern"
    )

    # Check dev1's context is now stale
    context = engine.active_contexts["order.py::process_order"]
    assert context.status == "STALE"
    assert "payment.py::charge" in context.changed_dependencies

    print(f"  Context status: {context.status}")
    print(f"  Changed dependencies: {context.changed_dependencies}")
    print(f"  Invalidation reasons: {context.invalidation_reasons}")


def test_context_sync_and_revalidation():
    """Test sync and revalidation workflow"""
    print("\n✓ Test: Context Sync & Revalidation")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ContextInvalidationEngine(memory, graph)

    graph.add_dependency("service.py::query", "db.py::execute")

    snapshot = engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="service.py::query",
        base_commit="abc123",
        symbols=["service.py::query", "db.py::execute"],
        assumptions={
            "response_time": "db.py::execute returns within 5 seconds"
        }
    )

    # Invalidate
    engine.mark_symbol_changed(
        symbol="db.py::execute",
        changed_by="dev2",
        reason="Added retry logic with exponential backoff"
    )

    # Sync
    success, message = engine.sync_context("service.py::query")
    assert success == True

    context = engine.active_contexts["service.py::query"]
    assert context.status == "SYNC_REQUIRED"

    # Revalidate (will find the timing assumption issue)
    success, message, issues = engine.revalidate_context("service.py::query")
    assert success == False  # Issues found
    assert len(issues) > 0

    print(f"  After sync status: {context.status}")
    print(f"  Revalidation issues: {issues}")


def test_context_revalidation_workflow():
    """Test getting human-friendly revalidation workflow"""
    print("\n✓ Test: Revalidation Workflow")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ContextInvalidationEngine(memory, graph)

    graph.add_dependency("ml.py::train", "dataset.py::load")

    engine.create_context_snapshot(
        actor="agent1",
        actor_type="agent",
        resource="ml.py::train_model",
        base_commit="def456",
        symbols=["ml.py::train", "dataset.py::load"],
        assumptions={
            "dataset_shape": "dataset.load() returns 10k rows",
            "features": "features match original training"
        }
    )

    # Invalidate
    engine.mark_symbol_changed(
        symbol="dataset.py::load",
        changed_by="dev1",
        reason="Added new feature columns"
    )

    # Get workflow
    workflow = engine.get_context_revalidation_workflow("ml.py::train_model")

    assert "message" in workflow
    assert "workflow_steps" in workflow
    assert len(workflow["workflow_steps"]) > 0

    print(f"  Message: {workflow['message']}")
    print(f"  Steps: {[s['action'] for s in workflow['workflow_steps']]}")


def test_multiple_contexts():
    """Test managing multiple developer contexts"""
    print("\n✓ Test: Multiple Developer Contexts")

    memory = DevelopmentMemory()
    graph = DependencyGraph()
    engine = ContextInvalidationEngine(memory, graph)

    graph.add_dependency("auth.py::validate", "db.py::lookup")
    graph.add_dependency("api.py::endpoint", "auth.py::validate")

    # Dev1 context
    engine.create_context_snapshot(
        actor="dev1",
        actor_type="human",
        resource="auth.py::validate",
        base_commit="abc123",
        symbols=["auth.py::validate", "db.py::lookup"]
    )

    # Dev2 context
    engine.create_context_snapshot(
        actor="dev2",
        actor_type="human",
        resource="api.py::endpoint",
        base_commit="abc123",
        symbols=["api.py::endpoint", "auth.py::validate"]
    )

    assert len(engine.active_contexts) == 2

    # Change db.py::lookup
    engine.mark_symbol_changed(
        symbol="db.py::lookup",
        changed_by="dev3",
        reason="Added caching layer"
    )

    # Should only invalidate dev1's context (direct dependency)
    dev1_context = engine.active_contexts["auth.py::validate"]
    dev2_context = engine.active_contexts["api.py::endpoint"]

    assert dev1_context.status == "STALE"
    # Dev2 might be indirectly affected but depends on implementation

    print(f"  Dev1 context status: {dev1_context.status}")
    print(f"  Dev2 context status: {dev2_context.status}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Neo 2.0 Phase 3 Tests: Context Invalidation Engine")
    print("=" * 60)

    try:
        test_dependency_graph()
        test_context_snapshot()
        test_context_invalidation()
        test_context_sync_and_revalidation()
        test_context_revalidation_workflow()
        test_multiple_contexts()

        print("\n" + "=" * 60)
        print("✓ All Phase 3 tests passed!")
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

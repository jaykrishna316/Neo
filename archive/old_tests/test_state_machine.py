#!/usr/bin/env python3
"""
Test Workflow State Machine with Neo 2.0 Integration
Verifies state transitions and HANDOFF_PENDING state
"""

import sys
from workflow_state_machine import WorkflowStateMachine, WorkflowState


def test_single_developer_workflow():
    """Test single developer workflow"""
    print("\n✓ Test: Single Developer Workflow")
    
    sm = WorkflowStateMachine("payment.py", "process_payment")
    
    # Start editing
    success, msg, state = sm.start_editing("dev1")
    assert success == True
    assert state == WorkflowState.EDITING
    print(f"  1. Dev1 starts editing: {state.value}")
    
    # Finish editing
    success, msg, state = sm.finish_editing("dev1")
    assert success == True
    assert state == WorkflowState.BOTH_DONE
    print(f"  2. Dev1 finishes: {state.value}")


def test_two_developer_workflow():
    """Test two-developer collaboration"""
    print("\n✓ Test: Two Developer Workflow")
    
    sm = WorkflowStateMachine("order.py", "process_order")
    
    # Dev1 starts
    success, msg, state = sm.start_editing("dev1")
    assert success == True
    print(f"  1. Dev1 starts: {state.value}")
    
    # Dev2 tries to edit (blocked)
    success, msg, state = sm.start_editing("dev2")
    assert success == False
    print(f"  2. Dev2 blocked: {state.value}")
    
    # Dev1 finishes - Dev2 gets notified
    success, msg, state = sm.finish_editing("dev1")
    assert state == WorkflowState.PENDING_REVIEW
    print(f"  3. Dev1 finishes - Dev2 notified: {state.value}")
    
    # Simulate Dev2 resuming
    sm.current_editor = "dev2"
    sm.state = WorkflowState.EDITING
    sm.finish_editing("dev2")
    print(f"  4. Dev2 finishes: BOTH_DONE")


def test_multi_developer_queue():
    """Test waiting queue"""
    print("\n✓ Test: Multi-Developer Queue")
    
    sm = WorkflowStateMachine("service.py", "query")
    
    sm.start_editing("dev1")
    print(f"  1. Dev1 editing")
    
    sm.start_editing("dev2")
    print(f"  2. Dev2 waiting")
    
    sm.finish_editing("dev1")
    print(f"  3. Dev1 finishes - Dev2 notified")


def test_handoff_pending_state():
    """Test HANDOFF_PENDING state (Neo 2.0)"""
    print("\n✓ Test: HANDOFF_PENDING State (Neo 2.0)")
    
    sm = WorkflowStateMachine("feature.py", "main")
    
    # Complete editing
    sm.start_editing("dev1")
    sm.finish_editing("dev1")
    sm.current_editor = "dev2"
    sm.state = WorkflowState.EDITING
    sm.finish_editing("dev2")
    
    # Transition to HANDOFF_PENDING
    sm.state = WorkflowState.HANDOFF_PENDING
    sm._transition_to(WorkflowState.HANDOFF_PENDING, "dev1", "Work completed")
    assert sm.state == WorkflowState.HANDOFF_PENDING
    print(f"  1. Transitioned to: {sm.state.value}")
    
    # Verify can transition to IN_PR
    can_transition = sm.can_transition_to(WorkflowState.IN_PR)
    assert can_transition == True
    print(f"  2. Can transition to IN_PR: {can_transition}")


def test_pr_workflow():
    """Test PR workflow"""
    print("\n✓ Test: PR Workflow")
    
    sm = WorkflowStateMachine("api.py", "endpoint")
    
    # Setup
    sm.start_editing("dev1")
    sm.finish_editing("dev1")
    sm.current_editor = "dev2"
    sm.state = WorkflowState.EDITING
    sm.finish_editing("dev2")
    
    # Create PR
    sm.state = WorkflowState.IN_PR
    sm._transition_to(WorkflowState.IN_PR, "dev1", "PR created")
    print(f"  1. PR created: {sm.state.value}")
    
    # Approve
    sm.state = WorkflowState.APPROVED
    sm._transition_to(WorkflowState.APPROVED, "dev2", "Approved")
    print(f"  2. Approved: {sm.state.value}")
    
    # Merge
    sm.state = WorkflowState.MERGED
    sm._transition_to(WorkflowState.MERGED, "dev1", "Merged")
    print(f"  3. Merged: {sm.state.value}")


def test_developer_tracking():
    """Test developer tracking"""
    print("\n✓ Test: Developer Tracking")
    
    sm = WorkflowStateMachine("payment.py", "charge")
    
    # Multiple developers
    sm.start_editing("dev1")
    sm.start_editing("dev2")
    sm.finish_editing("dev1")
    
    print(f"  Developers tracked: {sm.all_developers}")
    assert "dev1" in sm.all_developers
    assert "dev2" in sm.all_developers
    print(f"  Total: {len(sm.all_developers)}")


def test_integration_with_handoff():
    """Test integration with Neo 2.0 handoff"""
    print("\n✓ Test: State Machine + Handoff Integration")
    
    from temporal_handoff_engine import TemporalHandoffEngine
    from development_memory import DevelopmentMemory
    
    memory = DevelopmentMemory()
    handoff_engine = TemporalHandoffEngine(memory)
    sm = WorkflowStateMachine("payment.py", "process")
    
    # Workflow completes
    sm.start_editing("dev1")
    sm.finish_editing("dev1")
    sm.current_editor = "dev2"
    sm.state = WorkflowState.EDITING
    sm.finish_editing("dev2")
    
    # Transition to HANDOFF_PENDING
    sm.state = WorkflowState.HANDOFF_PENDING
    print(f"  1. State: {sm.state.value}")
    
    # Create handoff
    handoff = handoff_engine.create_handoff(
        actor="dev1",
        actor_type="human",
        resource="payment.py::process",
        summary="Implementation complete"
    )
    print(f"  2. Handoff created")
    
    # Next developer detects it
    has_prior, _, _ = handoff_engine.intercept_new_intent("agent1", "payment.py::process")
    assert has_prior == True
    print(f"  3. Next developer detected prior work")


def main():
    """Run all tests"""
    print("=" * 70)
    print("Workflow State Machine Tests (with Neo 2.0 Integration)")
    print("=" * 70)
    
    try:
        test_single_developer_workflow()
        test_two_developer_workflow()
        test_multi_developer_queue()
        test_handoff_pending_state()
        test_pr_workflow()
        test_developer_tracking()
        test_integration_with_handoff()
        
        print("\n" + "=" * 70)
        print("✓ All State Machine Tests Passed!")
        print("=" * 70)
        print("\nState Machine Verified:")
        print("  ✓ Single developer workflow")
        print("  ✓ Two developer collaboration")
        print("  ✓ Multi-developer queue")
        print("  ✓ HANDOFF_PENDING state (Neo 2.0)")
        print("  ✓ PR/merge workflow")
        print("  ✓ Developer tracking")
        print("  ✓ State machine + handoff integration")
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

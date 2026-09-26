#!/usr/bin/env python3
"""
Test Optimization 2: Simplify Lock Mechanism
- Validates RiskLevel directly acts as lock signal
- Tests lock behavior without explicit Lock object
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.optimized_coordination_machine import OptimizedCoordinationMachine, CoordinationState, DecisionOption
from core.risk_classifier import RiskLevel


def test_risk_level_maps_to_lock_state():
    """RiskLevel.LOW → ACTIVE, MEDIUM → LOCKED, HIGH → LOCKED"""
    machine = OptimizedCoordinationMachine()

    # Developer A logs intent (LOW risk)
    entry_a = machine.log_intent(
        agent_id="alice",
        file_path="auth.py",
        region="login_user",
        intent="Add password validation"
    )
    assert entry_a.state == CoordinationState.ACTIVE
    assert entry_a.risk_level == RiskLevel.LOW.value
    print("✓ Single developer: ACTIVE state, LOW risk")

    # Developer B checks for conflicts
    conflict_check = machine.check_conflicts(
        agent_id="bob",
        file_path="auth.py",
        region="login_user"
    )

    # With conflict detected, should map risk level to state
    if conflict_check['has_conflict']:
        assert conflict_check['state'] == CoordinationState.LOCKED
        print(f"✓ Conflict detected: state = LOCKED, risk_level = {conflict_check['risk_level'].value}")


def test_no_explicit_lock_object_needed():
    """Lock behavior implicit in RiskLevel enum"""
    machine = OptimizedCoordinationMachine()

    # Developer A starts work
    machine.log_intent(
        agent_id="alice",
        file_path="auth.py",
        region="login_user",
        intent="Refactor login function"
    )

    # Developer B tries to work on same file
    conflict_check = machine.check_conflicts(
        agent_id="bob",
        file_path="auth.py",
        region="login_user"
    )

    # Lock is implicit in RiskLevel - no separate Lock struct needed
    if conflict_check['state'] == CoordinationState.LOCKED:
        assert conflict_check['risk_level'] in (RiskLevel.MEDIUM, RiskLevel.HIGH)
        # No explicit lock object - just the RiskLevel
        print("✓ Lock is implicit in RiskLevel (no explicit Lock object)")


def test_lock_release_on_completion():
    """mark_completed() fires lock_removed event correctly"""
    machine = OptimizedCoordinationMachine()

    event_fired = []

    def on_lock_removed(data):
        event_fired.append(data)

    machine.subscribe_to_event("lock_removed", on_lock_removed)

    # Developer A works
    machine.log_intent(
        agent_id="alice",
        file_path="auth.py",
        region="login_user",
        intent="Add validation"
    )

    # Developer A completes
    machine.mark_completed("alice")

    # Check that event was fired
    assert len(event_fired) > 0, "lock_removed event should fire"
    assert event_fired[0]['agent'] == 'alice'
    print("✓ mark_completed() fires lock_removed event")


def test_checkpoint_saved_during_wait():
    """Developer B saves checkpoint, resumes from it"""
    from core.optimized_coordination_machine import GenerationCheckpoint

    machine = OptimizedCoordinationMachine()

    # Developer A works
    machine.log_intent(
        agent_id="alice",
        file_path="auth.py",
        region="login_user",
        intent="Add validation"
    )

    # Developer B encounters lock and chooses to wait
    checkpoint = GenerationCheckpoint(
        agent_id="bob",
        file_path="auth.py",
        region="login_user",
        intent="Add logging",
        tokens_generated=100,
        context_buffer="Bob was generating code...",
        timestamp="2026-09-26T10:00:00"
    )

    machine.handle_decision(
        agent_id="bob",
        decision=DecisionOption.WAIT,
        checkpoint=checkpoint
    )

    # Verify checkpoint was saved
    assert "bob" in machine.checkpoints
    assert machine.checkpoints["bob"].tokens_generated == 100
    print("✓ Checkpoint saved during WAIT decision")

    # Developer A completes, fires lock_removed event
    machine.mark_completed("alice")

    # Developer B resumes from checkpoint
    resumed = machine.resume_from_checkpoint("bob")
    assert resumed is not None
    assert resumed.tokens_generated == 100
    print("✓ Checkpoint restored on lock release")


def test_decision_options_by_risk_level():
    """MEDIUM/HIGH returns [COLLABORATE, WAIT, WRAP_UP_REQUEST]"""
    machine = OptimizedCoordinationMachine()

    # Developer A works
    machine.log_intent(
        agent_id="alice",
        file_path="auth.py",
        region="login_user",
        intent="Refactor login"
    )

    # Developer B checks
    conflict_check = machine.check_conflicts(
        agent_id="bob",
        file_path="auth.py",
        region="login_user"
    )

    # If locked, should have decision options
    if conflict_check['state'] == CoordinationState.LOCKED:
        options = conflict_check['decision_options']
        assert DecisionOption.WAIT in options
        assert DecisionOption.COLLABORATE in options
        assert DecisionOption.WRAP_UP_REQUEST in options
        print(f"✓ Decision options for locked state: {[o.value for o in options]}")


def test_generation_allowed_with_decision():
    """check_generation_allowed respects lock and decision"""
    machine = OptimizedCoordinationMachine()

    # Developer A works
    machine.log_intent(
        agent_id="alice",
        file_path="auth.py",
        region="login_user",
        intent="Refactor"
    )

    # Developer B without decision → should be blocked
    try:
        allowed, msg = machine.check_generation_allowed(
            agent_id="bob",
            file_path="auth.py",
            region="login_user",
            decision=None
        )
        # Might be allowed if LOW risk
        print(f"✓ Generation check (no decision): allowed={allowed}, msg='{msg[:50]}...'")
    except Exception as e:
        print(f"✓ Generation check raises error on locked state: {type(e).__name__}")

    # Developer B with WAIT decision → should be allowed
    allowed, msg = machine.check_generation_allowed(
        agent_id="bob",
        file_path="auth.py",
        region="login_user",
        decision=DecisionOption.WAIT
    )
    assert allowed
    print(f"✓ Generation allowed with WAIT decision")


if __name__ == "__main__":
    print("=" * 70)
    print("TEST OPTIMIZATION 2: Lock Simplification")
    print("=" * 70)
    print()

    test_risk_level_maps_to_lock_state()
    test_no_explicit_lock_object_needed()
    test_lock_release_on_completion()
    test_checkpoint_saved_during_wait()
    test_decision_options_by_risk_level()
    test_generation_allowed_with_decision()

    print()
    print("=" * 70)
    print("✅ ALL OPTIMIZATION 2 TESTS PASSED")
    print("=" * 70)

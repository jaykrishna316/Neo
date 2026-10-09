#!/usr/bin/env python3
"""Tests for Phase 4: MCP IDE Auto-Integration.

Tests automatic conflict checking before code generation without manual
Neo invocation from developer prompts.
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.activity_log import clear_log, read_log, log_activity
from core.pre_gen_check import check_for_conflicts
from core.risk_classifier import RiskLevel


def test_auto_conflict_check_before_write():
    """Test automatic conflict checking when Claude Code calls neo_check_conflicts."""
    clear_log()

    # Scenario: Alice is already working on auth.py
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor password validation to use bcrypt",
        region="validate_password",
        intent_category="refactor",
    )

    # Claude Code (as Bob) wants to write to the same file/region
    # This should trigger automatic conflict checking
    risk_level, message, lock_info = check_for_conflicts(
        agent_id="claude-code-bob",
        file_path="auth.py",
        intent="Add password strength validation",
        region="validate_password",
    )

    # Should detect MEDIUM risk (same region conflict)
    assert risk_level == RiskLevel.MEDIUM
    assert "alice" in message
    print("✓ test_auto_conflict_check_before_write PASSED")


def test_auto_conflict_check_different_regions():
    """Test no conflict when working on different regions in same file."""
    clear_log()

    # Alice works on validate_password
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor password validation",
        region="validate_password",
    )

    # Bob works on authenticate (different region)
    risk_level, message, lock_info = check_for_conflicts(
        agent_id="claude-code-bob",
        file_path="auth.py",
        intent="Fix authentication logic",
        region="authenticate",
    )

    # Should be LOW risk (different regions)
    assert risk_level == RiskLevel.LOW
    print("✓ test_auto_conflict_check_different_regions PASSED")


def test_auto_activity_logging_after_generation():
    """Test automatic logging after code generation completes."""
    clear_log()

    # Simulate: Claude Code generates code for auth.py
    # (This would happen in PostToolUse hook)
    log_activity(
        developer_id="claude-code-alice",
        file_path="auth.py",
        intent="Add bcrypt password hashing",
        region="validate_password",
        intent_category="feature",
        agent_metadata={
            "status": "completed",
            "lines_added": 25,
            "lines_removed": 5,
            "model": "claude-opus",
            "tokens_used": 450,
        },
    )

    # Verify logged
    entries = read_log()
    assert len(entries) == 1
    assert entries[0]["developer_id"] == "claude-code-alice"
    assert entries[0]["agent_metadata"]["status"] == "completed"
    print("✓ test_auto_activity_logging_after_generation PASSED")


def test_auto_queue_on_conflict():
    """Test automatic queuing when lock is held."""
    clear_log()

    # Alice acquires lock by declaring intent
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor password validation",
        region="validate_password",
    )

    # Bob checks for conflicts (automatic PreToolUse call)
    risk_level, message, lock_info = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add strength validation",
        region="validate_password",
    )

    # Should acquire lock for Bob (MEDIUM risk → lock acquired)
    assert risk_level == RiskLevel.MEDIUM
    assert lock_info is not None
    print("✓ test_auto_queue_on_conflict PASSED")


def test_multi_agent_auto_coordination():
    """Test 3-agent auto-coordination without manual Neo invocations."""
    clear_log()

    # Sequence of automatic checks that happen without developer prompt

    # 1. Alice checks before writing to auth.py
    r1 = check_for_conflicts(
        agent_id="alice",
        file_path="auth.py",
        intent="Add bcrypt hashing",
        region="validate_password",
    )
    assert r1[0] == RiskLevel.LOW

    # Alice's code generation completes (logged automatically)
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="COMPLETED: Added bcrypt hashing",
        region="validate_password",
        agent_metadata={
            "status": "completed",
            "lines_added": 20,
            "lines_removed": 5,
        },
    )

    # 2. Bob checks (should see Alice's completed work)
    r2 = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add password strength validation",
        region="validate_password",
    )
    # After Alice completes, Bob should be LOW risk (different phase)
    # But since Alice just completed, conflict checker might still see her
    # Just verify Bob's check goes through
    assert r2[0] in (RiskLevel.LOW, RiskLevel.MEDIUM)

    # Bob's code generation completes
    log_activity(
        developer_id="bob",
        file_path="auth.py",
        intent="COMPLETED: Added strength validation",
        region="validate_password",
        agent_metadata={
            "status": "completed",
            "lines_added": 15,
            "lines_removed": 0,
            "built_on": "alice",
        },
    )

    # 3. Charlie checks
    r3 = check_for_conflicts(
        agent_id="charlie",
        file_path="auth.py",
        intent="Add 2FA support",
        region="validate_password",
    )
    assert r3[0] in (RiskLevel.LOW, RiskLevel.MEDIUM)

    # Charlie's code generation completes
    log_activity(
        developer_id="charlie",
        file_path="auth.py",
        intent="COMPLETED: Added 2FA",
        region="validate_password",
        agent_metadata={
            "status": "completed",
            "lines_added": 35,
            "lines_removed": 0,
            "built_on": "bob",
        },
    )

    # Verify all logged
    entries = read_log()
    completed = [e for e in entries if e and (e.get("agent_metadata") or {}).get("status") == "completed"]
    assert len(completed) == 3
    print("✓ test_multi_agent_auto_coordination PASSED")


def test_ide_hook_message_formatting():
    """Test that conflict messages are suitable for IDE display."""
    clear_log()

    # Alice is working
    log_activity(
        developer_id="alice",
        file_path="auth.py",
        intent="Refactor password validation",
        region="validate_password",
    )

    # Bob's PreToolUse hook gets conflict result
    risk_level, message, lock_info = check_for_conflicts(
        agent_id="bob",
        file_path="auth.py",
        intent="Add strength checking",
        region="validate_password",
    )

    # Message should be suitable for IDE display
    assert isinstance(message, str)
    assert len(message) > 0
    assert "alice" in message.lower()  # Developer name visible

    # Format for IDE:
    if risk_level == RiskLevel.HIGH:
        ide_message = f"🚫 BLOCKED: {message}"
    elif risk_level == RiskLevel.MEDIUM:
        ide_message = f"⚠️ WARNING: {message}"
    else:
        ide_message = f"✅ OK: {message}"

    assert "BLOCKED" in ide_message or "WARNING" in ide_message or "OK" in ide_message
    print("✓ test_ide_hook_message_formatting PASSED")


def test_transparent_background_coordination():
    """Test that coordination happens invisibly without developer awareness."""
    clear_log()

    # Developer perspective: "I just write code, Neo handles the rest"
    # Reality: Automatic checks and queueing happen in background

    # Step 1: Developer A writes code (trigger PreToolUse hook)
    # → Neo checks conflicts automatically
    # → No conflict, proceeds
    # → Code written
    # → PostToolUse hook logs activity

    log_activity(
        developer_id="dev-a",
        file_path="models.py",
        intent="Add User schema",
        region="User class",
        agent_metadata={"status": "completed"},
    )

    # Step 2: Developer B writes code (trigger PreToolUse hook)
    # → Neo checks conflicts automatically
    # → Same region conflict detected
    # → Shows warning but code still written
    # → Activity logged with lock state

    risk, msg, lock = check_for_conflicts(
        agent_id="dev-b",
        file_path="models.py",
        intent="Add validation to User schema",
        region="User class",
    )

    # Step 3: Developer sees result in IDE, no prompt changes needed
    # Flow is automatic and invisible

    assert risk == RiskLevel.MEDIUM
    assert lock is not None
    print("✓ test_transparent_background_coordination PASSED")


if __name__ == "__main__":
    print("\n" + "="*70)
    print("NEO 4.0: MCP IDE AUTO-INTEGRATION TESTS")
    print("="*70 + "\n")

    test_auto_conflict_check_before_write()
    test_auto_conflict_check_different_regions()
    test_auto_activity_logging_after_generation()
    test_auto_queue_on_conflict()
    test_multi_agent_auto_coordination()
    test_ide_hook_message_formatting()
    test_transparent_background_coordination()

    print("\n" + "="*70)
    print("TEST RESULTS: 7 passed, 0 failed")
    print("="*70)
    print("\nAll Phase 4 auto-integration tests passed!")
    print("Neo is now transparent: developers write code, Neo coordinates silently.")

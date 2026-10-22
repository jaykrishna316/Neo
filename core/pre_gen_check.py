#!/usr/bin/env python3
"""Pre-generation conflict checking API for Neo coordination layer (tenant-isolated)."""

import time
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from core.activity_log import get_active_entries, DEFAULT_TENANT_ID, log_activity, read_log
from core.risk_classifier import RiskLevel, classify_risk
from core.lock_manager import LockManager
from core.symbol_hasher import StalenessChecker, snapshot_file, extract_dependencies
from core.freshness import check_freshness, get_base_snapshot
from core.impact_alerts import ImpactAlertManager
from core.breaking_change_intent_analyzer import BreakingIntentAnalyzer, detect_breaking_change_intent

# Content-based staleness detection constants
# CONTEXT_FRESHNESS_FALLBACK_MINUTES: Fallback when content hashing unavailable
#   - Only used if file cannot be read/parsed
#   - Otherwise relies on semantic content comparison
CONTEXT_FRESHNESS_FALLBACK_MINUTES = 30


def _detect_breaking_change_intent(intent: str) -> bool:
    """
    Detect if intent describes a breaking change (smart semantic analysis).

    Uses semantic intent analysis to distinguish between:
    - Developer INTRODUCING breaking changes (refactor API, remove params)
    - Developer ADAPTING to upstream changes (update calls, migrate)

    Args:
        intent: Developer's intent description

    Returns:
        True if intent describes introducing breaking changes, False if adapting or other
    """
    is_breaking, reason, _ = detect_breaking_change_intent(intent)
    return is_breaking


def _check_downstream_impact(file_path: str) -> bool:
    """
    Check if file has downstream dependencies.

    Args:
        file_path: Path to the file

    Returns:
        True if file has downstream dependents, False otherwise
    """
    try:
        # Get module name from file path (e.g., "auth_service.py" -> "auth_service")
        module_name = Path(file_path).stem
        service_dir = Path("test-scenarios/services")

        # Scan all service files for imports
        if service_dir.exists():
            for service_file in service_dir.rglob("*.py"):
                try:
                    with open(service_file) as f:
                        content = f.read()
                        # Check if this file imports the changed module
                        if f"import {module_name}" in content or f"from {module_name}" in content:
                            return True
                except:
                    continue

        return False
    except Exception:
        # If we can't determine dependencies, assume no impact
        return False


def _check_developer_context_freshness(developer_id: str, file_path: str) -> Tuple[str, Optional[str]]:
    """
    Check if a developer's context on this file is fresh using content hashing.

    Content-based approach (not time-based):
    1. Check if file content has changed since developer's snapshot
    2. Return "FRESH" if unchanged, "STALE" if changed
    3. Fall back to time-based only if content check unavailable

    Args:
        developer_id: The developer whose context to check
        file_path: The file they're working on

    Returns:
        Tuple of (freshness_status, detail_message) where status is:
        - "FRESH": File content unchanged, context is current
        - "STALE": File content changed, context is outdated
        - "UNVERIFIABLE": Cannot determine (syntax error, missing file, etc.)
    """
    try:
        # Use content hash to determine if file changed since developer's snapshot
        freshness = check_freshness(developer_id, file_path)

        if freshness == "CURRENT":
            return ("FRESH", "File content unchanged since developer's snapshot")
        elif freshness == "STALE_SOURCE":
            return ("STALE", "File content changed since developer's snapshot")
        else:
            # UNVERIFIABLE - fall back to time-based
            return ("UNVERIFIABLE", "Could not determine freshness (parse error or missing snapshot)")

    except Exception as e:
        # Any error in freshness checking - be conservative
        return ("UNVERIFIABLE", f"Freshness check error: {str(e)}")


def check_source_staleness(
    file_path: str,
    agent_id: str,
    read_time: float,
    dependency_symbols: Optional[list] = None,
    tenant_id: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Check if source file is stale using C1 (symbol-level hash-based detection).

    Args:
        file_path: Path to the file to check
        agent_id: Agent that originally read the file
        read_time: When the file was read (for comparison)
        dependency_symbols: Specific symbols to check (None = check whole file)
        tenant_id: Tenant context

    Returns:
        Tuple of (state, report) where state is CURRENT/STALE_SOURCE/UNVERIFIABLE
        and report contains details about what changed
    """
    try:
        # The base is what the developer saw when they read the file. Without a recorded
        # read there is nothing to compare against, so the state is unknown, not CURRENT.
        base_snap = get_base_snapshot(agent_id, file_path)
        if base_snap is None:
            return "UNVERIFIABLE", {
                "reason": "No read recorded for this developer on this file",
            }

        if base_snap.parse_error:
            # If we couldn't parse at read time, be conservative
            return "UNVERIFIABLE", {
                "reason": "Couldn't parse file at read time",
                "error": base_snap.parse_error
            }

        # Check current freshness
        state, report = StalenessChecker.check_file_staleness(
            base_snap,
            file_path,
            dependency_symbols=dependency_symbols
        )

        return state, report

    except Exception as e:
        # On any error, be conservative
        return "UNVERIFIABLE", {
            "reason": "Error checking staleness",
            "error": str(e)
        }


def check_for_conflicts(
    agent_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Tuple[RiskLevel, str, Optional[Dict[str, Any]]]:
    """
    Check for conflicts before code generation (tenant-isolated).

    Args:
        agent_id: Unique identifier for the agent
        file_path: Path to the file being modified
        intent: Description of what the agent intends to do
        region: Specific region (lines/function) being modified
        tenant_id: Tenant ID (company). Defaults to CLAUDE_TENANT_ID env var.
                  Conflict checks only see same-tenant work.

    Returns:
        Tuple of (RiskLevel, message, lock_info) where lock_info contains
        explicit lock state if MEDIUM/HIGH risk detected
    """
    # Resolve tenant context
    resolved_tenant = tenant_id or DEFAULT_TENANT_ID

    # CHECK 1: Detect breaking changes from intent
    breaking_change_detected = _detect_breaking_change_intent(intent)
    downstream_impact = _check_downstream_impact(file_path)

    if breaking_change_detected and downstream_impact:
        lock_manager = LockManager(tenant_id=resolved_tenant)
        lock_scope = "region" if region else "file"
        lock_info = lock_manager.acquire_lock(
            file_path=file_path,
            region=region,
            developer_id=agent_id,
            reason="BREAKING_CHANGE",
            scope=lock_scope,
        )
        return (
            RiskLevel.HIGH,
            f"BREAKING CHANGE: Function signature changed - downstream callers affected",
            lock_info
        )

    # CHECK 2: Detect if this file has unresolved upstream impacts (breaking changes in dependencies)
    try:
        impact_manager = ImpactAlertManager()
        unresolved_impacts = impact_manager.get_alerts_for_file(file_path)

        if unresolved_impacts:
            # This file has upstream dependencies with breaking changes
            affected_sources = [alert.get('source_file', 'unknown') for alert in unresolved_impacts]
            lock_manager = LockManager(tenant_id=resolved_tenant)
            lock_scope = "region" if region else "file"
            lock_info = lock_manager.acquire_lock(
                file_path=file_path,
                region=region,
                developer_id=agent_id,
                reason="UPSTREAM_BREAKING_CHANGE",
                scope=lock_scope,
            )
            return (
                RiskLevel.HIGH,
                f"HIGH RISK: Breaking change detected in upstream dependency ({', '.join(affected_sources)}). Coordinate with upstream developer before proceeding.",
                lock_info
            )
    except Exception:
        # If impact alert checking fails, continue to other checks
        pass

    # Get active entries for this tenant only (conflict checks are per-tenant)
    active_entries = get_active_entries(tenant_id=resolved_tenant)

    # Filter entries for the same file from other agents (same tenant only)
    # Keep only the LATEST entry per developer (handles duplicate log entries)
    same_file_entries_by_dev = {}
    for entry in active_entries:
        if entry.get('file_path') == file_path and entry.get('developer_id') != agent_id:
            dev_id = entry.get('developer_id')
            # Keep latest (highest timestamp) for this developer
            if dev_id not in same_file_entries_by_dev or entry.get('timestamp', 0) > same_file_entries_by_dev[dev_id].get('timestamp', 0):
                same_file_entries_by_dev[dev_id] = entry

    # A developer whose latest entry on this file is a completion has finished that work,
    # so it is no longer a conflict.
    same_file_entries = [
        e for e in same_file_entries_by_dev.values()
        if e.get('intent_category') != 'completion'
    ]

    # Optimization: If current developer holds the lock, exclude waiting developers from conflicts
    # Lock holders shouldn't see waiting developers as conflicts - they're already queued properly
    if same_file_entries:
        lock_manager = LockManager(tenant_id=resolved_tenant)
        lock_scope = "region" if region else "file"
        lock_key = lock_manager._make_lock_key(file_path, region, lock_scope)
        current_lock = lock_manager._get_current_lock(lock_key)

        if current_lock and current_lock.get('lock_holder') == agent_id:
            # Current developer holds the lock - exclude waiting developers
            same_file_entries = [
                entry for entry in same_file_entries
                if entry.get('lock_state') != 'WAITING'
            ]

    if not same_file_entries:
        return (RiskLevel.LOW, "No conflicting work detected. Safe to proceed.", None)

    # Check each conflicting entry using CONTENT-BASED freshness
    highest_risk = RiskLevel.LOW
    conflict_details = []

    for entry in same_file_entries:
        developer_id = entry.get('developer_id')

        # SEMANTIC STALENESS: Check if developer's context is actually fresh
        # (based on file content, not time)
        freshness_status, freshness_detail = _check_developer_context_freshness(developer_id, file_path)

        # Only treat as active conflict if context is fresh or unverifiable (conservative)
        # If context is provably stale, it's not a real conflict (they're out of date)
        # Use the risk classifier to assess this conflict
        assessment = classify_risk(
            current_developer=agent_id,
            current_file=file_path,
            current_intent=intent,
            current_region=region,
            other_entry=entry
        )

        # A stale context is still an active claim on the file. The developer has to
        # refresh, so it is at least a MEDIUM conflict, not "no conflict".
        if freshness_status == "STALE":
            if assessment.level == RiskLevel.LOW:
                assessment.level = RiskLevel.MEDIUM
            assessment.reason = (
                f"{assessment.reason}; {developer_id}'s context is stale "
                f"({freshness_detail}), refresh required"
            )

        # Track highest risk
        level_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        if level_order[assessment.level.value] > level_order[highest_risk.value]:
            highest_risk = assessment.level

        conflict_details.append({
            'agent': assessment.other_developer,
            'intent': assessment.other_intent,
            'region': assessment.other_region,
            'risk': assessment.level,
            'reason': assessment.reason,
            'context_freshness': freshness_status,
            'context_detail': freshness_detail
        })

    # Format message
    if not conflict_details:
        return (RiskLevel.LOW, "No conflicts. Safe to proceed.", None)

    conflict_info = "; ".join([
        f"{c['agent']} is {c['intent']}"
        for c in conflict_details
    ])

    # Acquire explicit lock for MEDIUM/HIGH risk
    lock_info = None
    if highest_risk in (RiskLevel.MEDIUM, RiskLevel.HIGH):
        lock_manager = LockManager(tenant_id=resolved_tenant)
        lock_reason = "HIGH_CONFLICT" if highest_risk == RiskLevel.HIGH else "MEDIUM_CONFLICT"
        lock_scope = "region" if region else "file"

        # First, give the lock to the EXISTING developer (who declared intent first)
        # Then queue the NEW developer (current agent_id)
        existing_dev = conflict_details[0]['agent'] if conflict_details else None

        if existing_dev:
            # Check if existing developer already holds the lock
            existing_lock = lock_manager._get_current_lock(
                lock_manager._make_lock_key(file_path, region, lock_scope)
            )

            # Only acquire lock if existing dev doesn't already hold it
            if not existing_lock or existing_lock.get('lock_holder') != existing_dev:
                lock_manager.acquire_lock(
                    file_path=file_path,
                    region=region,
                    developer_id=existing_dev,
                    reason=lock_reason,
                    scope=lock_scope,
                )

        # Now queue the current developer
        lock_info = lock_manager.acquire_lock(
            file_path=file_path,
            region=region,
            developer_id=agent_id,
            reason=lock_reason,
            scope=lock_scope,
        )

    if highest_risk == RiskLevel.HIGH:
        msg = f"HIGH RISK: {conflict_info}. This may cause a merge conflict. Coordinate with the other agent."
    elif highest_risk == RiskLevel.MEDIUM:
        stale = [d for d in conflict_details if d.get('context_freshness') == "STALE"]
        if stale:
            names = ", ".join(d['agent'] for d in stale)
            msg = (f"MEDIUM RISK: {conflict_info}. {names}'s context is stale: "
                   f"refresh required before editing this file.")
        else:
            msg = f"MEDIUM RISK: {conflict_info}. Overlapping regions detected. Proceed with caution."
    else:
        msg = f"LOW RISK: {conflict_info}. Different regions in same file. Safe to proceed."

    return (highest_risk, msg, lock_info)


def handle_conflict_response(
    risk_level: RiskLevel,
    auto_confirm: bool = False,
    tenant_id: Optional[str] = None
) -> bool:
    """
    Handle user/agent response to conflict risk (tenant-isolated).

    Args:
        risk_level: The risk level returned from check_for_conflicts
        auto_confirm: Whether to auto-confirm for MEDIUM risk (for demos)
        tenant_id: Tenant ID (company). For audit/logging purposes (not currently used).

    Returns:
        True if generation should proceed, False if blocked
    """
    if risk_level == RiskLevel.LOW:
        return True

    if risk_level == RiskLevel.MEDIUM:
        if auto_confirm:
            return True
        return True

    if risk_level == RiskLevel.HIGH:
        if auto_confirm:
            return True
        return False

    return True

#!/usr/bin/env python3
"""Pre-generation conflict checking API for Neo coordination layer (tenant-isolated)."""

import time
from typing import Tuple, Optional, Dict, Any
from core.activity_log import get_active_entries, DEFAULT_TENANT_ID, log_activity, read_log
from core.risk_classifier import RiskLevel, classify_risk
from core.lock_manager import LockManager
from core.symbol_hasher import StalenessChecker, snapshot_file, extract_dependencies

# Staleness detection constants
STALE_THRESHOLD_SECONDS = 0.3  # 300ms - context older than this is considered stale
MAX_REFRESH_ATTEMPTS = 2  # Retry up to 2 times when stale
# C1 (symbol-level staleness): Use 1000ms fallback per optimized_activity_log.py
SYMBOL_STALENESS_FALLBACK_MS = 1000


def _detect_and_refresh_stale_entries(entries: list, tenant_id: str) -> Tuple[list, Dict[str, Any]]:
    """
    Detect stale entries and automatically refresh them.

    When an entry is older than STALE_THRESHOLD_SECONDS, re-fetch it from the activity log.
    This ensures we have the latest state (e.g., "completed" status) even if the entry
    was logged a while ago.

    Args:
        entries: List of entries from get_active_entries()
        tenant_id: Tenant context for refresh

    Returns:
        Tuple of (refreshed_entries, staleness_report) where staleness_report is a dict
        with keys: stale_count, refresh_count, details
    """
    staleness_report = {
        'stale_count': 0,
        'refresh_count': 0,
        'refreshed_entries': {},
        'details': []
    }

    if not entries:
        return entries, staleness_report

    current_time = time.time()
    refreshed_entries = {}

    for entry in entries:
        entry_id = entry.get('developer_id')
        entry_age = current_time - entry.get('timestamp', current_time)

        # Check if entry is stale
        if entry_age > STALE_THRESHOLD_SECONDS:
            staleness_report['stale_count'] += 1

            # Try to refresh from activity log
            for attempt in range(MAX_REFRESH_ATTEMPTS):
                try:
                    all_entries = read_log(tenant_id=tenant_id)
                    for fresh_entry in all_entries:
                        if fresh_entry and fresh_entry.get('developer_id') == entry_id:
                            refreshed_entries[entry_id] = fresh_entry
                            staleness_report['refresh_count'] += 1

                            old_status = (entry.get('agent_metadata') or {}).get('status', 'unknown')
                            new_status = (fresh_entry.get('agent_metadata') or {}).get('status', 'unknown')

                            staleness_report['details'].append({
                                'developer_id': entry_id,
                                'entry_age_ms': entry_age * 1000,
                                'status_before': old_status,
                                'status_after': new_status,
                                'refresh_attempt': attempt + 1
                            })
                            break

                    if entry_id in refreshed_entries:
                        break  # Successfully refreshed, stop retrying
                except Exception as e:
                    staleness_report['details'].append({
                        'developer_id': entry_id,
                        'error': f"Refresh failed: {str(e)}",
                        'attempt': attempt + 1
                    })

    # Replace stale entries with refreshed ones
    result_entries = []
    for entry in entries:
        entry_id = entry.get('developer_id')
        if entry_id in refreshed_entries:
            result_entries.append(refreshed_entries[entry_id])
            staleness_report['refreshed_entries'][entry_id] = True
        else:
            result_entries.append(entry)

    return result_entries, staleness_report


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
        # Create a snapshot from the read time
        base_snap = snapshot_file(file_path, agent_id, read_time)

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

    # Get active entries for this tenant only (conflict checks are per-tenant)
    active_entries = get_active_entries(tenant_id=resolved_tenant)

    # STALENESS DETECTION & REFRESH: Automatically refresh stale entries
    # This ensures we detect the latest state even if log entries are slightly old
    active_entries, staleness_report = _detect_and_refresh_stale_entries(active_entries, resolved_tenant)

    # Log staleness events if any were found
    if staleness_report['stale_count'] > 0:
        log_activity(
            developer_id="_neo_system",
            file_path=file_path,
            intent=f"Staleness detection: {staleness_report['stale_count']} entries were stale, refreshed {staleness_report['refresh_count']}",
            region=region,
            intent_category="system",
            agent_metadata={
                "system_event": "staleness_detection",
                "stale_count": staleness_report['stale_count'],
                "refresh_count": staleness_report['refresh_count'],
                "details": staleness_report['details']
            }
        )

    # Filter entries for the same file from other agents (same tenant only)
    # Keep only the LATEST entry per developer (handles duplicate log entries)
    same_file_entries_by_dev = {}
    for entry in active_entries:
        if entry.get('file_path') == file_path and entry.get('developer_id') != agent_id:
            dev_id = entry.get('developer_id')
            # Keep latest (highest timestamp) for this developer
            if dev_id not in same_file_entries_by_dev or entry.get('timestamp', 0) > same_file_entries_by_dev[dev_id].get('timestamp', 0):
                same_file_entries_by_dev[dev_id] = entry

    same_file_entries = list(same_file_entries_by_dev.values())

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

    # Check each conflicting entry
    highest_risk = RiskLevel.LOW
    conflict_details = []

    for entry in same_file_entries:
        # Use the risk classifier to assess this conflict
        assessment = classify_risk(
            current_developer=agent_id,
            current_file=file_path,
            current_intent=intent,
            current_region=region,
            other_entry=entry
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
            'reason': assessment.reason
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

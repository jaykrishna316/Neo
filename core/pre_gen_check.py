#!/usr/bin/env python3
"""Pre-generation conflict checking API for Neo coordination layer."""

from typing import Tuple, Optional
from core.activity_log import get_active_entries
from core.risk_classifier import RiskLevel, classify_risk


def check_for_conflicts(
    agent_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
) -> Tuple[RiskLevel, str]:
    """
    Check for conflicts before code generation.

    Args:
        agent_id: Unique identifier for the agent
        file_path: Path to the file being modified
        intent: Description of what the agent intends to do
        region: Specific region (lines/function) being modified

    Returns:
        Tuple of (RiskLevel, message) indicating conflict risk and details
    """
    # Get all active entries from the activity log
    active_entries = get_active_entries()

    # Filter entries for the same file from other agents
    same_file_entries = [
        entry for entry in active_entries
        if entry.get('file_path') == file_path and entry.get('developer_id') != agent_id
    ]

    if not same_file_entries:
        return (RiskLevel.LOW, "No conflicting work detected. Safe to proceed.")

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
        return (RiskLevel.LOW, "No conflicts. Safe to proceed.")

    conflict_info = "; ".join([
        f"{c['agent']} is {c['intent']}"
        for c in conflict_details
    ])

    if highest_risk == RiskLevel.HIGH:
        msg = f"HIGH RISK: {conflict_info}. This may cause a merge conflict. Coordinate with the other agent."
    elif highest_risk == RiskLevel.MEDIUM:
        msg = f"MEDIUM RISK: {conflict_info}. Overlapping regions detected. Proceed with caution."
    else:
        msg = f"LOW RISK: {conflict_info}. Different regions in same file. Safe to proceed."

    return (highest_risk, msg)


def handle_conflict_response(
    risk_level: RiskLevel,
    auto_confirm: bool = False
) -> bool:
    """
    Handle user/agent response to conflict risk.

    Args:
        risk_level: The risk level returned from check_for_conflicts
        auto_confirm: Whether to auto-confirm for MEDIUM risk (for demos)

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

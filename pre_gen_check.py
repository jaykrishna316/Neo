#!/usr/bin/env python3
"""Pre-generation conflict check before code generation."""

from typing import Optional
import time

from activity_log import get_active_entries, log_entry_age_seconds
from risk_classifier import classify_risk, RiskLevel


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = seconds / 60
    return f"{int(minutes)}m"


def check_for_conflicts(
    developer_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
    expiry_minutes: int = 30,
) -> tuple[RiskLevel, Optional[str]]:
    """
    Check for conflicts before generation.

    Returns:
        (RiskLevel, message): The risk level and an optional message to display.
    """
    # Get active entries for this file
    active = get_active_entries(file_path, expiry_minutes)

    # Filter out entries from the same developer
    other_entries = [
        e for e in active if e["developer_id"] != developer_id
    ]

    if not other_entries:
        return RiskLevel.LOW, None

    # Assess risk from the first conflicting entry
    # (In a real system, we'd handle multiple conflicts more carefully)
    other_entry = other_entries[0]

    assessment = classify_risk(
        developer_id,
        file_path,
        intent,
        region,
        other_entry,
    )

    # Format message with age of conflicting work
    age = log_entry_age_seconds(other_entry)
    age_str = format_duration(age)

    message = (
        f"⚠️  {other_entry['developer_id']} is actively editing this file "
        f"(started {age_str} ago)\n"
        f"   Their intent: {other_entry['intent']}\n"
        f"   Region: {other_entry.get('region') or '(not specified)'}\n"
        f"   Reason: {assessment.reason}"
    )

    return assessment.level, message


def handle_conflict_response(risk_level: RiskLevel, message: str) -> bool:
    """
    Handle the conflict response based on risk level.

    Returns:
        True if generation should proceed, False if blocked.
    """
    if risk_level == RiskLevel.LOW:
        return True

    if risk_level == RiskLevel.MEDIUM:
        print("\n" + message)
        print("Generation will proceed. (Non-blocking warning)")
        return True

    if risk_level == RiskLevel.HIGH:
        print("\n🛑 CONFLICT DETECTED:")
        print(message)
        response = input("\nProceed with generation anyway? (y/n): ")
        return response.lower() in ("y", "yes")

    return True

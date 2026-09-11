#!/usr/bin/env python3
"""Risk classifier for detecting conflicting local changes."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import re


class RiskLevel(Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass
class ConflictAssessment:
    level: RiskLevel
    reason: str
    other_developer: str
    other_intent: str
    other_region: Optional[str]


def extract_line_range(region: str) -> Optional[tuple[int, int]]:
    """Extract line range from region string like 'lines 10-25'."""
    match = re.search(r'lines\s+(\d+)\s*-\s*(\d+)', region.lower())
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return None


def regions_overlap(region1: Optional[str], region2: Optional[str]) -> bool:
    """Check if two regions overlap (simple heuristic)."""
    if not region1 or not region2:
        return False

    # If both are line ranges, check actual overlap
    range1 = extract_line_range(region1)
    range2 = extract_line_range(region2)

    if range1 and range2:
        start1, end1 = range1
        start2, end2 = range2
        return not (end1 < start2 or end2 < start1)

    # If either is a function/class name, match if they're identical
    # or if one is clearly a child of the other
    if not range1 and not range2:
        # Both are symbolic references
        # Normalize: remove whitespace, compare base names
        name1 = region1.split(".")[-1].strip()
        name2 = region2.split(".")[-1].strip()
        return name1 == name2

    return False


def detect_signature_change(intent: str) -> bool:
    """Detect if intent explicitly mentions changing/removing a signature or API."""
    # High-confidence keywords that indicate structural/signature changes
    high_confidence = [
        "rename",
        "change signature",
        "remove",
        "delete",
        "deprecate",
        "move",
    ]

    lower_intent = intent.lower()

    # Strong signal: explicit rename, remove, delete
    if any(kw in lower_intent for kw in high_confidence):
        return True

    # "refactor" + API/signature mention is a signal
    if "refactor" in lower_intent:
        api_keywords = ["api", "signature", "interface", "contract"]
        return any(kw in lower_intent for kw in api_keywords)

    return False


def classify_risk(
    current_developer: str,
    current_file: str,
    current_intent: str,
    current_region: Optional[str],
    other_entry: dict,
) -> ConflictAssessment:
    """Classify risk of conflict between current and other developer's work."""

    other_developer = other_entry["developer_id"]
    other_file = other_entry["file_path"]
    other_intent = other_entry["intent"]
    other_region = other_entry.get("region")

    # Basic sanity: same developer, same file -> not a conflict
    if current_developer == other_developer:
        return ConflictAssessment(
            level=RiskLevel.LOW,
            reason="Same developer",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # Different file -> no conflict here
    if current_file != other_file:
        return ConflictAssessment(
            level=RiskLevel.LOW,
            reason="Different file",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # Check for region overlap
    overlaps = regions_overlap(current_region, other_region)

    # Check if other developer's change affects signature
    other_changes_signature = detect_signature_change(other_intent)

    # If regions don't overlap and no signature change detected -> LOW risk
    if not overlaps and not other_changes_signature:
        return ConflictAssessment(
            level=RiskLevel.LOW,
            reason="Non-overlapping regions, no signature changes detected",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # If signature change is explicit and regions overlap or interact -> HIGH risk
    if overlaps and other_changes_signature:
        return ConflictAssessment(
            level=RiskLevel.HIGH,
            reason="Overlapping region with potential signature/removal changes",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # Overlapping regions but no explicit signature change -> MEDIUM risk
    if overlaps:
        return ConflictAssessment(
            level=RiskLevel.MEDIUM,
            reason="Overlapping region detected",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # Signature change but no direct region overlap -> MEDIUM risk
    if other_changes_signature:
        return ConflictAssessment(
            level=RiskLevel.MEDIUM,
            reason="Signature/structural changes detected in same file",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # Default: some concern but not blocking
    return ConflictAssessment(
        level=RiskLevel.MEDIUM,
        reason="Active work on same file",
        other_developer=other_developer,
        other_intent=other_intent,
        other_region=other_region,
    )

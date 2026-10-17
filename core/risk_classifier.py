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
    layers_triggered: Optional[list] = None  # Which semantic layers detected conflict


@dataclass
class SemanticConflictLayer:
    """Result of evaluating one semantic layer."""
    name: str  # "syntactic", "scope", "semantic", "type", "data_flow"
    triggered: bool
    confidence: float  # 0.0 to 1.0
    reason: str


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

    # If either is a function/class name, match only if fully identical
    # Different classes with same method name don't overlap (A.validate vs B.validate)
    if not range1 and not range2:
        # Both are symbolic references - must be identical, not just same base name
        norm1 = region1.strip()
        norm2 = region2.strip()
        return norm1 == norm2

    return False


def detect_signature_change(intent: str) -> bool:
    """Detect if intent explicitly mentions changing/removing a signature or API."""
    lower_intent = intent.lower()

    # High-confidence keywords that indicate structural/signature changes
    strong_keywords = [
        "rename",
        "change signature",
        "remove ",  # space to avoid "remote"
        "delete",
        "deprecate",
    ]

    # Check strong keywords
    if any(kw in lower_intent for kw in strong_keywords):
        return True

    # "move" only counts if it's about moving functions/methods/APIs, not UI elements
    # Look for context: "move function", "move method", "move API", etc.
    if "move" in lower_intent:
        move_context = ["function", "method", "api", "parameter", "argument", "module", "class"]
        if any(ctx in lower_intent for ctx in move_context):
            return True

    # "refactor" + API/signature mention is a signal
    if "refactor" in lower_intent:
        api_keywords = ["api", "signature", "interface", "contract"]
        return any(kw in lower_intent for kw in api_keywords)

    return False


def evaluate_semantic_layers(
    current_developer: str,
    current_file: str,
    current_intent: str,
    current_region: Optional[str],
    other_entry: dict,
) -> list[SemanticConflictLayer]:
    """
    Evaluate conflict at multiple semantic layers.

    Layers (in order of escalation):
    1. Syntactic: Do they edit the same lines?
    2. Scope: Are they in the same function/class/method?
    3. Semantic: Do they modify related symbols?
    4. Type: Do changes break type contracts?
    5. Data flow: Do they affect same data paths?
    """

    other_developer = other_entry["developer_id"]
    other_intent = other_entry["intent"]
    other_region = other_entry.get("region")

    layers = []

    # Layer 1: Syntactic (line-level overlap)
    if current_region and other_region:
        overlap = regions_overlap(current_region, other_region)
        layers.append(SemanticConflictLayer(
            name="syntactic",
            triggered=overlap,
            confidence=0.95 if overlap else 0.05,
            reason="Same lines modified" if overlap else "Different lines"
        ))
    else:
        layers.append(SemanticConflictLayer(
            name="syntactic",
            triggered=not (current_region and other_region),
            confidence=0.9 if not (current_region and other_region) else 0.1,
            reason="File-level edit (no region)" if not (current_region and other_region) else "Both have regions"
        ))

    # Layer 2: Scope (function/class level)
    # If regions are specified and clear (not overlapping), scope conflict is low
    in_same_scope = regions_overlap(current_region, other_region) if (current_region and other_region) else True
    layers.append(SemanticConflictLayer(
        name="scope",
        triggered=in_same_scope,
        confidence=0.8 if in_same_scope else 0.2,
        reason="Same scope/function" if in_same_scope else "Different scopes"
    ))

    # Layer 3: Semantic (symbol-level coupling)
    signature_change = detect_signature_change(other_intent)
    layers.append(SemanticConflictLayer(
        name="semantic",
        triggered=signature_change,
        confidence=0.9 if signature_change else 0.3,
        reason="Signature/structural change detected" if signature_change else "Implementation change only"
    ))

    # Layer 4: Type safety (breaking type contracts)
    # Check if intent mentions type-related changes
    type_related = any(kw in other_intent.lower() for kw in
                      ["type", "return", "parameter", "signature", "interface", "protocol"])
    layers.append(SemanticConflictLayer(
        name="type",
        triggered=type_related and signature_change,
        confidence=0.85 if (type_related and signature_change) else 0.2,
        reason="Type system changes detected" if (type_related and signature_change) else "No type changes"
    ))

    # Layer 5: Data flow (shared data paths)
    # Heuristic: if both are modifying same file and at least one mentions data/state/mutation
    data_flow_keywords = ["data", "state", "cache", "db", "mutation", "update", "write"]
    mentions_data = any(kw in other_intent.lower() for kw in data_flow_keywords)
    same_file = (current_file == other_entry.get("file_path"))

    layers.append(SemanticConflictLayer(
        name="data_flow",
        triggered=same_file and mentions_data,
        confidence=0.8 if (same_file and mentions_data) else 0.1,
        reason="Shared data paths potentially affected" if (same_file and mentions_data) else "No shared data mutation"
    ))

    return layers


def classify_risk(
    current_developer: str,
    current_file: str,
    current_intent: str,
    current_region: Optional[str],
    other_entry: dict,
    use_staged_layers: bool = True,
) -> ConflictAssessment:
    """
    Classify risk of conflict between current and other developer's work.

    If use_staged_layers is True, returns staged semantic assessment with layer info.
    Otherwise, uses original heuristic-based classification.
    """

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
            layers_triggered=[],
        )

    # Different file -> no conflict here
    if current_file != other_file:
        return ConflictAssessment(
            level=RiskLevel.LOW,
            reason="Different file",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
            layers_triggered=[],
        )

    # Use staged semantic layers if requested
    if use_staged_layers:
        layers = evaluate_semantic_layers(
            current_developer, current_file, current_intent, current_region, other_entry
        )

        # Determine risk level from layers
        triggered_layers = [l.name for l in layers if l.triggered]

        if not triggered_layers:
            level = RiskLevel.LOW
            reason = "No conflict layers triggered"
        elif triggered_layers == ["syntactic"]:
            level = RiskLevel.LOW
            reason = "Syntactic layer only"
        elif "data_flow" in triggered_layers or "type" in triggered_layers:
            level = RiskLevel.HIGH
            reason = f"High-impact layers triggered: {', '.join(triggered_layers)}"
        elif "semantic" in triggered_layers or len(triggered_layers) > 2:
            level = RiskLevel.MEDIUM
            reason = f"Semantic/multiple layers triggered: {', '.join(triggered_layers)}"
        else:
            level = RiskLevel.MEDIUM
            reason = f"Mid-level conflict: {', '.join(triggered_layers)}"

        return ConflictAssessment(
            level=level,
            reason=reason,
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
            layers_triggered=triggered_layers,
        )

    # Original heuristic-based classification (fallback)
    # If either developer has no region specified, they're editing the entire file
    if current_region is None or other_region is None:
        return ConflictAssessment(
            level=RiskLevel.MEDIUM,
            reason="One or both developers editing entire file (no region specified)",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # Check for region overlap
    overlaps = regions_overlap(current_region, other_region)
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

    # If signature change is explicit and regions overlap -> HIGH risk
    if overlaps and other_changes_signature:
        return ConflictAssessment(
            level=RiskLevel.HIGH,
            reason="Overlapping region with potential signature/removal changes",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # Overlapping regions -> MEDIUM risk
    if overlaps:
        return ConflictAssessment(
            level=RiskLevel.MEDIUM,
            reason="Overlapping region detected",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # Signature change -> MEDIUM risk
    if other_changes_signature:
        return ConflictAssessment(
            level=RiskLevel.MEDIUM,
            reason="Signature/structural changes detected in same file",
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
        )

    # Default
    return ConflictAssessment(
        level=RiskLevel.MEDIUM,
        reason="Active work on same file",
        other_developer=other_developer,
        other_intent=other_intent,
        other_region=other_region,
    )

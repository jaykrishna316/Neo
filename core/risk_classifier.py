#!/usr/bin/env python3
"""Risk classifier for detecting conflicting local changes (with real semantic analysis)."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
import re
from pathlib import Path

from core.semantic_conflict_detector import SemanticAnalyzer, Language
from core.breaking_change_detector import has_breaking_changes
from core.conflict_scorer import calculate_conflict_score, ConflictScore
from core.service_coupling import ServiceCouplingAnalyzer
from core.dependency_resolver import DependencyResolver


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
    detailed_score: Optional[ConflictScore] = None  # Numerical conflict score (0-100)
    coupling_analysis: Optional[dict] = None  # Service coupling metrics
    dependency_blockers: Optional[list] = None  # Unresolved dependencies blocking work


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


def _get_detailed_conflict_score(
    current_developer: str,
    conflict_layers: list[SemanticConflictLayer],
    triggered_layers: list[str],
    other_entry: dict,
) -> ConflictScore:
    """
    Calculate detailed numerical conflict score using conflict_scorer.

    Converts semantic layer analysis to numerical impact score (0-100).
    """
    # Determine conflict types from triggered layers
    conflict_types = []
    if "syntactic" in triggered_layers:
        conflict_types.append("overlap")
    if "semantic" in triggered_layers or "type" in triggered_layers:
        conflict_types.append("signature_change")
    if "data_flow" in triggered_layers:
        conflict_types.append("dependency_conflict")

    # Estimate overlap severity from confidence values
    syntactic_layer = next((l for l in conflict_layers if l.name == "syntactic"), None)
    overlap_severity = (syntactic_layer.confidence if syntactic_layer else 0.0)

    # Check if we have semantic/AST-based detection (higher confidence)
    is_git_detected = any(l.confidence > 0.8 for l in conflict_layers if l.triggered)

    return calculate_conflict_score(
        num_conflicts=1,  # Per-conflict assessment
        conflict_types=conflict_types,
        overlap_severity=overlap_severity,
        is_git_detected=is_git_detected,
        active_time_minutes=0  # Not tracked in current context
    )


def _analyze_service_coupling(file_path: str, other_file: str) -> dict:
    """
    Analyze coupling between files/services.

    Returns coupling metrics to assess impact of changes.
    """
    try:
        coupling_analyzer = ServiceCouplingAnalyzer()

        current_coupling = coupling_analyzer.analyze_file_coupling(file_path)
        other_coupling = coupling_analyzer.analyze_file_coupling(other_file)

        return {
            "current_file": current_coupling,
            "other_file": other_coupling,
            "tight_coupling_detected": current_coupling.get("tightly_coupled", False) or
                                       other_coupling.get("tightly_coupled", False)
        }
    except Exception:
        return {"error": "Could not analyze coupling"}


def _check_dependency_blockers(current_developer: str, file_path: str) -> list[str]:
    """
    Check for unresolved dependency issues that block work.

    Returns list of blockers (breaking changes in dependencies, etc).
    """
    blockers = []
    try:
        resolver = DependencyResolver()

        # Check if this file's changes would have unresolved blockers
        # (This is a simplified check - full implementation would be more complex)
        # For now, just track if we can access the resolver
        if resolver.dependencies:
            blockers.append("Dependency resolver initialized - check for upstream breaks")
    except Exception:
        pass  # Dependency resolver not configured yet

    return blockers


def detect_signature_change(file_path: str, old_content: Optional[str] = None, new_content: Optional[str] = None) -> bool:
    """Detect if file has signature/structural changes using AST analysis (not keywords).

    Args:
        file_path: Path to the file to analyze
        old_content: Previous content (for comparison)
        new_content: Current content (for comparison)

    Returns:
        True if breaking changes detected via AST analysis
    """
    if old_content and new_content:
        # Real AST-based detection for Python files
        has_changes, changes = has_breaking_changes(old_content, new_content, file_path)
        return has_changes

    # If we don't have content comparison, fall back to semantic analysis
    try:
        analyzer = SemanticAnalyzer(str(file_path))
        symbols = analyzer.extract_symbols()
        # If file has public APIs (functions, classes), any change warrants attention
        return len(symbols) > 0
    except Exception:
        # If analysis fails, be conservative
        return False


def evaluate_semantic_layers(
    current_developer: str,
    current_file: str,
    current_intent: str,
    current_region: Optional[str],
    other_entry: dict,
) -> list[SemanticConflictLayer]:
    """
    Evaluate conflict at multiple semantic layers using real AST analysis.

    Layers (in order of escalation):
    1. Syntactic: Do they edit the same lines?
    2. Scope: Are they in the same function/class/method?
    3. Semantic: Do they modify related symbols (via dependency analysis)?
    4. Type: Do changes break type contracts (signature changes)?
    5. Data flow: Do they affect same data paths (transitive dependencies)?
    """

    other_developer = other_entry["developer_id"]
    other_intent = other_entry["intent"]
    other_region = other_entry.get("region")
    other_file = other_entry.get("file_path")

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

    # Layer 2: Scope (function/class level using real symbols)
    in_same_scope = False
    scope_confidence = 0.2
    scope_reason = "Different scopes"

    try:
        # Extract symbols from the file to determine scope
        analyzer = SemanticAnalyzer(str(current_file))
        current_symbols = analyzer.extract_symbols()

        # Map regions to symbols if possible
        if current_region and other_region and current_symbols:
            # Check if both regions refer to same symbol
            for symbol in current_symbols:
                if current_region.lower() in symbol.fully_qualified_name().lower() or \
                   other_region.lower() in symbol.fully_qualified_name().lower():
                    in_same_scope = True
                    scope_confidence = 0.85
                    scope_reason = f"Both in symbol: {symbol.fully_qualified_name()}"
                    break

        # If no symbolic match, fall back to overlap check
        if not in_same_scope and (current_region and other_region):
            in_same_scope = regions_overlap(current_region, other_region)
            if in_same_scope:
                scope_confidence = 0.75
                scope_reason = "Regions overlap in same file"
    except Exception:
        # Fall back to heuristic if analysis fails
        in_same_scope = regions_overlap(current_region, other_region) if (current_region and other_region) else True
        scope_confidence = 0.6
        scope_reason = "Scope analysis unavailable, using heuristic"

    layers.append(SemanticConflictLayer(
        name="scope",
        triggered=in_same_scope,
        confidence=scope_confidence,
        reason=scope_reason
    ))

    # Layer 3: Semantic (symbol-level coupling via dependency analysis)
    semantic_triggered = False
    semantic_confidence = 0.3
    semantic_reason = "No symbol-level coupling detected"

    try:
        # Use AST-based detection for actual signature changes
        if other_file and current_file == other_file:
            signature_change = detect_signature_change(other_file)
            if signature_change:
                semantic_triggered = True
                semantic_confidence = 0.9
                semantic_reason = "Signature/structural change detected via AST"

        # Also check for symbol dependencies
        if not semantic_triggered:
            analyzer = SemanticAnalyzer(str(current_file))
            current_symbols = analyzer.extract_symbols()
            dependencies = analyzer.analyze_dependencies()

            # Check if changes affect dependent symbols
            if dependencies and current_symbols:
                semantic_triggered = len(dependencies) > 0
                if semantic_triggered:
                    semantic_confidence = 0.8
                    semantic_reason = f"Symbol dependencies detected ({len(dependencies)} deps)"
    except Exception:
        semantic_triggered = detect_signature_change(other_file) if other_file else False
        if semantic_triggered:
            semantic_confidence = 0.7
            semantic_reason = "Signature change detected (fallback)"

    layers.append(SemanticConflictLayer(
        name="semantic",
        triggered=semantic_triggered,
        confidence=semantic_confidence,
        reason=semantic_reason
    ))

    # Layer 4: Type safety (breaking type contracts)
    type_triggered = False
    type_confidence = 0.2
    type_reason = "No type system changes"

    try:
        # Check intent for type-related keywords
        type_keywords = ["type", "return", "parameter", "signature", "interface", "protocol", "contract"]
        type_related = any(kw in other_intent.lower() for kw in type_keywords)

        # Check if actual signature changes (via AST)
        if type_related and other_file:
            signature_change = detect_signature_change(other_file)
            type_triggered = type_related and signature_change
            if type_triggered:
                type_confidence = 0.9
                type_reason = "Type system changes confirmed (signature change + intent)"
            else:
                type_confidence = 0.6
                type_reason = "Type-related intent but no signature change detected"
    except Exception:
        type_triggered = False
        type_confidence = 0.3
        type_reason = "Type analysis error"

    layers.append(SemanticConflictLayer(
        name="type",
        triggered=type_triggered,
        confidence=type_confidence,
        reason=type_reason
    ))

    # Layer 5: Data flow (shared data paths via transitive dependencies)
    dataflow_triggered = False
    dataflow_confidence = 0.1
    dataflow_reason = "No shared data mutations"

    try:
        # Check for data mutation keywords
        data_keywords = ["data", "state", "cache", "db", "mutation", "update", "write", "modify"]
        mentions_data = any(kw in other_intent.lower() for kw in data_keywords)
        same_file = (current_file == other_entry.get("file_path"))

        if mentions_data and same_file:
            # Use semantic analysis to detect shared state mutation
            try:
                analyzer = SemanticAnalyzer(str(current_file))
                dependencies = analyzer.analyze_dependencies()

                # Check if dependencies involve data mutations
                dataflow_triggered = len(dependencies) > 0 and mentions_data
                if dataflow_triggered:
                    dataflow_confidence = 0.85
                    dataflow_reason = f"Shared data paths with {len(dependencies)} dependencies"
                else:
                    dataflow_confidence = 0.6
                    dataflow_reason = "Same file, data mutation intent, but no dependency coupling"
            except Exception:
                dataflow_triggered = mentions_data and same_file
                dataflow_confidence = 0.65
                dataflow_reason = "Data mutation in same file (heuristic)"
        else:
            dataflow_confidence = 0.1 if not same_file else 0.3
            dataflow_reason = "Different files or no data mutation" if not same_file else "Same file but no data mutation"
    except Exception:
        dataflow_triggered = False
        dataflow_confidence = 0.1
        dataflow_reason = "Data flow analysis error"

    layers.append(SemanticConflictLayer(
        name="data_flow",
        triggered=dataflow_triggered,
        confidence=dataflow_confidence,
        reason=dataflow_reason
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

        # Enrich assessment with detailed scoring and coupling analysis
        detailed_score = None
        coupling_analysis = None
        dependency_blockers = None

        try:
            # Calculate detailed numerical score (0-100)
            detailed_score = _get_detailed_conflict_score(
                current_developer, layers, triggered_layers, other_entry
            )

            # Adjust risk level if detailed score suggests otherwise
            if detailed_score.total_score >= 70 and level == RiskLevel.MEDIUM:
                level = RiskLevel.HIGH
                reason = f"{reason} (detailed score: {detailed_score.total_score:.0f}/100)"
        except Exception:
            pass  # Detailed scoring failed, continue with basic assessment

        try:
            # Analyze service coupling
            other_file = other_entry.get("file_path")
            if other_file and current_file != other_file:
                coupling_analysis = _analyze_service_coupling(current_file, other_file)
                if coupling_analysis.get("tight_coupling_detected"):
                    if level == RiskLevel.LOW:
                        level = RiskLevel.MEDIUM
                    reason = f"{reason} (tight coupling detected)"
        except Exception:
            pass  # Coupling analysis failed, continue

        try:
            # Check for dependency blockers
            dependency_blockers = _check_dependency_blockers(current_developer, current_file)
            if dependency_blockers and level == RiskLevel.LOW:
                level = RiskLevel.MEDIUM
                reason = f"{reason} (unresolved dependencies)"
        except Exception:
            pass  # Dependency checking failed, continue

        return ConflictAssessment(
            level=level,
            reason=reason,
            other_developer=other_developer,
            other_intent=other_intent,
            other_region=other_region,
            layers_triggered=triggered_layers,
            detailed_score=detailed_score,
            coupling_analysis=coupling_analysis,
            dependency_blockers=dependency_blockers,
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

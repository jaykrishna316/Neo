"""Conflict scoring system - numerical impact assessment beyond LOW/MEDIUM/HIGH.

Provides granular scoring (0-100) for conflict impact, considering multiple factors.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ConflictScore:
    """Detailed conflict impact score."""
    total_score: float  # 0-100
    impact_factors: Dict[str, float]  # Individual factor scores
    risk_category: str  # LOW/MEDIUM/HIGH
    blockers: List[str]  # Critical issues
    warnings: List[str]  # Things to watch
    recommendations: List[str]  # Action items


def calculate_conflict_score(
    num_conflicts: int,
    conflict_types: List[str],
    developer_patterns: Dict[str, Dict] = None,
    overlap_severity: float = 0.5,  # 0-1, how much code overlaps
    is_git_detected: bool = False,
    active_time_minutes: int = 0,
) -> ConflictScore:
    """
    Calculate numerical conflict impact score (0-100).

    Args:
        num_conflicts: Number of conflicting developers/agents
        conflict_types: Types detected (overlap, signature_change, etc)
        developer_patterns: Developer speed patterns
        overlap_severity: How much of the code overlaps (0-1)
        is_git_detected: Whether git detected real function overlap
        active_time_minutes: How long conflict has been active

    Returns:
        ConflictScore with detailed breakdown
    """
    factors = {}
    blockers = []
    warnings = []
    recommendations = []

    # Factor 1: Number of conflicts (0-30 points)
    if num_conflicts == 0:
        factors["conflict_count"] = 0
    elif num_conflicts == 1:
        factors["conflict_count"] = 10
    elif num_conflicts <= 3:
        factors["conflict_count"] = 20
    else:
        factors["conflict_count"] = 30
        blockers.append(f"High conflict count: {num_conflicts} developers/agents")

    # Factor 2: Conflict type severity (0-25 points)
    type_score = 0
    if "overlap" in conflict_types:
        type_score += 8
    if "signature_change" in conflict_types:
        type_score += 12
        warnings.append("Signature changes detected - may break dependents")
    if "dependency_conflict" in conflict_types:
        type_score += 15
        blockers.append("Dependency conflict - requires coordination")

    factors["conflict_type"] = min(type_score, 25)

    # Factor 3: Git detection confidence (0-15 points)
    if is_git_detected:
        factors["git_detection"] = 15
        warnings.append("Real function-level conflict confirmed by git analysis")
    else:
        factors["git_detection"] = 5  # Heuristic-based, less confident

    # Factor 4: Code overlap severity (0-15 points)
    factors["overlap_severity"] = overlap_severity * 15
    if overlap_severity > 0.7:
        blockers.append("High code overlap - complex merge expected")

    # Factor 5: Time pressure (0-10 points)
    # Longer active conflicts increase pressure
    if active_time_minutes > 60:
        factors["time_pressure"] = 10
        warnings.append("Conflict active for >1 hour - coordinating becomes urgent")
    elif active_time_minutes > 30:
        factors["time_pressure"] = 5
    else:
        factors["time_pressure"] = 0

    # Factor 6: Developer velocity impact (0-5 points)
    # If waiting developers are fast, cost is higher
    velocity_score = 0
    if developer_patterns:
        fast_developers = sum(
            1 for dev, patterns in developer_patterns.items()
            if patterns.get("median", 0) < 600  # Less than 10 min
        )
        velocity_score = min(fast_developers, 5)

    factors["velocity_impact"] = velocity_score

    # Calculate total
    total_score = sum(factors.values())

    # Determine risk category (aligned with line/function-level detection)
    if total_score < 25:
        risk_category = "CAUTION"
        recommendations.append("Advisory: Same file detected, but different regions")
        recommendations.append("Proceed safely - ensure final merge testing")
    elif total_score < 70:
        risk_category = "MEDIUM"
        recommendations.append("Coordinate with conflicting developers before proceeding")
        recommendations.append("Have conflict resolution strategy ready")
    else:
        risk_category = "HIGH_RISK"
        recommendations.append("WAIT - actual line/function overlap detected")
        recommendations.append("Establish clear coordination protocol (wait/collaborate/wrap-up)")

    # Add specific recommendations based on factors
    if is_git_detected and factors["overlap_severity"] > 0.5:
        recommendations.append("Consider sequential execution - parallel merge risk is high")

    if num_conflicts > 2:
        recommendations.append("Establish change execution order with all parties")

    if "signature_change" in conflict_types:
        recommendations.append("Plan testing strategy for changed APIs")

    return ConflictScore(
        total_score=total_score,
        impact_factors=factors,
        risk_category=risk_category,
        blockers=blockers,
        warnings=warnings,
        recommendations=recommendations
    )


def score_to_risk_level(score: float) -> str:
    """Convert score to risk level with line/function-level detection thresholds.

    Neo uses refined conflict detection:
    - 0-25: CAUTION (same file, different regions/functions)
    - 26-70: MEDIUM RISK (partial overlap)
    - 70-100: HIGH_RISK (actual line/function overlap)
    """
    if score < 25:
        return "CAUTION"
    elif score < 70:
        return "MEDIUM"
    else:
        return "HIGH_RISK"


def compare_scores(score_a: ConflictScore, score_b: ConflictScore) -> Dict[str, Any]:
    """
    Compare two conflict scores.

    Returns:
        Comparison with delta and recommendation
    """
    delta = score_b.total_score - score_a.total_score

    return {
        "delta": delta,
        "direction": "worse" if delta > 0 else "better",
        "magnitude": abs(delta),
        "score_a": score_a.total_score,
        "score_b": score_b.total_score,
        "recommendation": (
            f"Risk increased by {delta:.1f} points" if delta > 0
            else f"Risk decreased by {abs(delta):.1f} points"
        )
    }


def get_score_breakdown_string(score: ConflictScore) -> str:
    """Generate human-readable score breakdown."""
    lines = [
        f"Conflict Impact Score: {score.total_score:.1f}/100 ({score.risk_category})",
        "",
        "Factor Breakdown:",
    ]

    for factor, value in score.impact_factors.items():
        factor_name = factor.replace("_", " ").title()
        lines.append(f"  • {factor_name}: {value:.1f}")

    if score.blockers:
        lines.append("")
        lines.append("Blockers:")
        for blocker in score.blockers:
            lines.append(f"  ❌ {blocker}")

    if score.warnings:
        lines.append("")
        lines.append("Warnings:")
        for warning in score.warnings:
            lines.append(f"  ⚠️  {warning}")

    if score.recommendations:
        lines.append("")
        lines.append("Recommendations:")
        for rec in score.recommendations:
            lines.append(f"  ✓ {rec}")

    return "\n".join(lines)


if __name__ == "__main__":
    print("Conflict Scoring System")
    print("=" * 60)

    # Example 1: Low risk
    print("\n1. Low Risk Scenario:")
    score = calculate_conflict_score(
        num_conflicts=1,
        conflict_types=["overlap"],
        overlap_severity=0.2,
        is_git_detected=False,
        active_time_minutes=5
    )
    print(get_score_breakdown_string(score))

    # Example 2: Medium risk
    print("\n\n2. Medium Risk Scenario:")
    score = calculate_conflict_score(
        num_conflicts=2,
        conflict_types=["overlap", "signature_change"],
        overlap_severity=0.5,
        is_git_detected=True,
        active_time_minutes=20
    )
    print(get_score_breakdown_string(score))

    # Example 3: High risk
    print("\n\n3. High Risk Scenario:")
    score = calculate_conflict_score(
        num_conflicts=4,
        conflict_types=["overlap", "signature_change", "dependency_conflict"],
        overlap_severity=0.8,
        is_git_detected=True,
        active_time_minutes=90
    )
    print(get_score_breakdown_string(score))

    # Example 4: Comparison
    print("\n\n4. Score Comparison:")
    score_before = calculate_conflict_score(
        num_conflicts=3,
        conflict_types=["overlap"],
        overlap_severity=0.6,
        is_git_detected=True,
        active_time_minutes=10
    )

    score_after = calculate_conflict_score(
        num_conflicts=2,
        conflict_types=["overlap"],
        overlap_severity=0.4,
        is_git_detected=True,
        active_time_minutes=15
    )

    comparison = compare_scores(score_before, score_after)
    print(f"Before: {score_before.total_score:.1f}")
    print(f"After: {score_after.total_score:.1f}")
    print(f"Change: {comparison['recommendation']}")

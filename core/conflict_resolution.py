"""Conflict resolution suggestions and merge strategies.

Recommends optimal resolution paths when conflicts are detected.
"""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass


class MergeStrategy(Enum):
    """Strategies for resolving conflicts."""
    SEQUENTIAL = "sequential"  # One developer finishes, then next
    PARALLEL = "parallel"      # Changes don't overlap, can happen together
    REBASE = "rebase"         # Reorder commits for clean history
    CHERRY_PICK = "cherry_pick"  # Apply specific commits
    MANUAL_MERGE = "manual_merge"  # Requires human coordination


@dataclass
class ResolutionSuggestion:
    """Suggested approach to resolve a conflict."""
    strategy: MergeStrategy
    description: str
    steps: List[str]
    estimated_time_minutes: int
    risk_level: str  # LOW/MEDIUM/HIGH
    confidence_score: float  # 0.0-1.0
    reasoning: str


def suggest_resolution(
    conflicting_developers: List[Dict[str, Any]],
    file_path: str,
    developer_patterns: Dict[str, Dict] = None,
) -> ResolutionSuggestion:
    """
    Suggest optimal resolution strategy for detected conflicts.

    Args:
        conflicting_developers: List of developers with conflicting changes
        file_path: File being modified
        developer_patterns: Developer completion time patterns

    Returns:
        ResolutionSuggestion with recommended approach
    """
    if not conflicting_developers:
        return ResolutionSuggestion(
            strategy=MergeStrategy.PARALLEL,
            description="No conflicts - changes can proceed in parallel",
            steps=["Proceed with generation"],
            estimated_time_minutes=0,
            risk_level="LOW",
            confidence_score=1.0,
            reasoning="No conflicting developers detected"
        )

    num_conflicts = len(conflicting_developers)

    # Strategy 1: Sequential (one person, then next)
    if num_conflicts == 1:
        dev = conflicting_developers[0]
        est_time = 15  # Default

        if developer_patterns and dev["developer_id"] in developer_patterns:
            patterns = developer_patterns[dev["developer_id"]]
            est_time = patterns.get("median", 15)

        return ResolutionSuggestion(
            strategy=MergeStrategy.SEQUENTIAL,
            description=f"Wait for {dev['developer_id']} to finish, then proceed",
            steps=[
                f"1. Notify {dev['developer_id']} of your intent",
                f"2. Wait {est_time} minutes for completion",
                "3. Pull latest changes",
                "4. Proceed with generation on updated base"
            ],
            estimated_time_minutes=est_time + 5,
            risk_level="LOW",
            confidence_score=0.95,
            reasoning="Single conflict is straightforward - sequential execution is safest"
        )

    # Strategy 2: Coordinate execution order
    if num_conflicts <= 3:
        ordered_devs = sorted(
            conflicting_developers,
            key=lambda d: d.get("timestamp", 0)
        )

        step_list = ["1. Coordinate with conflicting developers:"]
        total_time = 0

        for i, dev in enumerate(ordered_devs, 1):
            est = 15
            if developer_patterns and dev["developer_id"] in developer_patterns:
                patterns = developer_patterns[dev["developer_id"]]
                est = patterns.get("median", 15)

            step_list.append(f"   {i}. {dev['developer_id']}: {est}m ({dev['intent']})")
            total_time += est

        step_list.append("2. Execute in order: A → B → C")
        step_list.append("3. Each pulls before starting")

        return ResolutionSuggestion(
            strategy=MergeStrategy.SEQUENTIAL,
            description="Establish execution order with all conflicting developers",
            steps=step_list,
            estimated_time_minutes=total_time + 10,
            risk_level="MEDIUM",
            confidence_score=0.85,
            reasoning=f"Multiple conflicts ({num_conflicts}) need coordination - sequential with ordering minimizes merge issues"
        )

    # Strategy 3: Parallel if possible
    return ResolutionSuggestion(
        strategy=MergeStrategy.PARALLEL,
        description="Changes may not actually overlap - coordinate git strategies",
        steps=[
            "1. Extract exact functions each developer is modifying",
            "2. If no overlap at function level: proceed in parallel",
            "3. Each developer rebases before pushing",
            "4. Coordinate merge order"
        ],
        estimated_time_minutes=20,
        risk_level="MEDIUM",
        confidence_score=0.70,
        reasoning=f"High conflict count ({num_conflicts}) - check actual function-level overlap before committing to sequential"
    )


def get_merge_compatibility(
    dev_a_functions: set,
    dev_b_functions: set,
    file_path: str,
) -> Tuple[bool, str, float]:
    """
    Check if two sets of changes can merge cleanly.

    Args:
        dev_a_functions: Functions modified by developer A
        dev_b_functions: Functions modified by developer B
        file_path: File being modified

    Returns:
        (can_merge, reason, confidence)
    """
    overlap = dev_a_functions.intersection(dev_b_functions)

    if not overlap:
        return (
            True,
            "No function-level overlap - can merge cleanly",
            0.95
        )

    if len(overlap) == 1:
        func = list(overlap)[0]
        return (
            False,
            f"Both modifying {func}() - manual merge needed",
            0.90
        )

    return (
        False,
        f"Overlap in {len(overlap)} functions - complex merge required",
        0.80
    )


def estimate_resolution_effort(
    num_conflicts: int,
    num_files: int,
    conflict_types: List[str],
) -> Dict[str, Any]:
    """
    Estimate effort to resolve conflicts.

    Args:
        num_conflicts: Number of conflicting developers
        num_files: Number of files involved
        conflict_types: Types of conflicts (overlap, signature, etc)

    Returns:
        Effort estimation
    """
    base_time = 5  # minutes

    # Add time per conflict
    base_time += (num_conflicts - 1) * 10

    # Add time per file
    base_time += num_files * 3

    # Increase for signature changes
    if "signature_change" in conflict_types:
        base_time += 15

    # Increase for complex patterns
    if len(conflict_types) > 2:
        base_time += 10

    return {
        "estimated_minutes": base_time,
        "complexity": "simple" if base_time < 15 else "medium" if base_time < 30 else "complex",
        "requires_coordination": num_conflicts > 1,
        "requires_testing": "signature_change" in conflict_types,
        "can_parallelize": num_conflicts <= 1 or num_files > num_conflicts
    }


if __name__ == "__main__":
    print("Conflict Resolution Module")
    print("=" * 60)

    # Example 1: Single conflict
    print("\n1. Single Developer Conflict:")
    devs = [{"developer_id": "alice", "intent": "Refactor auth", "timestamp": 0}]
    suggestion = suggest_resolution(devs, "src/auth.py")
    print(f"   Strategy: {suggestion.strategy.value}")
    print(f"   Risk: {suggestion.risk_level}")
    print(f"   Time: ~{suggestion.estimated_time_minutes} min")
    print(f"   Reasoning: {suggestion.reasoning}")

    # Example 2: Multiple conflicts
    print("\n2. Multiple Developer Conflicts:")
    devs = [
        {"developer_id": "alice", "intent": "Refactor", "timestamp": 0},
        {"developer_id": "bob", "intent": "Add feature", "timestamp": 1},
        {"developer_id": "charlie", "intent": "Fix bug", "timestamp": 2}
    ]
    suggestion = suggest_resolution(devs, "src/auth.py")
    print(f"   Strategy: {suggestion.strategy.value}")
    print(f"   Risk: {suggestion.risk_level}")
    print(f"   Time: ~{suggestion.estimated_time_minutes} min")

    # Example 3: Effort estimation
    print("\n3. Effort Estimation:")
    effort = estimate_resolution_effort(
        num_conflicts=2,
        num_files=3,
        conflict_types=["overlap", "signature_change"]
    )
    print(f"   Complexity: {effort['complexity']}")
    print(f"   Time: ~{effort['estimated_minutes']} min")
    print(f"   Requires coordination: {effort['requires_coordination']}")

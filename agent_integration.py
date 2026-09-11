"""Agent integration for pre-generation conflict detection and guidance.

Provides hooks for Claude, Devin, and other AI agents to:
1. Check for conflicts before code generation
2. Receive conflict guidance in prompts
3. Log outcomes for learning
4. Coordinate with other agents/developers
"""

import json
import time
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from enum import Enum
from activity_log import read_log, log_activity, get_active_entries
from risk_classifier import classify_risk


class RecommendedAction(Enum):
    """Recommended action for agent when conflict detected."""
    PROCEED_SILENT = "proceed_silently"
    WARN_AND_PROCEED = "warn_and_proceed"
    REQUEST_CONFIRMATION = "request_confirmation"
    WAIT_FOR_RESOLUTION = "wait_for_resolution"
    COORDINATE_WITH_DEV = "coordinate_with_dev"


@dataclass
class ConflictingDeveloper:
    """Information about developer with conflicting changes."""
    developer_id: str
    file_path: str
    intent: str
    region: str
    timestamp: float
    time_ago: str
    risk_level: str = "MEDIUM"


@dataclass
class EnhancedConflictReport:
    """Enhanced conflict report for agent guidance."""
    risk_level: str
    reason: str
    has_conflicts: bool
    conflicting_developers: List[ConflictingDeveloper]
    overlapping_regions: List[str]
    dependency_conflicts: List[str]
    signature_changes: List[str]
    recommended_action: str
    estimated_wait_time: Optional[int]
    agent_guidance: str
    confidence_score: float


def format_duration(seconds: int) -> str:
    """Convert seconds to human-readable format."""
    if seconds < 60:
        return f"{seconds}s ago"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes}m ago"
    else:
        hours = seconds // 3600
        return f"{hours}h ago"


def check_conflicts_for_agent(
    agent_id: str,
    file_path: str,
    intent: str,
    region: str,
    model: Optional[str] = None
) -> EnhancedConflictReport:
    """
    Pre-generation hook: Check for conflicts affecting agent.

    Args:
        agent_id: Unique agent identifier (e.g., "claude-agent-1")
        file_path: File path agent wants to modify
        intent: What agent intends to do (e.g., "Add type hints")
        region: Code region (e.g., "login_user (lines 20-40)")
        model: Model name for logging (e.g., "claude-opus-5")

    Returns:
        EnhancedConflictReport with risk assessment and guidance
    """
    log_activity(agent_id, file_path, intent, region, agent_metadata={
        "model": model,
        "check_type": "pre_generation",
        "timestamp": time.time()
    })

    entries = get_active_entries()
    conflicts = []
    overlapping_regions = []
    dependency_conflicts = []
    signature_changes = []

    for entry in entries:
        if entry["file_path"] != file_path or entry["developer_id"] == agent_id:
            continue

        assessment = classify_risk(agent_id, file_path, intent, region, entry)
        if assessment.level.value != "LOW":
            dev = ConflictingDeveloper(
                developer_id=entry["developer_id"],
                file_path=entry["file_path"],
                intent=entry["intent"],
                region=entry.get("region", ""),
                timestamp=entry["timestamp"],
                time_ago=format_duration(int(time.time() - entry["timestamp"])),
                risk_level=assessment.level.value
            )
            conflicts.append(dev)

            if entry.get("region"):
                overlapping_regions.append(entry.get("region"))

            if "rename" in assessment.reason.lower() or "signature" in assessment.reason.lower():
                signature_changes.append(assessment.reason)

    if not conflicts:
        return EnhancedConflictReport(
            risk_level="LOW",
            reason="No conflicts detected",
            has_conflicts=False,
            conflicting_developers=[],
            overlapping_regions=[],
            dependency_conflicts=[],
            signature_changes=[],
            recommended_action=RecommendedAction.PROCEED_SILENT.value,
            estimated_wait_time=None,
            agent_guidance="Safe to proceed with generation.",
            confidence_score=0.95
        )

    risk_levels = [c.risk_level for c in conflicts]
    max_risk = max(risk_levels) if risk_levels else "LOW"

    if max_risk == "HIGH":
        action = RecommendedAction.WAIT_FOR_RESOLUTION.value
        wait_time = 300
        guidance = (
            f"HIGH risk conflict detected: {conflicts[0].developer_id} is editing "
            f"{conflicts[0].intent}. Wait ~5 minutes before retrying, or coordinate directly."
        )
    elif max_risk == "MEDIUM":
        action = RecommendedAction.WARN_AND_PROCEED.value
        wait_time = None
        guidance = (
            f"MEDIUM risk: {conflicts[0].developer_id} detected in overlapping region. "
            f"Proceed with caution and consider coordinating changes."
        )
    else:
        action = RecommendedAction.PROCEED_SILENT.value
        wait_time = None
        guidance = "Conflicts are low risk. Safe to proceed."

    return EnhancedConflictReport(
        risk_level=max_risk,
        reason=f"Conflicts with {len(conflicts)} developer(s)",
        has_conflicts=True,
        conflicting_developers=conflicts,
        overlapping_regions=list(set(overlapping_regions)),
        dependency_conflicts=dependency_conflicts,
        signature_changes=list(set(signature_changes)),
        recommended_action=action,
        estimated_wait_time=wait_time,
        agent_guidance=guidance,
        confidence_score=0.85 if max_risk == "MEDIUM" else 0.95
    )


def format_conflict_guidance_for_prompt(report: EnhancedConflictReport) -> str:
    """
    Format conflict report as prompt context for agent.

    Returns markdown-formatted guidance to inject into agent prompt.
    """
    if not report.has_conflicts:
        return (
            "## Pre-Generation Check\n"
            "✓ No conflicts detected. Safe to proceed with generation.\n"
        )

    guidance_lines = [
        f"## ⚠️  Pre-Generation Conflict Check ({report.risk_level} Risk)",
        f"\n**Status:** {report.reason}",
        f"**Recommendation:** {report.recommended_action.replace('_', ' ').title()}",
    ]

    if report.conflicting_developers:
        guidance_lines.append("\n### Conflicting Developers:")
        for dev in report.conflicting_developers:
            guidance_lines.append(
                f"- **{dev.developer_id}** ({dev.time_ago}): {dev.intent}\n"
                f"  Region: `{dev.region}`"
            )

    if report.overlapping_regions:
        guidance_lines.append("\n### Overlapping Regions:")
        for region in report.overlapping_regions:
            guidance_lines.append(f"- {region}")

    if report.signature_changes:
        guidance_lines.append("\n### Detected Signature Changes:")
        for change in report.signature_changes:
            guidance_lines.append(f"- {change}")

    guidance_lines.append(f"\n**Agent Guidance:** {report.agent_guidance}")

    if report.estimated_wait_time:
        guidance_lines.append(
            f"**Estimated Wait Time:** ~{report.estimated_wait_time // 60} minutes"
        )

    guidance_lines.append(f"\n**Confidence:** {int(report.confidence_score * 100)}%")

    return "\n".join(guidance_lines)


def log_agent_generation_outcome(
    agent_id: str,
    file_path: str,
    status: str,
    tokens_used: int,
    conflict_report: Optional[EnhancedConflictReport] = None,
    success: bool = True
) -> None:
    """
    Log the outcome of agent generation.

    Args:
        agent_id: Agent identifier
        file_path: File that was generated
        status: Generation status (success/failed/cancelled)
        tokens_used: Tokens consumed by generation
        conflict_report: Original conflict report (if any)
        success: Whether generation succeeded
    """
    outcome = {
        "agent_id": agent_id,
        "file_path": file_path,
        "status": status,
        "tokens_used": tokens_used,
        "success": success,
        "timestamp": time.time(),
        "had_conflicts": conflict_report.has_conflicts if conflict_report else False,
        "risk_level": conflict_report.risk_level if conflict_report else "NONE"
    }

    log_file = ".devsync/agent-outcomes.jsonl"
    with open(log_file, "a") as f:
        f.write(json.dumps(outcome) + "\n")


def should_proceed_with_generation(report: EnhancedConflictReport) -> bool:
    """Determine if agent should proceed with generation based on report."""
    return report.recommended_action != RecommendedAction.WAIT_FOR_RESOLUTION.value


if __name__ == "__main__":
    print("Agent Integration Module")
    print("=" * 50)

    print("\n1. Checking for conflicts (agent perspective)...")
    report = check_conflicts_for_agent(
        agent_id="claude-agent-1",
        file_path="src/auth.py",
        intent="Add type hints to login function",
        region="login_user (lines 20-40)",
        model="claude-opus-5"
    )

    print(f"\nRisk Level: {report.risk_level}")
    print(f"Has Conflicts: {report.has_conflicts}")
    print(f"Recommended Action: {report.recommended_action}")
    print(f"Guidance: {report.agent_guidance}")

    print("\n2. Prompt Injection Format:")
    prompt_context = format_conflict_guidance_for_prompt(report)
    print(prompt_context)

    print("\n3. Should proceed? ", should_proceed_with_generation(report))

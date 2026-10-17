"""
Unified pre-generation check combining conflict detection with impact alerts
Runs both checks without interfering with staleness detection or context refresh
"""

from typing import Dict, Tuple, List, Any, Optional
from core.pre_gen_check import check_for_conflicts
from core.impact_alerts import ImpactAlertManager
from core.risk_classifier import RiskLevel


def check_all_pre_gen_risks(
    file_path: str,
    agent_id: str,
    intent: str,
    region: Optional[str] = None,
    tenant_id: Optional[str] = None,
    repo_path: str = "."
) -> Dict[str, Any]:
    """
    Unified pre-generation check: conflicts + impact alerts

    This function ensures developers see:
    1. Conflicts: Other developers already working on this file
    2. Impact Alerts: Upstream changes affecting this file that haven't been addressed

    Both checks run independently and results are combined.
    Staleness detection and context refresh are unaffected.

    Args:
        file_path: File developer wants to edit
        agent_id: Developer's agent ID
        intent: What developer intends to do (read/write/refactor)
        region: Optional specific region in file
        tenant_id: Tenant context
        repo_path: Repository path

    Returns:
        {
            "status": "clear" | "conflicts" | "impacts" | "conflicts_and_impacts",
            "file": file_path,
            "safe_to_proceed": boolean,
            "conflicts": {
                "detected": boolean,
                "risk_level": RiskLevel,
                "message": string,
                "details": list
            },
            "impacts": {
                "detected": boolean,
                "alert_count": integer,
                "summary": string,
                "alerts": list
            },
            "recommendations": list
        }
    """

    # Initialize impact alert manager
    impact_manager = ImpactAlertManager(repo_path)

    # 1. Run conflict detection (unchanged from existing system)
    conflict_risk, conflict_msg, conflict_details = check_for_conflicts(
        file_path=file_path,
        agent_id=agent_id,
        intent=intent,
        region=region,
        tenant_id=tenant_id
    )

    has_conflicts = conflict_risk != RiskLevel.LOW

    # 2. Run impact alert check (independent of conflict check)
    impact_result = impact_manager.check_impacts_on_file(file_path)
    has_impacts = impact_result.get("has_impacts", False)
    impact_alerts = impact_result.get("alerts", [])

    # 3. Combine results
    if has_conflicts and has_impacts:
        status = "conflicts_and_impacts"
        safe = False
    elif has_conflicts:
        status = "conflicts"
        safe = False
    elif has_impacts:
        status = "impacts"
        safe = False
    else:
        status = "clear"
        safe = True

    # Generate recommendations
    recommendations = []
    if has_conflicts:
        recommendations.append("⚠️ Coordinate with other developers already editing this file")
    if has_impacts:
        recommendations.append("📋 Review unresolved impacts from upstream changes")
    if safe:
        recommendations.append("✅ Safe to proceed - no conflicts or impacts detected")

    # Generate impact summary
    impact_summary = ""
    if has_impacts:
        impact_summary = impact_manager.get_alert_summary(file_path)

    return {
        "status": status,
        "file": file_path,
        "safe_to_proceed": safe,
        "conflicts": {
            "detected": has_conflicts,
            "risk_level": conflict_risk.value if conflict_risk else "NONE",
            "message": conflict_msg,
            "details": conflict_details
        },
        "impacts": {
            "detected": has_impacts,
            "alert_count": len(impact_alerts),
            "alerts": impact_alerts,
            "summary": impact_summary
        },
        "recommendations": recommendations,
        "display_message": _format_display_message(
            status, conflict_msg, impact_summary, recommendations
        )
    }


def _format_display_message(status: str,
                            conflict_msg: str,
                            impact_summary: str,
                            recommendations: List[str]) -> str:
    """Format unified check result for developer display"""

    lines = []
    lines.append("=" * 80)

    if status == "clear":
        lines.append("✅ PRE-GENERATION CHECK: ALL CLEAR")
        lines.append("=" * 80)
        lines.append("")
        lines.append("No conflicts or impact alerts detected.")
        lines.append("Safe to proceed with your changes.")

    elif status == "conflicts":
        lines.append("⚠️ PRE-GENERATION CHECK: CONFLICTS DETECTED")
        lines.append("=" * 80)
        lines.append("")
        lines.append("CONFLICTS:")
        lines.append(conflict_msg)

    elif status == "impacts":
        lines.append("⚠️ PRE-GENERATION CHECK: IMPACT ALERTS")
        lines.append("=" * 80)
        lines.append("")
        lines.append("UNRESOLVED IMPACTS FROM UPSTREAM CHANGES:")
        lines.append(impact_summary)

    else:  # conflicts_and_impacts
        lines.append("🚫 PRE-GENERATION CHECK: CONFLICTS AND IMPACTS")
        lines.append("=" * 80)
        lines.append("")
        lines.append("CONFLICTS:")
        lines.append(conflict_msg)
        lines.append("")
        lines.append("IMPACTS:")
        lines.append(impact_summary)

    lines.append("")
    lines.append("RECOMMENDATIONS:")
    for rec in recommendations:
        lines.append(f"  • {rec}")

    lines.append("=" * 80)

    return "\n".join(lines)

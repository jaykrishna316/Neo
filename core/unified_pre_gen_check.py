"""
Unified pre-generation check combining conflict detection with impact alerts
Runs both checks without interfering with staleness detection or context refresh
"""

from typing import Dict, Tuple, List, Any, Optional
from core.pre_gen_check import check_for_conflicts
from core.impact_alerts import ImpactAlertManager
from core.risk_classifier import RiskLevel
from core.blast_radius import BlastRadiusCalculator, BlastRadiusReport
from core.coupling_metrics import CouplingMetricsCollector, record_developer_change


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


def calculate_blast_radius(
    file_path: str,
    change_type: str = "general",
    dependencies: Optional[Dict[str, List[str]]] = None,
    repo_path: str = "."
) -> Dict[str, Any]:
    """
    Calculate blast radius for a file change.

    Shows estimated impact scope and cost in dev-hours and tokens.

    Args:
        file_path: File that changed
        change_type: Type of change ("signature", "logic", "refactor", "general")
        dependencies: Optional dependency map (file -> [dependents])
        repo_path: Repository path

    Returns:
        {
            "success": boolean,
            "blast_radius": BlastRadiusReport dict,
            "summary": formatted string,
            "easy_count": int,
            "medium_count": int,
            "hard_count": int,
            "total_hours": float,
            "total_token_cost": int
        }
    """
    try:
        calculator = BlastRadiusCalculator(dependencies or {})
        report = calculator.calculate(file_path, change_type)

        return {
            "success": True,
            "blast_radius": report.to_dict(),
            "summary": calculator.format_report(report),
            "easy_count": report.easy_fixes,
            "medium_count": report.medium_fixes,
            "hard_count": report.hard_fixes,
            "total_hours": report.total_estimated_hours,
            "total_token_cost": report.total_token_cost
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_coupling_trends(
    window_days: int = 90,
    repo_path: str = "."
) -> Dict[str, Any]:
    """
    Get coupling trends between services.

    Shows which services are becoming increasingly coupled (regressions),
    and which are stable/decreasing.

    Args:
        window_days: Analysis window (default 90 days)
        repo_path: Repository path

    Returns:
        {
            "success": boolean,
            "trends": list of trend dicts,
            "summary": formatted string,
            "regressions": list of regression trends,
            "increasing": list of increasing coupling trends
        }
    """
    try:
        collector = CouplingMetricsCollector(f"{repo_path}/.devsync/coupling")
        trends = collector.compute_trends(window_days)

        regressions = [t for t in trends if t.regression]
        increasing = [t for t in trends if t.direction == "increasing" and t.velocity > 0.01]

        return {
            "success": True,
            "trends": [
                {
                    "service_a": t.service_a,
                    "service_b": t.service_b,
                    "current_score": round(t.current_score, 2),
                    "previous_score": round(t.previous_score, 2),
                    "velocity": round(t.velocity, 3),
                    "direction": t.direction,
                    "age_days": t.age_days,
                    "regression": t.regression
                }
                for t in trends
            ],
            "summary": collector.format_trends_report(trends),
            "regressions": len(regressions),
            "increasing": len(increasing)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def record_change_set(
    changed_files: List[str],
    developer_id: str,
    intent: str,
    repo_path: str = "."
) -> Dict[str, Any]:
    """
    Record a set of files changed together.

    Used to build coupling metrics over time.

    Args:
        changed_files: List of files modified in this change
        developer_id: Developer who made the change
        intent: Intent of the change
        repo_path: Repository path

    Returns:
        {"success": boolean, "message": string}
    """
    try:
        record_developer_change(
            changed_files,
            developer_id,
            intent,
            f"{repo_path}/.devsync/coupling"
        )
        return {
            "success": True,
            "message": f"Recorded {len(changed_files)} files for coupling analysis"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

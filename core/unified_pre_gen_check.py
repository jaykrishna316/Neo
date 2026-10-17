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
from core.entropy_coupling import analyze_entropy_coupling


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


def analyze_entropy_couplings(
    history_file: str = ".devsync/coupling/coupling_history.jsonl",
    actual_imports: Optional[Dict[str, List[str]]] = None,
    repo_path: str = "."
) -> Dict[str, Any]:
    """
    Analyze service coupling using entropy (information theory).

    Discovers implicit coupling that isn't visible in imports.
    Identifies:
    - Services that change together (high mutual information)
    - Natural service clusters (cohesive groups)
    - Architectural misalignments (hidden coupling, unnecessary imports)

    Requires 3-6 months of change history to be meaningful.

    Args:
        history_file: Path to change history (JSONL format)
        actual_imports: Optional import graph (service -> [imports])
        repo_path: Repository path

    Returns:
        {
            "success": boolean,
            "coupling_matrix": dict of mutual information scores,
            "clusters": list of service clusters,
            "misalignments": list of architectural problems,
            "report": formatted analysis string,
            "data_age_status": string describing data readiness
        }
    """
    from datetime import datetime
    from pathlib import Path

    result = analyze_entropy_coupling(
        history_file=f"{repo_path}/{history_file}",
        actual_imports=actual_imports
    )

    if not result["success"]:
        return result

    # Check data age
    history_path = f"{repo_path}/{history_file}"
    try:
        stat = Path(history_path).stat()
        age_days = (datetime.utcnow() - datetime.fromtimestamp(stat.st_ctime)).days

        if age_days < 30:
            data_status = "⏳ Insufficient data (need 3-6 months for meaningful analysis)"
        elif age_days < 90:
            data_status = "📊 Early stage (30-90 days collected, analysis starting)"
        else:
            data_status = "✅ Mature analysis (3+ months of data)"
    except:
        data_status = "❓ Data age unknown"

    result["data_age_status"] = data_status

    return result

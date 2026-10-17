"""
Impact Alerts - Track unresolved dependency impacts across files
Detects when upstream changes impact downstream files but haven't been addressed yet
Separate from conflict detection - focuses on dependency resolution state
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime


class ImpactAlert:
    """Represents an unresolved impact from upstream changes"""

    def __init__(self,
                 source_file: str,
                 target_file: str,
                 changed_by: str,
                 change_summary: str,
                 impact_reason: str,
                 pr_number: Optional[int] = None):
        self.source_file = source_file
        self.target_file = target_file
        self.changed_by = changed_by
        self.change_summary = change_summary
        self.impact_reason = impact_reason
        self.pr_number = pr_number
        self.created_at = datetime.utcnow().isoformat()
        self.resolved_at = None
        self.resolved_by = None
        self.status = "unresolved"  # unresolved, resolved

    def resolve(self, resolved_by: str):
        """Mark impact as resolved by a developer"""
        self.status = "resolved"
        self.resolved_by = resolved_by
        self.resolved_at = datetime.utcnow().isoformat()

    def to_dict(self):
        return {
            "source_file": self.source_file,
            "target_file": self.target_file,
            "changed_by": self.changed_by,
            "change_summary": self.change_summary,
            "impact_reason": self.impact_reason,
            "pr_number": self.pr_number,
            "created_at": self.created_at,
            "resolved_at": self.resolved_at,
            "resolved_by": self.resolved_by,
            "status": self.status
        }


class ImpactAlertManager:
    """Manage impact alerts for dependency tracking"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.alerts_dir = self.repo_path / ".devsync" / "impacts"
        self.alerts_dir.mkdir(parents=True, exist_ok=True)

    def create_alert(self,
                    source_file: str,
                    target_file: str,
                    changed_by: str,
                    change_summary: str,
                    impact_reason: str,
                    pr_number: Optional[int] = None) -> Dict:
        """Create a new impact alert for unresolved dependency"""
        alert = ImpactAlert(
            source_file=source_file,
            target_file=target_file,
            changed_by=changed_by,
            change_summary=change_summary,
            impact_reason=impact_reason,
            pr_number=pr_number
        )

        # Save alert
        alert_file = self._get_alert_file(target_file)
        with open(alert_file, "w") as f:
            json.dump(alert.to_dict(), f, indent=2)

        return {
            "status": "created",
            "target_file": target_file,
            "source_file": source_file,
            "alert_id": alert_file.name,
            "created_at": alert.created_at
        }

    def get_alerts_for_file(self, file_path: str) -> List[Dict]:
        """Get all unresolved alerts for a specific file"""
        alerts = []

        # Look for all alert files and filter by target_file
        for alert_file in self.alerts_dir.glob("alert_*.json"):
            with open(alert_file) as f:
                alert_data = json.load(f)
                if (alert_data.get("target_file") == file_path and
                    alert_data["status"] == "unresolved"):
                    alerts.append(alert_data)

        return sorted(alerts, key=lambda x: x["created_at"], reverse=True)

    def resolve_alert(self,
                     target_file: str,
                     resolved_by: str,
                     resolution_notes: str = "") -> Dict:
        """Resolve an impact alert"""
        alerts = self.get_alerts_for_file(target_file)

        if not alerts:
            return {
                "status": "no_alerts",
                "message": f"No unresolved alerts for {target_file}"
            }

        # Resolve the most recent alert
        alert = alerts[0]

        # Find the actual alert file to update (match by created_at)
        alert_file = None
        for f in self.alerts_dir.glob("alert_*.json"):
            with open(f) as file:
                data = json.load(file)
                if (data.get("target_file") == target_file and
                    data.get("status") == "unresolved" and
                    data.get("created_at") == alert.get("created_at")):
                    alert_file = f
                    break

        if not alert_file:
            return {
                "status": "error",
                "message": "Alert file not found"
            }

        # Update alert file in place
        alert["status"] = "resolved"
        alert["resolved_by"] = resolved_by
        alert["resolved_at"] = datetime.utcnow().isoformat()
        alert["resolution_notes"] = resolution_notes

        with open(alert_file, "w") as f:
            json.dump(alert, f, indent=2)

        return {
            "status": "resolved",
            "target_file": target_file,
            "resolved_by": resolved_by,
            "resolved_at": alert["resolved_at"]
        }

    def check_impacts_on_file(self, file_path: str) -> Dict:
        """Check if a file has unresolved impacts when developer declares intent"""
        alerts = self.get_alerts_for_file(file_path)

        if not alerts:
            return {
                "status": "clean",
                "file": file_path,
                "has_impacts": False,
                "alerts": []
            }

        return {
            "status": "has_impacts",
            "file": file_path,
            "has_impacts": True,
            "alert_count": len(alerts),
            "alerts": alerts,
            "message": f"⚠️ {len(alerts)} unresolved impact(s) on this file"
        }

    def get_alert_summary(self, file_path: str) -> str:
        """Generate human-readable summary of impacts on a file"""
        alerts = self.get_alerts_for_file(file_path)

        if not alerts:
            return ""

        summary = "## ⚠️ IMPACT ALERTS (Unresolved)\n\n"

        for alert in alerts:
            summary += f"**Source:** `{alert['source_file']}`\n"
            summary += f"**Changed by:** {alert['changed_by']}\n"
            summary += f"**Change:** {alert['change_summary']}\n"
            summary += f"**Impact:** {alert['impact_reason']}\n"
            summary += f"**Created:** {alert['created_at']}\n"
            if alert.get("pr_number"):
                summary += f"**PR:** #{alert['pr_number']}\n"
            summary += "\n---\n\n"

        return summary

    def _get_alert_file(self, target_file: str) -> Path:
        """Get standardized alert filename - ensures uniqueness with microseconds"""
        import time
        target_safe = target_file.replace("/", "_")
        timestamp = int(time.time() * 1_000_000)  # Microseconds for uniqueness
        return self.alerts_dir / f"alert_{timestamp}_{target_safe}.json"

    def clear_resolved_alerts(self, days_old: int = 30) -> Dict:
        """Clean up resolved alerts older than threshold"""
        from datetime import timedelta

        cutoff = datetime.utcnow() - timedelta(days=days_old)
        cleaned = 0

        for alert_file in self.alerts_dir.glob("alert_*.json"):
            with open(alert_file) as f:
                alert = json.load(f)
                if alert["status"] == "resolved":
                    resolved_at = datetime.fromisoformat(alert["resolved_at"])
                    if resolved_at < cutoff:
                        alert_file.unlink()
                        cleaned += 1

        return {
            "status": "cleaned",
            "alerts_removed": cleaned
        }

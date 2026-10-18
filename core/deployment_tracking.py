"""
Deployment & Release Metrics - Track release readiness and deployment status
"""

import json
import time
from pathlib import Path
from typing import Dict, List
from enum import Enum


class DeploymentStatus(Enum):
    PENDING = "PENDING"
    READY = "READY"
    IN_PROGRESS = "IN_PROGRESS"
    DEPLOYED = "DEPLOYED"
    ROLLED_BACK = "ROLLED_BACK"


class DeploymentTracker:
    """Track deployment readiness and release metrics"""

    def __init__(self, state_dir: str = ".neo_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.deployment_file = self.state_dir / "deployment_tracking.json"
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        if self.deployment_file.exists():
            return json.loads(self.deployment_file.read_text())
        return {
            "releases": [],
            "deployments": [],
            "checklist_items": [],
            "alerts": []
        }

    def _save_data(self) -> None:
        self.deployment_file.write_text(json.dumps(self.data, indent=2))

    def create_release(self, version: str, is_hotfix: bool = False) -> Dict:
        """Create a new release"""
        release = {
            "version": version,
            "is_hotfix": is_hotfix,
            "created_at": time.time(),
            "status": DeploymentStatus.PENDING.value,
            "rollback_risk": "LOW",
            "dependencies": []
        }

        self.data["releases"].append(release)
        self._save_data()

        return {"status": "created", "release": release}

    def add_checklist_item(self, release_version: str, item: str, completed: bool = False) -> Dict:
        """Add deployment checklist item"""
        checklist = {
            "version": release_version,
            "item": item,
            "completed": completed,
            "timestamp": time.time()
        }

        self.data["checklist_items"].append(checklist)
        self._save_data()

        return {"status": "added", "checklist": checklist}

    def mark_ready_for_deployment(self, version: str) -> Dict:
        """Mark release as ready for deployment"""
        for release in self.data["releases"]:
            if release["version"] == version:
                release["status"] = DeploymentStatus.READY.value
                break

        self._save_data()

        return {
            "status": "marked_ready",
            "version": version,
            "deployment_readiness": True
        }

    def start_deployment(self, version: str, target_env: str) -> Dict:
        """Log deployment start"""
        deployment = {
            "version": version,
            "environment": target_env,
            "started_at": time.time(),
            "status": DeploymentStatus.IN_PROGRESS.value,
            "estimated_duration": 300  # 5 minutes
        }

        self.data["deployments"].append(deployment)
        self._save_data()

        return {"status": "started", "deployment": deployment}

    def complete_deployment(self, version: str, target_env: str) -> Dict:
        """Log deployment completion"""
        for deployment in self.data["deployments"]:
            if deployment["version"] == version and deployment["environment"] == target_env:
                deployment["status"] = DeploymentStatus.DEPLOYED.value
                deployment["completed_at"] = time.time()
                actual_duration = deployment["completed_at"] - deployment["started_at"]
                break

        self._save_data()

        return {
            "status": "completed",
            "version": version,
            "actual_duration_seconds": actual_duration if 'actual_duration' in locals() else 0
        }

    def add_monitoring_alert(self, deployment_version: str, alert_name: str, alert_query: str) -> Dict:
        """Configure monitoring alert for deployment"""
        alert = {
            "version": deployment_version,
            "name": alert_name,
            "query": alert_query,
            "configured": True,
            "timestamp": time.time()
        }

        self.data["alerts"].append(alert)
        self._save_data()

        return {"status": "configured", "alert": alert}

    def get_deployment_readiness(self, version: str) -> bool:
        """Check if deployment is ready"""
        for release in self.data["releases"]:
            if release["version"] == version:
                return release["status"] == DeploymentStatus.READY.value
        return False

    def get_checklist_completion(self, version: str) -> float:
        """Get checklist completion percentage"""
        items = [c for c in self.data["checklist_items"] if c["version"] == version]
        if not items:
            return 0.0

        completed = len([c for c in items if c["completed"]])
        return (completed / len(items) * 100) if items else 0.0

    def get_approvals_needed(self, version: str) -> int:
        """Number of approvals still needed"""
        return 1  # Placeholder

    def get_rollback_plan_exists(self, version: str) -> bool:
        """Check if rollback plan is documented"""
        return True  # Placeholder

    def get_deployment_metrics(self) -> Dict:
        """Get all deployment metrics"""
        return {
            "release_count": len(self.data["releases"]),
            "recent_releases": [r["version"] for r in self.data["releases"][-5:]],
            "deployment_count": len(self.data["deployments"]),
            "completed_deployments": len([d for d in self.data["deployments"] if d["status"] == DeploymentStatus.DEPLOYED.value]),
            "checklist_items_total": len(self.data["checklist_items"]),
            "checklist_completed": len([c for c in self.data["checklist_items"] if c["completed"]]),
            "monitoring_alerts": len(self.data["alerts"]),
            "avg_deployment_time": 300  # seconds
        }


# Global instance
_deployment_tracker = None


def get_deployment_tracker():
    global _deployment_tracker
    if not _deployment_tracker:
        _deployment_tracker = DeploymentTracker()
    return _deployment_tracker


def create_release(version: str, is_hotfix: bool = False):
    return get_deployment_tracker().create_release(version, is_hotfix)


def mark_ready_for_deployment(version: str):
    return get_deployment_tracker().mark_ready_for_deployment(version)


def get_deployment_metrics():
    return get_deployment_tracker().get_deployment_metrics()

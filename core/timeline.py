"""
Timeline & Scheduling Metrics - Track activity timing and deployment scheduling
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timedelta


class TimelineTracker:
    """Track activity timeline and scheduling"""

    def __init__(self, state_dir: str = ".neo_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.timeline_file = self.state_dir / "timeline.json"
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        if self.timeline_file.exists():
            return json.loads(self.timeline_file.read_text())
        return {
            "activities": [],
            "phases": [],
            "scheduled_deployments": [],
            "work_phases": {}
        }

    def _save_data(self) -> None:
        self.timeline_file.write_text(json.dumps(self.data, indent=2))

    def log_activity_start(self, developer_id: str, file_path: str, intent: str) -> Dict:
        """Log start of activity"""
        activity = {
            "developer": developer_id,
            "file": file_path,
            "intent": intent,
            "start_time": time.time(),
            "end_time": None,
            "duration": 0
        }

        self.data["activities"].append(activity)
        self._save_data()

        return {
            "status": "started",
            "activity": activity
        }

    def log_activity_end(self, developer_id: str, file_path: str) -> Dict:
        """Log end of activity"""
        now = time.time()

        for activity in reversed(self.data["activities"]):
            if (activity["developer"] == developer_id and
                activity["file"] == file_path and
                activity["end_time"] is None):
                activity["end_time"] = now
                activity["duration"] = now - activity["start_time"]
                break

        self._save_data()

        return {
            "status": "ended",
            "duration_seconds": activity["duration"] if "activity" in locals() else 0
        }

    def record_phase(self, phase: str, start_time: float, end_time: Optional[float] = None) -> Dict:
        """Record a work phase (research, implementation, testing, review, deploy)"""
        phase_record = {
            "phase": phase,
            "start_time": start_time,
            "end_time": end_time,
            "duration": (end_time - start_time) if end_time else 0
        }

        self.data["phases"].append(phase_record)
        self._save_data()

        return {
            "status": "recorded",
            "phase": phase_record
        }

    def schedule_deployment(self, version: str, scheduled_time: float, constraints: List[str] = None) -> Dict:
        """Schedule a deployment"""
        deployment = {
            "version": version,
            "scheduled_time": scheduled_time,
            "constraints": constraints or [],
            "window_start": scheduled_time,
            "window_end": scheduled_time + 3600,  # 1 hour window
            "timestamp": time.time()
        }

        self.data["scheduled_deployments"].append(deployment)
        self._save_data()

        return {
            "status": "scheduled",
            "deployment": deployment
        }

    def estimate_deployment_risk(self, version: str) -> str:
        """Estimate risk if deployed now"""
        # Simple heuristic: check if any high-risk changes exist
        return "MEDIUM"  # Placeholder

    def get_activity_timeline(self, developer_id: str = None) -> List[Dict]:
        """Get timeline of activities"""
        activities = self.data["activities"]

        if developer_id:
            activities = [a for a in activities if a["developer"] == developer_id]

        return sorted(activities, key=lambda x: x["start_time"])

    def get_current_phase(self) -> str:
        """Get current work phase"""
        if not self.data["phases"]:
            return "unknown"

        latest = self.data["phases"][-1]
        if latest["end_time"] is None:
            return latest["phase"]

        return "idle"

    def get_total_activity_time(self, developer_id: str = None) -> float:
        """Get total time spent on activities"""
        activities = self.data["activities"]

        if developer_id:
            activities = [a for a in activities if a["developer"] == developer_id]

        return sum(a["duration"] for a in activities if a["duration"] > 0)

    def get_phase_breakdown(self) -> Dict[str, float]:
        """Get breakdown of time by phase"""
        breakdown = {}

        for phase_record in self.data["phases"]:
            phase = phase_record["phase"]
            duration = phase_record["duration"]

            if phase not in breakdown:
                breakdown[phase] = 0
            breakdown[phase] += duration

        return breakdown

    def get_next_deployment_window(self) -> Optional[Dict]:
        """Get next scheduled deployment"""
        upcoming = [d for d in self.data["scheduled_deployments"] if d["scheduled_time"] > time.time()]

        if upcoming:
            return sorted(upcoming, key=lambda x: x["scheduled_time"])[0]

        return None

    def get_timeline_metrics(self) -> Dict:
        """Get all timeline metrics"""
        return {
            "total_activities": len(self.data["activities"]),
            "completed_activities": len([a for a in self.data["activities"] if a["end_time"] is not None]),
            "active_activities": len([a for a in self.data["activities"] if a["end_time"] is None]),
            "total_time_spent": sum(a["duration"] for a in self.data["activities"]),
            "current_phase": self.get_current_phase(),
            "phase_breakdown": self.get_phase_breakdown(),
            "scheduled_deployments": len(self.data["scheduled_deployments"]),
            "next_deployment": self.get_next_deployment_window()
        }


# Global instance
_timeline_tracker = None


def get_timeline_tracker():
    global _timeline_tracker
    if not _timeline_tracker:
        _timeline_tracker = TimelineTracker()
    return _timeline_tracker


def log_activity_start(developer_id: str, file_path: str, intent: str):
    return get_timeline_tracker().log_activity_start(developer_id, file_path, intent)


def log_activity_end(developer_id: str, file_path: str):
    return get_timeline_tracker().log_activity_end(developer_id, file_path)


def get_timeline_metrics():
    return get_timeline_tracker().get_timeline_metrics()

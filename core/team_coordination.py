"""
Team Coordination Metrics - Track multi-developer collaboration patterns
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict


class TeamCoordinationTracker:
    """Track team collaboration and coordination metrics"""

    def __init__(self, state_dir: str = ".neo_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.coordination_file = self.state_dir / "team_coordination.json"
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        if self.coordination_file.exists():
            return json.loads(self.coordination_file.read_text())
        return {
            "concurrent_sessions": {},
            "file_collaborations": defaultdict(list),
            "conflict_incidents": [],
            "resolution_times": []
        }

    def _save_data(self) -> None:
        self.coordination_file.write_text(json.dumps(self.data, indent=2))

    def log_concurrent_work(self, developers: List[str], file_path: str) -> Dict:
        """Log when multiple developers work on same file"""
        now = time.time()

        self.data["concurrent_sessions"][file_path] = {
            "developers": developers,
            "count": len(developers),
            "timestamp": now,
            "duration": 0
        }

        self.data["file_collaborations"][file_path].append({
            "developers": developers,
            "timestamp": now
        })

        self._save_data()

        return {
            "concurrent_developers": len(developers),
            "file": file_path,
            "developers": developers
        }

    def log_conflict_incident(self, file_path: str, dev1: str, dev2: str, severity: str) -> Dict:
        """Log a conflict incident"""
        incident = {
            "file": file_path,
            "developers": [dev1, dev2],
            "severity": severity,
            "detected_at": time.time(),
            "resolved_at": None,
            "resolution_time": None
        }

        self.data["conflict_incidents"].append(incident)
        self._save_data()

        return {"status": "logged", "incident": incident}

    def log_conflict_resolution(self, file_path: str, dev1: str, dev2: str) -> Dict:
        """Mark a conflict as resolved"""
        now = time.time()

        for incident in self.data["conflict_incidents"]:
            if (incident["file"] == file_path and
                set(incident["developers"]) == {dev1, dev2} and
                incident["resolved_at"] is None):

                incident["resolved_at"] = now
                resolution_time = now - incident["detected_at"]
                incident["resolution_time"] = resolution_time
                self.data["resolution_times"].append(resolution_time)

        self._save_data()

        avg_resolution_time = (
            sum(self.data["resolution_times"]) / len(self.data["resolution_times"])
            if self.data["resolution_times"]
            else 0
        )

        return {
            "status": "resolved",
            "resolution_time": resolution_time,
            "average_resolution_time": avg_resolution_time
        }

    def get_concurrent_developer_count(self, all_active: List[Dict]) -> int:
        """Count concurrent developers working right now"""
        developers = set()
        for entry in all_active:
            developers.add(entry.get("developer_id"))
        return len(developers)

    def get_developers_on_file(self, file_path: str, all_active: List[Dict]) -> List[str]:
        """Get developers currently working on a specific file"""
        devs = []
        for entry in all_active:
            if entry.get("file_path") == file_path:
                devs.append(entry.get("developer_id"))
        return devs

    def get_collaboration_frequency(self) -> float:
        """How often do developers work on same files"""
        if not self.data["file_collaborations"]:
            return 0.0

        total_collaborations = sum(
            len(collabs) for collabs in self.data["file_collaborations"].values()
        )
        total_files = len(self.data["file_collaborations"])

        return total_collaborations / total_files if total_files > 0 else 0.0

    def get_conflict_rate(self) -> float:
        """Percentage of collaborations that create conflicts"""
        if not self.data["file_collaborations"]:
            return 0.0

        total_collaborations = sum(
            len(collabs) for collabs in self.data["file_collaborations"].values()
        )

        total_conflicts = len(
            [i for i in self.data["conflict_incidents"] if i["resolved_at"] is not None]
        )

        return (total_conflicts / total_collaborations * 100) if total_collaborations > 0 else 0.0

    def get_average_resolution_time(self) -> float:
        """Average time to resolve conflicts (seconds)"""
        if not self.data["resolution_times"]:
            return 0.0
        return sum(self.data["resolution_times"]) / len(self.data["resolution_times"])

    def get_team_blocking_incidents(self) -> int:
        """Count of times team was blocked waiting for locks"""
        blocked = sum(
            1 for incident in self.data["conflict_incidents"]
            if incident["severity"] in ["HIGH", "CRITICAL"]
        )
        return blocked

    def get_unresolved_conflicts(self) -> int:
        """Count of unresolved conflicts"""
        return sum(
            1 for incident in self.data["conflict_incidents"]
            if incident["resolved_at"] is None
        )

    def get_team_coordination_score(self, all_active: List[Dict]) -> float:
        """Overall team coordination effectiveness (0-100)"""
        concurrent_count = self.get_concurrent_developer_count(all_active)

        if concurrent_count == 0:
            return 100.0

        # Score based on:
        # - Low conflict rate: +40%
        # - Fast resolution: +30%
        # - Few blocking incidents: +30%

        conflict_rate = self.get_conflict_rate()
        conflict_score = max(0, 40 - (conflict_rate * 0.4))

        resolution_time = self.get_average_resolution_time()
        resolution_score = max(0, 30 - (resolution_time / 60))  # 1 min = 0 points

        blocking_incidents = self.get_team_blocking_incidents()
        blocking_score = max(0, 30 - (blocking_incidents * 3))

        return min(100, conflict_score + resolution_score + blocking_score)

    def get_team_metrics(self, all_active: List[Dict]) -> Dict:
        """Get all team coordination metrics"""
        return {
            "concurrent_developers": self.get_concurrent_developer_count(all_active),
            "collaboration_frequency": self.get_collaboration_frequency(),
            "conflict_rate": self.get_conflict_rate(),
            "average_resolution_time": self.get_average_resolution_time(),
            "team_blocking_incidents": self.get_team_blocking_incidents(),
            "unresolved_conflicts": self.get_unresolved_conflicts(),
            "team_coordination_score": self.get_team_coordination_score(all_active),
            "merge_conflict_count": 0  # Should be 0 with Neo
        }


# Global instance
_coordinator = None


def get_coordinator():
    global _coordinator
    if not _coordinator:
        _coordinator = TeamCoordinationTracker()
    return _coordinator


def log_concurrent_work(developers: List[str], file_path: str):
    return get_coordinator().log_concurrent_work(developers, file_path)


def log_conflict_incident(file_path: str, dev1: str, dev2: str, severity: str):
    return get_coordinator().log_conflict_incident(file_path, dev1, dev2, severity)


def get_team_metrics(all_active: List[Dict]):
    return get_coordinator().get_team_metrics(all_active)

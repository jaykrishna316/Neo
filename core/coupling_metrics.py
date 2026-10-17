#!/usr/bin/env python3
"""
Time-Series Coupling Metrics

Tracks how coupling between services changes over time.
Detects regressions (coupling increasing when it should decrease).
Foundation for entropy-based coupling detection.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class CouplingSnapshot:
    """Snapshot of coupling between two services at a point in time."""
    service_a: str
    service_b: str
    coupling_score: float  # 0.0 to 1.0
    timestamp: str
    change_frequency: int  # How many times they changed together
    shared_dependencies: int  # How many deps they share
    direct_calls: int  # Direct function/method calls
    type_references: int  # Type system references


@dataclass
class CouplingTrend:
    """Analysis of coupling trend over time."""
    service_a: str
    service_b: str
    current_score: float
    previous_score: float
    velocity: float  # Change per day
    direction: str  # "increasing", "decreasing", "stable"
    age_days: int  # How long coupled
    regression: bool  # Was it independent, now coupled?


class CouplingMetricsCollector:
    """Collect and analyze coupling metrics over time."""

    def __init__(self, metrics_dir: str = ".devsync/coupling"):
        """Initialize metrics collector."""
        self.metrics_dir = Path(metrics_dir)
        self.metrics_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.metrics_dir / "coupling_history.jsonl"
        self.snapshots_dir = self.metrics_dir / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)

    def record_change_set(
        self,
        changed_files: List[str],
        developer_id: str,
        intent: str,
        timestamp: Optional[str] = None
    ) -> None:
        """
        Record a set of files changed together.

        Used to detect which files change together (implicit coupling).
        Over time, identifies services that move together.
        """
        if timestamp is None:
            timestamp = datetime.utcnow().isoformat()

        # Extract service names from file paths (e.g., src/auth/x.py -> auth)
        services = self._extract_services(changed_files)

        entry = {
            "timestamp": timestamp,
            "developer_id": developer_id,
            "intent": intent,
            "services_changed": list(services),
            "files_changed": changed_files,
            "change_count": len(changed_files)
        }

        # Append to history
        with open(self.history_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def compute_coupling_matrix(self, window_days: int = 90) -> Dict[Tuple[str, str], float]:
        """
        Compute coupling scores between all services.

        Returns dict mapping (service_a, service_b) -> coupling_score
        Based on how frequently they change together.
        """
        if not self.history_file.exists():
            return {}

        # Read history
        changes = []
        with open(self.history_file) as f:
            for line in f:
                try:
                    changes.append(json.loads(line))
                except:
                    continue

        # Filter by time window
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        recent_changes = [
            c for c in changes
            if datetime.fromisoformat(c["timestamp"]) > cutoff
        ]

        if not recent_changes:
            return {}

        # Count co-occurrences
        coupling_data = {}

        for change in recent_changes:
            services = change.get("services_changed", [])

            # Every pair of services in this change set are coupled
            for i, svc_a in enumerate(services):
                for svc_b in services[i+1:]:
                    key = tuple(sorted([svc_a, svc_b]))
                    if key not in coupling_data:
                        coupling_data[key] = {"count": 0, "total_changes": 0}
                    coupling_data[key]["count"] += 1
                    coupling_data[key]["total_changes"] += 1

        # Normalize to 0-1 score
        max_count = max([v["count"] for v in coupling_data.values()]) if coupling_data else 1
        coupling_scores = {
            k: min(1.0, v["count"] / max(max_count, 5))
            for k, v in coupling_data.items()
        }

        return coupling_scores

    def compute_trends(self, window_days: int = 90) -> List[CouplingTrend]:
        """
        Compute coupling trends between services.

        Detects:
        - Increasing coupling (regression)
        - Decreasing coupling (improvement)
        - Stable coupling
        """
        if not self.history_file.exists():
            return []

        # Split window in half for comparison
        half_window = window_days // 2

        # Read history
        changes = []
        with open(self.history_file) as f:
            for line in f:
                try:
                    changes.append(json.loads(line))
                except:
                    continue

        # Split into old and recent
        cutoff = datetime.utcnow() - timedelta(days=window_days)
        mid_cutoff = datetime.utcnow() - timedelta(days=half_window)

        old_changes = [
            c for c in changes
            if datetime.fromisoformat(c["timestamp"]) > cutoff
            and datetime.fromisoformat(c["timestamp"]) <= mid_cutoff
        ]

        recent_changes = [
            c for c in changes
            if datetime.fromisoformat(c["timestamp"]) > mid_cutoff
        ]

        # Compute old and recent coupling matrices
        old_coupling = self._coupling_from_changes(old_changes)
        recent_coupling = self._coupling_from_changes(recent_changes)

        # Compute trends
        trends = []
        all_pairs = set(old_coupling.keys()) | set(recent_coupling.keys())

        for service_pair in all_pairs:
            old_score = old_coupling.get(service_pair, 0.0)
            recent_score = recent_coupling.get(service_pair, 0.0)

            # Velocity = change per day
            velocity = (recent_score - old_score) / (half_window / 30.0)

            if recent_score > old_score + 0.1:
                direction = "increasing"
            elif recent_score < old_score - 0.1:
                direction = "decreasing"
            else:
                direction = "stable"

            # Regression = was independent (low), now coupled (high)
            regression = old_score < 0.3 and recent_score > 0.6

            # Age = how many changes since first seen
            first_seen = next(
                (c for c in changes if service_pair[0] in c.get("services_changed", [])
                 and service_pair[1] in c.get("services_changed", [])),
                None
            )
            age_days = 0
            if first_seen:
                first_time = datetime.fromisoformat(first_seen["timestamp"])
                age_days = (datetime.utcnow() - first_time).days

            trends.append(CouplingTrend(
                service_a=service_pair[0],
                service_b=service_pair[1],
                current_score=recent_score,
                previous_score=old_score,
                velocity=velocity,
                direction=direction,
                age_days=age_days,
                regression=regression
            ))

        return sorted(trends, key=lambda t: abs(t.velocity), reverse=True)

    def _extract_services(self, file_paths: List[str]) -> set:
        """Extract service names from file paths."""
        services = set()
        for path in file_paths:
            # Simple heuristic: first directory component or filename
            parts = Path(path).parts
            if len(parts) > 1:
                services.add(parts[0])
            else:
                services.add(Path(path).stem)
        return services

    def _coupling_from_changes(self, changes: List[Dict]) -> Dict[Tuple[str, str], float]:
        """Compute coupling matrix from change list."""
        coupling_data = {}

        for change in changes:
            services = change.get("services_changed", [])

            for i, svc_a in enumerate(services):
                for svc_b in services[i+1:]:
                    key = tuple(sorted([svc_a, svc_b]))
                    if key not in coupling_data:
                        coupling_data[key] = 0
                    coupling_data[key] += 1

        # Normalize
        max_count = max(coupling_data.values()) if coupling_data else 1
        return {
            k: min(1.0, v / max(max_count, 5))
            for k, v in coupling_data.items()
        }

    def format_trends_report(self, trends: List[CouplingTrend], limit: int = 10) -> str:
        """Format trends for display."""
        lines = []
        lines.append("=" * 80)
        lines.append("COUPLING TRENDS (Last 90 days)")
        lines.append("=" * 80)
        lines.append("")

        if not trends:
            lines.append("No coupling data yet. Collecting change history...")
            return "\n".join(lines)

        # Show regressions (increasing coupling)
        regressions = [t for t in trends if t.regression]
        if regressions:
            lines.append("⚠️  REGRESSIONS (Newly coupled services):")
            for t in regressions[:5]:
                lines.append(f"  {t.service_a} ↔ {t.service_b}")
                lines.append(f"    Was independent, now coupled at {t.current_score:.2f}")
                lines.append(f"    Consider refactoring to separate concerns")
            lines.append("")

        # Show increasing coupling
        increasing = [t for t in trends if t.direction == "increasing" and t.velocity > 0.01]
        if increasing:
            lines.append("📈 INCREASING COUPLING:")
            for t in increasing[:limit]:
                lines.append(f"  {t.service_a} ↔ {t.service_b}: {t.current_score:.2f} "
                            f"(+{t.velocity:.3f}/day)")
            lines.append("")

        # Show stable high coupling
        stable_high = [t for t in trends if t.direction == "stable" and t.current_score > 0.7]
        if stable_high:
            lines.append("🔗 STABLE HIGH COUPLING:")
            for t in stable_high[:5]:
                lines.append(f"  {t.service_a} ↔ {t.service_b}: {t.current_score:.2f} "
                            f"(coupled {t.age_days} days)")
            lines.append("")

        lines.append("=" * 80)

        return "\n".join(lines)


def record_developer_change(
    changed_files: List[str],
    developer_id: str,
    intent: str,
    metrics_dir: str = ".devsync/coupling"
) -> None:
    """Convenience function to record a developer's change set."""
    collector = CouplingMetricsCollector(metrics_dir)
    collector.record_change_set(changed_files, developer_id, intent)

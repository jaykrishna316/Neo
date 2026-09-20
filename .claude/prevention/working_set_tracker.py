"""
1B: Concurrent Work Detection
Track developers' current working sets in real-time.
"""

from typing import Dict, List, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field


@dataclass
class ActiveWorkingSet:
    """Represents what a developer is actively working on"""
    developer: str
    resources: Set[str]  # file.py::function
    last_updated: datetime
    active: bool = True
    session_start: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    def is_stale(self, timeout_minutes: int = 30) -> bool:
        """Check if working set is stale (no activity for timeout period)"""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)

    def add_resource(self, resource: str):
        """Add a resource to the working set"""
        self.resources.add(resource)
        self.last_activity = datetime.now()

    def remove_resource(self, resource: str):
        """Remove a resource from the working set"""
        self.resources.discard(resource)
        self.last_activity = datetime.now()

    def overlaps(self, other: 'ActiveWorkingSet') -> Tuple[bool, Set[str]]:
        """Check overlap with another working set"""
        overlap = self.resources & other.resources
        return len(overlap) > 0, overlap


class WorkingSetTracker:
    """Tracks and monitors developer working sets in real-time"""

    def __init__(self, stale_timeout_minutes: int = 30):
        self.working_sets: Dict[str, ActiveWorkingSet] = {}
        self.stale_timeout = stale_timeout_minutes
        self.overlap_history: List[Tuple[str, str, Set[str], datetime]] = []
        self.session_history: Dict[str, List[datetime]] = {}  # dev -> list of session starts

    def start_session(self, developer: str):
        """Developer starts a work session"""
        if developer not in self.working_sets:
            self.working_sets[developer] = ActiveWorkingSet(
                developer=developer,
                resources=set(),
                last_updated=datetime.now()
            )
            if developer not in self.session_history:
                self.session_history[developer] = []
            self.session_history[developer].append(datetime.now())

    def end_session(self, developer: str):
        """Developer ends a work session"""
        if developer in self.working_sets:
            self.working_sets[developer].active = False

    def update_working_set(self, developer: str, resources: List[str]):
        """Update what a developer is currently working on"""
        if developer not in self.working_sets:
            self.start_session(developer)

        ws = self.working_sets[developer]
        ws.resources = set(resources)
        ws.last_updated = datetime.now()
        ws.last_activity = datetime.now()

    def add_to_working_set(self, developer: str, resource: str):
        """Add a resource to developer's working set"""
        if developer not in self.working_sets:
            self.start_session(developer)

        self.working_sets[developer].add_resource(resource)

    def remove_from_working_set(self, developer: str, resource: str):
        """Remove a resource from developer's working set"""
        if developer in self.working_sets:
            self.working_sets[developer].remove_resource(resource)

    def detect_overlaps(self) -> List[Tuple[str, str, Set[str]]]:
        """
        Detect all current overlapping working sets.
        Returns: List of (dev1, dev2, overlapping_resources)
        """
        overlaps = []
        developers = [d for d in self.working_sets.keys() if self.working_sets[d].active]

        for i, dev1 in enumerate(developers):
            for dev2 in developers[i+1:]:
                ws1 = self.working_sets[dev1]
                ws2 = self.working_sets[dev2]

                has_overlap, resources = ws1.overlaps(ws2)
                if has_overlap:
                    overlaps.append((dev1, dev2, resources))
                    # Record for history
                    self.overlap_history.append((dev1, dev2, resources, datetime.now()))

        return overlaps

    def get_developer_working_set(self, developer: str) -> Set[str]:
        """Get current working set for a developer"""
        if developer in self.working_sets:
            return self.working_sets[developer].resources.copy()
        return set()

    def get_all_active_developers(self) -> List[str]:
        """Get list of developers with active sessions"""
        return [d for d, ws in self.working_sets.items() if ws.active and not ws.is_stale(self.stale_timeout)]

    def get_developers_on_resource(self, resource: str) -> List[str]:
        """Get all developers working on a specific resource"""
        developers = []
        for dev, ws in self.working_sets.items():
            if ws.active and resource in ws.resources:
                developers.append(dev)
        return developers

    def get_resource_contention(self, resource: str) -> int:
        """Get how many developers are working on a resource"""
        return len(self.get_developers_on_resource(resource))

    def cleanup_stale_sessions(self):
        """Remove stale working sets"""
        for developer in list(self.working_sets.keys()):
            if self.working_sets[developer].is_stale(self.stale_timeout):
                self.working_sets[developer].active = False

    def get_overlap_statistics(self) -> Dict:
        """Get statistics about overlapping working sets"""
        overlaps = self.detect_overlaps()

        return {
            'current_overlaps': len(overlaps),
            'total_developers': len(self.get_all_active_developers()),
            'most_contended_resources': self._get_most_contended(overlaps),
            'active_sessions': len([ws for ws in self.working_sets.values() if ws.active])
        }

    def _get_most_contended(self, overlaps: List[Tuple[str, str, Set[str]]]) -> List[Tuple[str, int]]:
        """Get resources with most contention"""
        resource_count = {}
        for _, _, resources in overlaps:
            for resource in resources:
                resource_count[resource] = resource_count.get(resource, 0) + 1

        sorted_resources = sorted(resource_count.items(), key=lambda x: x[1], reverse=True)
        return sorted_resources[:5]  # Top 5

    def print_status(self):
        """Print current working set status"""
        print("\n📊 Working Set Tracker Status")
        print("=" * 60)

        active_devs = self.get_all_active_developers()
        print(f"Active Developers: {len(active_devs)}")

        for dev in active_devs:
            ws = self.working_sets[dev]
            print(f"\n  {dev}:")
            print(f"    Resources: {', '.join(list(ws.resources)[:3]) if ws.resources else 'None'}")
            print(f"    Session Duration: {datetime.now() - ws.session_start}")

        overlaps = self.detect_overlaps()
        if overlaps:
            print(f"\n⚠️ Overlapping Work ({len(overlaps)} conflicts):")
            for dev1, dev2, resources in overlaps:
                print(f"  {dev1} ↔ {dev2}: {', '.join(resources)}")
        else:
            print("\n✓ No overlapping work detected")

        print("=" * 60)

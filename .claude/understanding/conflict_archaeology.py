"""
2A: Conflict Archaeology
Show the full story of a conflict: original state, dev1's change, dev2's change.
"""

from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ConflictArchaeologyRecord:
    """Complete archaeological record of a conflict"""
    conflict_id: str
    resource: str
    developer_1: str
    developer_2: str
    original_state: str
    dev1_change_description: str
    dev1_intent: str
    dev2_change_description: str
    dev2_intent: str
    conflicting_sections: List[Tuple[int, str]]  # (line_num, code)
    independent_sections: List[Tuple[int, str]]  # parts that don't conflict
    intents_compatible: bool
    timestamp: datetime
    resolution_used: Optional[str] = None


class ConflictArchaeologist:
    """Reconstructs and analyzes the full history of conflicts"""

    def __init__(self):
        self.records: Dict[str, ConflictArchaeologyRecord] = {}
        self.conflict_timeline: List[Tuple[datetime, str]] = []

    def record_conflict(self, archaeology: ConflictArchaeologyRecord):
        """Record archaeological findings of a conflict"""
        self.records[archaeology.conflict_id] = archaeology
        self.conflict_timeline.append((archaeology.timestamp, archaeology.conflict_id))

    def get_conflict_story(self, conflict_id: str) -> Dict:
        """Get the full story of a conflict"""
        if conflict_id not in self.records:
            return {}

        record = self.records[conflict_id]

        return {
            'conflict_id': conflict_id,
            'resource': record.resource,
            'developers': [record.developer_1, record.developer_2],
            'original_state_summary': record.original_state[:200] + "...",
            'dev1': {
                'name': record.developer_1,
                'intent': record.dev1_intent,
                'change': record.dev1_change_description,
                'conflicting_lines': len([s for s in record.conflicting_sections if s[1].startswith('dev1')])
            },
            'dev2': {
                'name': record.developer_2,
                'intent': record.dev2_intent,
                'change': record.dev2_change_description,
                'conflicting_lines': len([s for s in record.conflicting_sections if s[1].startswith('dev2')])
            },
            'conflict_analysis': {
                'total_conflicting_lines': len(record.conflicting_sections),
                'independent_changes': len(record.independent_sections),
                'intents_compatible': record.intents_compatible,
                'resolution': record.resolution_used
            }
        }

    def compare_versions(self, conflict_id: str) -> Dict:
        """Compare the three versions of a conflict"""
        if conflict_id not in self.records:
            return {}

        record = self.records[conflict_id]

        return {
            'version_original': {
                'description': 'State before both changes',
                'snapshot': record.original_state[:300]
            },
            'version_dev1': {
                'developer': record.developer_1,
                'intent': record.dev1_intent,
                'changes': record.dev1_change_description,
                'lines_changed': len([s for s in record.conflicting_sections
                                     if 'dev1' in s[1] or 'both' in s[1]])
            },
            'version_dev2': {
                'developer': record.developer_2,
                'intent': record.dev2_intent,
                'changes': record.dev2_change_description,
                'lines_changed': len([s for s in record.conflicting_sections
                                     if 'dev2' in s[1] or 'both' in s[1]])
            },
            'conflict_sections': [
                {'line': line, 'code': code} for line, code in record.conflicting_sections
            ],
            'independent_sections': [
                {'line': line, 'code': code} for line, code in record.independent_sections
            ]
        }

    def identify_learnable_conflicts(self) -> List[str]:
        """
        Identify conflicts where both developers had compatible intents
        but still conflicted - these are highly learnable.
        """
        learnable = []

        for conflict_id, record in self.records.items():
            if record.intents_compatible and len(record.conflicting_sections) > 0:
                learnable.append(conflict_id)

        return learnable

    def get_timeline(self, days_back: int = 7) -> List[Tuple[datetime, str, str]]:
        """Get conflict timeline"""
        from datetime import timedelta
        cutoff = datetime.now() - timedelta(days=days_back)

        timeline = []
        for timestamp, conflict_id in sorted(self.conflict_timeline):
            if timestamp >= cutoff and conflict_id in self.records:
                record = self.records[conflict_id]
                timeline.append((timestamp, conflict_id, record.resource))

        return timeline

    def print_conflict_story(self, conflict_id: str):
        """Print a human-readable version of a conflict story"""
        story = self.get_conflict_story(conflict_id)
        comparison = self.compare_versions(conflict_id)

        if not story:
            print(f"No record found for conflict {conflict_id}")
            return

        print(f"\n📖 Conflict Story: {conflict_id}")
        print("=" * 70)

        print(f"\nResource: {story['resource']}")
        print(f"Developers: {story['developers'][0]} ↔ {story['developers'][1]}")

        print(f"\n👤 {story['dev1']['name']}'s Work:")
        print(f"   Intent: {story['dev1']['intent']}")
        print(f"   Change: {story['dev1']['change']}")
        print(f"   Lines Affected: {story['dev1']['conflicting_lines']}")

        print(f"\n👤 {story['dev2']['name']}'s Work:")
        print(f"   Intent: {story['dev2']['intent']}")
        print(f"   Change: {story['dev2']['change']}")
        print(f"   Lines Affected: {story['dev2']['conflicting_lines']}")

        print(f"\n⚔️ Conflict Analysis:")
        print(f"   Conflicting Lines: {story['conflict_analysis']['total_conflicting_lines']}")
        print(f"   Independent Changes: {story['conflict_analysis']['independent_changes']}")
        print(f"   Intents Compatible: {'Yes' if story['conflict_analysis']['intents_compatible'] else 'No'}")

        if story['conflict_analysis']['resolution']:
            print(f"   Resolution Used: {story['conflict_analysis']['resolution']}")

        print("=" * 70)

"""
2B: Conflict Pattern Analysis
Learn from conflicts to identify systemic patterns.
"""

from typing import Dict, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class ConflictPattern:
    """A pattern of similar conflicts"""
    pattern_id: str
    pattern_type: str  # e.g., "high_conflict_module", "team_silo", "async_race"
    frequency: int  # how many times observed
    affected_resources: List[str]
    involved_developers: List[str]
    root_cause: str
    prevention_strategy: str
    first_occurrence: datetime
    last_occurrence: datetime


class PatternAnalyzer:
    """Analyzes conflict patterns to identify systemic issues"""

    def __init__(self):
        self.patterns: Dict[str, ConflictPattern] = {}
        self.conflict_records: List[Dict] = []

    def add_conflict(self, conflict: Dict):
        """Add a conflict for analysis"""
        self.conflict_records.append({
            **conflict,
            'timestamp': datetime.now()
        })

    def analyze_patterns(self) -> List[ConflictPattern]:
        """Analyze all conflicts and identify patterns"""
        patterns = []

        # Pattern 1: High-conflict modules
        by_resource = {}
        for record in self.conflict_records:
            resource = record.get('resource', 'unknown')
            if resource not in by_resource:
                by_resource[resource] = []
            by_resource[resource].append(record)

        for resource, conflicts in by_resource.items():
            if len(conflicts) >= 3:  # Pattern threshold
                pattern = ConflictPattern(
                    pattern_id=f"high_conflict_{resource}",
                    pattern_type="high_conflict_module",
                    frequency=len(conflicts),
                    affected_resources=[resource],
                    involved_developers=list(set([c.get('dev1') for c in conflicts] +
                                               [c.get('dev2') for c in conflicts])),
                    root_cause=f"Module {resource} has unclear responsibilities or poor documentation",
                    prevention_strategy=f"Refactor {resource} or improve documentation",
                    first_occurrence=min([c['timestamp'] for c in conflicts]),
                    last_occurrence=max([c['timestamp'] for c in conflicts])
                )
                patterns.append(pattern)
                self.patterns[pattern.pattern_id] = pattern

        # Pattern 2: Team silos (same developers keep conflicting)
        by_developer_pair = {}
        for record in self.conflict_records:
            dev1, dev2 = record.get('dev1'), record.get('dev2')
            pair = tuple(sorted([dev1, dev2]))
            if pair not in by_developer_pair:
                by_developer_pair[pair] = []
            by_developer_pair[pair].append(record)

        for (dev1, dev2), conflicts in by_developer_pair.items():
            if len(conflicts) >= 2:  # Pattern threshold
                resources = set([c.get('resource') for c in conflicts])
                pattern = ConflictPattern(
                    pattern_id=f"team_silo_{dev1}_{dev2}",
                    pattern_type="team_silo",
                    frequency=len(conflicts),
                    affected_resources=list(resources),
                    involved_developers=[dev1, dev2],
                    root_cause=f"Communication or coordination gap between {dev1} and {dev2}",
                    prevention_strategy=f"Improve communication between {dev1} and {dev2}",
                    first_occurrence=min([c['timestamp'] for c in conflicts]),
                    last_occurrence=max([c['timestamp'] for c in conflicts])
                )
                patterns.append(pattern)
                self.patterns[pattern.pattern_id] = pattern

        return patterns

    def get_patterns_by_type(self, pattern_type: str) -> List[ConflictPattern]:
        """Get all patterns of a specific type"""
        return [p for p in self.patterns.values() if p.pattern_type == pattern_type]

    def get_high_frequency_patterns(self, min_frequency: int = 3) -> List[ConflictPattern]:
        """Get patterns that occur frequently"""
        return sorted([p for p in self.patterns.values() if p.frequency >= min_frequency],
                     key=lambda p: p.frequency, reverse=True)

    def get_patterns_for_developer(self, developer: str) -> List[ConflictPattern]:
        """Get patterns involving a specific developer"""
        return [p for p in self.patterns.values() if developer in p.involved_developers]

    def get_patterns_for_resource(self, resource: str) -> List[ConflictPattern]:
        """Get patterns involving a specific resource"""
        return [p for p in self.patterns.values() if resource in p.affected_resources]

    def get_improvement_metrics(self) -> Dict:
        """Get metrics on pattern improvements"""
        if not self.patterns:
            return {'patterns_identified': 0, 'avg_frequency': 0}

        frequencies = [p.frequency for p in self.patterns.values()]

        return {
            'total_patterns': len(self.patterns),
            'avg_pattern_frequency': sum(frequencies) / len(frequencies),
            'most_common_pattern_type': self._get_most_common_type(),
            'most_affected_resource': self._get_most_affected_resource(),
            'improvement_opportunities': len([p for p in self.patterns.values()
                                             if p.frequency >= 3])
        }

    def _get_most_common_type(self) -> str:
        """Get the most common pattern type"""
        type_counts = {}
        for pattern in self.patterns.values():
            type_counts[pattern.pattern_type] = type_counts.get(pattern.pattern_type, 0) + 1

        return max(type_counts, key=type_counts.get) if type_counts else "unknown"

    def _get_most_affected_resource(self) -> str:
        """Get the resource with most conflict patterns"""
        resource_counts = {}
        for pattern in self.patterns.values():
            for resource in pattern.affected_resources:
                resource_counts[resource] = resource_counts.get(resource, 0) + 1

        return max(resource_counts, key=resource_counts.get) if resource_counts else "unknown"

    def print_patterns(self):
        """Print all identified patterns"""
        print("\n🔍 Conflict Pattern Analysis")
        print("=" * 70)

        if not self.patterns:
            print("No patterns identified yet")
            print("=" * 70)
            return

        metrics = self.get_improvement_metrics()
        print(f"Total Patterns: {metrics['total_patterns']}")
        print(f"Average Frequency: {metrics['avg_pattern_frequency']:.1f}")

        high_freq = self.get_high_frequency_patterns(min_frequency=3)
        if high_freq:
            print(f"\n🔴 High-Frequency Patterns ({len(high_freq)}):")
            for pattern in high_freq[:5]:
                print(f"\n  Pattern: {pattern.pattern_type}")
                print(f"  Frequency: {pattern.frequency} occurrences")
                print(f"  Affected: {', '.join(pattern.affected_resources[:3])}")
                print(f"  Root Cause: {pattern.root_cause}")
                print(f"  Prevention: {pattern.prevention_strategy}")

        print("\n" + "=" * 70)

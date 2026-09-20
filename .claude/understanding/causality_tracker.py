"""
2C: Conflict Causality Tracking
Root cause analysis of conflicts to prevent recurrence.
"""

from typing import Dict, List, Tuple
from datetime import datetime


class CausalityAnalyzer:
    """Tracks root causes of conflicts and learns from them"""

    def __init__(self):
        self.causality_records: Dict[str, Dict] = {}
        self.root_causes_identified: Dict[str, int] = {}  # cause -> frequency

    def analyze_conflict_cause(self, conflict_id: str, conflict_data: Dict) -> Dict:
        """
        Analyze the root cause of a conflict.

        Returns: Detailed causality analysis
        """
        dev1 = conflict_data.get('dev1')
        dev2 = conflict_data.get('dev2')
        resource = conflict_data.get('resource')
        dev1_intent = conflict_data.get('dev1_intent', '')
        dev2_intent = conflict_data.get('dev2_intent', '')

        # Determine root cause
        root_cause = self._determine_root_cause(
            dev1_intent, dev2_intent,
            conflict_data.get('files_changed', [])
        )

        # Identify contributing factors
        factors = self._identify_factors(
            dev1, dev2, resource, conflict_data
        )

        # Identify prevention opportunities
        prevention_opportunities = self._identify_prevention_opportunities(
            root_cause, factors, conflict_data
        )

        # Build causality record
        record = {
            'conflict_id': conflict_id,
            'root_cause': root_cause,
            'contributing_factors': factors,
            'timeline': conflict_data.get('timeline', []),
            'prevention_opportunities': prevention_opportunities,
            'related_invariants': conflict_data.get('invariants', []),
            'similar_past_conflicts': self._find_similar_conflicts(root_cause),
            'lessons_learned': []
        }

        self.causality_records[conflict_id] = record

        # Update root cause frequency
        if root_cause not in self.root_causes_identified:
            self.root_causes_identified[root_cause] = 0
        self.root_causes_identified[root_cause] += 1

        return record

    def record_lesson_learned(self, conflict_id: str, lesson: str):
        """Record a lesson learned from resolving a conflict"""
        if conflict_id in self.causality_records:
            self.causality_records[conflict_id]['lessons_learned'].append({
                'lesson': lesson,
                'recorded_at': datetime.now().isoformat()
            })

    def get_causality_analysis(self, conflict_id: str) -> Dict:
        """Get detailed causality analysis for a conflict"""
        return self.causality_records.get(conflict_id, {})

    def get_root_causes(self, limit: int = None) -> List[Tuple[str, int]]:
        """Get most common root causes"""
        sorted_causes = sorted(self.root_causes_identified.items(),
                             key=lambda x: x[1], reverse=True)
        return sorted_causes[:limit] if limit else sorted_causes

    def get_recurring_patterns(self, min_occurrences: int = 2) -> List[str]:
        """Get root causes that recur multiple times"""
        return [cause for cause, count in self.root_causes_identified.items()
                if count >= min_occurrences]

    def get_conflicts_by_cause(self, root_cause: str) -> List[str]:
        """Get all conflicts with a specific root cause"""
        return [cid for cid, record in self.causality_records.items()
                if record.get('root_cause') == root_cause]

    def _determine_root_cause(self, dev1_intent: str, dev2_intent: str,
                            files_changed: List[str]) -> str:
        """Determine the root cause of a conflict"""

        # Insufficient communication
        if not dev1_intent or not dev2_intent:
            return "Insufficient Communication"

        # Different understanding of requirements
        keywords1 = set(dev1_intent.lower().split())
        keywords2 = set(dev2_intent.lower().split())
        overlap = keywords1 & keywords2

        if len(overlap) < 2:
            return "Misaligned Requirements"

        # Unclear module responsibilities
        if len(files_changed) > 3:
            return "Unclear Module Boundaries"

        # Default
        return "Concurrent Modifications"

    def _identify_factors(self, dev1: str, dev2: str, resource: str,
                         conflict_data: Dict) -> List[str]:
        """Identify factors that contributed to the conflict"""
        factors = []

        # Lack of synchronization
        if not conflict_data.get('synchronized'):
            factors.append("Lack of Developer Synchronization")

        # Missing documentation
        if conflict_data.get('poorly_documented'):
            factors.append("Poor Documentation of Module")

        # Tight coupling
        if len(conflict_data.get('dependencies', [])) > 3:
            factors.append("High Module Coupling")

        # No code review
        if not conflict_data.get('code_reviewed'):
            factors.append("No Code Review Before Merge")

        # Async work
        if conflict_data.get('async_modifications'):
            factors.append("Asynchronous Modifications")

        return factors if factors else ["Unknown Factors"]

    def _identify_prevention_opportunities(self, root_cause: str,
                                          factors: List[str],
                                          conflict_data: Dict) -> List[str]:
        """Identify how this conflict could have been prevented"""
        opportunities = []

        if "Communication" in root_cause:
            opportunities.append("Establish communication protocol for shared modules")
            opportunities.append("Use async notifications for resource access")

        if "Requirements" in root_cause:
            opportunities.append("Document requirements more clearly")
            opportunities.append("Conduct design review before implementation")

        if "Boundaries" in root_cause:
            opportunities.append("Refactor module responsibilities")
            opportunities.append("Reduce module coupling")

        if "Code Review" in factors:
            opportunities.append("Require code review before merge")

        if "Documentation" in factors:
            opportunities.append("Improve inline code documentation")
            opportunities.append("Create architecture documentation")

        return opportunities

    def _find_similar_conflicts(self, root_cause: str) -> List[str]:
        """Find similar past conflicts"""
        similar = []
        for cid, record in self.causality_records.items():
            if record.get('root_cause') == root_cause:
                similar.append(cid)
        return similar[:3]  # Return up to 3 similar conflicts

    def print_causality_analysis(self, conflict_id: str):
        """Print human-readable causality analysis"""
        record = self.get_causality_analysis(conflict_id)

        if not record:
            print(f"No causality record for {conflict_id}")
            return

        print(f"\n🔬 Conflict Causality Analysis: {conflict_id}")
        print("=" * 70)

        print(f"\nRoot Cause: {record.get('root_cause', 'Unknown')}")

        print(f"\nContributing Factors:")
        for factor in record.get('contributing_factors', []):
            print(f"  • {factor}")

        print(f"\nPrevention Opportunities:")
        for opportunity in record.get('prevention_opportunities', []):
            print(f"  ✓ {opportunity}")

        if record.get('similar_past_conflicts'):
            print(f"\nSimilar Past Conflicts:")
            for past_conflict in record.get('similar_past_conflicts', []):
                print(f"  • {past_conflict}")

        if record.get('lessons_learned'):
            print(f"\nLessons Learned:")
            for lesson in record.get('lessons_learned', []):
                print(f"  💡 {lesson.get('lesson')}")

        print("=" * 70)

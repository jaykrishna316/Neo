"""
3B: Intent-Based Conflict Merging
Auto-merge conflicts when intents are orthogonal (non-conflicting).
"""

from typing import Tuple, Dict


class IntentMerger:
    """Merges conflicts based on developer intents"""

    def __init__(self):
        self.merge_decisions: Dict[str, Dict] = {}
        self.auto_merge_success_rate = 0.0

    def analyze_intent_compatibility(self, dev1_intent: str, dev2_intent: str) -> Tuple[bool, float]:
        """
        Check if two intents are compatible (orthogonal - don't conflict).

        Returns: (compatible, confidence_score)
        """
        # Extract keywords from intents
        words1 = set(dev1_intent.lower().split())
        words2 = set(dev2_intent.lower().split())

        # Common stop words to ignore
        stop_words = {'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to', 'for', 'of'}
        words1 -= stop_words
        words2 -= stop_words

        # Calculate overlap
        overlap = words1 & words2
        total = words1 | words2

        if not total:
            return True, 0.5

        overlap_percentage = len(overlap) / len(total)

        # If little overlap, intents are orthogonal
        if overlap_percentage < 0.2:
            return True, 1.0 - overlap_percentage

        return False, overlap_percentage

    def attempt_auto_merge(self, dev1_intent: str, dev2_intent: str,
                          dev1_changes: str, dev2_changes: str,
                          conflict_id: str) -> Tuple[str, float]:
        """
        Attempt to automatically merge based on intents.

        Returns: (merge_result, confidence)
                merge_result: 'auto_merged' | 'manual_required' | 'expert_decision'
        """
        compatible, intent_confidence = self.analyze_intent_compatibility(dev1_intent, dev2_intent)

        if not compatible:
            return 'manual_required', 1.0 - intent_confidence

        # Check if changes are localized to different parts
        change_overlap = self._calculate_change_overlap(dev1_changes, dev2_changes)

        if change_overlap < 0.2:  # Very little change overlap
            result = 'auto_merged'
            confidence = min(intent_confidence, 1.0 - change_overlap)
        else:
            result = 'expert_decision'  # Expert should validate
            confidence = intent_confidence * (1.0 - change_overlap)

        # Record decision
        self.merge_decisions[conflict_id] = {
            'dev1_intent': dev1_intent,
            'dev2_intent': dev2_intent,
            'intent_confidence': intent_confidence,
            'change_overlap': change_overlap,
            'result': result,
            'confidence': confidence
        }

        return result, confidence

    def get_merge_candidates(self, min_confidence: float = 0.8) -> Dict:
        """Get conflicts that can be auto-merged"""
        candidates = [
            (conflict_id, decision)
            for conflict_id, decision in self.merge_decisions.items()
            if decision['result'] == 'auto_merged' and decision['confidence'] >= min_confidence
        ]

        return {
            'auto_merge_candidates': len(candidates),
            'candidates': candidates,
            'avg_confidence': sum(d['confidence'] for _, d in candidates) / len(candidates) if candidates else 0
        }

    def get_merge_success_rate(self) -> float:
        """Get success rate of auto-merges"""
        auto_merges = [d for d in self.merge_decisions.values() if d['result'] == 'auto_merged']

        if not auto_merges:
            return 0.0

        return sum(d['confidence'] for d in auto_merges) / len(auto_merges)

    def _calculate_change_overlap(self, changes1: str, changes2: str) -> float:
        """
        Calculate how much the changes overlap.

        Returns: score from 0 (no overlap) to 1 (complete overlap)
        """
        lines1 = set(changes1.lower().split('\n'))
        lines2 = set(changes2.lower().split('\n'))

        if not lines1 or not lines2:
            return 0.0

        overlap = lines1 & lines2
        total = lines1 | lines2

        return len(overlap) / len(total) if total else 0.0

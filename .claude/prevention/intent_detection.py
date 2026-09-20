"""
1A: Intent-Aware Path Detection
Detect when developers have overlapping work intents.
"""

from typing import List, Dict, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass


@dataclass
class DeveloperIntent:
    """Represents a developer's current work intent"""
    developer: str
    intent_description: str
    scope: List[str]  # affected functions/modules
    confidence: float  # 0-1: how confident
    timestamp: datetime


class IntentDetector:
    """Detects and tracks developer intents from activity logs"""

    def __init__(self):
        self.intents: Dict[str, DeveloperIntent] = {}
        self.historical_intents: List[DeveloperIntent] = []
        self.intent_keywords = {}  # cache for quick lookup

    def extract_intent_from_event(self, developer: str, event_data: Dict) -> Optional[DeveloperIntent]:
        """
        Extract intent from a development event.
        Looks at commit messages, PR descriptions, and code comments.
        """
        intent_text = ""
        confidence = 0.5

        if 'commit_message' in event_data:
            intent_text = event_data['commit_message']
            confidence = 0.8
        elif 'pr_description' in event_data:
            intent_text = event_data['pr_description']
            confidence = 0.7
        elif 'branch_name' in event_data:
            intent_text = event_data['branch_name'].replace('_', ' ').replace('-', ' ')
            confidence = 0.6

        if not intent_text:
            return None

        # Extract scope (affected modules/functions)
        scope = self._extract_scope(event_data.get('files_changed', []))

        intent = DeveloperIntent(
            developer=developer,
            intent_description=intent_text.strip(),
            scope=scope,
            confidence=confidence,
            timestamp=datetime.now()
        )

        return intent

    def register_intent(self, intent: DeveloperIntent):
        """Register a developer's intent"""
        self.intents[intent.developer] = intent
        self.historical_intents.append(intent)
        self._update_intent_keywords(intent)

    def detect_overlaps(self) -> List[Tuple[str, str, List[str]]]:
        """
        Detect overlapping intents between developers.
        Returns: List of (dev1, dev2, overlapping_modules)
        """
        overlaps = []
        developers = list(self.intents.keys())

        for i, dev1 in enumerate(developers):
            for dev2 in developers[i+1:]:
                intent1 = self.intents[dev1]
                intent2 = self.intents[dev2]

                # Check for scope overlap
                overlap = set(intent1.scope) & set(intent2.scope)

                if overlap:
                    overlaps.append((dev1, dev2, list(overlap)))

        return overlaps

    def get_developer_intent(self, developer: str) -> Optional[DeveloperIntent]:
        """Get current intent for a developer"""
        return self.intents.get(developer)

    def get_intent_compatibility(self, dev1: str, dev2: str) -> Tuple[bool, float]:
        """
        Check if two intents are compatible (non-conflicting).
        Returns: (compatible, confidence_score)
        """
        intent1 = self.intents.get(dev1)
        intent2 = self.intents.get(dev2)

        if not intent1 or not intent2:
            return True, 0.0

        # Same scope = likely incompatible
        overlap = set(intent1.scope) & set(intent2.scope)
        if overlap:
            return False, 1.0 - (len(overlap) / max(len(intent1.scope), len(intent2.scope)))

        # Check keyword overlap in descriptions
        words1 = set(intent1.intent_description.lower().split())
        words2 = set(intent2.intent_description.lower().split())
        keyword_overlap = len(words1 & words2) / len(words1 | words2) if (words1 | words2) else 0

        return keyword_overlap < 0.3, 1.0 - keyword_overlap

    def _extract_scope(self, files_changed: List[str]) -> List[str]:
        """Extract module/function scope from file changes"""
        scope = []

        for file_path in files_changed:
            # Extract module name (simplified - in production, would parse actual code)
            parts = file_path.replace('.py', '').split('/')
            if parts:
                scope.append(parts[-1])  # Use filename as module indicator

        return list(set(scope))  # Remove duplicates

    def _update_intent_keywords(self, intent: DeveloperIntent):
        """Update keyword index for quick searching"""
        keywords = intent.intent_description.lower().split()
        self.intent_keywords[intent.developer] = keywords

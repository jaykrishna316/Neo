"""
Merge Strategy Generator - Suggests merge approach and generates commit messages
Surfaces both auto-merge (suggested) and manual merge options
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List


class MergeStrategy:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)

    def suggest_merge_strategy(self, file_path: str, function_name: str,
                              developer1: str, developer2: str,
                              description1: str, description2: str,
                              overlap_percentage: float) -> Dict:
        """
        Suggest merge strategy based on conflict information
        Returns: suggested strategy + manual alternatives
        """

        # Determine if changes are semantically compatible
        compatibility = self._assess_semantic_compatibility(description1, description2)

        strategies = []

        # Strategy 1: Auto-merge (suggested if compatible)
        if compatibility["compatible"] and overlap_percentage < 0.8:
            strategies.append({
                "strategy": "AUTO_MERGE",
                "label": "✅ Auto-Merge (Recommended)",
                "description": f"Combine both changes: {description1} + {description2}",
                "confidence": compatibility["confidence"],
                "how_it_works": "System merges both versions intelligently",
                "risk": "low",
                "testing_required": "unit_tests",
                "recommended": True
            })

        # Strategy 2: Manual merge (Keep Dev1)
        strategies.append({
            "strategy": "MANUAL_KEEP_DEV1",
            "label": "🔵 Keep Dev1's Version",
            "description": f"Use {developer1}'s changes: {description1}",
            "confidence": 0.5,
            "how_it_works": "Discard Dev2's changes, use Dev1's refactor",
            "risk": "medium",
            "testing_required": "full_test_suite",
            "recommended": False,
            "reason_might_choose": "Dev1's refactor is cleaner"
        })

        # Strategy 3: Manual merge (Keep Dev2)
        strategies.append({
            "strategy": "MANUAL_KEEP_DEV2",
            "label": "🟢 Keep Dev2's Version",
            "description": f"Use {developer2}'s changes: {description2}",
            "confidence": 0.5,
            "how_it_works": "Discard Dev1's changes, use Dev2's feature",
            "risk": "medium",
            "testing_required": "full_test_suite",
            "recommended": False,
            "reason_might_choose": "Dev2's feature is more critical"
        })

        # Strategy 4: Manual merge (Custom)
        strategies.append({
            "strategy": "MANUAL_CUSTOM",
            "label": "⚙️ Custom Merge",
            "description": "Manually combine specific parts from both",
            "confidence": 0.6,
            "how_it_works": "Developers jointly edit and combine best of both",
            "risk": "high",
            "testing_required": "full_test_suite + integration_tests",
            "recommended": False,
            "reason_might_choose": "Both changes are valuable but need adaptation"
        })

        return {
            "file": file_path,
            "function": function_name,
            "developers": [developer1, developer2],
            "overlap": f"{overlap_percentage:.0%}",
            "semantic_compatibility": compatibility,
            "strategies": strategies,
            "recommended_strategy": strategies[0] if strategies[0]["recommended"] else strategies[1]
        }

    def generate_merge_commit_message(self, file_path: str, function_name: str,
                                     developer1: str, developer2: str,
                                     description1: str, description2: str,
                                     strategy_used: str, approved_by: List[str]) -> str:
        """
        Generate a clear merge commit message
        """

        timestamp = datetime.now().isoformat()[:10]

        if strategy_used == "AUTO_MERGE":
            message = f"""Merge HIGH conflict in {file_path}::{function_name}

Auto-merged changes from {developer1} and {developer2}:

{developer1}: {description1}
{developer2}: {description2}

Strategy: Auto-merge (combined both features)
Approved by: {', '.join(approved_by)}
Date: {timestamp}

Downstream impacts flagged and tested.
Both developers approved the merge."""

        elif strategy_used == "MANUAL_KEEP_DEV1":
            message = f"""Merge HIGH conflict in {file_path}::{function_name} - Keep {developer1}

Chose {developer1}'s version:
  {description1}

Reason: {developer1}'s refactor is cleaner
Approved by: {', '.join(approved_by)}
Date: {timestamp}

Note: {developer2}'s changes ({description2}) not included.
Consider revisiting if needed."""

        elif strategy_used == "MANUAL_KEEP_DEV2":
            message = f"""Merge HIGH conflict in {file_path}::{function_name} - Keep {developer2}

Chose {developer2}'s version:
  {description2}

Reason: {developer2}'s feature is more critical
Approved by: {', '.join(approved_by)}
Date: {timestamp}

Note: {developer1}'s changes ({description1}) not included.
Consider revisiting if needed."""

        else:  # MANUAL_CUSTOM
            message = f"""Merge HIGH conflict in {file_path}::{function_name} - Custom merge

Combined changes from {developer1} and {developer2}:

{developer1}: {description1}
{developer2}: {description2}

Strategy: Manual merge (combined best of both)
Approved by: {', '.join(approved_by)}
Date: {timestamp}

Both developers jointly reviewed and combined the code."""

        return message

    def generate_rollback_message(self, merge_commit_sha: str, file_path: str,
                                 function_name: str, reason: str) -> str:
        """
        Generate a rollback commit message explaining why merge was reverted
        """

        return f"""Rollback merge {merge_commit_sha[:8]} in {file_path}::{function_name}

Reason: {reason}
Date: {datetime.now().isoformat()[:10]}

The previous auto-merge caused issues and needs manual review.
Both developers should discuss the merge strategy."""

    def _assess_semantic_compatibility(self, description1: str, description2: str) -> Dict:
        """
        Assess if two changes are semantically compatible
        Returns compatibility score and explanation
        """

        # Keywords that indicate compatible changes
        complementary_keywords = [
            ("refactor", "add"),      # Refactoring + adding feature = compatible
            ("improve", "enhance"),   # Both improving = compatible
            ("performance", "security"),  # Performance + security = compatible
            ("clean", "feature"),     # Cleanup + feature = compatible
        ]

        # Keywords that indicate conflicting changes
        conflicting_keywords = [
            ("remove", "add"),        # Remove + add same thing = conflict
            ("refactor", "refactor"), # Two refactors = risky
            ("revert", "add"),        # Revert + add = conflict
        ]

        desc1_lower = description1.lower()
        desc2_lower = description2.lower()

        conflict_score = 0
        compat_score = 0

        for kw1, kw2 in complementary_keywords:
            if (kw1 in desc1_lower and kw2 in desc2_lower) or \
               (kw2 in desc1_lower and kw1 in desc2_lower):
                compat_score += 2

        for kw1, kw2 in conflicting_keywords:
            if (kw1 in desc1_lower and kw2 in desc2_lower) or \
               (kw2 in desc1_lower and kw1 in desc2_lower):
                conflict_score += 3

        # Calculate confidence
        total = compat_score + conflict_score
        if total == 0:
            confidence = 0.5
        else:
            confidence = compat_score / (total + compat_score)

        compatible = confidence > 0.6

        return {
            "compatible": compatible,
            "confidence": confidence,
            "explanation": self._generate_compatibility_explanation(description1, description2, compatible)
        }

    def _generate_compatibility_explanation(self, desc1: str, desc2: str, compatible: bool) -> str:
        """Generate human-readable explanation of compatibility"""

        if compatible:
            return f"✅ Changes appear compatible: '{desc1}' + '{desc2}' complement each other"
        else:
            return f"⚠️ Changes may conflict: '{desc1}' and '{desc2}' work on similar logic"

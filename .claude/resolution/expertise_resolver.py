"""
3A: Expertise-Based Conflict Resolution
Resolve conflicts based on developer expertise rather than arbitrary rules.
"""

from typing import Dict, Tuple, Optional


class ExpertiseResolver:
    """Resolves conflicts based on developer expertise levels"""

    def __init__(self):
        self.expertise_scores: Dict[str, Dict[str, float]] = {}  # dev -> resource -> score
        self.resolution_history: Dict[str, Dict] = {}

    def register_expertise(self, developer: str, resource: str, score: float):
        """Register expertise level for a developer on a resource"""
        if developer not in self.expertise_scores:
            self.expertise_scores[developer] = {}
        self.expertise_scores[developer][resource] = score

    def resolve_conflict(self, dev1: str, dev2: str, resource: str,
                        conflict_id: str) -> Tuple[str, float]:
        """
        Resolve conflict based on expertise.

        Returns: (winning_developer, confidence_score)
        """
        score1 = self.get_expertise(dev1, resource)
        score2 = self.get_expertise(dev2, resource)

        # Check for significant difference
        difference = abs(score1 - score2)

        if difference > 0.2:  # Significant expertise difference
            winner = dev1 if score1 > score2 else dev2
            confidence = min(difference, 1.0)
        else:
            # If expertise is similar, need other criteria
            winner = "manual_required"
            confidence = 0.5

        # Record resolution
        self.resolution_history[conflict_id] = {
            'dev1': dev1,
            'dev2': dev2,
            'resource': resource,
            'winner': winner,
            'dev1_score': score1,
            'dev2_score': score2,
            'confidence': confidence
        }

        return winner, confidence

    def get_expertise(self, developer: str, resource: str) -> float:
        """Get expertise score for a developer on a resource"""
        return self.expertise_scores.get(developer, {}).get(resource, 0.0)

    def get_expert_for_resource(self, resource: str) -> Optional[str]:
        """Get the top expert for a resource"""
        experts = []

        for dev, scores in self.expertise_scores.items():
            if resource in scores:
                experts.append((dev, scores[resource]))

        if not experts:
            return None

        return max(experts, key=lambda x: x[1])[0]

    def establish_hierarchy(self, resource: str) -> Dict:
        """Establish expertise hierarchy for a resource"""
        experts = []

        for dev, scores in self.expertise_scores.items():
            if resource in scores:
                experts.append((dev, scores[resource]))

        experts.sort(key=lambda x: x[1], reverse=True)

        return {
            'top_expert': experts[0] if experts else None,
            'hierarchy': [(dev, score) for dev, score in experts],
            'expert_count': len(experts)
        }

    def get_resolution_history(self, developer: str) -> Dict:
        """Get resolution history for a developer"""
        resolutions = []

        for conflict_id, record in self.resolution_history.items():
            if record['winner'] == developer:
                resolutions.append({
                    'conflict_id': conflict_id,
                    'resource': record['resource'],
                    'opponent': record['dev2'] if record['dev1'] == developer else record['dev1'],
                    'expertise_advantage': abs(record['dev1_score'] - record['dev2_score'])
                })

        return {
            'developer': developer,
            'conflicts_won': len(resolutions),
            'resolutions': resolutions
        }

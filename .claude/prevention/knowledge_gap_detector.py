"""
1E: Knowledge Gap Detection
Detect when developers silently work on code without consulting experts.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExpertProfile:
    """Expert profile for a resource"""
    expert: str
    resource: str
    expertise_score: float  # 0-1
    num_modifications: int
    last_modification: datetime
    mentorship_potential: bool = True


class KnowledgeGapDetector:
    """Detects knowledge gaps and silos in the team"""

    def __init__(self, expertise_threshold: float = 0.7):
        self.experts: Dict[str, ExpertProfile] = {}  # resource::expert -> profile
        self.developer_interactions: Dict[str, List[str]] = {}  # dev -> list of reviewed devs
        self.expertise_threshold = expertise_threshold
        self.gaps_detected: List[Dict] = []

    def register_expert(self, expert: str, resource: str,
                       expertise_score: float, num_modifications: int):
        """Register an expert for a resource"""
        key = f"{resource}::{expert}"
        self.experts[key] = ExpertProfile(
            expert=expert,
            resource=resource,
            expertise_score=expertise_score,
            num_modifications=num_modifications,
            last_modification=datetime.now()
        )

    def detect_gap(self, developer: str, expert: str, resource: str) -> Optional[Dict]:
        """
        Detect if a non-expert is working on expert knowledge without consulting expert.

        Returns: Gap information if detected
        """
        key = f"{resource}::{expert}"

        if key not in self.experts:
            return None

        expert_profile = self.experts[key]

        # Check if developer has recent interactions with expert
        has_interaction = (developer in self.developer_interactions and
                          expert in self.developer_interactions.get(developer, []))

        if expert_profile.expertise_score >= self.expertise_threshold and not has_interaction:
            gap = {
                'developer': developer,
                'expert': expert,
                'resource': resource,
                'expert_score': expert_profile.expertise_score,
                'risk_level': self._calculate_risk(expert_profile),
                'suggestion': f"Consider pairing with @{expert} for {resource}",
                'learning_opportunity': f"Learn from {expert}'s {expert_profile.num_modifications} modifications",
                'timestamp': datetime.now()
            }

            self.gaps_detected.append(gap)
            return gap

        return None

    def record_interaction(self, developer: str, reviewed_by: str):
        """Record that a developer was reviewed/mentored by another developer"""
        if developer not in self.developer_interactions:
            self.developer_interactions[developer] = []

        if reviewed_by not in self.developer_interactions[developer]:
            self.developer_interactions[developer].append(reviewed_by)

    def get_gap_for_developer(self, developer: str) -> List[Dict]:
        """Get all knowledge gaps for a developer"""
        return [g for g in self.gaps_detected if g['developer'] == developer]

    def get_high_risk_gaps(self) -> List[Dict]:
        """Get all high-risk knowledge gaps"""
        return [g for g in self.gaps_detected if g['risk_level'] in ['HIGH', 'CRITICAL']]

    def get_expert_for_resource(self, resource: str) -> Optional[str]:
        """Get the top expert for a resource"""
        resource_experts = [e for k, e in self.experts.items() if k.startswith(f"{resource}::")]

        if not resource_experts:
            return None

        # Sort by expertise score
        top_expert = sorted(resource_experts, key=lambda x: x.expertise_score, reverse=True)[0]
        return top_expert.expert if top_expert.expertise_score >= self.expertise_threshold else None

    def get_experts_for_resource(self, resource: str, min_score: float = None) -> List[ExpertProfile]:
        """Get all experts for a resource"""
        if min_score is None:
            min_score = self.expertise_threshold

        resource_experts = [e for k, e in self.experts.items() if k.startswith(f"{resource}::")]
        return sorted([e for e in resource_experts if e.expertise_score >= min_score],
                     key=lambda x: x.expertise_score, reverse=True)

    def suggest_pairing(self, developer: str, resource: str) -> Optional[str]:
        """Suggest a mentor for a developer on a resource"""
        expert = self.get_expert_for_resource(resource)

        if expert and expert != developer:
            return expert

        return None

    def get_knowledge_distribution(self, resource: str) -> Dict:
        """Get knowledge distribution for a resource"""
        experts = self.get_experts_for_resource(resource, min_score=0.0)

        if not experts:
            return {'distribution': 'unknown', 'risk': 'HIGH'}

        total_modifications = sum(e.num_modifications for e in experts)

        # Check if knowledge is concentrated
        top_expert_mods = experts[0].num_modifications if experts else 0
        concentration = top_expert_mods / total_modifications if total_modifications > 0 else 0

        return {
            'total_experts': len(experts),
            'top_expert': experts[0].expert if experts else None,
            'top_expert_score': experts[0].expertise_score if experts else 0,
            'knowledge_concentration': concentration,
            'at_risk': concentration > 0.8  # High concentration = risk
        }

    def _calculate_risk(self, expert_profile: ExpertProfile) -> str:
        """Calculate risk level for knowledge gap"""
        score = expert_profile.expertise_score
        mods = expert_profile.num_modifications

        if score >= 0.95 or mods > 50:
            return "CRITICAL"
        elif score >= 0.85 or mods > 20:
            return "HIGH"
        elif score >= 0.7 or mods > 5:
            return "MEDIUM"
        else:
            return "LOW"

    def print_status(self):
        """Print knowledge gap detector status"""
        print("\n👥 Knowledge Gap Detection Status")
        print("=" * 60)

        print(f"Total Experts Registered: {len(self.experts)}")
        print(f"Gaps Detected: {len(self.gaps_detected)}")

        high_risk = self.get_high_risk_gaps()
        if high_risk:
            print(f"\n🔴 High-Risk Gaps ({len(high_risk)}):")
            for gap in high_risk[:3]:
                print(f"  {gap['developer']} working on {gap['resource']}")
                print(f"    Expert: {gap['expert']} (score: {gap['expert_score']:.0%})")
                print(f"    Suggestion: {gap['suggestion']}")

        if not self.gaps_detected:
            print("\n✓ No knowledge gaps detected")

        print("=" * 60)


def create_expert_profiles_from_activity_log(activity_log) -> Dict[str, ExpertProfile]:
    """
    Helper function to create expert profiles from Neo 2.0's activity log.
    Integrates with Phase 4 (Provenance).
    """
    profiles = {}

    # In production, would read from activity_log.get_developer_history()
    # This is a placeholder showing the integration point

    return profiles

"""
3C: Multi-Agent Negotiation
Have autonomous agents negotiate when they disagree.
"""

from typing import Dict, Tuple, List
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AgentDecision:
    """Record of an agent's decision"""
    agent: str
    resource: str
    proposed_change: str
    confidence: float
    reasoning: str
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class AgentNegotiator:
    """Handles negotiation between autonomous agents on conflicts"""

    def __init__(self):
        self.agent_decisions: Dict[str, List[AgentDecision]] = {}
        self.negotiation_history: Dict[str, Dict] = {}
        self.policies: Dict[str, Dict] = {}  # Policy rules for negotiation

    def register_decision(self, decision: AgentDecision):
        """Register an agent's decision"""
        agent = decision.agent
        if agent not in self.agent_decisions:
            self.agent_decisions[agent] = []
        self.agent_decisions[agent].append(decision)

    def negotiate_conflict(self, agent1: str, agent2: str, resource: str,
                          conflict_id: str) -> Tuple[str, str, float]:
        """
        Negotiate between two agents on a conflict.

        Returns: (winning_agent, resolution_strategy, confidence)
        """
        # Get latest decisions from each agent
        decisions1 = self.agent_decisions.get(agent1, [])
        decisions2 = self.agent_decisions.get(agent2, [])

        if not decisions1 or not decisions2:
            return "manual_required", "insufficient_data", 0.0

        latest1 = decisions1[-1]
        latest2 = decisions2[-1]

        # Apply policies to determine winner
        winner, strategy, confidence = self._apply_negotiation_policies(
            agent1, latest1, agent2, latest2, resource
        )

        # Record negotiation
        self.negotiation_history[conflict_id] = {
            'agent1': agent1,
            'agent2': agent2,
            'resource': resource,
            'agent1_confidence': latest1.confidence,
            'agent2_confidence': latest2.confidence,
            'winner': winner,
            'strategy': strategy,
            'negotiation_confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }

        return winner, strategy, confidence

    def set_policy(self, policy_name: str, rules: Dict):
        """Set negotiation policy"""
        self.policies[policy_name] = rules

    def get_policy(self, policy_name: str) -> Dict:
        """Get a negotiation policy"""
        return self.policies.get(policy_name, {})

    def get_negotiation_history(self, agent: str) -> List[Dict]:
        """Get negotiation history for an agent"""
        history = []

        for conflict_id, record in self.negotiation_history.items():
            if record['agent1'] == agent or record['agent2'] == agent:
                history.append(record)

        return history

    def get_agent_consensus_rate(self, agent: str) -> float:
        """Get rate at which an agent's decisions win negotiations"""
        history = self.get_negotiation_history(agent)

        if not history:
            return 0.0

        wins = sum(1 for record in history if record['winner'] == agent)
        return wins / len(history)

    def _apply_negotiation_policies(self, agent1: str, decision1: AgentDecision,
                                   agent2: str, decision2: AgentDecision,
                                   resource: str) -> Tuple[str, str, float]:
        """Apply policies to determine negotiation outcome"""

        # Policy 1: Confidence-based
        if abs(decision1.confidence - decision2.confidence) > 0.3:
            winner = agent1 if decision1.confidence > decision2.confidence else agent2
            confidence = max(decision1.confidence, decision2.confidence)
            return winner, "confidence_based", confidence

        # Policy 2: Priority-based (if set)
        resource_policy = self.policies.get(f"resource_{resource}", {})
        if 'priority' in resource_policy:
            priority_map = resource_policy['priority']
            if agent1 in priority_map and agent2 in priority_map:
                winner = agent1 if priority_map[agent1] > priority_map[agent2] else agent2
                return winner, "priority_based", 0.8

        # Policy 3: Seniority/expertise-based (if set)
        seniority_policy = self.policies.get('seniority', {})
        if agent1 in seniority_policy and agent2 in seniority_policy:
            if seniority_policy[agent1] > seniority_policy[agent2]:
                return agent1, "seniority_based", 0.75
            else:
                return agent2, "seniority_based", 0.75

        # Default: Equal confidence, need manual resolution
        if decision1.confidence == decision2.confidence:
            return "manual_required", "equal_confidence", 0.5

        # Fallback
        return agent1, "default", 0.5

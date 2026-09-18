"""
Neo 3.0 Conflict Prevention Engine - Data Models

Defines all data structures used for conflict detection, prevention, understanding, and resolution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from enum import Enum


class AlertType(Enum):
    """Types of conflict alerts"""
    INTENT_OVERLAP = "intent_overlap"
    CONCURRENT_WORK = "concurrent_work"
    TEMPORAL_PREDICT = "temporal_predict"
    SEMANTIC_VIOLATION = "semantic_violation"
    KNOWLEDGE_GAP = "knowledge_gap"


class AlertSeverity(Enum):
    """Severity levels for alerts"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConflictType(Enum):
    """Types of conflicts that can occur"""
    CODE_MERGE = "code_merge"
    INTENT_MISMATCH = "intent_mismatch"
    SEMANTIC_VIOLATION = "semantic_violation"
    ARCHITECTURAL_VIOLATION = "architectural_violation"
    KNOWLEDGE_SILO = "knowledge_silo"


class ResolutionStrategy(Enum):
    """How a conflict was or should be resolved"""
    AUTO_MERGE = "auto_merge"
    EXPERTISE_BASED = "expertise_based"
    INTENT_BASED = "intent_based"
    MANUAL = "manual"
    AGENT_NEGOTIATED = "agent_negotiated"


@dataclass
class ConflictAlert:
    """Alert about a potential or actual conflict"""
    alert_type: AlertType
    severity: AlertSeverity
    developer_1: str
    developer_2: str
    resource: str
    reason: str
    timestamp: datetime
    suggested_action: str
    metadata: Dict = field(default_factory=dict)

    def to_dict(self):
        return {
            'alert_type': self.alert_type.value,
            'severity': self.severity.value,
            'developer_1': self.developer_1,
            'developer_2': self.developer_2,
            'resource': self.resource,
            'reason': self.reason,
            'timestamp': self.timestamp.isoformat(),
            'suggested_action': self.suggested_action,
            'metadata': self.metadata
        }


@dataclass
class IntentModel:
    """Represents a developer's intent for work"""
    developer: str
    resource: str
    intent_description: str
    timestamp: datetime
    scope: List[str]  # affected functions/modules
    related_commits: List[str] = field(default_factory=list)
    confidence: float = 1.0  # 0-1: how confident we are about this intent

    def overlaps_with(self, other: 'IntentModel') -> bool:
        """Check if two intents overlap on the same resources"""
        return bool(set(self.scope) & set(other.scope))


@dataclass
class WorkingSet:
    """Tracks what a developer is currently working on"""
    developer: str
    resources: List[str]  # file.py::function
    last_updated: datetime
    active: bool = True

    def overlaps_with(self, other: 'WorkingSet') -> Tuple[bool, List[str]]:
        """Check overlap and return overlapping resources"""
        overlap = list(set(self.resources) & set(other.resources))
        return len(overlap) > 0, overlap


@dataclass
class ConflictPrediction:
    """Prediction of a future conflict"""
    resource: str
    developer_1: str
    developer_2: str
    probability: float  # 0-1
    predicted_time: datetime
    reason: str
    prevention_suggestion: str

    def is_high_risk(self) -> bool:
        return self.probability > 0.7


@dataclass
class SemanticViolation:
    """Detected violation of a semantic invariant"""
    resource: str
    developer: str
    invariant_description: str
    violated_line: int
    severity: AlertSeverity
    fix_suggestion: str
    related_invariants: List[str] = field(default_factory=list)


@dataclass
class KnowledgeGap:
    """Detected gap in knowledge distribution"""
    resource: str
    expert_developer: str
    non_expert_developer: str
    expert_contribution_percentage: float
    risk_level: str  # LOW, MEDIUM, HIGH
    suggested_pairing: str
    learning_opportunity: str


@dataclass
class ConflictRecord:
    """Historical record of a conflict"""
    conflict_id: str
    conflict_type: ConflictType
    resource: str
    developer_1: str
    developer_2: str
    timestamp: datetime
    description: str
    resolution_strategy: ResolutionStrategy
    outcome: str
    led_to_bug: bool = False
    bug_severity: Optional[str] = None
    lessons_learned: List[str] = field(default_factory=list)

    def to_dict(self):
        return {
            'conflict_id': self.conflict_id,
            'conflict_type': self.conflict_type.value,
            'resource': self.resource,
            'developers': [self.developer_1, self.developer_2],
            'timestamp': self.timestamp.isoformat(),
            'resolution_strategy': self.resolution_strategy.value,
            'led_to_bug': self.led_to_bug,
            'bug_severity': self.bug_severity
        }


@dataclass
class ConflictPattern:
    """Identified pattern of conflicts"""
    pattern_id: str
    conflict_type: ConflictType
    frequency: int  # how many times this pattern occurred
    affected_resources: List[str]
    involved_developers: List[str]
    root_cause: str
    prevention_strategy: str
    last_occurrence: datetime
    improvement_percentage: Optional[float] = None  # if prevention was applied

    def to_dict(self):
        return {
            'pattern_id': self.pattern_id,
            'conflict_type': self.conflict_type.value,
            'frequency': self.frequency,
            'affected_resources': self.affected_resources,
            'root_cause': self.root_cause,
            'prevention_strategy': self.prevention_strategy
        }


@dataclass
class ConflictArchaeology:
    """Full archaeological record of a conflict"""
    conflict_id: str
    original_state: str  # code before either change
    developer_1_change: str  # what dev1 changed and why
    developer_2_change: str  # what dev2 changed and why
    conflicting_lines: List[Tuple[int, str]]  # (line_number, code)
    independent_changes: List[Tuple[int, str]]  # (line_number, code)
    dev1_intent: str
    dev2_intent: str
    intents_compatible: bool
    timestamp: datetime


@dataclass
class CausalityAnalysis:
    """Root cause analysis of a conflict"""
    conflict_id: str
    root_cause: str
    contributing_factors: List[str]
    timeline: List[Tuple[datetime, str]]  # sequence of events
    prevention_opportunities: List[str]  # where could this have been prevented?
    affected_invariants: List[str]
    similar_past_conflicts: List[str]


@dataclass
class DeveloperExpertise:
    """Expertise information for a developer"""
    developer: str
    resource: str
    expertise_score: float  # 0-1
    num_modifications: int
    last_modification: datetime
    review_authority: float  # 0-1: authority to make decisions
    mentorship_potential: bool
    knowledge_transfer_needed: bool


@dataclass
class IntentBasedMerge:
    """Result of intent-based conflict merging"""
    conflict_id: str
    developer_1_intent: str
    developer_2_intent: str
    intents_compatible: bool
    merge_result: str  # auto_merged | manual_required | expert_decision
    merged_code: Optional[str] = None
    merge_quality_score: float = 0.0  # 0-1


@dataclass
class AgentNegotiation:
    """Record of agent negotiation on a conflict"""
    negotiation_id: str
    agent_1: str
    agent_2: str
    conflicting_decisions: List[str]
    agent_1_reasoning: str
    agent_2_reasoning: str
    resolution: str
    resolution_agent: str  # which agent's preference won
    confidence: float  # 0-1: how confident in this resolution
    human_override: Optional[str] = None

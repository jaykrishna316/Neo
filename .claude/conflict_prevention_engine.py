"""
Neo 3.0 Conflict Prevention Engine - Core Orchestrator

Central engine that orchestrates all conflict prevention, understanding, and resolution layers.
Integrates with Neo 2.0's 5 phases and State Machine v2.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from conflict_models import (
    ConflictAlert, AlertType, AlertSeverity, ConflictType,
    IntentModel, WorkingSet, ConflictPrediction, ConflictPattern,
    ConflictRecord, DeveloperExpertise
)
from alert_system import AlertSystem, AlertBuilder


class ConflictPreventionEngine:
    """
    Core orchestrator for Neo 3.0 conflict prevention system.

    Manages all prevention (1A-1E), understanding (2A-2C), and resolution (3A-3C) layers.
    Integrates with Neo 2.0 foundation:
    - Phase 1: Event Model (intent extraction)
    - Phase 2: Handoffs (context understanding)
    - Phase 3: Context Invalidation (stale context detection)
    - Phase 4: Provenance (expertise tracking)
    - Phase 5: Autonomy (agent policies)
    - State Machine v2 (developer queuing)
    """

    def __init__(self):
        self.alert_system = AlertSystem()

        # Prevention layer data
        self.intent_models: Dict[str, IntentModel] = {}  # per developer
        self.working_sets: Dict[str, WorkingSet] = {}    # per developer
        self.conflict_predictions: List[ConflictPrediction] = []

        # Understanding layer data
        self.conflict_records: Dict[str, ConflictRecord] = {}  # conflict_id -> record
        self.conflict_patterns: Dict[str, ConflictPattern] = {}  # pattern_id -> pattern

        # Resolution layer data
        self.expert_map: Dict[str, DeveloperExpertise] = {}  # resource -> expertise

        # Neo 2.0 integrations
        self.activity_log = None  # Phase 1 integration
        self.handoff_engine = None  # Phase 2 integration
        self.context_invalidation = None  # Phase 3 integration
        self.provenance_engine = None  # Phase 4 integration
        self.autonomy_engine = None  # Phase 5 integration
        self.state_machine = None  # State Machine v2

        # Statistics
        self.stats = {
            'alerts_generated': 0,
            'conflicts_prevented': 0,
            'conflicts_resolved': 0,
            'patterns_identified': 0
        }

    # ============================================================
    # Initialization & Integration
    # ============================================================

    def integrate_with_neo2(self, activity_log, handoff_engine, context_invalidation,
                           provenance_engine, autonomy_engine, state_machine):
        """Integrate with Neo 2.0 components"""
        self.activity_log = activity_log
        self.handoff_engine = handoff_engine
        self.context_invalidation = context_invalidation
        self.provenance_engine = provenance_engine
        self.autonomy_engine = autonomy_engine
        self.state_machine = state_machine

    # ============================================================
    # LAYER 1: PREVENTION (1A-1E)
    # ============================================================

    def detect_intent_overlap(self, dev1: str, dev2: str) -> Optional[ConflictAlert]:
        """
        1A: Intent-Aware Path Detection
        Detect when two developers have overlapping work intents
        """
        if dev1 not in self.intent_models or dev2 not in self.intent_models:
            return None

        intent1 = self.intent_models[dev1]
        intent2 = self.intent_models[dev2]

        if intent1.overlaps_with(intent2):
            alert = (AlertBuilder()
                    .with_type(AlertType.INTENT_OVERLAP)
                    .with_severity(AlertSeverity.MEDIUM)
                    .with_developers(dev1, dev2)
                    .with_resource(', '.join(set(intent1.scope) & set(intent2.scope)))
                    .with_reason(f"{dev1} working on '{intent1.intent_description}', "
                                f"{dev2} working on '{intent2.intent_description}' - "
                                f"overlapping scope detected")
                    .with_suggestion(f"Coordinate between {dev1} and {dev2} to synchronize work")
                    .with_metadata('intent1', intent1.intent_description)
                    .with_metadata('intent2', intent2.intent_description)
                    .build())

            self.alert_system.emit_alert(alert)
            self.stats['alerts_generated'] += 1
            return alert

        return None

    def detect_concurrent_work(self, dev1: str, dev2: str) -> Optional[ConflictAlert]:
        """
        1B: Concurrent Work Detection
        Track overlapping working sets in real-time
        """
        if dev1 not in self.working_sets or dev2 not in self.working_sets:
            return None

        ws1 = self.working_sets[dev1]
        ws2 = self.working_sets[dev2]

        overlaps, overlap_resources = ws1.overlaps_with(ws2)

        if overlaps:
            alert = (AlertBuilder()
                    .with_type(AlertType.CONCURRENT_WORK)
                    .with_severity(AlertSeverity.MEDIUM)
                    .with_developers(dev1, dev2)
                    .with_resource(', '.join(overlap_resources))
                    .with_reason(f"Both developers working on: {', '.join(overlap_resources)}")
                    .with_suggestion(f"Developers are in the same neighborhood. Consider coordination.")
                    .with_metadata('overlapping_resources', overlap_resources)
                    .build())

            self.alert_system.emit_alert(alert)
            self.stats['alerts_generated'] += 1
            return alert

        return None

    def predict_conflict(self, dev1: str, dev2: str, resource: str,
                        hours_ahead: int = 1) -> Optional[ConflictPrediction]:
        """
        1C: Temporal Conflict Prediction
        Predict conflicts before they happen based on context invalidation
        """
        if not self.context_invalidation:
            return None

        try:
            invalidated = self.context_invalidation.get_invalidated_contexts(resource)

            # If context is invalidated and both devs are active in this area, high risk
            if invalidated and dev1 in self.working_sets and dev2 in self.working_sets:
                probability = 0.75
                prediction = ConflictPrediction(
                    resource=resource,
                    developer_1=dev1,
                    developer_2=dev2,
                    probability=probability,
                    predicted_time=datetime.now() + timedelta(hours=hours_ahead),
                    reason=f"Context invalidation detected in {resource} + concurrent work",
                    prevention_suggestion=f"Coordinate merge strategy before {hours_ahead} hour(s)"
                )

                self.conflict_predictions.append(prediction)

                if prediction.is_high_risk():
                    alert = (AlertBuilder()
                            .with_type(AlertType.TEMPORAL_PREDICT)
                            .with_severity(AlertSeverity.HIGH)
                            .with_developers(dev1, dev2)
                            .with_resource(resource)
                            .with_reason(f"High probability ({probability:.0%}) of conflict predicted")
                            .with_suggestion(prediction.prevention_suggestion)
                            .build())

                    self.alert_system.emit_alert(alert)
                    self.stats['alerts_generated'] += 1

                return prediction
        except Exception:
            pass

        return None

    def check_semantic_violations(self, developer: str, resource: str) -> List[ConflictAlert]:
        """
        1D: Semantic Invariant Checking
        Detect logical conflicts (invariant violations) that git can't see
        """
        # Placeholder for semantic analysis
        # In full implementation, would parse code and check contracts
        return []

    def detect_knowledge_gaps(self, developer: str, resource: str) -> Optional[ConflictAlert]:
        """
        1E: Knowledge Gap Detection
        Detect when developers silently work on code without consulting experts
        """
        if not self.provenance_engine:
            return None

        try:
            expert = self.provenance_engine.get_expert_for_resource(resource)
            if expert and expert != developer:
                expert_score = self.provenance_engine.get_developer_expertise(expert, resource)

                if expert_score > 0.8:  # High expertise
                    alert = (AlertBuilder()
                            .with_type(AlertType.KNOWLEDGE_GAP)
                            .with_severity(AlertSeverity.LOW)
                            .with_developers(developer, expert)
                            .with_resource(resource)
                            .with_reason(f"{expert} is the expert in this area (score: {expert_score:.0%})")
                            .with_suggestion(f"Consider pairing with @{expert} for better code quality")
                            .build())

                    self.alert_system.emit_alert(alert)
                    self.stats['alerts_generated'] += 1
                    return alert
        except Exception:
            pass

        return None

    # ============================================================
    # LAYER 2: UNDERSTANDING (2A-2C)
    # ============================================================

    def analyze_conflict_archaeology(self, conflict_id: str) -> Dict:
        """
        2A: Conflict Archaeology
        Show the full story of a conflict
        """
        if conflict_id not in self.conflict_records:
            return {}

        record = self.conflict_records[conflict_id]

        return {
            'conflict_id': conflict_id,
            'developers': [record.developer_1, record.developer_2],
            'resource': record.resource,
            'timestamp': record.timestamp,
            'type': record.conflict_type.value,
            'resolution_strategy': record.resolution_strategy.value,
            'outcome': record.outcome,
            'led_to_bug': record.led_to_bug
        }

    def analyze_conflict_patterns(self) -> List[ConflictPattern]:
        """
        2B: Conflict Pattern Analysis
        Learn from conflicts to identify systemic patterns
        """
        patterns = []

        # Group conflicts by resource
        by_resource = {}
        for conflict_id, record in self.conflict_records.items():
            if record.resource not in by_resource:
                by_resource[record.resource] = []
            by_resource[record.resource].append(record)

        # Identify patterns
        for resource, conflicts in by_resource.items():
            if len(conflicts) >= 2:  # Pattern = 2+ similar conflicts
                pattern = ConflictPattern(
                    pattern_id=f"pattern_{resource}_{datetime.now().timestamp()}",
                    conflict_type=conflicts[0].conflict_type,
                    frequency=len(conflicts),
                    affected_resources=[resource],
                    involved_developers=list(set([c.developer_1 for c in conflicts] +
                                                 [c.developer_2 for c in conflicts])),
                    root_cause=f"Multiple conflicts in {resource}",
                    prevention_strategy=f"Improve documentation or refactor {resource}",
                    last_occurrence=max([c.timestamp for c in conflicts])
                )
                patterns.append(pattern)
                self.conflict_patterns[pattern.pattern_id] = pattern

        return patterns

    def analyze_causality(self, conflict_id: str) -> Dict:
        """
        2C: Conflict Causality Tracking
        Root cause analysis of conflicts
        """
        if conflict_id not in self.conflict_records:
            return {}

        record = self.conflict_records[conflict_id]

        return {
            'conflict_id': conflict_id,
            'type': record.conflict_type.value,
            'description': record.description,
            'outcome': record.outcome,
            'led_to_bug': record.led_to_bug,
            'lessons_learned': record.lessons_learned
        }

    # ============================================================
    # LAYER 3: RESOLUTION (3A-3C)
    # ============================================================

    def resolve_by_expertise(self, dev1: str, dev2: str, resource: str) -> str:
        """
        3A: Expertise-Based Resolution
        Resolve conflicts based on developer expertise
        """
        if not self.provenance_engine:
            return "manual"

        try:
            score1 = self.provenance_engine.get_developer_expertise(dev1, resource)
            score2 = self.provenance_engine.get_developer_expertise(dev2, resource)

            if score1 > score2 + 0.2:  # Significant difference
                return dev1
            elif score2 > score1 + 0.2:
                return dev2
        except Exception:
            pass

        return "manual"

    def merge_by_intent(self, dev1_intent: str, dev2_intent: str) -> Tuple[bool, str]:
        """
        3B: Intent-Based Conflict Merging
        Auto-merge when intents are orthogonal (don't conflict)
        """
        # Simple heuristic: if intents are very different, they're likely orthogonal
        keywords1 = set(dev1_intent.lower().split())
        keywords2 = set(dev2_intent.lower().split())

        overlap = keywords1 & keywords2

        # If very little overlap in keywords, intents are orthogonal
        if len(overlap) < 2:
            return True, "auto_merge"

        return False, "manual_required"

    def negotiate_agent_conflict(self, agent1_decision: str, agent2_decision: str) -> str:
        """
        3C: Multi-Agent Negotiation
        Have agents negotiate when they disagree
        """
        # Placeholder for agent negotiation logic
        # In full implementation, would apply policies and decision rules
        if agent1_decision == agent2_decision:
            return agent1_decision

        return "manual_required"

    # ============================================================
    # Utilities
    # ============================================================

    def register_developer_intent(self, developer: str, resource: str,
                                  intent: str, scope: List[str]):
        """Register a developer's intent"""
        self.intent_models[developer] = IntentModel(
            developer=developer,
            resource=resource,
            intent_description=intent,
            timestamp=datetime.now(),
            scope=scope
        )

    def update_working_set(self, developer: str, resources: List[str]):
        """Update a developer's current working set"""
        self.working_sets[developer] = WorkingSet(
            developer=developer,
            resources=resources,
            last_updated=datetime.now(),
            active=True
        )

    def record_conflict(self, conflict: ConflictRecord):
        """Record a conflict for learning"""
        self.conflict_records[conflict.conflict_id] = conflict

    def get_statistics(self) -> Dict:
        """Get engine statistics"""
        return {
            **self.stats,
            'active_alerts': len(self.alert_system.active_alerts),
            'alert_statistics': self.alert_system.get_alert_statistics(),
            'patterns_identified': len(self.conflict_patterns),
            'conflicts_recorded': len(self.conflict_records)
        }

    def print_status(self):
        """Print engine status"""
        stats = self.get_statistics()
        print("\n🔧 Neo 3.0 Conflict Prevention Engine Status")
        print("=" * 50)
        print(f"Alerts Generated: {stats['alerts_generated']}")
        print(f"Active Alerts: {stats['active_alerts']}")
        print(f"Conflicts Prevented: {stats['conflicts_prevented']}")
        print(f"Patterns Identified: {stats['patterns_identified']}")
        print(f"Conflicts Recorded: {stats['conflicts_recorded']}")
        print("\nActive Alerts by Severity:")
        for severity, count in stats['alert_statistics']['by_severity'].items():
            print(f"  {severity.upper()}: {count}")
        print("=" * 50)

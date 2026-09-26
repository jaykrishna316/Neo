#!/usr/bin/env python3
"""
Optimized Coordination Machine - Optimization 2

Simplified Lock Mechanism using RiskLevel Classification

OPTIMIZATION 2: Simplify lock mechanism
- OLD: Explicit lock state management + separate risk_score (0-100)
- NEW: Use RiskLevel (LOW/MEDIUM/HIGH) directly as lock signal
- Impact: Simpler code, same behavior, faster (no extra state to manage)

Lock behavior is implicit in RiskLevel:
- LOW: no lock (safe to proceed)
- MEDIUM: lock active (queue behind current developer)
- HIGH: lock + escalation (conflict detected)

No explicit Lock() needed — RiskLevel.MEDIUM IS the lock.
"""

from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any, Tuple
import json
from pathlib import Path

from core.risk_classifier import RiskLevel, classify_risk


class CoordinationState(Enum):
    """States in the coordination state machine"""
    ACTIVE = "active"              # Developer actively working
    LOCKED = "locked"              # HIGH or MEDIUM risk detected
    WAITING = "waiting"            # Developer paused, sleeping
    COLLABORATE = "collaborate"    # Developers reached out to collaborate
    COMPLETED = "completed"        # Developer finished their work
    LOCK_REMOVED = "lock_removed"  # Event: lock cleared, ready to wake
    RESUMED = "resumed"            # Developer's Claude woke up and resuming
    COORDINATED = "coordinated"    # Collaboration resulted in coordination


class DecisionOption(Enum):
    """Options for Developer B when encountering lock"""
    COLLABORATE = "collaborate"    # Reach out and work together
    WAIT = "wait"                 # Pause and sleep until lock removed
    WRAP_UP_REQUEST = "wrap_up_request"  # Request Developer A to finish soon


class ConflictBlockedError(Exception):
    """Raised when generation is blocked by a MEDIUM/HIGH risk conflict"""
    pass


@dataclass
class GenerationCheckpoint:
    """Saved state for a paused Claude generation"""
    agent_id: str
    file_path: str
    region: str
    intent: str
    tokens_generated: int
    context_buffer: str
    timestamp: str

    def to_json(self):
        return asdict(self)


@dataclass
class CoordinationLogEntry:
    """Entry in the shared coordination log"""
    agent_id: str
    file_path: str
    region: str
    intent: str
    state: CoordinationState
    timestamp: str
    expires_at: str
    risk_level: Optional[str] = None  # Simplified: RiskLevel.value instead of risk_score
    conflict_with: Optional[List[str]] = None
    checkpoint: Optional[GenerationCheckpoint] = None
    decision: Optional[DecisionOption] = None

    def to_dict(self):
        d = asdict(self)
        d['state'] = self.state.value
        if self.checkpoint:
            d['checkpoint'] = self.checkpoint.to_json()
        if self.decision:
            d['decision'] = self.decision.value
        return d


class OptimizedCoordinationMachine:
    """
    OPTIMIZATION 2: Simplified state machine using RiskLevel as lock signal.

    Lock behavior is implicit in RiskLevel:
    - LOW: no lock (safe to proceed)
    - MEDIUM: lock active (queue behind current developer)
    - HIGH: lock + escalation (conflict detected)

    Workflow:
    1. Developer A logs ACTIVE state, starts working
    2. Developer B checks for conflicts
    3. Risk classifier returns RiskLevel (LOW/MEDIUM/HIGH)
    4. If MEDIUM or HIGH:
       - State -> LOCKED
       - Developer B gets decision options
       - If WAIT: State -> WAITING, saves checkpoint
    5. Developer A completes:
       - State -> COMPLETED
       - Fires lock_removed event
    6. Developer B wakes up:
       - State -> RESUMED
       - Resumes from checkpoint
    """

    def __init__(self, log_file: Path = Path(".devsync/coordination.log.json")):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.entries: List[CoordinationLogEntry] = []
        self.event_subscribers: Dict[str, List[Callable]] = {}
        self.checkpoints: Dict[str, GenerationCheckpoint] = {}
        self._load_log()

    def _load_log(self):
        """Load log from disk"""
        if self.log_file.exists():
            with open(self.log_file, 'r') as f:
                data = json.load(f)
                self.entries = [
                    CoordinationLogEntry(
                        agent_id=e['agent_id'],
                        file_path=e['file_path'],
                        region=e['region'],
                        intent=e['intent'],
                        state=CoordinationState(e['state']),
                        timestamp=e['timestamp'],
                        expires_at=e['expires_at'],
                        risk_level=e.get('risk_level'),
                        conflict_with=e.get('conflict_with'),
                    )
                    for e in data
                ]

    def _save_log(self):
        """Persist log to disk"""
        with open(self.log_file, 'w') as f:
            json.dump([e.to_dict() for e in self.entries], f, indent=2)

    def _clean_expired(self):
        """Remove expired entries"""
        now = datetime.now()
        self.entries = [
            e for e in self.entries
            if datetime.fromisoformat(e.expires_at) > now
        ]

    def log_intent(
        self,
        agent_id: str,
        file_path: str,
        region: str,
        intent: str,
        duration_minutes: int = 30
    ) -> CoordinationLogEntry:
        """Log a new work intent"""
        now = datetime.now()
        expires_at = now + timedelta(minutes=duration_minutes)

        entry = CoordinationLogEntry(
            agent_id=agent_id,
            file_path=file_path,
            region=region,
            intent=intent,
            state=CoordinationState.ACTIVE,
            timestamp=now.isoformat(),
            expires_at=expires_at.isoformat(),
            risk_level=RiskLevel.LOW.value,
        )

        self.entries.append(entry)
        self._save_log()
        return entry

    def check_conflicts(
        self,
        agent_id: str,
        file_path: str,
        region: str,
    ) -> Dict[str, Any]:
        """
        OPTIMIZATION 2: Check conflicts using RiskLevel directly.

        Returns:
            {
                'has_conflict': bool,
                'risk_level': RiskLevel (LOW/MEDIUM/HIGH),
                'conflicting_agents': [agent_ids],
                'state': ACTIVE | LOCKED,
                'decision_options': [COLLABORATE, WAIT, WRAP_UP_REQUEST] if LOCKED
            }
        """
        self._clean_expired()

        # Find active entries on same file
        conflicts = [
            e for e in self.entries
            if e.file_path == file_path
            and e.state == CoordinationState.ACTIVE
            and e.agent_id != agent_id
        ]

        if not conflicts:
            return {
                'has_conflict': False,
                'risk_level': RiskLevel.LOW,
                'conflicting_agents': [],
                'state': CoordinationState.ACTIVE,
                'decision_options': []
            }

        # OPTIMIZATION 2: Use risk classifier to get RiskLevel
        # Instead of calculating a 0-100 score, get the semantic level directly
        other_entry = conflicts[0]  # Check against first conflicting entry
        assessment = classify_risk(
            current_developer=agent_id,
            current_file=file_path,
            current_intent="",
            current_region=region,
            other_entry={
                'developer_id': other_entry.agent_id,
                'file_path': other_entry.file_path,
                'intent': other_entry.intent,
                'region': other_entry.region,
            }
        )

        risk_level = assessment.level

        # Map risk level to state and decision options
        # MEDIUM or HIGH -> LOCKED state
        if risk_level in (RiskLevel.MEDIUM, RiskLevel.HIGH):
            state = CoordinationState.LOCKED
            decision_options = [
                DecisionOption.COLLABORATE,
                DecisionOption.WAIT,
                DecisionOption.WRAP_UP_REQUEST
            ]
        else:
            state = CoordinationState.ACTIVE
            decision_options = []

        return {
            'has_conflict': True,
            'risk_level': risk_level,  # RiskLevel enum, not 0-100 score
            'conflicting_agents': [c.agent_id for c in conflicts],
            'conflict_details': [c.intent for c in conflicts],
            'state': state,
            'decision_options': decision_options
        }

    def check_generation_allowed(
        self,
        agent_id: str,
        file_path: str,
        region: str,
        decision: Optional[DecisionOption] = None
    ) -> Tuple[bool, str]:
        """
        Enforce generation gate: check if generation is allowed.

        OPTIMIZATION 2: Use RiskLevel directly.
        - LOW: always allowed
        - MEDIUM: allowed only with WAIT/COLLABORATE decision
        - HIGH: blocked unless decision provided

        Returns:
            (allowed: bool, message: str)
        """
        conflict_check = self.check_conflicts(agent_id, file_path, region)
        risk_level = conflict_check['risk_level']

        if risk_level == RiskLevel.LOW:
            return True, "LOW risk - safe to proceed"

        if risk_level == RiskLevel.MEDIUM:
            if decision is None:
                return False, (
                    f"MEDIUM risk lock active with {conflict_check['conflicting_agents']}. "
                    f"Choose WAIT/COLLABORATE/WRAP_UP_REQUEST."
                )
            self.handle_decision(agent_id, decision)
            return True, f"MEDIUM risk - proceeding with {decision.value}"

        # HIGH risk
        if decision is None:
            raise ConflictBlockedError(
                f"HIGH risk conflict detected with {conflict_check['conflicting_agents']}. "
                f"Must choose WAIT/COLLABORATE/WRAP_UP_REQUEST."
            )

        self.handle_decision(agent_id, decision)
        return True, f"HIGH risk - escalation triggered with {decision.value}"

    def handle_decision(
        self,
        agent_id: str,
        decision: DecisionOption,
        checkpoint: Optional[GenerationCheckpoint] = None
    ):
        """Handle Developer B's decision when encountering lock"""
        if decision == DecisionOption.WAIT:
            self._enter_waiting_state(agent_id, checkpoint)
        elif decision == DecisionOption.COLLABORATE:
            self._enter_collaboration_state(agent_id)
        elif decision == DecisionOption.WRAP_UP_REQUEST:
            self._request_wrap_up(agent_id)

    def _enter_waiting_state(
        self,
        agent_id: str,
        checkpoint: Optional[GenerationCheckpoint]
    ):
        """Developer B enters WAITING state with checkpoint"""
        entry = CoordinationLogEntry(
            agent_id=agent_id,
            file_path="waiting",
            region="",
            intent=f"Waiting for lock release",
            state=CoordinationState.WAITING,
            timestamp=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=2)).isoformat(),
            risk_level=RiskLevel.MEDIUM.value,
            checkpoint=checkpoint
        )
        self.entries.append(entry)
        if checkpoint:
            self.checkpoints[agent_id] = checkpoint
        self._save_log()

    def _enter_collaboration_state(self, agent_id: str):
        """Developer B initiated collaboration"""
        entry = CoordinationLogEntry(
            agent_id=agent_id,
            file_path="collaborate",
            region="",
            intent=f"Requested collaboration",
            state=CoordinationState.COLLABORATE,
            timestamp=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=1)).isoformat(),
        )
        self.entries.append(entry)
        self._save_log()

    def _request_wrap_up(self, agent_id: str):
        """Request Developer A to wrap up"""
        pass

    def mark_completed(self, agent_id: str):
        """Developer A marks work complete"""
        active = next(
            (e for e in self.entries if e.agent_id == agent_id and e.state == CoordinationState.ACTIVE),
            None
        )
        if active:
            active.state = CoordinationState.COMPLETED
            self._save_log()
            self._fire_event("lock_removed", {"agent": agent_id})

    def subscribe_to_event(self, event_type: str, callback: Callable):
        """Subscribe to an event"""
        if event_type not in self.event_subscribers:
            self.event_subscribers[event_type] = []
        self.event_subscribers[event_type].append(callback)

    def _fire_event(self, event_type: str, data: Dict[str, Any]):
        """Fire an event to all subscribers"""
        if event_type in self.event_subscribers:
            for callback in self.event_subscribers[event_type]:
                callback(data)

    def resume_from_checkpoint(self, agent_id: str) -> Optional[GenerationCheckpoint]:
        """Resume from saved checkpoint"""
        if agent_id in self.checkpoints:
            checkpoint = self.checkpoints[agent_id]
            return checkpoint
        return None

    def get_status(self, agent_id: Optional[str] = None):
        """Get current status of coordination"""
        if agent_id:
            entries = [e for e in self.entries if e.agent_id == agent_id]
        else:
            entries = self.entries

        return [{
            'agent': e.agent_id,
            'file': e.file_path,
            'state': e.state.value,
            'intent': e.intent,
            'risk_level': e.risk_level
        } for e in entries]

"""
Event-Driven Coordination State Machine for Multi-Agent File Access

This module implements a state machine that allows agents to:
- Log work intent with state
- Pause on conflicts with automatic wake-up
- Collaborate or wait based on risk level
- Resume from exact checkpoint when safe
"""

from enum import Enum
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
import json
import asyncio
from pathlib import Path


class CoordinationState(Enum):
    """States in the coordination state machine"""
    ACTIVE = "active"              # Developer actively working
    LOCKED = "locked"              # High risk conflict detected
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


@dataclass
class GenerationCheckpoint:
    """Saved state for a paused Claude generation"""
    agent_id: str
    file_path: str
    region: str
    intent: str
    tokens_generated: int
    context_buffer: str  # The prompt/context so far
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
    risk_score: Optional[int] = None
    conflict_with: Optional[List[str]] = None  # List of agent IDs
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


class CoordinationStateMachine:
    """
    Manages state transitions for multi-agent file coordination.

    Workflow:
    1. Developer A logs ACTIVE state, starts working
    2. Developer B checks for conflicts
    3. If HIGH risk:
       - State -> LOCKED
       - Developer B gets decision options
       - If WAIT: State -> WAITING, saves checkpoint, subscribes to event
       - If COLLABORATE: State -> COLLABORATE, notifies both devs
    4. Developer A completes:
       - State -> COMPLETED
       - Fires lock_removed event
    5. Developer B wakes up:
       - State -> RESUMED
       - Resumes from checkpoint
       - State -> ACTIVE (now generating)
    """

    def __init__(self, log_file: Path = Path(".devsync/coordination.log.json")):
        self.log_file = log_file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.entries: List[CoordinationLogEntry] = []
        self.event_subscribers: Dict[str, List[Callable]] = {}  # event_type -> callbacks
        self.checkpoints: Dict[str, GenerationCheckpoint] = {}  # agent_id -> checkpoint
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
                        risk_score=e.get('risk_score'),
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
        Check for conflicts when a new agent wants to work.

        Returns:
            {
                'has_conflict': bool,
                'risk_score': 0-100,
                'conflicting_agents': [agent_ids],
                'state': ACTIVE | LOCKED,
                'decision_options': [COLLABORATE, WAIT, WRAP_UP_REQUEST]
            }
        """
        self._clean_expired()

        # Find active entries on same file/region
        conflicts = [
            e for e in self.entries
            if e.file_path == file_path
            and e.state == CoordinationState.ACTIVE
            and e.agent_id != agent_id
            and self._regions_overlap(e.region, region)
        ]

        if not conflicts:
            return {
                'has_conflict': False,
                'risk_score': 0,
                'conflicting_agents': [],
                'state': CoordinationState.ACTIVE,
                'decision_options': []
            }

        # Calculate risk score
        risk_score = self._calculate_risk(conflicts, agent_id)

        # Determine state and options
        if risk_score >= 70:
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
            'risk_score': risk_score,
            'conflicting_agents': [c.agent_id for c in conflicts],
            'conflict_details': [c.intent for c in conflicts],
            'state': state,
            'decision_options': decision_options
        }

    def _regions_overlap(self, region1: str, region2: str) -> bool:
        """Check if two region strings overlap"""
        # Simple check for now: if both mention same function or overlapping lines
        # In production, this would use AST parsing
        return "lines" in region1 and "lines" in region2

    def _calculate_risk(self, conflicts: List[CoordinationLogEntry], agent_id: str) -> int:
        """Calculate risk score 0-100"""
        score = 0

        # Conflict count
        score += min(len(conflicts) * 30, 30)

        # Type severity (assume modification = high risk)
        score += 25  # Default high risk for any overlap

        # Time pressure (longer active = higher risk)
        now = datetime.now()
        for conflict in conflicts:
            elapsed = (now - datetime.fromisoformat(conflict.timestamp)).total_seconds()
            if elapsed > 1800:  # 30+ minutes
                score += 10

        return min(score, 100)

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
            intent=f"Waiting for conflict resolution",
            state=CoordinationState.WAITING,
            timestamp=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(hours=2)).isoformat(),
            checkpoint=checkpoint
        )
        self.entries.append(entry)
        if checkpoint:
            self.checkpoints[agent_id] = checkpoint
        self._save_log()
        print(f"✓ {agent_id} entered WAITING state. Checkpoint saved.")

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
        print(f"✓ {agent_id} initiated COLLABORATION. Notification sent.")

    def _request_wrap_up(self, agent_id: str):
        """Request Developer A to wrap up"""
        print(f"✓ {agent_id} requesting wrap-up from active developers")

    def mark_completed(self, agent_id: str):
        """Developer A marks work complete"""
        # Find active entry
        active = next(
            (e for e in self.entries if e.agent_id == agent_id and e.state == CoordinationState.ACTIVE),
            None
        )
        if active:
            active.state = CoordinationState.COMPLETED
            self._save_log()
            print(f"✓ {agent_id} marked COMPLETED")

            # Fire lock_removed event
            self._fire_event("lock_removed", {"agent": agent_id})

    def subscribe_to_event(self, event_type: str, callback: Callable):
        """Subscribe to an event (e.g., 'lock_removed')"""
        if event_type not in self.event_subscribers:
            self.event_subscribers[event_type] = []
        self.event_subscribers[event_type].append(callback)

    def _fire_event(self, event_type: str, data: Dict[str, Any]):
        """Fire an event to all subscribers"""
        if event_type in self.event_subscribers:
            for callback in self.event_subscribers[event_type]:
                callback(data)

    async def await_event(self, event_type: str, timeout_seconds: int = 3600):
        """Async wait for an event (non-blocking sleep)"""
        event_received = asyncio.Event()

        def on_event(data):
            event_received.set()

        self.subscribe_to_event(event_type, on_event)

        try:
            await asyncio.wait_for(event_received.wait(), timeout=timeout_seconds)
            return True
        except asyncio.TimeoutError:
            return False

    def resume_from_checkpoint(self, agent_id: str) -> Optional[GenerationCheckpoint]:
        """Resume from saved checkpoint"""
        if agent_id in self.checkpoints:
            checkpoint = self.checkpoints[agent_id]
            print(f"✓ {agent_id} RESUMED from checkpoint")
            print(f"  Context buffer: {len(checkpoint.context_buffer)} chars")
            print(f"  Tokens generated so far: {checkpoint.tokens_generated}")
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
            'risk_score': e.risk_score
        } for e in entries]


# Example Usage
if __name__ == "__main__":
    sm = CoordinationStateMachine()

    print("=" * 70)
    print("SCENARIO: Two Agents Working on Same File")
    print("=" * 70)

    # Developer A starts working
    print("\n1️⃣ Developer A (Claude) logs intent:")
    dev_a = sm.log_intent(
        agent_id="claude-agent-1",
        file_path="src/auth.py",
        region="login_user (lines 20-40)",
        intent="Refactor login_user for better error handling"
    )
    print(f"   State: {dev_a.state.value}")
    print(f"   File: {dev_a.file_path} {dev_a.region}")

    # Developer B checks for conflicts
    print("\n2️⃣ Developer B (Devin) checks before proceeding:")
    check_result = sm.check_conflicts(
        agent_id="devin-agent",
        file_path="src/auth.py",
        region="add_validation (lines 25-50)"
    )
    print(f"   Has conflict: {check_result['has_conflict']}")
    print(f"   Risk score: {check_result['risk_score']}/100")
    print(f"   State: {check_result['state'].value}")
    print(f"   Conflicting with: {check_result['conflicting_agents']}")

    if check_result['state'] == CoordinationState.LOCKED:
        print(f"   ⚠️  HIGH RISK LOCK DETECTED")
        print(f"   Decision options: {[opt.value for opt in check_result['decision_options']]}")

    # Developer B chooses to WAIT
    print("\n3️⃣ Developer B (Devin) chooses to WAIT:")
    checkpoint = GenerationCheckpoint(
        agent_id="devin-agent",
        file_path="src/auth.py",
        region="lines 25-50",
        intent="add validation to login_user",
        tokens_generated=150,
        context_buffer="Devin is adding validation checks...",
        timestamp=datetime.now().isoformat()
    )
    sm.handle_decision(
        agent_id="devin-agent",
        decision=DecisionOption.WAIT,
        checkpoint=checkpoint
    )

    # Developer A finishes
    print("\n4️⃣ Developer A (Claude) finishes work:")
    sm.mark_completed("claude-agent-1")

    # Developer B resumes
    print("\n5️⃣ Developer B (Devin) wakes up from event:")
    resumed = sm.resume_from_checkpoint("devin-agent")
    if resumed:
        print(f"   ✓ Ready to continue generating")
        print(f"   Can now safely access: {resumed.file_path}")

    # Final status
    print("\n" + "=" * 70)
    print("Final Coordination Status:")
    print("=" * 70)
    for status in sm.get_status():
        print(f"  {status['agent']}: {status['state']} on {status['file']}")

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


class ConflictBlockedError(Exception):
    """Raised when code generation is blocked due to HIGH_RISK conflict"""
    def __init__(self, conflict_type: str, risk_score: int, blocking_agents: List[str]):
        self.conflict_type = conflict_type
        self.risk_score = risk_score
        self.blocking_agents = blocking_agents
        super().__init__(
            f"HIGH_RISK conflict detected (score: {risk_score}/100). "
            f"Code generation blocked. Blocking agents: {', '.join(blocking_agents)}. "
            f"Choose: WAIT (pause with checkpoint), COLLABORATE (coordinate), or WRAP_UP_REQUEST."
        )


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
        Uses refined line/function-level detection, not just file-level.

        Returns:
            {
                'has_conflict': bool,
                'conflict_type': 'none' | 'caution' | 'high_risk',
                'risk_score': 0-100,
                'conflicting_agents': [agent_ids],
                'state': ACTIVE | LOCKED,
                'decision_options': [COLLABORATE, WAIT, WRAP_UP_REQUEST],
                'message': human-readable warning
            }
        """
        self._clean_expired()

        # Find active entries on same file
        same_file = [
            e for e in self.entries
            if e.file_path == file_path
            and e.state == CoordinationState.ACTIVE
            and e.agent_id != agent_id
        ]

        if not same_file:
            return {
                'has_conflict': False,
                'conflict_type': 'none',
                'risk_score': 0,
                'conflicting_agents': [],
                'state': CoordinationState.ACTIVE,
                'decision_options': [],
                'message': 'No conflicts detected'
            }

        # Check line/function-level overlap
        actual_conflicts = [
            e for e in same_file
            if self._regions_overlap(e.region, region)
        ]

        # No actual line/function overlap
        if not actual_conflicts:
            return {
                'has_conflict': True,
                'conflict_type': 'caution',
                'risk_score': 25,  # Low risk
                'conflicting_agents': [e.agent_id for e in same_file],
                'conflict_details': [e.intent for e in same_file],
                'state': CoordinationState.ACTIVE,
                'decision_options': [],  # No forced wait
                'message': f'⚠️  Caution: Other agents working on {file_path} but in different sections. Proceed with caution.'
            }

        # Actual line/function overlap = HIGH RISK
        risk_score = self._calculate_risk(actual_conflicts, agent_id)

        return {
            'has_conflict': True,
            'conflict_type': 'high_risk',
            'risk_score': risk_score,
            'conflicting_agents': [c.agent_id for c in actual_conflicts],
            'conflict_details': [c.intent for c in actual_conflicts],
            'state': CoordinationState.LOCKED,
            'decision_options': [
                DecisionOption.COLLABORATE,
                DecisionOption.WAIT,
                DecisionOption.WRAP_UP_REQUEST
            ],
            'message': f'🚨 HIGH RISK: {len(actual_conflicts)} agent(s) touching overlapping lines/functions. Recommendation: {", ".join([opt.value for opt in [DecisionOption.WAIT, DecisionOption.COLLABORATE]])}'
        }

    def check_generation_allowed(
        self,
        agent_id: str,
        file_path: str,
        region: str,
        decision_made: Optional[DecisionOption] = None
    ) -> Dict[str, Any]:
        """
        ENFORCEMENT GATE: Check if code generation is allowed.

        Raises ConflictBlockedError if:
        - HIGH_RISK conflict detected AND
        - No valid decision has been made (WAIT/COLLABORATE/WRAP_UP_REQUEST)

        Returns:
            {
                'allowed': bool,
                'reason': str,
                'decision_status': 'none' | 'pending_acknowledgment' | 'confirmed',
                'blocking_agents': [agent_ids]
            }
        """
        conflict_check = self.check_conflicts(agent_id, file_path, region)

        # LOW/CAUTION risk - always allowed
        if conflict_check['conflict_type'] in ['none', 'caution']:
            return {
                'allowed': True,
                'reason': 'No HIGH_RISK conflict detected',
                'decision_status': 'not_required',
                'blocking_agents': []
            }

        # HIGH_RISK requires valid decision
        if conflict_check['conflict_type'] == 'high_risk':
            # Decision not made - BLOCK
            if not decision_made:
                raise ConflictBlockedError(
                    conflict_type='high_risk',
                    risk_score=conflict_check['risk_score'],
                    blocking_agents=conflict_check['conflicting_agents']
                )

            # Decision made but not yet acknowledged by blocking agent
            decision_status = self._check_decision_acknowledgment(
                agent_id,
                decision_made,
                conflict_check['conflicting_agents']
            )

            if decision_status == 'pending_acknowledgment':
                raise ConflictBlockedError(
                    conflict_type='high_risk_pending_ack',
                    risk_score=conflict_check['risk_score'],
                    blocking_agents=conflict_check['conflicting_agents']
                )

            return {
                'allowed': True,
                'reason': f'Decision confirmed: {decision_made.value}',
                'decision_status': decision_status,
                'blocking_agents': []
            }

    def _check_decision_acknowledgment(
        self,
        agent_id: str,
        decision: DecisionOption,
        conflicting_agents: List[str]
    ) -> str:
        """
        Check if decision requires mutual acknowledgment and if it's been received.

        Returns: 'confirmed' | 'pending_acknowledgment'
        """
        if decision == DecisionOption.WAIT:
            # WAIT requires blocking agent to acknowledge they know someone is waiting
            # Check if blocking agent(s) have logged acknowledgment
            blocking_agent = conflicting_agents[0] if conflicting_agents else None
            if blocking_agent:
                ack = self._find_acknowledgment(blocking_agent, agent_id, "wait_acknowledged")
                return "confirmed" if ack else "pending_acknowledgment"
            return "confirmed"

        elif decision == DecisionOption.COLLABORATE:
            # COLLABORATE requires both agents to agree
            blocking_agent = conflicting_agents[0] if conflicting_agents else None
            if blocking_agent:
                ack = self._find_acknowledgment(blocking_agent, agent_id, "collaborate_confirmed")
                return "confirmed" if ack else "pending_acknowledgment"
            return "confirmed"

        return "confirmed"  # WRAP_UP_REQUEST doesn't require acknowledgment

    def _find_acknowledgment(
        self,
        target_agent: str,
        requesting_agent: str,
        ack_type: str
    ) -> bool:
        """Check if target agent has acknowledged the decision"""
        for entry in self.entries:
            if (entry.agent_id == target_agent and
                entry.intent.startswith(f"ACK:{ack_type}") and
                requesting_agent in entry.intent):
                # Check if acknowledgment is recent (within last 5 minutes)
                ack_time = datetime.fromisoformat(entry.timestamp)
                if (datetime.now() - ack_time).total_seconds() < 300:
                    return True
        return False

    def acknowledge_wait(self, agent_id: str, waiting_agent: str):
        """Blocking agent acknowledges that another agent is waiting"""
        entry = CoordinationLogEntry(
            agent_id=agent_id,
            file_path="acknowledgment",
            region="",
            intent=f"ACK:wait_acknowledged:{waiting_agent}",
            state=CoordinationState.ACTIVE,
            timestamp=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(minutes=5)).isoformat()
        )
        self.entries.append(entry)
        self._save_log()
        print(f"✓ {agent_id} acknowledged that {waiting_agent} is waiting")

    def acknowledge_collaborate(self, agent_id: str, initiating_agent: str):
        """Agent acknowledges collaboration request"""
        entry = CoordinationLogEntry(
            agent_id=agent_id,
            file_path="acknowledgment",
            region="",
            intent=f"ACK:collaborate_confirmed:{initiating_agent}",
            state=CoordinationState.COLLABORATE,
            timestamp=datetime.now().isoformat(),
            expires_at=(datetime.now() + timedelta(minutes=5)).isoformat()
        )
        self.entries.append(entry)
        self._save_log()
        print(f"✓ {agent_id} confirmed collaboration with {initiating_agent}")

    def _regions_overlap(self, region1: str, region2: str) -> bool:
        """
        Check if two region strings have ACTUAL line/function overlap.
        Returns True only if they touch the same lines or functions.

        Format: "function_name (lines X-Y)" or "lines X-Y"
        Example: "login_user (lines 20-40)" overlaps with "validate_creds (lines 25-35)"
        """
        import re

        # Extract line ranges
        lines1 = self._extract_line_range(region1)
        lines2 = self._extract_line_range(region2)

        # Extract function names
        func1 = self._extract_function_name(region1)
        func2 = self._extract_function_name(region2)

        # Same function = overlap
        if func1 and func2 and func1 == func2:
            return True

        # No line info = assume no overlap
        if not lines1 or not lines2:
            return False

        # Check line overlap
        start1, end1 = lines1
        start2, end2 = lines2
        return not (end1 < start2 or end2 < start1)  # Overlap if NOT mutually exclusive

    def _extract_line_range(self, region: str) -> Optional[tuple]:
        """Extract (start, end) line numbers from region string"""
        import re
        match = re.search(r'lines?\s+(\d+)-(\d+)', region)
        if match:
            return (int(match.group(1)), int(match.group(2)))
        return None

    def _extract_function_name(self, region: str) -> Optional[str]:
        """Extract function name from region string"""
        import re
        match = re.search(r'(\w+)\s*\(', region)
        if match:
            return match.group(1)
        return None

    def _calculate_risk(self, conflicts: List[CoordinationLogEntry], agent_id: str) -> int:
        """
        Calculate risk score 0-100 for actual line/function conflicts.

        Factors:
        - Conflict count (multiple agents = higher risk)
        - Line overlap degree (exact same lines = highest risk)
        - Time pressure (how long has conflict been active)
        - Conflict type (rename/delete > modification > read)
        """
        score = 0

        # Number of conflicting agents (30 points)
        conflict_count = min(len(conflicts), 3)
        score += conflict_count * 20  # 20 per agent, max 60

        # Line overlap severity (30 points)
        # Assume if we're here, there's line overlap
        # More specific functions = higher risk
        if any("function" in c.intent.lower() for c in conflicts):
            score += 30
        else:
            score += 25

        # Time pressure (20 points)
        # Longer active conflicts = higher risk
        now = datetime.now()
        max_elapsed = 0
        for conflict in conflicts:
            elapsed = (now - datetime.fromisoformat(conflict.timestamp)).total_seconds()
            max_elapsed = max(max_elapsed, elapsed)

        if max_elapsed > 1800:  # 30+ minutes
            score += 20
        elif max_elapsed > 900:  # 15+ minutes
            score += 10
        else:
            score += 5

        # Intent severity (20 points)
        # Refactoring/renaming = higher risk
        high_risk_keywords = ["refactor", "rename", "delete", "rewrite"]
        for conflict in conflicts:
            if any(keyword in conflict.intent.lower() for keyword in high_risk_keywords):
                score += 15
                break

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

    def check_wait_timeout(
        self,
        waiting_agent: str,
        blocking_agent: str,
        escalate_after_minutes: int = 30
    ) -> Dict[str, Any]:
        """
        ESCALATION GATE: Check if waiting agent has exceeded timeout.

        If blocking agent has been active longer than escalate_after_minutes,
        escalate to automatic release or escalation message.

        Returns:
            {
                'status': 'waiting' | 'timeout' | 'escalated',
                'elapsed_minutes': int,
                'escalation_action': str
            }
        """
        # Find blocking agent's active entry
        blocking_entry = next(
            (e for e in self.entries
             if e.agent_id == blocking_agent and e.state == CoordinationState.ACTIVE),
            None
        )

        if not blocking_entry:
            return {
                'status': 'completed',
                'elapsed_minutes': 0,
                'escalation_action': 'none'
            }

        # Calculate elapsed time
        now = datetime.now()
        elapsed = (now - datetime.fromisoformat(blocking_entry.timestamp)).total_seconds() / 60

        if elapsed > escalate_after_minutes:
            # Timeout exceeded - escalate
            return {
                'status': 'timeout',
                'elapsed_minutes': int(elapsed),
                'escalation_action': 'force_release',
                'message': f'⚠️  Blocking agent {blocking_agent} exceeded {escalate_after_minutes}min timeout. Releasing {waiting_agent}.'
            }

        return {
            'status': 'waiting',
            'elapsed_minutes': int(elapsed),
            'escalation_action': 'none',
            'message': f'{waiting_agent} waiting for {blocking_agent}. Elapsed: {int(elapsed)}min / {escalate_after_minutes}min timeout'
        }

    def force_release_lock(self, blocking_agent: str, waiting_agents: List[str]):
        """
        Force release a lock if blocking agent exceeds timeout.

        This is a last-resort enforcement when coordination fails.
        """
        # Mark blocking agent as completed
        active = next(
            (e for e in self.entries
             if e.agent_id == blocking_agent and e.state == CoordinationState.ACTIVE),
            None
        )

        if active:
            active.state = CoordinationState.COMPLETED
            self._save_log()
            print(f"⚠️  FORCE RELEASE: {blocking_agent} exceeded timeout. Lock released.")

            # Wake all waiting agents
            for waiting_agent in waiting_agents:
                self._fire_event("lock_removed", {
                    "agent": blocking_agent,
                    "reason": "timeout_exceeded",
                    "force_released": True
                })
                print(f"🔔 {waiting_agent} woken: blocking agent exceeded timeout")

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

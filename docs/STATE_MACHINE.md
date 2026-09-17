# Neo Coordination State Machine

## Overview

The Neo coordination state machine manages multi-agent file access by detecting conflicts before code generation and enforcing safe execution through state transitions. Agents move through distinct states as they encounter conflicts, pause, and resume work.

## States

### 1. **ACTIVE**
- **When**: Agent is actively generating code
- **Transitions to**: LOCKED (if conflict detected), COMPLETED (when done)
- **Checkpoint**: None stored
- **Example**: Agent A starts writing OAuth2 logic in `auth.py`

### 2. **LOCKED**
- **When**: High-risk conflict detected (risk score ≥ 70)
- **Entry condition**: Agent B checks conflicts and finds Agent A working on overlapping code
- **Agent's options**:
  - **WAIT**: Pause and sleep until lock releases (→ WAITING)
  - **COLLABORATE**: Coordinate with other agents (→ COLLABORATE)
  - **WRAP_UP_REQUEST**: Request holding agent to finish soon
- **Duration**: Persists until Agent B chooses an action
- **Example**: Agent B wants to add validation to same function as Agent A

### 3. **WAITING**
- **When**: Agent B chose WAIT from LOCKED state
- **Entry checkpoint**: Context buffer, tokens generated, intent, region saved
- **Subscriptions**: Agent B subscribes to `lock_removed` event
- **Timeout**: 2 hours (auto-cleans stale entries)
- **Next state**: RESUMED (when event fires)
- **Example**: Agent B's generation paused; checkpoint holds 150 tokens of context

### 4. **RESUMED**
- **When**: Waiting agent wakes up from `lock_removed` event
- **Checkpoint recovery**: Full context restored from checkpoint
- **Tokens preserved**: Can resume mid-generation with same prompt state
- **Next state**: ACTIVE (resumes generating)
- **Example**: Agent A finishes; Agent B wakes and continues from saved point

### 5. **ACTIVE** (resumed)
- **After**: Agent resumes from checkpoint
- **No friction**: Already analyzed conflicts, can generate freely
- **Example**: Agent B generates remaining validation code

### 6. **COMPLETED**
- **When**: Agent A marks work done
- **Triggers**: `lock_removed` event (fires automatically)
- **To waiting agents**: Wakes any agents in WAITING state
- **Example**: Agent A finishes OAuth2 work, triggers event

### 7. **COLLABORATE**
- **When**: Agent B chose COLLABORATE from LOCKED state
- **Notification**: Both agents notified of coordination request
- **Next state**: COORDINATED or manual sync
- **Example**: Agents coordinate in real-time on overlapping changes

### 8. **LOCK_REMOVED** (event)
- **When**: Fired by completing agent or 30-min timeout
- **Payload**: `{"agent": holding_agent_id, "escalated": bool, "waiting_agents": [...]}`
- **Subscribers**: All agents in WAITING state on same file
- **Result**: Wakes all subscribers

### 9. **COORDINATED**
- **When**: Collaboration resulted in coordination
- **Example**: Agents agreed on API changes and synchronized work

## State Transition Flows

### Scenario 1: Conflict Detection & Wait Recovery

```
Agent A                          Agent B
   │                               │
   ├─ log_intent()                 │
   │  state: ACTIVE                │
   │                               │
   │                        ┌──────┴──────────┐
   │                        │                 │
   │               ┌────────▶ CONFLICT DETECTED
   │               │         (risk ≥ 70)
   │               │                 │
   │               │         state: LOCKED
   │               │                 │
   │               │  ┌──────────────┼──────────────┐
   │               │  │              │              │
   │               │  ▼              ▼              ▼
   │               │ WAIT       COLLABORATE  WRAP_UP_REQUEST
   │               │  │              │              │
   │               │  ▼              │              │
   │               │ WAITING         │              │
   │               │  │              │              │
   │               │  │ (checkpoint   │              │
   │               │  │  saved)       │              │
   │               │  │              │              │
   ├─ mark_completed()               │              │
   │  state: COMPLETED               │              │
   │  fires: lock_removed event       │              │
   │  │                              │              │
   │  └─────────────────────────────▶ RESUMED
   │                                  │
   │                            ┌─────▼─────┐
   │                            │   ACTIVE   │
   │                            │ (continues)│
   │                            └────────────┘
   │
   ▼
```

### Scenario 2: Timeout Escalation (30 minutes)

```
Agent A (ACTIVE)              Waiting Agent (WAITING)
   │                                  │
   │                        (awaiting lock_removed)
   │                                  │
   │                        (30 min timeout)
   │                                  │
   ├─────────────────────────────────▶ LOCK_REMOVED
   │  force_release_lock()           (escalated: true)
   │  state: LOCK_REMOVED             │
   │                                  ▼
   │                             RESUMED
   │                             (continues)
   │
   ▼
```

### Scenario 3: No Conflict

```
Agent A (ACTIVE)    Agent B
   │                  │
   │          ┌───────┴─────────┐
   │          │ Check conflicts │
   │          │                 │
   │          ▼                 │
   │       Risk: 0-30 (LOW)     │
   │       → Silent pass        │
   │                            │
   │                      (continues freely)
   │                            │
   ▼                            ▼
```

## Three-Tier Enforcement Gates

### Tier 1: Generation Gate
- **Location**: `check_generation_allowed()`
- **Decision point**: HIGH-risk (score ≥ 70) blocks generation
- **Outcome**: Raises `ConflictBlockedError` if no decision provided
- **Recovery**: Agent must choose WAIT/COLLABORATE/WRAP_UP_REQUEST

### Tier 2: Mutual Acknowledgment
- **Location**: `acknowledge_wait()`
- **Enforcement**: Both agents confirm coordination state
- **Purpose**: Ensures checkpoint is durably saved before continuing
- **Outcome**: Confirms entry into WAITING state with saved context

### Tier 3: Auto-Escalation
- **Location**: `force_release_lock()`
- **Timeout**: 30 minutes
- **Trigger**: Automatic if holding agent doesn't complete
- **Outcome**: Lock releases; waiting agent resumes with escalation flag

## Risk Scoring

Risk score (0-100) combines four factors:

1. **File overlap**: Same file = higher risk
2. **Region overlap**: Overlapping line ranges = higher risk
3. **Time pressure**: Agent holding lock >30 min = higher risk
4. **Agent count**: Multiple agents on same region = higher risk

**Classification**:
- 0-30: **LOW** → Silent pass (continue)
- 30-70: **MEDIUM** → Warning (proceed with caution)
- 70-100: **HIGH** → Blocking (requires decision)

## Checkpoint Mechanism

When Agent B enters WAITING state, Neo saves:

```python
@dataclass
class GenerationCheckpoint:
    agent_id: str              # "agent-b"
    file_path: str             # "src/auth.py"
    region: str                # "lines 25-50"
    intent: str                # "Add password validation"
    tokens_generated: int      # 150 (so far)
    context_buffer: str        # Full prompt context (can be 1000+ chars)
    timestamp: str             # ISO format
```

**On resume**:
- Agent B's prompt state is restored exactly
- No re-analysis of intent needed
- Generation continues from token offset
- Avoids duplicate work, saves compute cost

## Event System

### Event: `lock_removed`

Fired when:
- Agent A marks work COMPLETED
- 30-minute timeout auto-escalates
- Manual force release

Payload:
```json
{
  "agent": "claude-agent-1",
  "escalated": false,
  "waiting_agents": ["devin-agent", "chatgpt-agent"]
}
```

Subscribers:
- All agents in WAITING state on affected file
- Woken asynchronously via `await_event()`

## Code Integration Points

### Agent declares intent
```python
from core.coordination_machine import CoordinationStateMachine

sm = CoordinationStateMachine()
entry = sm.log_intent(
    agent_id="claude-agent",
    file_path="src/auth.py",
    region="login_user (20-40)",
    intent="Add OAuth2"
)
# entry.state = ACTIVE
```

### Agent checks for conflicts
```python
conflict_check = sm.check_conflicts(
    agent_id="devin-agent",
    file_path="src/auth.py",
    region="add_validation (25-50)"
)
# conflict_check['state'] could be LOCKED
# conflict_check['decision_options'] = [WAIT, COLLABORATE, WRAP_UP_REQUEST]
```

### Agent handles conflict decision
```python
if conflict_check['state'] == CoordinationState.LOCKED:
    checkpoint = GenerationCheckpoint(
        agent_id="devin-agent",
        file_path="src/auth.py",
        region="lines 25-50",
        intent="add validation",
        tokens_generated=150,
        context_buffer="...",  # Full prompt context
        timestamp=datetime.now().isoformat()
    )
    sm.handle_decision(
        agent_id="devin-agent",
        decision=DecisionOption.WAIT,
        checkpoint=checkpoint
    )
```

### Agent awaits lock removal
```python
# Non-blocking async wait
async def work():
    lock_released = await sm.await_event("lock_removed", timeout_seconds=3600)
    if lock_released:
        checkpoint = sm.resume_from_checkpoint("devin-agent")
        # Continue generating from checkpoint
```

## Timing & Performance

| Operation | Latency |
|-----------|---------|
| log_intent | 2-5ms |
| check_conflicts | 5-10ms |
| Risk calculation | <1ms |
| Checkpoint save | 2-3ms |
| Resume from checkpoint | 1-2ms |
| Event dispatch | <1ms |

**Total overhead before generation**: <10ms

## Edge Cases

### 1. Agent Never Completes
- **Prevention**: 30-minute timeout auto-escalates
- **Result**: Waiting agent resumes with escalation flag
- **Cost**: One escalation event per 30 minutes

### 2. Multiple Agents Waiting
- **Behavior**: All receive same `lock_removed` event
- **Ordering**: First to acquire lock wins (FIFO via entry order)
- **Risk**: Could cascade conflicts, but less than uncoordinated

### 3. Stale Checkpoints
- **Cleanup**: Entries expire after 2 hours in WAITING state
- **Storage**: Checkpoints kept in-memory for active agents
- **Persistence**: Coordination log saved to `.devsync/coordination.log.json`

### 4. Immediate Conflict Resolution
- **Scenario**: Agent A finishes within seconds of B's lock
- **Behavior**: B wakes immediately, resumes without friction
- **Outcome**: Seamless handoff; no wasted time

## Testing Scenarios

See `tests/` for validation:

1. **Two agents, overlapping regions** → MEDIUM/HIGH risk
2. **Two agents, non-overlapping** → LOW risk
3. **Timeout after 30 minutes** → Auto-escalation
4. **Three agents cascading** → Multiple decisions
5. **Checkpoint persistence** → Full state recovery

## Visual Reference

See `examples/state-diagram.html` for interactive diagram showing:
- Complete Agent A and Agent B workflows
- Conflict detection and decision point
- WAIT path with checkpoint
- COLLABORATE and WRAP_UP_REQUEST paths
- Event-driven recovery flow
- Three-tier enforcement gates

---

**For implementation**: See `core/coordination_machine.py`  
**For usage examples**: See `examples/lean_agents.py` and `examples/cli_demo.py`

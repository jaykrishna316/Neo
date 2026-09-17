# Neo Coordination State Machine

## Overview

**Neo 1.0** (core/): Manages conflict detection and checkpoint-based work pausing with 8 states and 1 event type.

**Neo 2.0** (.claude/): Enterprise-ready multi-phase architecture with 10 workflow states driven by ~32 development lifecycle events across 5 phases:
- **Phase 1**: Intent Declaration (6 events)
- **Phase 2**: Temporal Handoff (3 events) - Independent of PR/MR creation
- **Phase 3**: Context Invalidation (5 events) - Detects stale paused contexts
- **Phase 4**: Work Lifecycle & Review (7 events) - Tracks all operations
- **Phase 5**: Provenance & Agent Autonomy (6 events) - Audit trail + learning

This document covers both versions. Neo 1.0 is production-ready; Neo 2.0 is under active development in `.claude/` with phase-based testing.

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

## Neo 2.0 Architecture (In `.claude/`)

### Workflow States (10 total)

Neo 2.0 extends the workflow beyond coordination to track the complete dev cycle:

| State | Purpose | When | Next States |
|-------|---------|------|-------------|
| AVAILABLE | Resource ready for edit | No one working | EDITING |
| EDITING | Dev holding lock, generating | Dev started work | BOTH_DONE, CONFLICT_WAITING |
| CONFLICT_WAITING | Dev paused, awaiting lock release | Another dev wants same file | PENDING_REVIEW |
| PENDING_REVIEW | Dev B reviewing A's work or continuing | A finished, B reviewing | BOTH_DONE |
| BOTH_DONE | Both devs finished edits | Work complete on file | IN_PR, HANDOFF_PENDING, EDITING |
| HANDOFF_PENDING | **Phase 2**: Work ready for handoff (NEW) | Created for temporal handoff | IN_PR, EDITING |
| IN_PR | Pull request created | PR opened on GitHub | APPROVED, BOTH_DONE |
| APPROVED | All reviewers approved | Review complete | MERGED |
| MERGED | Merged to main branch | Merge commit created | ROLLED_BACK |
| ROLLED_BACK | Reverted, tracking why | Critical issue post-merge | EDITING, AVAILABLE |

### Event Categories (32 total)

Organized by lifecycle phase:

**Phase 1: Intent (6 events)**
- DEVELOPER_REGISTERED, INTENT_DECLARED, INTENT_UPDATED, INTENT_AUTHORIZED, INTENT_BLOCKED, INTENT_CANCELLED (plus INTENT_EXPIRED)

**Phase 2: Handoff (3 events)**
- HANDOFF_CREATED, HANDOFF_ACKNOWLEDGED, HANDOFF_CONSUMED

**Phase 3: Context (5 events)**
- CONTEXT_SNAPSHOT_CREATED, CONTEXT_INVALIDATED, CONTEXT_SYNC_REQUIRED, CONTEXT_REVALIDATING, CONTEXT_REVALIDATED

**Phase 4: Work & Review (7 events)**
- WORK_STARTED, WORK_PAUSED, WORK_RESUMED, WORK_COMPLETED, REVIEW_REQUESTED, REVIEW_STARTED, REVIEW_COMPLETED

**Phase 4-5: Resource & Git (6 + 4 events)**
- RESOURCE_CLAIMED, RESOURCE_RELEASED, RESOURCE_CONFLICT_DETECTED
- BRANCH_CREATED, COMMIT_CREATED, PR_CREATED, PR_MERGED

**Phase 5: System (5 events)**
- STATE_TRANSITION, ERROR_OCCURRED, NOTIFICATION_SENT

### Neo 2.0 Key Components

**event_model.py**: EventType enum with 32 event types, Event dataclass, EventFactory for typed event creation.

**development_memory.py**: Append-only log of all events, queryable by:
- Actor (developer/agent ID)
- Resource (file:function)
- Event type
- Time range
- Task ID (Jira, GitHub issue)

**temporal_handoff_engine.py**: Phase 2 - manages completed work transfer. HandoffRecords can be:
- PENDING (awaiting acknowledgment)
- ACKNOWLEDGED (next dev understands prior work)
- CONSUMED (handoff used by next dev)
- EXPIRED (24hr timeout)

**context_invalidation_engine.py**: Phase 3 - detects when paused agent's saved context becomes stale. If another dev changed a symbol the paused agent depends on, fires CONTEXT_INVALIDATED event.

**reviewer_provenance_engine.py**: Phase 4 - tracks who reviewed what and when. Every COMMIT_CREATED carries developer metadata and co-authors.

**agent_autonomy_engine.py**: Phase 5 - learns from events. Analyzes conflict patterns to improve risk scoring and decision gates over time.

**workflow_state_machine.py**: Manages the 10 workflow states and validates transitions.

### Neo 2.0 Workflow Example

```
DEV1                          NEO 2.0                        DEV2
 │
 ├─ INTENT_DECLARED("dev1", "auth.py::login")
 │
 ├─ WORK_STARTED
 │  state: EDITING
 │
 ├─ RESOURCE_CLAIMED("auth.py::login")
 │
 │                         
 │                    ├─ INTENT_DECLARED("dev2", "auth.py::login")
 │                    │  ↓
 │                    ├─ RESOURCE_CONFLICT_DETECTED
 │                    │  (risk: 85, HIGH)
 │                    │  ↓
 │                    ├─ INTENT_BLOCKED("dev2")
 │
 ├─ WORK_COMPLETED
 │  state: BOTH_DONE
 │
 ├─ HANDOFF_CREATED              
 │  state: HANDOFF_PENDING     ├─ HANDOFF_ACKNOWLEDGED("dev2")
 │                             │
 │  (30 events total           ├─ CONTEXT_SNAPSHOT_CREATED
 │   in real scenario)         │
 │                             ├─ WORK_RESUMED("dev2")
 │                             │
 │                             ├─ WORK_COMPLETED("dev2")
 │                             │
 │                             ├─ BRANCH_CREATED
 │                             │
 │                             ├─ COMMIT_CREATED
 │                             │  (co-authors: dev1, dev2)
 │                             │
 │                             ├─ PR_CREATED
 │                             │
 │                             ├─ REVIEW_REQUESTED
 │                             │
 │                             ├─ REVIEW_COMPLETED
 │                             │
 │                             ├─ STATE_TRANSITION
 │                             │  (IN_PR → APPROVED)
 │                             │
 │                             ├─ PR_MERGED
```

### Neo 2.0 vs Neo 1.0 Comparison

| Aspect | Neo 1.0 | Neo 2.0 |
|--------|---------|---------|
| **States** | 8 (ACTIVE, LOCKED, WAITING, COLLABORATE, COMPLETED, LOCK_REMOVED, RESUMED, COORDINATED) | 10 (adds HANDOFF_PENDING, distinguishes CONFLICT_WAITING) |
| **Events** | 1 (lock_removed) | ~32 (across 5 phases) |
| **Phases** | Single-phase (coordination only) | 5 phases (Intent → Handoff → Context → Review → Autonomy) |
| **Handoff** | Simple event notification | Phase 2: Independent handoff records, temporal tracking |
| **Context** | Checkpoint saved in memory | Phase 3: CONTEXT_INVALIDATED when deps change |
| **Provenance** | None | Phase 4: Full audit trail of commits, reviews, actors |
| **Learning** | None | Phase 5: Autonomy engine learns from event patterns |
| **Development Memory** | Activity log only | Complete event history, queryable |
| **Scope** | Conflict prevention | Multi-team, distributed, enterprise |

### Neo 2.0 Test Files

- `test_phase1_events.py`: Event creation and serialization
- `test_phase2_handoff.py`: Handoff records and consumption
- `test_phase3_context.py`: Context invalidation on dependency changes
- `test_phase4_provenance.py`: Commit provenance and review tracking
- `test_phase5_autonomy.py`: Agent learning from patterns

Run full suite:
```bash
cd .claude
python test_integration_all_phases.py
```

---

**Neo 1.0 (Production)**: See `core/coordination_machine.py`  
**Neo 2.0 (Enterprise)**: See `.claude/` directory and `.claude/workflow_state_machine.py`  
**Visual Reference**: See `examples/state-diagram.html` (Neo 1.0) and `examples/neo2-state-diagram.html` (Neo 2.0)

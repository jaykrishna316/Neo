# Integration Architecture: Shared State Management for Multi-Agent Coordination

## Overview

The coordination state machine requires a **shared state layer** that all agents can read, write, and subscribe to for events. This document describes how to architect this for enterprise deployments.

## Core Components

### 1. Shared Activity Log Storage

**Options:**

#### Option A: Git-Backed (Simple, Version-Controlled)
```
.devsync/
├── coordination.log.json      # Primary log (append-only)
├── checkpoints/               # Saved generation contexts
│   ├── claude-agent-1.json
│   ├── devin-agent.json
│   └── human-dev-alice.json
└── events/                    # Event history
    ├── lock_removed.log
    └── collaboration.log
```

**Advantages:**
- Git history shows all coordination events
- Easy to audit and replay
- No external service needed
- Works offline (eventually consistent)

**Disadvantages:**
- Git merge conflicts on concurrent writes
- Latency on large teams
- Need polling for event detection

**Best for:** Small teams, internal projects, prototypes

#### Option B: Cloud-Backed (Scalable)
```
Cloud Store (Firebase, Supabase, DynamoDB, etc.)
├── collections/coordination-entries
├── collections/checkpoints
├── subscriptions/lock_removed
├── subscriptions/collaboration_proposed
└── subscriptions/state_changed
```

**Advantages:**
- Real-time sync across agents
- WebSocket/event subscriptions built-in
- Scales to unlimited agents
- No merge conflicts
- Audit logging
- Access control per agent

**Disadvantages:**
- External dependency
- Cost at scale
- Network latency
- Vendor lock-in

**Best for:** Enterprises, distributed teams, production systems

#### Option C: Hybrid (Local Cache + Cloud Sync)
```
Each Agent:
├── Local Cache (.devsync/local-cache.json)
├── Event Queue (FIFO for failed events)
└── Sync Service (background thread)

Cloud Backend:
├── Primary coordination log
├── Event bus
└── Checkpoint store
```

**Advantages:**
- Fast local operations (cache hits)
- Resilient to network outages (queue)
- Real-time when connected
- Automatic sync in background

**Best for:** High-performance requirements, unreliable networks

---

## 2. Event Bus / Notification System

Agents need to **subscribe to events** without polling.

### Real-Time Event Delivery

**WebSocket (Recommended for Real-Time)**
```
Agent connects to event bus:
ws://coordination-service/events?agent_id=claude-agent-1

Events streamed in real-time:
{
  "event_type": "lock_removed",
  "triggered_at": "2026-09-11T15:45:01Z",
  "data": {
    "file": "src/auth.py",
    "released_by": "claude-agent-1",
    "waiting_agent": "devin-agent"
  }
}
```

**Advantages:**
- Instant notification
- Low latency (milliseconds)
- Bidirectional communication
- Supports multiple event types

**Disadvantages:**
- Requires persistent connection
- More complex infrastructure
- Firewall/proxy issues possible

**Implementation Options:**
- Firebase Realtime DB
- Supabase (Postgres + Realtime)
- Ably
- AWS AppSync
- Custom WebSocket server (Socket.io, Tornado, etc.)

### Polling Fallback (Simple)
```python
# For agents without real-time capability
while waiting:
    event = activity_log.check_event("lock_removed", agent_id)
    if event:
        resume()
    sleep(2)  # Poll every 2 seconds
```

**Advantages:**
- Simple to implement
- Works behind any firewall
- No persistent connections

**Disadvantages:**
- Higher latency
- Token waste (agents checking frequently)
- Doesn't scale (100 agents polling = 50 checks/sec)

---

## 3. Agent Integration Points

### Pre-Generation Hook

Every agent needs a hook that runs **before generating code**:

```python
@before_generation
async def coordination_check(agent_id, file_path, region, intent):
    """
    Called before any code generation.
    
    Returns:
        - 'proceed': Go ahead, no conflicts
        - 'wait': Conflict detected, return to caller to retry later
        - 'collaborate': High-risk conflict, suggest collaboration
        - 'blocked': Critical conflict, must wait
    """
    
    # 1. Log this agent's intent
    log_entry = activity_log.log_intent(
        agent_id=agent_id,
        file_path=file_path,
        region=region,
        intent=intent
    )
    
    # 2. Check for conflicts
    conflict_check = activity_log.check_conflicts(
        agent_id=agent_id,
        file_path=file_path,
        region=region
    )
    
    # 3. Return recommendation
    if conflict_check['risk_score'] < 30:
        return {'action': 'proceed'}
    
    elif conflict_check['risk_score'] < 70:
        return {
            'action': 'proceed_with_caution',
            'warning': f"Low risk conflict with {conflict_check['conflicting_agents']}",
            'estimated_wait': 300  # seconds
        }
    
    else:  # HIGH RISK
        return {
            'action': 'decision_required',
            'risk_score': conflict_check['risk_score'],
            'options': ['collaborate', 'wait', 'wrap_up_request']
        }
```

### Post-Generation Hook

After code is generated:

```python
@after_generation
def coordination_complete(agent_id, file_path, generation_status):
    """
    Called after code generation completes or is cancelled.
    """
    
    if generation_status == 'completed':
        activity_log.mark_completed(agent_id)
        activity_log.fire_event('lock_removed', {'agent': agent_id})
    
    elif generation_status == 'cancelled':
        activity_log.mark_cancelled(agent_id)
```

### Checkpoint/Resume Hook

When agent pauses due to lock:

```python
@on_high_risk_lock
async def handle_lock_decision(agent_id, decision, generation_context):
    """
    Called when agent encounters HIGH RISK lock.
    """
    
    if decision == 'wait':
        # Save checkpoint
        checkpoint = GenerationCheckpoint(
            agent_id=agent_id,
            context_buffer=generation_context['prompt'],
            tokens_generated=generation_context['tokens'],
            intent=generation_context['intent'],
            file_path=generation_context['file']
        )
        activity_log.save_checkpoint(checkpoint)
        
        # Subscribe to wake event
        await activity_log.await_event('lock_removed')
        
        # Resume from checkpoint
        resume_from_checkpoint(checkpoint)
    
    elif decision == 'collaborate':
        activity_log.notify_collaboration_request(
            initiating_agent=agent_id,
            target_agent=conflicting_agents[0],
            context=generation_context
        )
```

---

## 4. Deployment Architectures

### Architecture A: Git-Based (Small Team)

```
Developer Machine 1 (Claude)
    ↓
    └─→ .devsync/coordination.log.json
         ↓
Developer Machine 2 (Devin)    ←→ Git Repository
    ↓
    └─→ .devsync/coordination.log.json
    
Human Developer (VS Code with agent extension)
    ↓
    └─→ .devsync/coordination.log.json
```

**Sync Mechanism:** Git pull/push (eventual consistency)
**Event Detection:** Polling
**Scalability:** Up to ~10 agents

---

### Architecture B: Cloud-Backed (Scalable)

```
Claude Agent
    ↓
    └─→ REST/gRPC Client ─┐
                           ├─→ Coordination Service (Cloud)
Devin Agent                 │   ├─ State Store (Database)
    ↓                       │   ├─ Event Bus (WebSocket)
    └─→ REST/gRPC Client ─┤   ├─ Checkpoint Store
                           │   └─ Auth/Access Control
Human Developer             │
    ↓                       │
    └─→ REST/gRPC Client ─┘

Agents subscribe to events via WebSocket
Persistent connection → real-time updates
```

**Sync Mechanism:** Central service (strong consistency)
**Event Detection:** WebSocket subscriptions
**Scalability:** Unlimited agents (auto-scaling)

---

### Architecture C: Hybrid (Best of Both)

```
Each Agent
    ├─ Local Cache (.devsync/local-cache.json)
    ├─ Event Queue (FIFO)
    └─ Sync Service (background)
        ↓
    Coordination Cloud Service
        ├─ State Store
        ├─ Event Bus
        └─ Checkpoint Store

Workflow:
1. Agent checks local cache (fast)
2. Agent logs intent locally (fast)
3. Background sync sends to cloud
4. Cloud broadcasts to other agents
5. Agent subscribes to events via WebSocket
6. Falls back to polling if disconnected
```

**Advantages:**
- Fast (cache hits in <10ms)
- Resilient (works offline)
- Real-time (WebSocket when connected)

---

## 5. API Specification

### Core Endpoints/Methods

```python
class CoordinationClient:
    """
    Interface that all agents use to interact with coordination layer.
    Implemented differently for Git, Cloud, Hybrid.
    """
    
    # Logging
    def log_intent(self, agent_id: str, file: str, region: str, intent: str) -> LogEntry
    def mark_completed(self, agent_id: str) -> None
    def mark_cancelled(self, agent_id: str) -> None
    
    # Conflict Detection
    def check_conflicts(self, agent_id: str, file: str, region: str) -> ConflictReport
    
    # Checkpoints
    def save_checkpoint(self, checkpoint: GenerationCheckpoint) -> None
    def load_checkpoint(self, agent_id: str) -> Optional[GenerationCheckpoint]
    
    # Events
    def subscribe_to_event(self, event_type: str, callback: Callable) -> None
    async def await_event(self, event_type: str, timeout: int = 3600) -> bool
    def fire_event(self, event_type: str, data: Dict) -> None
    
    # Status
    def get_status(self, agent_id: Optional[str] = None) -> List[LogEntry]
```

### Event Types

```
- lock_removed: Lock on file released, agent can resume
- collaboration_proposed: Another agent wants to collaborate
- state_changed: Any agent changed state
- conflict_detected: New conflict detected
- coordination_complete: All agents finished on a file
- agent_online/offline: Agent connected/disconnected
```

---

## 6. Access Control & Security

### Per-Agent Permissions

```json
{
  "agent_id": "claude-agent-1",
  "permissions": {
    "read": ["src/auth.py", "src/models.py"],
    "write": ["src/auth.py"],
    "collaborate_with": ["devin-agent", "human-dev-alice"],
    "see_checkpoints": ["own_only"]
  },
  "rate_limits": {
    "log_intent_per_minute": 10,
    "check_conflicts_per_minute": 60
  },
  "encryption": "tls_1_3"
}
```

### Audit Logging

Every action logged for compliance:
```json
{
  "timestamp": "2026-09-11T15:30:15Z",
  "agent_id": "claude-agent-1",
  "action": "log_intent",
  "file": "src/auth.py",
  "ip_address": "10.0.1.5",
  "status": "success"
}
```

---

## 7. Implementation Checklist

- [ ] Choose storage backend (Git, Cloud, or Hybrid)
- [ ] Implement CoordinationClient interface
- [ ] Set up event bus / notification system
- [ ] Add pre-generation hook to agent framework
- [ ] Add post-generation hook to agent framework
- [ ] Implement checkpoint save/load
- [ ] Add WebSocket or polling for event detection
- [ ] Set up access control & authentication
- [ ] Add audit logging
- [ ] Create monitoring/dashboards
- [ ] Load test with expected agent count
- [ ] Document for team

---

## 8. Next Steps

See the framework-specific integration guides:
- `ENTERPRISE_SCALING_CLAUDE.md` - Claude SDK integration
- `ENTERPRISE_SCALING_OPENAI.md` - OpenAI API integration  
- `ENTERPRISE_SCALING_DEVIN.md` - Devin framework integration
- `ENTERPRISE_SCALING_CODEX.md` - GitHub Copilot/Codex integration

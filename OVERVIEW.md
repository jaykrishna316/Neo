# Neo: System Overview

**Neo** is an event-driven coordination framework that prevents merge conflicts **before code is written**, enabling distributed AI agents and developers to work safely on shared codebases. Like "The One" in The Matrix, Neo orchestrates harmony between agents before conflicts emerge.

## The Problem

When multiple agents (Claude, OpenAI, Devin, GitHub Copilot) or developers work on the same codebase simultaneously:

```
Developer A starts working on src/auth.py (lines 40-80)
  ↓
Developer B doesn't know this, also tries to modify src/auth.py (lines 45-75)
  ↓
Both write diverging changes
  ↓
Git merge conflict → manual resolution → wasted tokens → broken build
```

This wastes tokens, time, and causes developers to manually resolve conflicts after the fact.

## The Solution

Neo introduces a **shared activity log** and **event-driven state machine** that agents check **before** generating code:

```
Developer A announces: "I'm working on src/auth.py (lines 40-80)"
  ↓
Developer B asks: "Is it safe to work here?"
  ↓
Neo checks: "HIGH RISK - Developer A is overlapping"
  ↓
Developer B gets options: Wait / Collaborate / Request wrap-up
  ↓
Developer B waits (no tokens wasted, sleeping until Developer A finishes)
  ↓
Developer A completes → fires lock_removed event
  ↓
Developer B resumes from exact checkpoint
  ↓
Sequential commits, clean merge, zero manual work
```

## Key Concepts

### 1. Shared Activity Log
A synchronized record of who is working where:
```json
{
  "agent_id": "claude-agent-1",
  "file_path": "src/auth.py",
  "region": "lines 40-80",
  "intent": "Add OAuth2 support",
  "state": "ACTIVE",
  "timestamp": "2026-09-11T15:30:00Z"
}
```

Storage options:
- **Git-backed** (simple, version-controlled)
- **Cloud-backed** (scalable, real-time)
- **Hybrid** (fast local cache + cloud sync)

### 2. Event-Driven State Machine
Six core states with clear transitions:

```
ACTIVE (Agent working)
  ↓ (check_conflicts)
LOCKED (High risk detected)
  ├─→ WAITING (Agent B pauses, checkpoint saved)
  │     ↓ (lock_removed event fires)
  │   RESUMED (Agent B wakes up)
  │
  └─→ COLLABORATE (Agents coordinate)
        ↓
      COORDINATED

ACTIVE → COMPLETED (Agent finishes work)
  ↓ (fires lock_removed event)
Agent notified and wakes up
```

### 3. Pre-Generation Hook
Before any code generation, agents call:

```python
check = coordination.check_conflicts(
    agent_id="claude-agent-1",
    file_path="src/auth.py",
    region="lines 40-80"
)

if check['risk_score'] > 70:  # HIGH RISK
    # Show options: Wait / Collaborate / Request wrap-up
    pass
elif check['risk_score'] > 30:  # MEDIUM RISK
    # Show warning, but allow proceeding
    pass
else:  # LOW RISK
    # Safe to proceed
    pass
```

### 4. Checkpoint System
When an agent pauses on a conflict, the full generation context is saved:

```python
checkpoint = GenerationCheckpoint(
    agent_id="claude-agent-1",
    file_path="src/auth.py",
    region="lines 40-80",
    intent="Add OAuth2 support",
    tokens_generated=150,
    context_buffer="<full prompt so far>",
    timestamp="2026-09-11T15:30:00Z"
)
```

When the lock clears, the agent resumes from this exact point—no regeneration needed.

### 5. Event Subscriptions
Agents don't poll. They subscribe to events and sleep:

```python
# Agent B waits for Developer A to finish
# No token waste, no polling
await coordination.await_event('lock_removed')

# Event fires when Developer A completes
# Agent B wakes up immediately and resumes
```

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Agents / Developers                                        │
│  ├─ Claude (via Anthropic SDK)                             │
│  ├─ OpenAI (via GPT-4 + function calling)                  │
│  ├─ Devin (autonomous agent)                               │
│  ├─ GitHub Copilot (VS Code extension)                     │
│  └─ Human developers                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Coordination Client Interface                              │
│  (language/framework agnostic)                              │
│  ├─ log_intent()                                            │
│  ├─ check_conflicts()                                       │
│  ├─ save_checkpoint() / load_checkpoint()                   │
│  ├─ await_event()                                           │
│  └─ mark_completed()                                        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  CoordinationStateMachine                                   │
│  (Core business logic)                                      │
│  ├─ State transitions (ACTIVE → LOCKED → WAITING → etc)    │
│  ├─ Risk scoring (0-100)                                   │
│  ├─ Conflict detection                                      │
│  └─ Event dispatch                                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Shared State Backends (Pluggable)                          │
│  ├─ Git (.devsync/coordination.log.json)                   │
│  ├─ PostgreSQL                                              │
│  ├─ DynamoDB                                                │
│  ├─ Firebase Realtime DB                                   │
│  └─ Custom (implement CoordinationBackend interface)        │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│  Event Buses (Pluggable)                                    │
│  ├─ WebSocket (real-time)                                  │
│  ├─ Polling (fallback)                                      │
│  ├─ Redis Pub/Sub                                           │
│  ├─ Kafka                                                    │
│  └─ Custom (implement EventBus interface)                   │
└─────────────────────────────────────────────────────────────┘
```

## File Structure

```
codeNinja/
├── coordination_state_machine.py       # Core state machine logic
├── activity_log.py                     # Legacy activity log (POC)
├── agent_integration.py                # Agent-specific integrations
├── websocket_support.py                # Event bus for WebSocket
│
├── docs/
│   ├── INTEGRATION_ARCHITECTURE.md     # Core patterns & deployment
│   ├── ENTERPRISE_SCALING_CLAUDE.md    # Claude SDK integration
│   ├── ENTERPRISE_SCALING_OPENAI.md    # OpenAI API integration
│   ├── ENTERPRISE_SCALING_DEVIN.md     # Devin autonomous agent
│   ├── ENTERPRISE_SCALING_CODEX.md     # GitHub Copilot/Codex
│   ├── state-machine-scenarios.html    # Interactive visualization
│   └── git-workflow-comparison.html    # Git graph comparison
│
├── marketing/
│   ├── linkedin_post_v2.md             # LinkedIn content
│   └── medium_article_v2.md            # Medium article
│
├── ROADMAP.md                          # Feature prioritization
├── CONTRIBUTING.md                     # Contributor guidelines
├── CODE_OF_CONDUCT.md                  # Community standards
├── LICENSE                             # MIT License
└── README.md                           # Quick start guide
```

## How to Use Neo

### For Developers Using Claude/Devin/Copilot

1. **During Setup:** Connect your agent to Neo's coordination service
2. **Before Generating Code:** System automatically checks for conflicts
3. **If Conflict Detected:** Agent shows you options (wait/collaborate/request wrap-up)
4. **If Waiting:** Agent saves context and sleeps (no token waste)
5. **When Ready:** Agent resumes automatically from exact checkpoint

### For Framework Integrators

Implement the coordination client interface:

```python
from coordination_state_machine import CoordinationStateMachine

# 1. Initialize
coordination = CoordinationStateMachine()

# 2. Log intent (when agent starts)
coordination.log_intent(
    agent_id="claude-agent-1",
    file_path="src/auth.py",
    region="lines 40-80",
    intent="Add OAuth2 support"
)

# 3. Check before generating
check = coordination.check_conflicts(
    agent_id="claude-agent-1",
    file_path="src/auth.py",
    region="lines 40-80"
)

if check['risk_score'] > 70:
    # Handle high-risk: offer options
    checkpoint = coordination.save_checkpoint(...)
    await coordination.await_event('lock_removed')
    checkpoint = coordination.load_checkpoint("claude-agent-1")
    # Resume from checkpoint

# 4. Mark complete when done
coordination.mark_completed("claude-agent-1")
```

See framework-specific guides in `docs/ENTERPRISE_SCALING_*.md`.

### For Platform Teams

Deploy Neo's coordination service:

```python
from coordination_service import CoordinationService

# Option 1: Git-backed (simple)
service = CoordinationService(backend='git')

# Option 2: Cloud-backed (scalable)
service = CoordinationService(
    backend='cloud',
    database='postgresql://...',
    event_bus='websocket'
)

# Option 3: Hybrid (fast + resilient)
service = CoordinationService(
    backend='hybrid',
    local_cache=True,
    cloud_sync=True
)

# Start service
await service.start()
```

See `docs/INTEGRATION_ARCHITECTURE.md` for deployment patterns.

## Decision Options When Conflicts Detected

When an agent encounters a HIGH RISK lock, it gets three options:

### 1. **WAIT**
- Agent pauses and saves checkpoint
- No tokens wasted (event-driven wake-up, not polling)
- When Developer A finishes → `lock_removed` event fires
- Agent resumes from exact checkpoint
- **Best for:** Most conflicts (simple, no coordination overhead)

### 2. **COLLABORATE**
- Both agents coordinate together
- They might split the work, or one wraps up while the other waits
- Requires real-time communication (Slack, Discord, email)
- **Best for:** Critical features where coordination adds value

### 3. **REQUEST WRAP-UP**
- Agent asks Developer A to finish sooner
- More polite than forcing a lock, but signals urgency
- **Best for:** Time-sensitive tasks

## Risk Scoring (0-100)

```
0-30:   LOW RISK       (Different regions, no signature changes)
        → Silent proceed
        
30-70:  MEDIUM RISK    (Overlapping regions, minor conflicts)
        → Show warning, allow proceeding
        
70-100: HIGH RISK      (Exact same region, signature changes)
        → Show decision options, require action
```

Scoring factors:
- Region overlap (lines, functions, classes)
- Signature changes (API modifications)
- Type changes
- Historical patterns (ML-based learning)

## Deployment Architectures

### Architecture A: Git-Backed (Small Teams, Prototypes)
```
Agents → Git commit to .devsync/ → Git poll for updates
```
- **Pros:** Simple, version-controlled, no external dependency
- **Cons:** Eventual consistency, polling latency
- **Best for:** 1-10 agents

### Architecture B: Cloud-Backed (Enterprise, Distributed)
```
Agents → REST/gRPC → Coordination Service → Cloud Database
         ↕ WebSocket for events
```
- **Pros:** Real-time, scalable, auditable
- **Cons:** External dependency, cost
- **Best for:** 10-100+ agents, enterprises

### Architecture C: Hybrid (Best of Both)
```
Agents → Local Cache + Background Sync → Cloud Service
         ↕ WebSocket when connected, polling fallback
```
- **Pros:** Fast (local cache), resilient (works offline), real-time (WebSocket)
- **Cons:** More complex
- **Best for:** High-performance requirements, unreliable networks

## Framework-Specific Integration

Neo provides adapters for:

| Framework | Integration Point | Status | Docs |
|-----------|-------------------|--------|------|
| **Claude (Anthropic SDK)** | Tool use loop | ✅ Complete | [Guide](docs/ENTERPRISE_SCALING_CLAUDE.md) |
| **OpenAI (GPT-4)** | Function calling | ✅ Complete | [Guide](docs/ENTERPRISE_SCALING_OPENAI.md) |
| **Devin** | Task execution hooks | ✅ Complete | [Guide](docs/ENTERPRISE_SCALING_DEVIN.md) |
| **GitHub Copilot** | VS Code extension | ✅ Complete | [Guide](docs/ENTERPRISE_SCALING_CODEX.md) |
| **Human Developers** | IDE plugins | 🔄 Planned | TBD |

## Learning Paths

### For Developers
1. Read this OVERVIEW
2. Check out visualizations: `docs/state-machine-scenarios.html`
3. Read marketing content: `marketing/medium_article_v2.md`
4. Try the code: `python3 cli_simulation.py`

### For Framework Integrators
1. Read this OVERVIEW
2. Study core state machine: `coordination_state_machine.py`
3. Read your framework guide: `docs/ENTERPRISE_SCALING_*.md`
4. Implement `CoordinationClient` interface
5. Write integration tests

### For Platform/DevOps Teams
1. Read this OVERVIEW
2. Study `docs/INTEGRATION_ARCHITECTURE.md`
3. Choose deployment architecture (Git/Cloud/Hybrid)
4. Deploy coordination service
5. Configure database + event bus

### For Contributors
1. Read this OVERVIEW
2. See [ROADMAP.md](ROADMAP.md) for contribution opportunities
3. Check [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines
4. Pick an issue and start coding

## Next Steps

- **Try it:** Open `docs/state-machine-scenarios.html` for interactive demo
- **Understand it:** Read `docs/INTEGRATION_ARCHITECTURE.md`
- **Build it:** See [ROADMAP.md](ROADMAP.md) for immediate priorities
- **Contribute:** See [CONTRIBUTING.md](CONTRIBUTING.md)

## Questions?

- **How does it work?** See this OVERVIEW and the visualizations
- **How do I integrate?** See `docs/ENTERPRISE_SCALING_*.md` for your framework
- **How do I contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)
- **What's the roadmap?** See [ROADMAP.md](ROADMAP.md)

---

**Built for distributed teams. Powered by coordination. Enabled by Neo. 🧵**

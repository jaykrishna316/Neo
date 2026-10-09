# Phase 5: Cross-Agent Orchestration

**Status**: Architecture & design ready  
**Goal**: Coordinate Claude, Devin, OpenAI, and other agents on the same codebase

---

## Overview

Phase 5 extends Neo beyond single-team coordination to enable multiple **different AI agents** to work together on shared code. Each agent has unique capabilities:

- **Claude Code**: Best for architecture, complex logic, refactoring
- **Devin**: Best for debugging, testing, deployment automation
- **OpenAI (GPT-4)**: Best for specific tasks, fine-grained code changes
- **Custom agents**: Build your own for domain-specific tasks

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Project Shared Codebase                   │
│                    (Git Repository)                         │
└────────────────────────────────────────────────────────────┘
                            ↕
        ┌────────────────────────────────────┐
        │   Neo Orchestration Layer          │
        │  (Cloud Activity Log + Lock Mgr)   │
        └────────────────────────────────────┘
            ↑           ↑           ↑           ↑
         Claude      Devin        OpenAI    Custom
         Code                              Agents
    (MCP Adapter) (REST Adapter) (API Adapter) (Webhook)
```

## How It Works

### 1. Agent Registration

Each agent registers itself with Neo:

```python
# When Claude Code starts
neo.register_agent(
    agent_id="claude-code-session-123",
    agent_type="claude",
    capabilities=["architecture", "refactoring", "testing"],
    max_concurrent_files=3
)

# When Devin joins
neo.register_agent(
    agent_id="devin-task-456",
    agent_type="devin",
    capabilities=["debugging", "testing", "deployment"],
    max_concurrent_files=2
)
```

### 2. Intent Declaration

Agent declares work before starting:

```python
# Claude: "I'm refactoring authentication"
neo.declare_intent(
    agent_id="claude-code-123",
    file_path="auth.py",
    intent="Refactor authentication to use OAuth2",
    region="authenticate, login",
    dependencies=["models.py:User"]
)

# Devin: "I'm writing tests for auth"
neo.declare_intent(
    agent_id="devin-456",
    file_path="tests/test_auth.py",
    intent="Add comprehensive OAuth2 tests",
    dependencies=["auth.py"]
)
```

### 3. Conflict Detection with Cross-Agent Awareness

Neo checks not just same-human conflicts, but **cross-agent** conflicts:

```python
risk, message, lock = neo.check_for_conflicts(
    agent_id="devin-456",
    file_path="auth.py",
    intent="Add OAuth2 tests"
)
# Returns: RiskLevel.MEDIUM
# "Claude Code (claude-code-123) is refactoring authenticate (lines 45-120)
#  Devin waiting in queue (position 0)
#  Estimated wait: 2 minutes"
```

### 4. Queue Management

Agents queue fairly:

```
File: auth.py
├─ Claude Code: ACQUIRED (refactor, ETA 2 min)
├─ Devin: WAITING (test, queue pos 0)
└─ OpenAI: WAITING (docs, queue pos 1)
```

When Claude finishes:
- Lock released
- Devin promoted to ACQUIRED
- OpenAI remains WAITING
- **Fresh context** flows: Devin sees Claude's refactored code

### 5. Cross-Agent Context Flow

When lock transfers, new agent gets full context:

```python
# Devin gets promoted, receives context
context = neo.get_fresh_context(
    agent_id="devin-456",
    file_path="auth.py"
)
# Returns:
# {
#   "previous_agent": "claude-code-123",
#   "changes": {
#     "lines_added": 45,
#     "lines_removed": 20,
#     "functions_added": ["oauth_login", "oauth_callback"],
#     "functions_modified": ["authenticate"]
#   },
#   "summary": "OAuth2 flow added with callback handler",
#   "tests_written": false
# }

# Devin knows Claude added oauth_login and oauth_callback
# Devin writes tests for those new functions
```

## Integration Points

### Claude Code (MCP)

Already implemented. Neo MCP server handles `neo_check_conflicts`, `neo_log_activity`.

```python
# Claude Code calls this before writing
result = mcp_tool("neo_check_conflicts", {
    "agent_id": session_id,
    "file_path": "auth.py",
    "intent": "Refactor to OAuth2"
})
```

### Devin (REST API)

Devin would call Neo via REST:

```bash
curl -X POST http://neo-server/api/check-conflicts \
  -H "Authorization: Bearer $DEVIN_TOKEN" \
  -d '{
    "agent_id": "devin-task-456",
    "agent_type": "devin",
    "file_path": "auth.py",
    "intent": "Add OAuth2 tests"
  }'
```

### OpenAI (Webhook)

OpenAI would trigger webhooks:

```json
{
  "event": "code_generation_started",
  "agent_id": "openai-gpt4-789",
  "agent_type": "openai",
  "file_path": "utils.py",
  "intent": "Add utility functions"
}
```

### Custom Agents (Webhook + SDK)

Any custom agent can register:

```python
from neo_sdk import NeoClient

client = NeoClient(url="https://neo-server.com", token="...")
client.declare_intent(
    agent_id="my-bot-123",
    file_path="lib.py",
    intent="Optimize performance"
)
```

## Implementation Phases

### Phase 5a: REST API Server

Expose Neo via HTTP REST API for non-MCP agents:

```
POST /api/agents/register
POST /api/intents/declare
GET  /api/conflicts/check
POST /api/activity/log
GET  /api/lock-state/{file_path}
```

### Phase 5b: Multi-Agent Adapter

Create adapter layer that handles different agent types:

```python
class AgentAdapter(ABC):
    @abstractmethod
    def check_conflicts(self, agent_id, file_path, intent) -> Dict:
        pass
    
    @abstractmethod
    def log_activity(self, agent_id, file_path, intent, metadata) -> bool:
        pass

class MCPAdapter(AgentAdapter):
    # Handles Claude Code via MCP
    pass

class RESTAdapter(AgentAdapter):
    # Handles Devin, external APIs via REST
    pass

class WebhookAdapter(AgentAdapter):
    # Handles webhooks from external systems
    pass
```

### Phase 5c: Context Serialization

Agents need to understand each other's changes:

```python
context = {
    "agent_id": "claude-code-123",
    "agent_type": "claude",
    "changes": {
        "file_path": "auth.py",
        "lines_added": 45,
        "lines_removed": 20,
        "functions_added": ["oauth_login"],
        "functions_modified": ["authenticate"],
        "summary": "Added OAuth2 flow"
    },
    "next_steps": [
        "Add tests for new functions",
        "Update documentation",
        "Deploy to staging"
    ]
}
```

### Phase 5d: Coordination Dashboard

Web UI showing all agents and their work:

```
Neo Coordination Dashboard
═══════════════════════════════════════════

Project: my-project
Repository: github.com/user/my-project

Active Agents (4):
├─ 👤 Claude Code [claude-code-123]
│  ├─ Status: WORKING
│  ├─ File: auth.py (lines 45-120)
│  ├─ Intent: Refactor OAuth2
│  └─ ETA: 2 minutes
│
├─ 🤖 Devin [devin-456]
│  ├─ Status: WAITING (queue pos 0)
│  ├─ File: tests/test_auth.py
│  ├─ Intent: Write OAuth2 tests
│  └─ Will start: ~2 min
│
├─ 🔧 OpenAI GPT-4 [openai-789]
│  ├─ Status: WAITING (queue pos 1)
│  ├─ File: docs/auth.md
│  ├─ Intent: Document OAuth2
│  └─ Will start: ~5 min
│
└─ 📝 Custom Bot [custom-xyz]
   ├─ Status: WAITING (queue pos 2)
   ├─ File: lib/utils.py
   ├─ Intent: Optimize performance
   └─ Will start: ~7 min

Recent Activity:
  • Claude Code completed auth.py refactor (+45 lines, -20 removed)
  • Devin promoted to lock holder
  • OpenAI marked for queue position 1
```

## Execution Flow Example

### Scenario: Build Full Feature with 3 Agents

**Goal**: Implement OAuth2 from scratch with tests and docs

**Timeline**:

```
T+0:00 - Claude Code: "I'll refactor auth to use OAuth2"
         └─ Declares intent, acquires lock on auth.py
         └─ Neo logs: claude-code-123 ACQUIRED auth.py

T+0:15 - Devin: "I'll write tests for OAuth2"
         └─ Checks conflicts → MEDIUM (claude working)
         └─ Neo logs: devin-456 WAITING (queue pos 0)

T+0:20 - OpenAI: "I'll document OAuth2"
         └─ Checks conflicts → MEDIUM (claude + devin)
         └─ Neo logs: openai-789 WAITING (queue pos 1)

T+2:00 - Claude Code: "Done! Added oauth_login, oauth_callback"
         └─ Logs completion: auth.py +45 lines, -20 removed
         └─ Release lock
         └─ Devin promoted
         └─ Neo logs: devin-456 ACQUIRED (received context from claude)

T+2:05 - Devin: "Starting tests now, I see oauth_login and oauth_callback"
         └─ Uses fresh context from Claude
         └─ Writes test_oauth_login, test_oauth_callback
         └─ Neo logs: devin-456 COMPLETED tests (+35 lines)
         └─ OpenAI promoted

T+4:15 - OpenAI: "Starting docs, I see new functions and tests"
         └─ Uses context from both Claude and Devin
         └─ Writes authentication.md with examples
         └─ Neo logs: openai-789 COMPLETED docs (+200 lines)

RESULT: Complete OAuth2 feature built end-to-end with 0 conflicts! ✅
```

## Benefits vs Challenges

### Benefits
- ✅ **Zero merge conflicts**: Sequential execution prevents all conflicts
- ✅ **Optimal task assignment**: Each agent does what it's best at
- ✅ **Fast development**: Agents don't wait; queue system is transparent
- ✅ **Context sharing**: Each agent sees previous agent's changes
- ✅ **Auditability**: Every change and agent logged

### Challenges
- 🔄 **Queueing overhead**: Agents might wait longer than parallel work
- 🔄 **Agent coordination**: Requires agents to understand each other's context
- 🔄 **API compatibility**: Devin, OpenAI APIs differ significantly
- 🔄 **Error handling**: One bad agent change blocks others in queue

### Mitigations
- **Smart queueing**: Agents on different files run in parallel
- **Context protocol**: Standardize how agents describe changes
- **Adapter layer**: Normalize different API styles
- **Rollback support**: If agent fails, Neo can rollback changes

## Success Metrics (Phase 5)

- [ ] REST API fully functional and tested
- [ ] Devin integration working (can check conflicts via API)
- [ ] OpenAI integration working (can check conflicts via webhook)
- [ ] Cross-agent coordination test passing (3+ agents, 0 conflicts)
- [ ] Dashboard showing live agent coordination
- [ ] Documentation for 3rd-party agent integration

## Timeline

| Phase | Task | Effort | Status |
|-------|------|--------|--------|
| 5a | REST API Server | 4 hours | ⏳ Planned |
| 5b | Multi-Agent Adapter | 3 hours | ⏳ Planned |
| 5c | Context Serialization | 2 hours | ⏳ Planned |
| 5d | Coordination Dashboard | 4 hours | ⏳ Planned |
| 5e | Devin Integration | 3 hours | ⏳ Planned |
| 5f | OpenAI Integration | 3 hours | ⏳ Planned |
| **Total** | **Cross-Agent Orchestration** | **19 hours** | ⏳ |

## Next Steps

1. ✅ Phase 1-4 complete and tested
2. ⏳ Implement Phase 5a: REST API
3. ⏳ Build adapters for Devin, OpenAI, custom agents
4. ⏳ Deploy coordination dashboard
5. ⏳ Integration tests with real agents
6. 🚀 Launch multi-agent projects!

## Questions?

- **How do agents know what others are doing?** → Activity log + lock state
- **What if an agent crashes mid-work?** → Lock timeout (30 min default), next agent promotes
- **Can agents work in parallel?** → Yes, if on different files/regions
- **What about performance?** → Lock transfers are <1s, queue overhead minimal
- **Is this production-ready?** → Phases 1-4 yes, Phase 5 in development

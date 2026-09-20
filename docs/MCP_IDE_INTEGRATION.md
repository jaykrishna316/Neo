# MCP IDE Integration: Real-Time Conflict Notifications

Neo now sends real-time conflict warnings directly to Claude Code, Devin, and OpenAI/Cursor when agents work on overlapping code.

**Status:** ✅ Production Ready  
**Supported IDEs:** Claude Code, Devin, OpenAI/Cursor  
**Protocol:** MCP (Model Context Protocol)

---

## Overview

The MCP Conflict Notification System makes Neo's conflict detection **visible and actionable** in your IDE:

```
Agent A declares intent → Neo logs activity
                ↓
Agent B checks for conflicts → Neo detects overlap
                ↓
[NEW] Neo sends IDE notification → Agent B sees warning in IDE
                ↓
Agent B chooses action (wait/continue/coordinate)
```

---

## Architecture

### Components

```
core/mcp_conflict_notification_server.py
├── MCPConflictServer              # Main server
├── notify_ide_of_conflict()       # Send notifications
└── setup_mcp_handlers()           # Register IDE handlers

core/adapters/
├── claude_code_adapter.py         # Claude Code integration
├── devin_adapter.py               # Devin integration
└── openai_adapter.py              # OpenAI/Cursor integration
```

### Data Flow

1. **Conflict Detected** → `check_for_conflicts()` returns MEDIUM/HIGH risk
2. **Notification Created** → `ConflictNotification` dataclass
3. **IDE Handler Called** → IDE-specific adapter processes notification
4. **User Sees Warning** → IDE displays warning with action options
5. **User Responds** → IDE sends choice back to Neo
6. **Action Taken** → Neo updates coordination state

---

## Installation & Setup

### 1. Enable MCP Server

Add to your environment or startup script:

```bash
# Enable MCP server for notifications
export NEO_MCP_ENABLED=true
export NEO_MCP_HOST=localhost
export NEO_MCP_PORT=9000
```

### 2. Initialize Handlers

In your agent startup code:

```python
from core.mcp_conflict_notification_server import setup_mcp_handlers

# Setup IDE handlers
setup_mcp_handlers()
```

### 3. Integrate with Conflict Check

Modify your pre-generation check to notify IDEs:

```python
from core.pre_gen_check import check_for_conflicts
from core.mcp_conflict_notification_server import notify_ide_of_conflict

# Check for conflicts
risk, message = check_for_conflicts(
    agent_id="claude-code",
    file_path="src/auth.py",
    intent="Add OAuth2",
    region="authenticate() lines 20-40"
)

# If conflict detected, notify IDE
if risk.name in ["MEDIUM", "HIGH"]:
    await notify_ide_of_conflict(
        agent_id="claude-code",
        conflicting_agent="devin-agent",
        file_path="src/auth.py",
        intent="Add OAuth2",
        risk_level=risk.name,
        message=message,
        region="authenticate() lines 20-40",
        ide_targets=["claude-code"]  # Notify Claude Code
    )
```

---

## Claude Code Integration

### What User Sees

```
╔════════════════════════════════════════════════════════════════╗
║  🟡 Neo Coordination: CAUTION - MEDIUM Risk                     ║
╚════════════════════════════════════════════════════════════════╝

⚠️  Another Agent is Working Here

Agent:        devin-agent
File:         src/auth.py
Region:       authenticate() lines 20-40
Intent:       Add rate limiting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Actions:
  [Continue]        Proceed with your changes
  [Wait]            Wait for devin-agent to finish
  [Coordinate]      Send coordination request
  [Override]        Force proceed (expert mode)

🟡 WARNING: Can proceed but coordination recommended
```

### Installation

1. **Claude Code MCP Plugin**
   ```bash
   # Add to .claude/settings.json
   {
     "mcp_servers": {
       "neo_conflict": {
         "type": "stdio",
         "command": "python3",
         "args": ["core/mcp_conflict_notification_server.py"]
       }
     }
   }
   ```

2. **Setup Handler**
   ```python
   from core.adapters.claude_code_adapter import handle_conflict_notification
   
   # Handler automatically registers in setup_mcp_handlers()
   ```

3. **Usage in Claude Code**
   ```python
   # Automatic: When check_for_conflicts() detects conflict,
   # Claude Code will see the warning popup
   ```

---

## Devin Integration

### What User Sees

```
[14:23:45] 🟡 NEO COORDINATION ALERT [MEDIUM]

╭─ Conflict Detected ─────────────────────────────────────────╮
│
│  Another agent is working on this code:
│
│  🤖 Agent:     devin-agent
│  📄 File:      src/auth.py
│  📍 Region:    authenticate() lines 20-40
│  💭 Intent:    Add rate limiting
│
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
│
│  Your Options:
│
│  1️⃣  [CONTINUE]    Proceed with your changes
│  2️⃣  [WAIT]        Pause and wait for devin-agent
│  3️⃣  [COORDINATE]  Send message to devin-agent
│
╰──────────────────────────────────────────────────────────────╯

Type your choice (1/2/3) or 'help':
```

### Installation

1. **Devin MCP Connection**
   ```bash
   # Devin auto-connects to local Neo MCP server
   # Ensure NEO_MCP_ENABLED=true and NEO_MCP_PORT=9000
   ```

2. **Setup Handler**
   ```python
   from core.adapters.devin_adapter import handle_conflict_notification
   
   # Handler automatically registers in setup_mcp_handlers()
   ```

3. **Usage in Devin**
   ```python
   # Devin automatically receives and displays conflict warnings
   # User can type 1/2/3 to choose action
   ```

---

## OpenAI/Cursor Integration

### What User Sees

#### Chat Sidebar Message
```
✅ **Neo Coordination Alert** [MEDIUM]

Another agent is working on the code you're about to modify:

- **Agent:** devin-agent
- **File:** `src/auth.py`
- **Region:** authenticate() lines 20-40
- **Intent:** Add rate limiting

⚠️ **WARNING:** You can proceed, but merge conflicts may occur.

**Recommended Actions:**

1. **Wait** - Pause and let devin-agent finish first
2. **Coordinate** - Send a coordination message
3. **Continue** - Proceed with your changes
4. **Override** - Force priority (expert mode)

What would you like to do?
```

#### Inline Code Comment
```python
# 🟡 [Neo] devin-agent is modifying this region
# 🟡 Conflict Level: MEDIUM
# 🟡 Intent: Add rate limiting
# 🟡 Consider waiting or coordinating
def authenticate(self, username: str, password: str) -> bool:
    ...
```

#### Status Bar
```
🟡 Conflict detected in src/auth.py
```

### Installation

1. **Cursor Extension Setup**
   ```bash
   # Create .cursor/mcp_servers.json
   {
     "neo_conflict": {
       "command": "python3",
       "args": ["core/mcp_conflict_notification_server.py"],
       "env": {
         "NEO_MCP_ENABLED": "true"
       }
     }
   }
   ```

2. **Setup Handler**
   ```python
   from core.adapters.openai_adapter import handle_conflict_notification
   
   # Handler automatically registers in setup_mcp_handlers()
   ```

3. **Usage in Cursor**
   ```python
   # Cursor displays notification in chat sidebar
   # User responds with choice
   # Inline comments appear in affected code regions
   ```

---

## API Reference

### notify_ide_of_conflict()

Send a conflict notification to one or more IDEs.

```python
from core.mcp_conflict_notification_server import notify_ide_of_conflict

results = await notify_ide_of_conflict(
    agent_id="claude-code",           # Agent receiving notification
    conflicting_agent="devin-agent",  # Agent causing conflict
    file_path="src/auth.py",          # File with conflict
    intent="Add OAuth2",              # What this agent is doing
    risk_level="MEDIUM",              # LOW/MEDIUM/HIGH
    message="Devin is adding rate limiting",
    region="authenticate() lines 20-40",  # Optional: specific region
    ide_targets=["claude-code"]       # Optional: notify only these IDEs
)

# results: {"claude-code": True, "devin": False, "openai": False}
```

### ConflictNotification

Dataclass representing a notification:

```python
@dataclass
class ConflictNotification:
    notification_id: str          # Unique ID
    timestamp: str                # ISO format
    agent_id: str                 # Receiving agent
    conflicting_agent: str        # Agent causing conflict
    file_path: str                # File affected
    intent: str                   # What the other agent is doing
    risk_level: str               # LOW/MEDIUM/HIGH
    message: str                  # Detailed message
    region: Optional[str]         # Code region
    blocking: bool                # If HIGH risk
    suggested_action: str         # proceed/wait/coordinate
```

### IDE Adapter Handlers

Each adapter has an async handler that processes notifications:

```python
# Claude Code
from core.adapters.claude_code_adapter import handle_conflict_notification
await handle_conflict_notification(notification_dict)

# Devin
from core.adapters.devin_adapter import handle_conflict_notification
await handle_conflict_notification(notification_dict)

# OpenAI/Cursor
from core.adapters.openai_adapter import handle_conflict_notification
await handle_conflict_notification(notification_dict)
```

---

## Example: End-to-End Workflow

### Scenario: Devin and Claude Code both modifying same function

```python
# 1. Devin declares intent
from core.activity_log import log_activity

log_activity(
    developer_id="devin-agent",
    file_path="src/auth.py",
    intent="Add rate limiting to authenticate()",
    region="authenticate() lines 20-40"
)

# 2. Claude Code checks for conflicts
from core.pre_gen_check import check_for_conflicts
from core.mcp_conflict_notification_server import notify_ide_of_conflict

risk, message = check_for_conflicts(
    agent_id="claude-code",
    file_path="src/auth.py",
    intent="Add OAuth2 to authenticate()",
    region="authenticate() lines 20-40"
)

# 3. Conflict detected! Notify Claude Code IDE
if risk.name == "MEDIUM":
    await notify_ide_of_conflict(
        agent_id="claude-code",
        conflicting_agent="devin-agent",
        file_path="src/auth.py",
        intent="Add OAuth2",
        risk_level="MEDIUM",
        message=message,
        region="authenticate() lines 20-40",
        ide_targets=["claude-code"]
    )
    # Claude Code user sees: ⚠️ WARNING popup
    # User chooses: [Wait] to let Devin finish
    # Result: No merge conflict! ✅

# 4. Devin finishes, Claude Code continues
# Both changes successfully merged
```

---

## Configuration

### Environment Variables

```bash
# Enable/disable MCP server
export NEO_MCP_ENABLED=true

# MCP server host/port
export NEO_MCP_HOST=localhost
export NEO_MCP_PORT=9000

# IDE-specific settings
export NEO_CLAUDE_CODE_ENABLED=true
export NEO_DEVIN_ENABLED=true
export NEO_OPENAI_ENABLED=true
```

### .devsync Configuration

```json
{
  "mcp": {
    "enabled": true,
    "server": {
      "host": "localhost",
      "port": 9000
    },
    "ides": {
      "claude-code": {
        "enabled": true,
        "warning_level": "medium"
      },
      "devin": {
        "enabled": true,
        "warning_level": "medium"
      },
      "openai": {
        "enabled": true,
        "warning_level": "medium"
      }
    }
  }
}
```

---

## Troubleshooting

### IDE Not Receiving Notifications

1. **Check MCP Server Running**
   ```bash
   ps aux | grep mcp_conflict_notification_server
   ```

2. **Verify Port Open**
   ```bash
   lsof -i :9000
   ```

3. **Check Handler Registered**
   ```python
   from core.mcp_conflict_notification_server import get_mcp_server
   server = get_mcp_server()
   print(server.notification_handlers)
   ```

### Notifications Appear But Actions Don't Work

1. **Verify handlers are async**
   ```python
   asyncio.iscoroutinefunction(handler)  # Should be True
   ```

2. **Check adapter imports**
   ```python
   from core.adapters import claude_code_adapter
   # Should not raise ImportError
   ```

### High Latency

1. **Monitor notification latency**
   ```bash
   grep "latency" .devsync/conflict_notifications.log
   ```

2. **Reduce polling interval** (if applicable)
   - Default: 1000ms
   - Can lower to 500ms for faster detection

---

## Best Practices

1. **Always call `setup_mcp_handlers()` on startup**
   ```python
   from core.mcp_conflict_notification_server import setup_mcp_handlers
   setup_mcp_handlers()  # Call once at app initialization
   ```

2. **Notify before code generation**
   ```python
   # Notify BEFORE agent generates code
   await notify_ide_of_conflict(...)
   # Then agent gets user response and acts accordingly
   ```

3. **Handle both sync and async IDEs**
   ```python
   # Adapters handle both:
   if asyncio.iscoroutinefunction(handler):
       await handler(notification)
   else:
       handler(notification)
   ```

4. **Log all notifications for audit trail**
   ```bash
   cat .devsync/conflict_notifications.log | python3 -m json.tool
   ```

---

## Future Enhancements

- [ ] Slack integration for team notifications
- [ ] IDE-agnostic REST API for conflict queries
- [ ] Visual conflict graphs in web dashboard
- [ ] Automatic coordination suggestions based on history
- [ ] Mobile app for agent monitoring

---

## Support

- **Issues:** [GitHub Issues](https://github.com/jaykrishna316/Neo/issues)
- **Docs:** [docs/](.) folder
- **Examples:** [examples/](../examples/) folder

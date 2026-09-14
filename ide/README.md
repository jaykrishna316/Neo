# Neo IDE Integration for Claude Code

**Automatic conflict detection integrated into Claude Code IDE**

Prevents merge conflicts, failed builds, and wasted tokens by detecting resource conflicts *before* code generation.

---

## What It Does

When you generate code in Claude Code IDE:

```
You describe intent
        ↓
Neo checks for conflicts (pre-generation)
        ↓
✅ LOW risk → Code generates normally
⚠️ MEDIUM risk → Warning shown, proceed or wait
🚫 HIGH risk → Generation blocked, requires confirmation
```

**Result:** No merge conflicts, failed builds, or wasted agent tokens.

---

## Installation (Claude Code IDE)

### Step 1: Add to MCP Servers

Edit `~/.claude/mcp_servers.json`:

```json
{
  "neo-conflict-detection": {
    "command": "python3",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "NEO_MULTITENANCY": "false",
      "CLAUDE_TENANT_ID": "default"
    }
  }
}
```

### Step 2: Restart Claude Code IDE

Close and reopen Claude Code. Neo will now run automatically before code generation.

### Step 3: Confirm It's Working

You should see the conflict detection status appear before generation:
- ✅ GREEN (LOW) - safe
- ⚠️ ORANGE (MEDIUM) - warning
- 🚫 RED (HIGH) - blocked

---

## Enterprise Multitenancy Setup

For organizations using Neo multitenancy:

```json
{
  "neo-conflict-detection": {
    "command": "python3",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "NEO_MULTITENANCY": "true",
      "CLAUDE_TENANT_ID": "acme-corp"
    }
  }
}
```

**Each team/org:** Use their own `CLAUDE_TENANT_ID`

```json
{
  "neo-conflict-detection": {
    "command": "python3",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "NEO_MULTITENANCY": "true",
      "CLAUDE_TENANT_ID": "backend-team"
    }
  }
}
```

---

## How It Works

### Architecture

```
Claude Code IDE
    ↓ (before generation)
    ↓
MCP Server (neo-conflict-detection)
    ↓
Neo Core (check_for_conflicts)
    ↓
Activity Log (.devsync/)
    ↓
Risk Classifier (HIGH/MEDIUM/LOW)
    ↓
IDE Response (✅/⚠️/🚫)
    ↓
User Decision (generate/wait/confirm)
```

### MCP Methods

Neo exposes 4 MCP methods:

#### `neo/check_conflicts`
Check for conflicts before generation.

**Request:**
```json
{
  "method": "neo/check_conflicts",
  "params": {
    "agent_id": "claude-opus-1",
    "file_path": "src/auth.py",
    "intent": "Add OAuth2 support",
    "region": "authenticate_user function"
  }
}
```

**Response:**
```json
{
  "success": true,
  "risk_level": "MEDIUM",
  "message": "Another agent is working on src/auth.py",
  "should_block": false,
  "should_warn": true,
  "tenant_id": "acme-corp"
}
```

#### `neo/log_activity`
Log agent intent for conflict tracking.

**Request:**
```json
{
  "method": "neo/log_activity",
  "params": {
    "agent_id": "claude-opus-1",
    "file_path": "src/auth.py",
    "intent": "Add OAuth2 support",
    "intent_category": "feature"
  }
}
```

#### `neo/get_active_work`
See all active work in current tenant.

**Response:**
```json
{
  "success": true,
  "active_entries": [
    {
      "developer_id": "agent-a",
      "file_path": "src/auth.py",
      "intent": "Add OAuth2",
      "timestamp": 1234567890.5
    }
  ],
  "count": 1,
  "tenant_id": "acme-corp"
}
```

#### `neo/get_status`
Check server status.

**Response:**
```json
{
  "success": true,
  "status": "ok",
  "multitenancy_enabled": true,
  "tenant_id": "acme-corp",
  "version": "1.0"
}
```

---

## UI Integration

### Risk Level Display

**LOW (Safe)**
- Status: ✅ GREEN
- Message: "Clear to proceed"
- Action: Auto-continue

**MEDIUM (Warning)**
- Status: ⚠️ ORANGE
- Message: "Developer X working on this file - confirm?"
- Action: User can proceed or wait

**HIGH (Blocked)**
- Status: 🚫 RED
- Message: "Developer Y is making signature changes - coordinate first"
- Action: Requires explicit confirmation to override

---

## Usage Scenarios

### Scenario 1: No Conflicts (Typical)

```
Claude Code: Add OAuth2 to src/auth.py
             ↓
Neo: Check conflicts
     ✅ No conflicts detected
     ↓
Generation proceeds automatically
```

### Scenario 2: File Overlap (Warning)

```
Claude Code: Add logging to src/auth.py
             ↓
Neo: Check conflicts
     ⚠️ Agent-B also working on src/auth.py
        (different region - low risk)
     ↓
Warning shown: "Agent-B working on this file"
User confirms → generation proceeds
```

### Scenario 3: Signature Change (Blocked)

```
Claude Code: Refactor authenticate() function
             ↓
Neo: Check conflicts
     🚫 Agent-C changing same function signature
        (high risk - will break Agent-D's code)
     ↓
Generation blocked: "Cannot proceed"
User options:
  a) Wait for Agent-C to finish
  b) Coordinate with Agent-C
  c) Force override (not recommended)
```

---

## Configuration

### Environment Variables

```bash
# Enable multitenancy (optional)
export NEO_MULTITENANCY=true

# Set tenant ID (required if multitenancy enabled)
export CLAUDE_TENANT_ID=your-org-name

# MCP server port (optional)
export NEO_MCP_PORT=8000
```

### Claude Code Settings

Add to `.claude/config.json`:

```json
{
  "neo": {
    "enabled": true,
    "warn_on_medium": true,
    "block_on_high": true,
    "show_active_work": true,
    "show_suggestion_panel": true
  }
}
```

---

## Performance

| Operation | Latency | Notes |
|-----------|---------|-------|
| Conflict check | <10ms | Sub-perceptible |
| MCP overhead | <5ms | Negligible |
| Total pre-gen time | <15ms | User doesn't notice |

**Result:** Zero friction - happens transparently before code generation.

---

## Troubleshooting

### "Neo not responding"

**Cause:** MCP server failed to start  
**Solution:** Check permissions and Python installation

```bash
# Verify Python is available
python3 --version

# Test MCP server directly
python3 -m ide.mcp_neo_server
```

### "Conflict detection not working"

**Cause:** MCP server not configured correctly  
**Solution:** Verify ~/.claude/mcp_servers.json syntax

```bash
# Check configuration
cat ~/.claude/mcp_servers.json | python3 -m json.tool
```

### "Wrong tenant showing"

**Cause:** CLAUDE_TENANT_ID not set correctly  
**Solution:** Check environment variable

```bash
echo $CLAUDE_TENANT_ID
# Should show your tenant ID (e.g., "acme-corp")
```

### "Conflicts not detected"

**Cause:** Keyword heuristics not matching intent  
**Solution:** Use conflict trigger keywords in intent

**Good intents:**
- "Rename authenticate_user to loginUser"
- "Remove password validation"
- "Change database migration"

**Vague intents:**
- "Update authentication logic"
- "Improve code quality"
- "Refactor utils"

---

## Disabling Neo

### Temporarily (This Session)

```bash
# Remove from MCP config temporarily
# Or set in Claude Code: NEO_ENABLED=false
```

### Permanently

Remove the neo-conflict-detection entry from `~/.claude/mcp_servers.json` and restart Claude Code.

---

## Advanced: Custom IDE Hook

For custom IDE integrations:

```python
from ide.claude_code_integration import create_ide_hook

hook = create_ide_hook()
risk, message, meta = hook.check_before_generation(
    agent_id="my-agent",
    file_path="src/app.py",
    intent="Add feature X"
)

if hook.should_block(risk):
    print("⚠️ Conflicts detected - require confirmation")
elif hook.should_warn(risk):
    print("⚠️ Warning - proceed with caution")
else:
    print("✅ Safe to generate")
```

---

## API Reference

### NeoIDEHook

**Methods:**
- `check_before_generation(agent_id, file_path, intent, selection)` → (risk, message, metadata)
- `should_block(risk_level)` → boolean
- `should_warn(risk_level)` → boolean
- `get_ui_state(risk_level)` → dict

### NeoMCPServer

**Methods:**
- `handle_request(request)` → response dict
- `check_conflicts(params)` → conflict check result
- `log_activity_handler(params)` → logging confirmation
- `get_active_work(params)` → active entries
- `get_status()` → server status

---

## Next Steps

1. **Install** - Add to `~/.claude/mcp_servers.json`
2. **Restart** - Close and reopen Claude Code
3. **Test** - Start coding and watch Neo detect conflicts
4. **Configure** - Customize risk levels and settings as needed

---

**Status:** Production-ready  
**Latency:** <15ms (imperceptible)  
**Overhead:** Negligible  
**Cost:** Zero (runs locally)

For support, see `IDE_INTEGRATION.md` or the main Neo documentation.

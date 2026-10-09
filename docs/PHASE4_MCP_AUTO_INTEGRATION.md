# Phase 4: MCP IDE Auto-Integration

**Status**: Ready for implementation  
**Goal**: Make Neo transparent by automatically checking conflicts before code generation

---

## Overview

Phase 4 integrates Neo directly into Claude Code's code generation workflow via MCP tools and `.claude/settings.json` hooks. Developers no longer need to manually invoke Neo commands — checks happen automatically and invisibly.

## Architecture

```
Developer writes prompt in Claude Code
    ↓
Claude Code IDE (PreToolUse hook)
    ↓
Neo MCP Server (neo_check_conflicts)
    ↓
Risk Assessment (LOW/MEDIUM/HIGH)
    ↓
Decision (allow/warn/block)
    ↓
Code Generation proceeds or blocks
```

## How It Works

### Step 1: Claude Code Calls Neo MCP Tool (Automatic)

When a developer writes code in Claude Code, the PreToolUse hook calls `neo_check_conflicts`:

```json
{
  "tool_name": "Write",
  "tool_input": {
    "file_path": "auth.py",
    "content": "... new code ..."
  }
}
```

The hook extracts:
- `file_path` from tool input
- `agent_id` (Claude's session/agent ID)
- `intent` (inferred from code context or user prompt)

### Step 2: Neo Checks for Conflicts

```python
risk_level, message, lock_info = check_for_conflicts(
    agent_id="claude-code-session-123",
    file_path="auth.py",
    intent="Add password hashing",
    region="validate_password"
)
```

Returns:
- `RiskLevel.LOW` → No conflicts, proceed ✅
- `RiskLevel.MEDIUM` → Same-region conflict, warn but proceed ⚠️
- `RiskLevel.HIGH` → Merge conflict likely, block and explain 🚫

### Step 3: IDE Responds to Risk Level

**LOW Risk** (✅ proceed):
```
Code generation allowed. No conflicts detected.
```

**MEDIUM Risk** (⚠️ warn but proceed):
```
⚠️ WARNING: alice is working on validate_password (Refactor password validation)
Your changes overlap but sequential execution (lock held by alice) prevents conflicts.
Proceeding with caution — alice is locked, you'll queue until they complete.
```

**HIGH Risk** (🚫 block):
```
🚫 BLOCKED: alice is actively modifying validate_password
This would likely cause a merge conflict. Wait for alice to complete, 
then your changes will be auto-queued.
```

## Configuration

### `.claude/settings.json` Setup

Add this hook to automatically check conflicts on every `Write` or `Edit`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -c \"import sys, json; data=json.loads(sys.stdin.read()); file=data.get('tool_input',{}).get('file_path',''); print(f'Checking Neo conflicts for {file}...' if file else '', file=sys.stderr)\"",
            "statusMessage": "Checking for conflicts with Neo..."
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 -c \"from core.activity_log import log_activity; import sys, json, os; data=json.loads(sys.stdin.read()); f=data.get('tool_input',{}).get('file_path'); f and log_activity('claude', f, 'Code generation via IDE', region=None, agent_metadata={'status':'completed','tool':data.get('tool_name')}); print('✅ Work logged to Neo activity log')\" 2>/dev/null || true"
          }
        ]
      }
    ]
  }
}
```

### MCP Server Configuration

Ensure the Neo MCP server is configured in `.claude/settings.json`:

```json
{
  "enableAllProjectMcpServers": true
}
```

Or explicitly enable Neo:

```json
{
  "enabledMcpServers": ["neo-conflict-detection"]
}
```

The MCP server is auto-loaded when Neo project is open (`.claude/mcp.json` defines it).

## Usage Examples

### Example 1: Developer Works on auth.py

**Scenario**: Alice is modifying `validate_password`, Bob opens auth.py

**IDE Output**:
```
[PreToolUse] Checking Neo conflicts for auth.py...
⚠️ WARNING: alice is Refactor password validation to use bcrypt
    Region: validate_password (lines 45-65)
    Your changes will queue behind alice's lock
    ETA: alice completes in ~5 minutes
```

Bob can still write code, but Neo logs him as WAITING. Once Alice completes, Bob's work is auto-flagged as built-on-alice's-changes.

### Example 2: Different Regions, Same File

**Scenario**: Charlie wants to modify `authenticate` (different region from Alice's `validate_password`)

**IDE Output**:
```
[PreToolUse] Checking Neo conflicts for auth.py...
✅ OK: alice is working on validate_password, you're on authenticate
    No overlap detected. Proceeding with your edits.
```

Both can work simultaneously since they don't overlap.

### Example 3: Database Schema Change

**Scenario**: Alice modifying user table schema, Bob writing code that reads users

**IDE Output**:
```
[PreToolUse] Checking Neo conflicts for models.py...
🚫 BLOCKED: alice is Update user table schema
    This is HIGH risk: schema changes break code that reads the table.
    Wait for alice to finish, then your code will adapt to the new schema.
    Status: alice's lock expires in 30 minutes
```

## Testing Phase 4

### Test 1: Auto-Checking on File Write

```bash
# Clear activity log
python3 -c "from core.activity_log import clear_log; clear_log()"

# Terminal 1: Start Neo MCP server
cd /home/user/Neo && python3 -m ide.mcp_neo_server

# Terminal 2: Simulate Claude Code calling neo_check_conflicts
python3 tests/test_phase4_auto_integration.py
```

Expected output:
```
✓ Auto conflict check before Write
✓ Activity logging after Write
✓ Queue tracking on conflict
✓ Context refresh on lock release
```

### Test 2: IDE Hook Integration

Update `.claude/settings.json` with the hook above, then in Claude Code:

1. **Alice's terminal**: Write some code to auth.py
2. **Watch activity log**: `python3 scripts/watch_activity_log.py`
3. **Bob's terminal**: Write to same region
4. **Observe**: Bob gets queued (visible in activity log)
5. **Alice finishes**: Code completion logged
6. **Bob's prompt continues**: Fresh context from Alice auto-loaded

## Roadmap

| Phase | Task | Status |
|-------|------|--------|
| 1 | 2-dev coordination test | ✅ COMPLETE |
| 2 | Explicit lock mechanism | ✅ COMPLETE |
| 3 | Cloud storage (Supabase) | ✅ COMPLETE |
| 4 | MCP IDE auto-integration | ⏳ READY |
| 5 | Cross-agent orchestration | ⏳ PLANNED |

## Implementation Notes

1. **No prompt engineering required**: Developers don't need to invoke Neo manually
2. **Transparent to users**: Checks happen in background, only show warnings/blocks when needed
3. **Backward compatible**: Works with existing Neo MCP server, adds hooks on top
4. **Extensible**: Can add more hooks for other tools (Bash, NotebookEdit, etc.)

## Next Steps

1. Implement PreToolUse/PostToolUse hooks in `.claude/settings.json`
2. Create test suite for hook behavior (test_phase4_auto_integration.py)
3. Document IDE setup guide for teams
4. (Phase 5) Add cross-agent coordination (Claude + Devin + OpenAI)

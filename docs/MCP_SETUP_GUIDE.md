# Neo MCP Server Setup Guide

**This guide explains how to set up the Neo MCP (Model Context Protocol) server so Claude Code can automatically check for conflicts before generating code.**

## What Is This?

The Neo MCP server allows Claude Code IDE to call Neo's conflict detection **before** any code is written. This prevents merge conflicts and wasted tokens by catching resource conflicts early.

## Architecture

```
Claude Code IDE
    ↓ (before Write/Edit)
    ↓
MCP Client (JSON-RPC 2.0)
    ↓
Neo MCP Server
    ↓
check_for_conflicts() → Risk Level (LOW/MEDIUM/HIGH)
    ↓
Claude Code (allow/warn/block)
```

## Prerequisites

- Python 3.8+
- `pip` and `venv`
- Neo repository cloned
- Claude Code IDE installed

## Installation Steps

### Step 1: Create Virtual Environment

```bash
cd /path/to/Neo
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### Step 2: Install MCP SDK

```bash
pip install mcp
```

### Step 3: Update `.mcp.json`

Create or update `.mcp.json` in your Neo project root:

```json
{
  "mcpServers": {
    "neo": {
      "command": "/path/to/Neo/.venv/bin/python3",
      "args": ["-m", "ide.mcp_neo_server"],
      "env": {
        "PYTHONPATH": "/path/to/Neo",
        "NEO_MULTITENANCY": "false",
        "CLAUDE_TENANT_ID": "default"
      }
    }
  }
}
```

**Critical Points:**
- Replace `/path/to/Neo` with your actual full path
- The `command` must point to the venv Python (not system python3)
- Use absolute paths, not relative paths
- For multitenancy: set `NEO_MULTITENANCY` to `"true"` and customize `CLAUDE_TENANT_ID`

### Step 4: Update Global Claude Code Settings

Add hook configuration to your global settings at `~/.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python3 /path/to/Neo/scripts/check_conflict_hook.py",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

**Important:** Replace `/path/to/Neo` with your actual Neo directory path.

### Step 5: Restart Claude Code

- Close Claude Code completely (force quit if needed)
- Reopen Claude Code
- Claude Code will now auto-launch the MCP server

## Verification

### Test 1: Call MCP Tool from Claude Code

In Claude Code, try this prompt:

```
Call the neo_check_conflicts MCP tool on src/auth.py
```

Expected response:
```
LOW risk, safe to proceed
```

(If conflicts exist, you'll see MEDIUM or HIGH risk instead)

### Test 2: Automatic Hook Triggers

Try this prompt:

```
Add a comment to src/auth.py
```

Before writing, the hook should run automatically:
- **LOW risk** → Writes silently
- **MEDIUM risk** → Shows warning, you can proceed
- **HIGH risk** → Blocks the write, shows message

### Test 3: Server Direct Test

Verify the server works standalone:

```bash
cd /path/to/Neo
source .venv/bin/activate
python3 -m ide.mcp_neo_server
```

Should start and wait for JSON-RPC input (no banner—that's correct).

## MCP Tools Reference

### neo_check_conflicts

Check for conflicts before code generation.

**Parameters:**
- `agent_id`: Developer identifier (e.g., "claude-code")
- `file_path`: File being edited (e.g., "src/auth.py")
- `intent`: What you're doing (e.g., "code generation")
- `region`: (optional) Code region

**Response:**
```json
{
  "success": true,
  "risk_level": "LOW|MEDIUM|HIGH",
  "message": "Description of conflicts if any",
  "should_block": false,
  "should_warn": false
}
```

### neo_log_activity

Log developer activity for tracking.

**Parameters:**
- `agent_id`: Developer identifier
- `file_path`: File path
- `intent`: What the developer is doing
- `intent_category`: (optional) feature|bugfix|refactor|other
- `region`: (optional) Code region

### neo_get_active_work

Get all active developer work.

**Returns:** List of active entries with timestamps and intents.

### neo_get_status

Check Neo MCP server status.

**Returns:** Version, multitenancy setting, tenant ID.

## Troubleshooting

### MCP Server Times Out (CONNECT_TIMEOUT)

**Problem:** Claude Code can't connect to the Neo MCP server.

**Solutions:**
1. Verify `.mcp.json` is valid JSON:
   ```bash
   python3 -m json.tool /path/to/Neo/.mcp.json
   ```

2. Verify venv and mcp are installed:
   ```bash
   source /path/to/Neo/.venv/bin/activate
   python3 -c "import mcp; print(mcp.__version__)"
   ```

3. Check the command path is absolute:
   ```bash
   which python3  # Use full path in .mcp.json
   ```

4. Completely restart Claude Code after changing `.mcp.json`

5. Verify Python can start the server:
   ```bash
   source /path/to/Neo/.venv/bin/activate
   python3 -m ide.mcp_neo_server
   ```

### ModuleNotFoundError: No module named 'mcp'

**Problem:** MCP SDK isn't installed.

**Solution:**
```bash
source /path/to/Neo/.venv/bin/activate
pip install mcp
```

### Hook Not Running

**Problem:** Pre-generation hook doesn't trigger before writes.

**Solution:**
1. Verify `~/.claude/settings.json` has the hook
2. Completely restart Claude Code
3. Try an edit operation
4. Check hook command path is correct and absolute

### Hook Is Slow

**Problem:** Conflict check takes > 5 seconds.

**Solution:** Increase timeout in `~/.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "python3 /path/to/Neo/scripts/check_conflict_hook.py",
        "timeout": 10
      }]
    }]
  }
}
```

## Key Implementation Details

### Why Real MCP Protocol Matters

Custom JSON protocols don't work with Claude Code's MCP client. The server **must** implement:
- **JSON-RPC 2.0** (not raw JSON lines)
- **initialize handshake** (not just a startup banner)
- **tools/list** endpoint
- **tools/call** endpoint

### Why Virtual Environment

System Python usually doesn't have the MCP SDK. Use project-local `.venv/`:
- Dependencies stay isolated
- Team gets consistent versions
- `.mcp.json` points to known Python with mcp

### Why Absolute Paths

Claude Code's subprocess launcher needs absolute paths:
- Can't resolve relative paths
- Can't rely on $PATH
- Use `which python3` to get full path

## Example: Multi-Developer Workflow

```
Developer A: "Add OAuth2 to src/auth.py"
    ↓
Claude Code calls neo_check_conflicts
    ↓
Neo: "HIGH RISK - B is changing authenticate() signature"
    ↓
Claude Code: ⚠️ "Coordinate with B first"
    ↓
Developer A waits for B to finish
    ↓
Developer B finishes and pushes
    ↓
Developer A tries again
    ↓
Neo: "LOW RISK - Safe now"
    ↓
Code generates ✅
```

## Testing

Run the two-developer coordination test:

```bash
python3 tests/test_two_developer_coordination.py
```

Shows:
- ✅ Lock applied at 2+ developers
- ✅ Conflict detection working
- ✅ Context refresh after first dev finishes
- ✅ Zero conflicts in final result

## Support

If you encounter issues:
1. Check the Troubleshooting section
2. Review `.mcp.json` and `~/.claude/settings.json`
3. Run the test suite to verify core functionality
4. Check Claude Code logs in `~/.claude/logs/`

---

**Status:** ✅ Production-ready  
**Protocol:** JSON-RPC 2.0 via stdio  
**SDK:** mcp >= 0.3.0  
**Python:** 3.8+

For automatic pre-generation hooks, see `AUTOMATIC_CONFLICT_DETECTION.md`.

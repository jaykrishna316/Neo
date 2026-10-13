# Neo MCP Server Troubleshooting Guide

This guide covers common issues with Neo's MCP (Model Context Protocol) server connectivity and provides step-by-step solutions.

## Quick Diagnostics

### Check if MCP Server is Running

```bash
cd /path/to/Neo
ps aux | grep "ide.mcp_neo_server"
```

If you see a Python process running `ide.mcp_neo_server`, the server is active.

### Check MCP Tools Availability in Claude Code

In Claude Code, ask:
```
List all available MCP tools you can access
```

Look for tools starting with `mcp__neo__`:
- `mcp__neo__neo_check_conflicts`
- `mcp__neo__neo_log_activity`
- `mcp__neo__neo_get_active_work`
- `mcp__neo__neo_get_status`

If these are missing, the MCP server isn't connected.

---

## Common Issues & Solutions

### Issue 1: MCP Server Won't Start

**Symptom:** Running `python3 -m ide.mcp_neo_server` produces an error or exits immediately.

**Diagnosis:**
```bash
cd /path/to/Neo
PYTHONPATH=. .venv/bin/python3 -m ide.mcp_neo_server
```

Check the error message that appears.

**Solutions:**

#### A. Missing `mcp` Package
**Error:** `ModuleNotFoundError: No module named 'mcp'`

**Fix:**
```bash
cd /path/to/Neo
.venv/bin/pip install mcp>=0.1.0
```

Verify installation:
```bash
.venv/bin/pip list | grep mcp
```

---

#### B. Wrong Python Path
**Error:** `No such file or directory` or import errors

**Fix:** Verify the full path to Python in your venv:
```bash
which python3  # Get the system python
cd /path/to/Neo
ls -la .venv/bin/python3
```

Then start the server with the full path:
```bash
/full/path/to/Neo/.venv/bin/python3 -m ide.mcp_neo_server
```

---

#### C. Wrong PYTHONPATH
**Error:** `ModuleNotFoundError: No module named 'core'` or `ide`

**Fix:** Always set PYTHONPATH when starting:
```bash
cd /path/to/Neo
PYTHONPATH=. .venv/bin/python3 -m ide.mcp_neo_server
```

The `.` means "current directory" (Neo root).

---

### Issue 2: MCP Server Starts but Claude Code Can't Connect

**Symptom:** Server runs fine (terminal blocks, no errors), but Neo tools aren't available in Claude Code.

**Root Cause:** `.claude/mcpjson/neo.mcpjson` configuration is incorrect or Claude Code hasn't reloaded it.

**Solutions:**

#### A. Fix `.claude/mcpjson/neo.mcpjson` Configuration

**On macOS:**
```json
{
  "mcpServers": {
    "neo-conflict-detection": {
      "command": "/Users/yourname/Neo/.venv/bin/python3",
      "args": ["-m", "ide.mcp_neo_server"],
      "env": {
        "PYTHONPATH": "/Users/yourname/Neo",
        "NEO_MULTITENANCY": "false",
        "CLAUDE_TENANT_ID": "default"
      }
    }
  }
}
```

**On Linux:**
```json
{
  "mcpServers": {
    "neo-conflict-detection": {
      "command": "/home/user/Neo/.venv/bin/python3",
      "args": ["-m", "ide.mcp_neo_server"],
      "env": {
        "PYTHONPATH": "/home/user/Neo",
        "NEO_MULTITENANCY": "false",
        "CLAUDE_TENANT_ID": "default"
      }
    }
  }
}
```

**Key Points:**
- `command` must be the **full absolute path** to Python
- Don't use bare `python3` - it won't work reliably
- `PYTHONPATH` must point to the Neo root directory

Verify the path exists:
```bash
ls -la /your/full/path/Neo/.venv/bin/python3
```

---

#### B. Restart Claude Code IDE

After fixing the configuration, fully restart Claude Code:
```bash
# Close Claude Code completely
# Then reopen it
```

Claude Code only reads the MCP configuration on startup.

---

### Issue 3: "Neo MCP Server Disconnected"

**Symptom:** Tools were working, then Claude Code says "Neo MCP server has disconnected."

**Root Causes:**
1. MCP server process crashed
2. MCP server was killed
3. Network interruption (rare in local setup)

**Solutions:**

#### A. Restart the MCP Server Process

Kill any existing processes:
```bash
pkill -f "ide.mcp_neo_server"
```

Wait a moment, then restart:
```bash
cd /path/to/Neo
PYTHONPATH=. .venv/bin/python3 -m ide.mcp_neo_server
```

The terminal should block (waiting for client). If it exits or shows an error, see **Issue 1**.

---

#### B. Restart Claude Code IDE

Even if the server is running, Claude Code may need to reconnect:
1. Close Claude Code completely
2. Reopen it
3. Try the MCP tool again

---

### Issue 4: MCP Tool Calls Fail with "Internal Error"

**Symptom:** MCP tools load, but calling them returns "Neo MCP server encountered an internal issue."

**Common Errors:**

#### A. "too many values to unpack (expected 2, got 3)"

**Symptom:** `neo_check_conflicts` returns "server-side error"

**Location:** `ide/mcp_neo_server.py` line 123

**Problem:** `check_for_conflicts()` returns 3 values, but code only unpacked 2.

**Before (Wrong):**
```python
try:
    risk_level, message = check_for_conflicts(
        agent_id=agent_id,
        file_path=file_path,
        intent=intent,
        region=region,
        tenant_id=final_tenant,
    )
```

**After (Correct):**
```python
try:
    risk_level, message, lock_info = check_for_conflicts(
        agent_id=agent_id,
        file_path=file_path,
        intent=intent,
        region=region,
        tenant_id=final_tenant,
    )
```

**Verification:**
```bash
grep -A 6 "risk_level, message" ide/mcp_neo_server.py | head -1
# Should show: risk_level, message, lock_info = check_for_conflicts(
```

---

#### B. Activity Logging Fails: Missing Timestamp

**Symptom:** `neo_log_activity` returns "server-side error: too many values to unpack"

**Location:** `ide/mcp_neo_server.py` line 188-193

**Problem:** ActivityEntry requires timestamp, but MCP tool wasn't providing it:

**Before (Wrong):**
```python
entry = ActivityEntry(
    developer_id=agent_id,
    file_path=file_path,
    intent=intent,
    region=region,
)
```

**After (Correct):**
```python
entry = ActivityEntry(
    developer_id=agent_id,
    file_path=file_path,
    intent=intent,
    region=region,
    timestamp=time.time(),           # REQUIRED - Unix timestamp
    tenant_id=final_tenant,           # REQUIRED - for multitenancy support
    intent_category=intent_category,  # OPTIONAL but recommended
)
```

**Verification:**
```bash
# Check that time is imported at the top of the file:
head -20 ide/mcp_neo_server.py | grep "import time"
# Should output: import time

# Verify the fix is in place:
grep -A 8 "entry = ActivityEntry" ide/mcp_neo_server.py | grep "timestamp=time.time()"
# Should find the line with timestamp=time.time()
```

---

#### C. Conflict Check Returns Unexpected Risk Level

**Symptom:** `neo_check_conflicts` runs but returns wrong data

**Diagnosis:** Check that `check_for_conflicts` in `core/pre_gen_check.py` is being called correctly:
```python
risk_level, message, lock_info = check_for_conflicts(
    agent_id=agent_id,
    file_path=file_path,
    intent=intent,
    region=region,
    tenant_id=final_tenant,
)
```

All parameters must match the function signature.

---

### Issue 4.5: JSONL Format Error in core/activity_log.py

**Symptom:** Activity log entries won't parse, or old `clear_log()` function breaks JSONL format

**Location:** `core/activity_log.py` line 283

**Problem:** `clear_log()` was writing JSON array syntax instead of empty JSONL:

**Before (Wrong):**
```python
def clear_log(tenant_id: Optional[str] = None) -> None:
    log_file = ensure_log_exists(tenant_id)
    log_file.write_text(json.dumps([]))  # Writes [] - wrong format!
```

**After (Correct):**
```python
def clear_log(tenant_id: Optional[str] = None) -> None:
    log_file = ensure_log_exists(tenant_id)
    log_file.write_text("")  # Writes empty file - correct!
```

**Why:** Activity log uses JSONL format (one JSON object per line), not JSON array. Writing `[]` breaks the parser.

**Verification:**
```bash
# Check the fix is in place:
grep -A 2 "def clear_log" core/activity_log.py | grep 'write_text'
# Should show: log_file.write_text("") - NOT json.dumps([])
```

---

### Issue 5: Activity Log Not Getting Updated

**Symptom:** `neo_log_activity` returns success, but `.devsync/activity-log.json` is empty or not updated.

**Solutions:**

#### A. Check if Activity Log Directory Exists

```bash
ls -la .devsync/
```

Should show:
```
-rw-r--r--  1 user  staff     N Oct 13 12:00 activity-log.json
```

If missing, create it:
```bash
mkdir -p .devsync
```

---

#### B. Verify File Permissions

```bash
chmod 644 .devsync/activity-log.json
chmod 755 .devsync/
```

---

#### C. Check Activity Log Format

The activity log uses JSONL format (one JSON object per line), not a JSON array.

**Correct format:**
```
{"developer_id":"alice","file_path":"src/auth.py","timestamp":1234567890,...}
{"developer_id":"bob","file_path":"src/auth.py","timestamp":1234567891,...}
```

**Wrong format:**
```
[
  {"developer_id":"alice",...},
  {"developer_id":"bob",...}
]
```

If the file has the wrong format, clear it:
```bash
echo "" > .devsync/activity-log.json
```

---

### Issue 6: Multitenancy Issues

**Symptom:** Activity logs from different agents are mixing or not isolated.

**Check Configuration:**
```bash
cat .claude/mcpjson/neo.mcpjson | grep NEO_MULTITENANCY
```

Should show `"NEO_MULTITENANCY": "false"` for single-tenant setup.

**If multitenancy is enabled but shouldn't be:**
```json
"env": {
  "PYTHONPATH": "/path/to/Neo",
  "NEO_MULTITENANCY": "false",
  "CLAUDE_TENANT_ID": "default"
}
```

---

### Issue 7: Automatic Hook Configuration (Optional)

**Note:** This is optional. You can call Neo MCP tools manually in Claude Code, or set up hooks for automatic conflict checking.

**For Automatic Pre-Generation Conflict Checking:**

Configure `.claude/settings.json`:
```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "agent",
            "prompt": "Before the user edits this file, check if there are any conflicts with neo_check_conflicts MCP tool. Extract the file_path from the tool input and use it to check for conflicts.",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "agent",
            "prompt": "After the user edits a file, automatically log the activity using neo_log_activity MCP tool.",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

This enables:
- **PreToolUse:** Automatically run conflict check before file edits
- **PostToolUse:** Automatically log activity after file edits

**Troubleshooting Hooks:**
- Hooks only run if MCP tools are available (requires working MCP server)
- Restart Claude Code after changing settings.json
- Hook errors appear in the Claude Code terminal, not the MCP server terminal

---

## Verification Checklist

Use this checklist to verify your MCP setup is working:

- [ ] MCP package installed: `pip list | grep mcp`
- [ ] `core/activity_log.py` line 283 has `log_file.write_text("")` (not `json.dumps([])`)
- [ ] `ide/mcp_neo_server.py` line 123 unpacks 3 values: `risk_level, message, lock_info`
- [ ] `ide/mcp_neo_server.py` line 188+ has `timestamp=time.time()` in ActivityEntry creation
- [ ] `.claude/mcpjson/neo.mcpjson` exists with correct absolute paths (not bare `python3`)
- [ ] Python path is absolute: `/Users/xxx/...` (macOS) or `/home/xxx/...` (Linux)
- [ ] PYTHONPATH points to Neo root directory
- [ ] MCP server runs: `PYTHONPATH=. python3 -m ide.mcp_neo_server` (blocks, doesn't exit)
- [ ] Claude Code restarted after config changes
- [ ] Neo tools appear in Claude Code MCP tools list
- [ ] `neo_check_conflicts` returns LOW/MEDIUM/HIGH risk
- [ ] `neo_log_activity` logs without errors
- [ ] `.devsync/activity-log.json` has entries in JSONL format (one JSON object per line)

---

## Testing the Full Workflow

Once everything is working:

### Single Developer Test

1. **Check conflicts before creating file:**
   ```
   Use mcp__neo__neo_check_conflicts
   agent_id: claude-code-dev-1
   file_path: src/test.py
   intent: Add test functions
   ```

2. **Create the file** in Claude Code

3. **Log the activity:**
   ```
   Use mcp__neo__neo_log_activity
   agent_id: claude-code-dev-1
   file_path: src/test.py
   intent: Add test functions - COMPLETED
   intent_category: feature
   ```

4. **Verify activity log:**
   ```bash
   cat .devsync/activity-log.json | jq '.'
   ```

### Two Developer Test

1. **First developer** follows single developer test above

2. **Second developer** checks conflicts on same file:
   ```
   Use mcp__neo__neo_check_conflicts
   agent_id: claude-code-dev-2
   file_path: src/test.py
   intent: Add more tests
   ```

   Should show **MEDIUM or HIGH RISK** due to conflict with first developer.

3. **Verify lock state** in activity log:
   ```bash
   cat .devsync/activity-log.json | jq '.[] | {developer_id, lock_state}'
   ```

---

## Logs and Debugging

### Check MCP Server Logs

If the server is running, errors appear in the terminal where you started it.

To capture logs to a file:
```bash
cd /path/to/Neo
PYTHONPATH=. .venv/bin/python3 -m ide.mcp_neo_server > mcp_server.log 2>&1 &
```

Then view:
```bash
tail -f mcp_server.log
```

### Check Activity Log Structure

```bash
cat .devsync/activity-log.json | jq '.'
```

Each entry should have:
- `developer_id`: Agent making the change
- `file_path`: File being modified
- `intent`: What they're doing
- `timestamp`: Unix timestamp (float)
- `tenant_id`: Should be "default" for single-tenant

---

## Getting Help

If you're still stuck:

1. **Collect diagnostic info:**
   ```bash
   echo "=== Python Version ===" && python3 --version
   echo "=== MCP Installed ===" && pip list | grep mcp
   echo "=== Config ===" && cat .claude/mcpjson/neo.mcpjson
   echo "=== Python Path ===" && which python3
   echo "=== venv Python ===" && ls -la .venv/bin/python3
   ```

2. **Start server with verbose output:**
   ```bash
   PYTHONPATH=. python3 -m ide.mcp_neo_server
   ```

3. **Check for errors** in the terminal output

4. **Verify the fix** is actually in the code by checking the file directly:
   ```bash
   grep "timestamp=time.time()" ide/mcp_neo_server.py
   ```

---

## Summary

| Issue | Solution |
|-------|----------|
| Server won't start | Install `mcp` package, check Python path |
| Tools not in Claude Code | Fix `.claude/mcpjson/neo.mcpjson`, restart Claude Code |
| Server disconnects | Kill old process, restart with `PYTHONPATH=.` |
| Tool calls fail | Check code for proper unpacking, timestamp handling |
| Activity log empty | Check file format (JSONL not JSON), permissions |
| Multitenancy issues | Set `NEO_MULTITENANCY` to false in config |

---

**Version:** 1.0  
**Last Updated:** October 13, 2024

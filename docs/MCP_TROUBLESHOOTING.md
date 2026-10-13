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

## Reference Implementation: `ide/mcp_neo_server.py`

This is the **canonical, working version** of the MCP server file. Use this as a reference if your implementation is not working. Key requirements:

- **Line 123:** Unpacks 3 values from `check_for_conflicts()`: `risk_level, message, lock_info`
- **Lines 188-196:** Creates `ActivityEntry` with all required fields including `timestamp=time.time()`
- **All tools** (neo_check_conflicts, neo_log_activity, neo_get_active_work, neo_get_status) properly implemented
- **Rate limiting** and **multitenancy** support included

### Complete File Content

```python
#!/usr/bin/env python3
"""MCP (Model Context Protocol) Server for Neo Conflict Detection.

Allows Claude Code IDE to call Neo conflict detection via MCP protocol.
Runs as a subprocess managed by Claude Code, speaking real MCP
(JSON-RPC 2.0 over stdio, including the `initialize` handshake) via the
official `mcp` SDK.
"""

import os
import sys
import time
import logging
import re
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server.mcpserver import MCPServer

from core.activity_log_adapter import ActivityLogAdapter
from core.activity_log import ActivityEntry
from core.pre_gen_check import check_for_conflicts, check_source_staleness
from core.delta_refresh import DeltaGenerator, ContextRefreshBuilder
from core.symbol_hasher import snapshot_file

TENANT_ID = os.getenv("CLAUDE_TENANT_ID", "default")
MULTITENANCY = os.getenv("NEO_MULTITENANCY", "false").lower() == "true"
RATE_LIMIT_PER_MINUTE = int(os.getenv("NEO_RATE_LIMIT", "100"))
DEBUG_MODE = os.getenv("NEO_DEBUG", "false").lower() == "true"

logger = logging.getLogger("neo-mcp")
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

mcp = MCPServer(name="neo-conflict-detection", version="1.0")


class RateLimiter:
    """Rate limiter for MCP requests per tenant."""

    def __init__(self, requests_per_minute: int = 100):
        self.limit = requests_per_minute
        self.requests: Dict[str, deque] = defaultdict(deque)

    def is_allowed(self, tenant_id: str) -> bool:
        """Check if request is allowed for tenant."""
        now = time.time()
        minute_ago = now - 60

        while self.requests[tenant_id] and self.requests[tenant_id][0] < minute_ago:
            self.requests[tenant_id].popleft()

        if len(self.requests[tenant_id]) >= self.limit:
            return False

        self.requests[tenant_id].append(now)
        return True

    def get_remaining(self, tenant_id: str) -> int:
        """Get remaining requests for tenant this minute."""
        now = time.time()
        minute_ago = now - 60

        while self.requests[tenant_id] and self.requests[tenant_id][0] < minute_ago:
            self.requests[tenant_id].popleft()

        return self.limit - len(self.requests[tenant_id])


def _validate_tenant_id(tenant_id: Optional[str]) -> bool:
    """Validate tenant_id format (alphanumeric + hyphens)."""
    if not tenant_id:
        return True
    return bool(re.match(r"^[a-zA-Z0-9\-_]+$", tenant_id))


def _tenant() -> Optional[str]:
    return TENANT_ID if MULTITENANCY else None


rate_limiter = RateLimiter(RATE_LIMIT_PER_MINUTE)


@mcp.tool(name="neo_check_conflicts")
def neo_check_conflicts(
    agent_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Check for conflicts before code generation.

    Args:
        agent_id: Unique identifier for the calling agent.
        file_path: File being modified.
        intent: Description of what the agent intends to do.
        region: Optional region (lines/function) being modified.
        tenant_id: Optional tenant for multitenancy (overrides env if provided).
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        risk_level, message, lock_info = check_for_conflicts(
            agent_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
            tenant_id=final_tenant,
        )
        risk_str = risk_level.value if hasattr(risk_level, "value") else str(risk_level)

        return {
            "success": True,
            "risk_level": risk_str,
            "message": message,
            "should_block": risk_str == "HIGH",
            "should_warn": risk_str == "MEDIUM",
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Conflict check failed: {e}")
        return {
            "success": False,
            "error": f"Conflict check failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_log_activity")
def neo_log_activity(
    agent_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
    intent_category: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Log a developer's or agent's intent to work on a file.

    Args:
        agent_id: Unique identifier for the calling agent.
        file_path: File being modified.
        intent: Description of what the agent intends to do.
        region: Optional region (lines/function) being modified.
        intent_category: Optional category (feature/bugfix/refactor/other).
        tenant_id: Optional tenant for multitenancy (overrides env if provided).
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        entry = ActivityEntry(
            developer_id=agent_id,
            file_path=file_path,
            intent=intent,
            region=region,
            timestamp=time.time(),
            tenant_id=final_tenant,
            intent_category=intent_category,
        )
        ActivityLogAdapter.append_entry(entry, tenant_id=final_tenant)
        return {
            "success": True,
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Activity log write failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_get_active_work")
def neo_get_active_work(tenant_id: Optional[str] = None) -> Dict[str, Any]:
    """View all active developers/agents currently logged as working.

    Args:
        tenant_id: Optional tenant for multitenancy (overrides env if provided).
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        entries = ActivityLogAdapter.get_active_entries(tenant_id=final_tenant)
        return {
            "success": True,
            "active_entries": [
                e.to_dict() if hasattr(e, "to_dict") else e.__dict__ for e in entries
            ],
            "count": len(entries),
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Active work query failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "count": 0,
            "active_entries": [],
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_check_source_staleness")
def neo_check_source_staleness(
    file_path: str,
    agent_id: str,
    read_time: float,
    dependency_symbols: Optional[list] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Check if source file is stale using C1 (symbol-level hash detection).

    Args:
        file_path: Path to the file to check
        agent_id: Agent that originally read the file
        read_time: When the file was read (Unix timestamp)
        dependency_symbols: Specific symbols to check (None = whole file)
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        state, report = check_source_staleness(
            file_path=file_path,
            agent_id=agent_id,
            read_time=read_time,
            dependency_symbols=dependency_symbols,
            tenant_id=final_tenant,
        )

        return {
            "success": True,
            "staleness_state": state,  # CURRENT / STALE_SOURCE / UNVERIFIABLE
            "report": report,
            "is_current": state == "CURRENT",
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Staleness check failed: {e}")
        return {
            "success": False,
            "error": f"Staleness check failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_get_context_refresh")
def neo_get_context_refresh(
    file_path: str,
    agent_id: str,
    base_snapshot_time: float,
    dependency_symbols: Optional[list] = None,
    tenant_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get symbol-level context refresh delta (C2).

    Uses delta refresh to send only changed symbols instead of full file,
    reducing token costs by 10-100x.

    Args:
        file_path: Path to the file to refresh
        agent_id: Agent requesting the refresh
        base_snapshot_time: When agent last read the file
        dependency_symbols: Specific symbols to include (None = all)
        tenant_id: Optional tenant for multitenancy
    """
    final_tenant = tenant_id if tenant_id else _tenant()

    if not _validate_tenant_id(final_tenant):
        return {
            "success": False,
            "error": "Invalid tenant_id format",
            "status_code": 403,
        }

    if not rate_limiter.is_allowed(final_tenant or "default"):
        remaining = rate_limiter.get_remaining(final_tenant or "default")
        return {
            "success": False,
            "error": f"Rate limit exceeded (remaining: {remaining})",
            "status_code": 429,
            "tenant_id": final_tenant,
        }

    try:
        # Create base snapshot from when file was originally read
        base_snap = snapshot_file(file_path, agent_id, base_snapshot_time)

        if base_snap.parse_error:
            return {
                "success": False,
                "error": f"Couldn't parse file at snapshot time: {base_snap.parse_error}",
                "status_code": 400,
                "tenant_id": final_tenant,
            }

        # Generate delta from base to current
        delta = DeltaGenerator.generate(
            base_snap,
            file_path,
            dependency_symbols=dependency_symbols
        )

        # Build human-readable message
        message = ContextRefreshBuilder.build_message([delta], agent_id, file_path)

        # Estimate token cost
        tokens = ContextRefreshBuilder.estimate_tokens(delta)

        return {
            "success": True,
            "delta_type": delta.delta_type,  # symbols / unified_diff / full_file
            "message": message,
            "token_estimate": tokens,
            "added_symbols": delta.added_symbols or [],
            "removed_symbols": delta.removed_symbols or [],
            "changed_symbols": delta.changed_symbols or [],
            "delta": delta.to_dict(),
            "tenant_id": final_tenant,
        }
    except Exception as e:
        logger.warning(f"Context refresh failed: {e}")
        return {
            "success": False,
            "error": f"Context refresh failed: {str(e)}",
            "status_code": 500,
            "tenant_id": final_tenant,
        }


@mcp.tool(name="neo_get_status")
def neo_get_status() -> Dict[str, Any]:
    """Check Neo MCP server status."""
    return {
        "success": True,
        "status": "ok",
        "multitenancy_enabled": MULTITENANCY,
        "tenant_id": TENANT_ID,
        "version": "1.0",
        "features": ["conflict_detection", "activity_logging", "c1_staleness", "c2_delta_refresh"],
    }


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
```

### Critical Implementation Notes

**Lines 123-129 (neo_check_conflicts):**
```python
risk_level, message, lock_info = check_for_conflicts(
    agent_id=agent_id,
    file_path=file_path,
    intent=intent,
    region=region,
    tenant_id=final_tenant,
)
```
**MUST unpack 3 values**, not 2. The `lock_info` is required.

**Lines 188-196 (neo_log_activity):**
```python
entry = ActivityEntry(
    developer_id=agent_id,
    file_path=file_path,
    intent=intent,
    region=region,
    timestamp=time.time(),           # REQUIRED - Unix timestamp
    tenant_id=final_tenant,           # REQUIRED - for multitenancy
    intent_category=intent_category,  # Optional but recommended
)
```
**MUST include `timestamp=time.time()`** and `tenant_id=final_tenant` when creating ActivityEntry.

### Verification

To verify your file matches this reference:

```bash
# Check line 123 unpacks 3 values
grep -A 6 "risk_level, message, lock_info = check_for_conflicts" ide/mcp_neo_server.py

# Check line 188+ has timestamp
grep -A 8 "entry = ActivityEntry(" ide/mcp_neo_server.py | grep "timestamp=time.time()"

# Check all tools are defined
grep -c "@mcp.tool" ide/mcp_neo_server.py  # Should output: 6
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

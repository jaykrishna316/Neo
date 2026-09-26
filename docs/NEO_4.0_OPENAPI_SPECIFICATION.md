# Neo 4.0 OpenAPI Specification

**Version:** 4.0  
**Status:** Production Ready  
**Date:** 2026-09-26

Semantic Multi-Developer Coordination Engine

---

## Table of Contents

1. [Overview](#overview)
2. [MCP Setup for Claude Code IDE](#mcp-setup-for-claude-code-ide)
3. [MCP Tools (Endpoints)](#mcp-tools-endpoints)
4. [State Machine](#state-machine)
5. [Data Schemas](#data-schemas)
6. [Workflow Examples](#workflow-examples)
7. [Additional Resources](#additional-resources)

---

## Overview

Neo is a semantic coordination engine that eliminates Git merge conflicts by moving conflict resolution one layer below Git through intelligent semantic coordination and automatic conflict prevention.

### Key Features

- **Explicit Lock Mechanism:** Developer-aware locks with queue management and auto-promotion
- **Real-time Conflict Detection:** Semantic analysis before code generation
- **Activity Logging:** File-based coordination log at `.devsync/activity-log.json`
- **Risk Classification:** LOW/MEDIUM/HIGH risk assessment with actionable feedback
- **Multitenancy Support:** Team-isolated activity logs and conflict checking
- **MCP Integration:** Native Claude Code IDE integration via Model Context Protocol

### Architecture

```
Claude Code IDE
    ↓ (before generation)
Neo MCP Server (ide.mcp_neo_server)
    ↓
Core Neo Logic (check_for_conflicts)
    ↓
Activity Log (.devsync/activity-log.json)
    ↓
Risk Classifier + Lock Manager
    ↓
IDE Response (✅/⚠️/🚫)
```

---

## MCP Setup for Claude Code IDE

### Configuration

Add the following to your Claude Code configuration:

```json
{
  "neo-conflict-detection": {
    "command": "/absolute/path/to/Neo/.venv/bin/python3",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "PYTHONPATH": "/absolute/path/to/Neo",
      "NEO_MULTITENANCY": "false",
      "CLAUDE_TENANT_ID": "default"
    }
  }
}
```

### Environment Variables

| Variable | Value | Description |
|----------|-------|-------------|
| `PYTHONPATH` | `/path/to/Neo` | Path to Neo project root |
| `NEO_MULTITENANCY` | `true` or `false` | Enable team isolation (default: false) |
| `CLAUDE_TENANT_ID` | `your-team-name` | Team identifier (only if multitenancy=true) |

### Verification

Test the MCP connection with:

```bash
PYTHONPATH=. .venv/bin/python3 -c "
import asyncio
from mcp.client.stdio import stdio_client

async def main():
    params = StdioServerParameters(
        command='.venv/bin/python3',
        args=['-m', 'ide.mcp_neo_server'],
        env={'PYTHONPATH': '.', 'NEO_MULTITENANCY': 'false'},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            tools = await session.list_tools()
            print(f'Available tools: {len(tools)}')

asyncio.run(main())
"
```

---

## MCP Tools (Endpoints)

### neo_check_conflicts

Check for conflicts before code generation.

**Parameters:**
- `agent_id` (string, required): Unique identifier for the calling agent/developer
- `file_path` (string, required): Path to the file being modified
- `intent` (string, required): Description of what the agent intends to do
- `region` (string, optional): Specific region (lines/function name) being modified

**Response:**
- `success` (boolean): Operation succeeded
- `risk_level` (string): `LOW` | `MEDIUM` | `HIGH`
- `message` (string): Human-readable risk assessment
- `should_block` (boolean): Whether IDE should block generation (HIGH risk)
- `should_warn` (boolean): Whether IDE should warn user (MEDIUM risk)
- `lock_info` (object): Explicit lock state (when conflict detected)
- `tenant_id` (string): Team identifier (if multitenancy enabled)

### neo_log_activity

Log developer intent to work on a file.

**Parameters:**
- `agent_id` (string, required): Unique identifier for the calling agent/developer
- `file_path` (string, required): Path to the file being modified
- `intent` (string, required): Description of the work to be done
- `region` (string, optional): Specific region (lines/function) being modified
- `intent_category` (string, optional): Category: feature, bugfix, refactor, or other

**Response:**
- `success` (boolean): Activity logged successfully
- `tenant_id` (string): Team identifier (if multitenancy enabled)

### neo_get_active_work

View all currently active developers and their work.

**Parameters:** None required

**Response:**
- `success` (boolean): Query succeeded
- `active_entries` (array): List of active work entries
- `count` (integer): Number of active entries
- `tenant_id` (string): Team identifier (if multitenancy enabled)

### neo_get_status

Check Neo server status and configuration.

**Parameters:** None required

**Response:**
- `success` (boolean): Server is operational
- `status` (string): Server status (ok, degraded, down)
- `version` (string): Neo version (4.0)
- `multitenancy_enabled` (boolean): Team isolation enabled
- `tenant_id` (string): Current team identifier

---

## State Machine

Neo implements a complete state machine to coordinate multi-developer work and manage lock lifecycle. The state machine transitions based on developer actions, conflict detection, and lock status.

### States Overview

| State | Description | Triggered When | Lock Status |
|-------|-------------|-----------------|------------|
| `INITIAL` | No developers active, log is empty | System startup or all developers complete | None |
| `SINGLE_DEV` | One developer working on a file (LOW risk) | First developer declares intent on a file | No lock applied (only 1 dev) |
| `MULTI_DEV_SAME_FILE` | Multiple developers on same file (MEDIUM/HIGH risk) | Second developer declares intent on same file as first | Lock applies automatically |
| `MULTI_DEV_SMART_DETECTION` | Intent-based conflict analysis (different functions/regions) | Developers work on different regions but same file | MEDIUM risk lock (semantic analysis) |
| `DEV_COMPLETES_WORK` | Developer finishes and publishes changes | Developer marks work as completed in activity log | Lock released, next dev queued gets promoted |
| `DEV_GETS_FRESH_CONTEXT` | Next developer sees completed work in log | Developer checks conflicts after previous dev completes | Lock acquired for this developer |
| `MULTI_DEV_DIFFERENT_FILES` | Multiple developers on different files (LOW risk) | Developer works on different file than others | No lock (file-level isolation) |
| `STRESS_TEST` | 4+ developers on same file (HIGH risk) | Third or more developer declares on same file | Lock maintains queue, auto-promotion |
| `REGION_SPECIFIC_CHECK` | Function-level conflict detection | Developer specifies region (lines/function name) | Region-scoped lock applied |
| `ALL_DEVELOPERS_COMPLETE` | All developers finished, ready to merge | Last developer completes and publishes | All locks released → back to INITIAL |

### State Transition Diagram

```
    ┌─────────────┐
    │   INITIAL   │  (No developers active)
    │  (State 0)  │
    └──────┬──────┘
           │
           ▼
    ┌──────────────────────┐
    │ SINGLE_DEV (LOW RISK)│  Developer A declares intent
    │     (State 1)        │  → Check conflicts: LOW
    │  risk_level: LOW     │  → No lock applied
    └──────┬───────────────┘
           │
           ▼
    ┌───────────────────────────┐
    │ MULTI_DEV_SAME_FILE       │  Developer B declares on same file
    │  (State 2)                │  → Check conflicts: MEDIUM/HIGH
    │ risk_level: MEDIUM/HIGH   │  → Lock applied (sequential access)
    └──────┬────────────────────┘
           │
           ├─ (If different regions)
           │  ▼
           │ MULTI_DEV_SMART_DETECTION (State 2b)
           │  → Intent-based analysis (OAuth2 vs JWT)
           │  → Still MEDIUM (2 devs on same file)
           │
           ▼
    ┌──────────────────────────────┐
    │ DEV_A_COMPLETES_WORK         │  Developer A finishes & publishes
    │  (State 3)                   │  → Add metadata to activity log
    │  Next: Context refresh       │  → Lines added/removed recorded
    └──────┬───────────────────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │ DEV_B_GETS_FRESH_CONTEXT     │  Developer B checks conflicts again
    │  (State 4)                   │  → Sees Dev A's changes in log
    │  Risk updated: now can see   │  → Context includes A's completion
    │  A's changes                 │  → Ready to proceed safely
    └──────┬───────────────────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │ MULTI_DEV_DIFFERENT_FILES    │  Developer C on different file
    │  (State 6)                   │  → Check conflicts: LOW
    │  risk_level: LOW             │  → No lock (different file)
    │  no_lock: file_isolation     │  → Works in parallel
    └──────┬───────────────────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │ STRESS_TEST (N_DEVS)         │  4+ developers on same file
    │  (State 7)                   │  → Each new dev: risk increases
    │  risk_level: HIGH            │  → Lock applies/maintains
    │  all_tracked: true           │  → Sequential queuing
    └──────┬───────────────────────┘
           │
           ▼
    ┌──────────────────────────────┐
    │ ALL_DEVELOPERS_COMPLETE      │  All devs finish → back to initial
    │  (State 9 → 0)               │  → Log persisted for audit
    │  ready_for_merge: true       │  → No conflicts detected
    └──────────────────────────────┘
```

### Lock Behavior by State

- **INITIAL:** No locks
- **SINGLE_DEV:** No locks (only 1 developer)
- **MULTI_DEV_SAME_FILE:** Lock applies automatically (prevents simultaneous writes)
- **MULTI_DEV_SMART_DETECTION:** MEDIUM risk lock on overlapping regions
- **DEV_A_COMPLETES_WORK:** Lock released, next developer auto-promoted
- **DEV_B_GETS_FRESH_CONTEXT:** New lock acquired for Developer B
- **MULTI_DEV_DIFFERENT_FILES:** No locks (file isolation)
- **STRESS_TEST:** Lock maintains queue: [bob (next), charlie (2nd), diana (3rd)] → Auto-promotion on each release
- **ALL_DEVELOPERS_COMPLETE:** All locks released

### Risk Levels by State

| State | Risk Level | Rationale |
|-------|-----------|-----------|
| INITIAL, SINGLE_DEV, MULTI_DEV_DIFFERENT_FILES | LOW | Single developer or different files → safe to proceed |
| MULTI_DEV_SMART_DETECTION | MEDIUM | 2 developers, same file, potentially overlapping regions |
| MULTI_DEV_SAME_FILE, STRESS_TEST | HIGH | 3+ developers or same-file work → sequential execution required |

### Transitions Triggered by Events

#### INITIAL → SINGLE_DEV
- **Event:** Developer A declares intent via `neo_log_activity()`
- **Condition:** No other developers active on any file
- **Action:** Create activity log entry, set state to ACTIVE
- **Result:** Developer can proceed (LOW risk, no lock)

#### SINGLE_DEV → MULTI_DEV_SAME_FILE
- **Event:** Developer B declares intent on same file as Developer A
- **Condition:** Developer B calls `check_for_conflicts()` with Developer A active on same file
- **Action:** `LockManager.acquire_lock()` called, lock created with Developer A as holder
- **Result:** Developer B queued (queue_position=0), lock_state=WAITING

#### MULTI_DEV_SAME_FILE → DEV_A_COMPLETES_WORK
- **Event:** Developer A finishes and publishes changes
- **Condition:** activity log marked with status='completed', metadata added
- **Action:** `LockManager.release_lock()` called, Developer B auto-promoted
- **Result:** Lock state transitions: ACQUIRED (A) → RELEASED, WAITING (B) → ACQUIRED

#### MULTI_DEV_SAME_FILE → MULTI_DEV_DIFFERENT_FILES
- **Event:** Developer C declares intent on different file
- **Condition:** C's file_path differs from A's and B's file
- **Action:** No lock created (file isolation)
- **Result:** Developer C proceeds in parallel (LOW risk)

#### MULTI_DEV_SAME_FILE → STRESS_TEST
- **Event:** Third (Charlie) and fourth+ developers declare on same file
- **Condition:** 3+ developers active on same file
- **Action:** Lock maintains queue, queue_position increments
- **Result:** Queue: [bob (0), charlie (1), diana (2)], each waits for previous

### Context Refresh Mechanics

When a developer transitions from WAITING to ACQUIRED state, they receive fresh context containing:

- **Completed work metadata:** Lines added/removed by previous developer
- **Change summary:** What changed and where
- **Timestamp:** When previous developer completed
- **Built on reference:** Dependency chain (e.g., "built_on": "alice")

This ensures each developer can see and integrate previous changes before beginning their work.

---

## Data Schemas

### Activity Entry

```json
{
  "developer_id": "alice",
  "file_path": "src/auth.py",
  "intent": "Add OAuth2 authentication",
  "region": "authenticate_user (lines 45-80)",
  "timestamp": 1695164017.5,
  "intent_category": "feature",
  
  "lock_state": "ACQUIRED",
  "lock_holder": "alice",
  "lock_acquired_at": 1695164017.5,
  "lock_expires_at": 1695165817.5,
  "lock_timeout_seconds": 1800,
  "lock_reason": "MEDIUM_CONFLICT",
  "lock_scope": "region",
  "queue_position": null,
  "waiting_for": null
}
```

### Lock Info (Returned by check_for_conflicts)

```json
{
  "success": false,
  "lock_holder": "alice",
  "lock_state": "ACQUIRED",
  "lock_acquired_at": 1695164017.5,
  "lock_expires_at": 1695165817.5,
  "queue_position": 0,
  "waiting_for": "alice",
  "queue_list": ["bob", "charlie"]
}
```

### Risk Levels

| Level | Value | Description | IDE Action |
|-------|-------|-------------|-----------|
| LOW | `LOW` | No conflicting work detected | ✅ Allow generation |
| MEDIUM | `MEDIUM` | Overlapping regions detected, lock applied | ⚠️ Warn user, queue developer |
| HIGH | `HIGH` | Same-file work by multiple developers | 🚫 Block generation |

### Lock States

| State | Description |
|-------|-------------|
| `ACQUIRED` | Developer holds the lock and can proceed |
| `WAITING` | Developer is queued, waiting for lock holder to finish |
| `RELEASED` | Lock has been released, next developer auto-promoted |

---

## Workflow Examples

### Example 1: Single Developer (No Lock)

```
1. Alice calls neo_check_conflicts(agent_id='alice', file_path='auth.py', ...)
   ↓ Response: risk_level=LOW, message="No conflicting work detected"
   ✅ Alice proceeds with generation

2. Alice calls neo_log_activity(agent_id='alice', file_path='auth.py', ...)
```

### Example 2: Two Developers (Lock Applied)

```
1. Alice calls neo_log_activity(agent_id='alice', file_path='auth.py', intent='...')
   ↓ No lock (only 1 dev on this file)

2. Bob calls neo_check_conflicts(agent_id='bob', file_path='auth.py', ...)
   ↓ Response: risk_level=MEDIUM, should_warn=true
   ↓ lock_info: {lock_holder='alice', queue_position=0}
   ⚠️ Bob is queued, must wait for Alice

3. Alice completes work
   ↓ LockManager.release_lock() called
   ↓ Bob auto-promoted from WAITING to ACQUIRED

4. Bob calls neo_check_conflicts again
   ↓ Response: risk_level=LOW (Alice's lock released)
   ✅ Bob proceeds with generation
```

### Example 3: Three Developers (Queue Management)

```
1. Alice declares intent on auth.py → NO lock (1 dev)
2. Bob declares intent on auth.py → LOCK APPLIES (2 devs), queue_position=0
3. Charlie declares intent on auth.py → Queued, queue_position=1

Queue: [bob (next), charlie (2nd)]

4. Alice completes → Bob auto-promoted to ACQUIRED
5. Bob completes → Charlie auto-promoted to ACQUIRED

Result: Sequential execution with 0 conflicts
```

### API Call Examples

```bash
# Check for conflicts before generation
{
  "tool": "neo_check_conflicts",
  "arguments": {
    "agent_id": "claude-code-dev1",
    "file_path": "src/api/auth.py",
    "intent": "Add OAUTH2 token refresh endpoint",
    "region": "refresh_token() function"
  }
}

# Response (LOW risk)
{
  "success": true,
  "risk_level": "LOW",
  "message": "No conflicting work detected. Safe to proceed.",
  "should_block": false,
  "should_warn": false,
  "lock_info": null,
  "tenant_id": "default"
}

# Response (MEDIUM risk)
{
  "success": true,
  "risk_level": "MEDIUM",
  "message": "Developer 'bob' is working on overlapping regions",
  "should_block": false,
  "should_warn": true,
  "lock_info": {
    "lock_holder": "bob",
    "queue_position": 0,
    "waiting_for": "bob"
  },
  "tenant_id": "default"
}
```

---

## Additional Resources

- **Activity Log:** `.devsync/activity-log.json` — File-based coordination log
- **Core Implementation:** `core/mcp_server.py`, `ide/mcp_neo_server.py`
- **Conflict Detection:** `core/pre_gen_check.py`
- **Lock Management:** `core/lock_manager.py`
- **Risk Classification:** `core/risk_classifier.py`
- **State Machine:** `core/coordination_machine.py`

### Support

For issues or questions about Neo 4.0, refer to:
- `README.md` - Neo overview and usage
- `CLAUDE.md` - Project instructions and MCP setup
- `docs/` - Additional documentation

---

**Last Updated:** 2026-09-26  
**Neo Version:** 4.0  
**Status:** Production Ready

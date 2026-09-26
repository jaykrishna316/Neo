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

| State | Description | Triggered When | Transitions To |
|-------|-------------|-----------------|-----------------|
| `ACTIVE` | Developer is actively working and generating code | Developer logs intent via `neo_log_activity()` | LOCKED (if conflict), COMPLETED (when done) |
| `LOCKED` | High-risk conflict detected, developer blocked | Another developer on same file with HIGH risk conflict | WAITING (developer pauses), COLLABORATE (if agreed) |
| `WAITING` | Developer paused, sleeping, checkpoint saved | Developer chooses WAIT option when locked | RESUMED (when lock released and event fires) |
| `COLLABORATE` | Developers reached out to collaborate together | Developer chooses COLLABORATE option instead of waiting | COORDINATED (when collaboration completes) |
| `COMPLETED` | Developer finished work, changes published | Developer marks work complete in activity log | LOCK_REMOVED (next dev in queue promoted) |
| `LOCK_REMOVED` | Event fired: lock cleared, next developer ready to wake | Previous developer released lock | RESUMED (next developer in queue wakes up) |
| `RESUMED` | Developer woke from WAITING, resuming from checkpoint | Lock released and developer subscribed to event | ACTIVE (resume generation) |
| `COORDINATED` | Collaboration resulted in joint coordination | Multiple developers agreed on shared approach | COMPLETED (after joint work) |

### State Transition Diagram

```
                    ┌──────────────────────────────────────────┐
                    │  DEVELOPER DECLARES INTENT               │
                    │  neo_log_activity()                      │
                    └───────────────────┬──────────────────────┘
                                        │
                                        ▼
                    ┌──────────────────────────────────┐
                    │         ACTIVE                   │
                    │  Developer generating code       │
                    │  (LOW risk, no conflict)         │
                    └────────┬────────────────┬────────┘
                             │                │
                    (conflict detected)  (work complete)
                             │                │
                    ┌────────▼─────┐     ┌────▼─────────┐
                    │   LOCKED     │     │  COMPLETED   │
                    │ HIGH risk    │     │  Published   │
                    │ conflict     │     │  changes     │
                    └─┬──────────┬─┘     └────┬─────────┘
                      │          │            │
            ┌─────────┘          └────┐       │
            │ (Developer chooses)     │       │
            │                         │       │
            ▼                         ▼       ▼
    ┌────────────────┐    ┌────────────────────────┐
    │   WAITING      │    │ LOCK_REMOVED           │
    │ Paused, sleeping│   │ Event: Next dev ready  │
    │ Checkpoint     │    │ Lock cleared           │
    │ saved          │    └────┬───────────────────┘
    └────┬───────────┘         │
         │                      │ (wake up notification)
         │            ┌─────────▼─────────┐
         │            │    RESUMED        │
         │            │ Woke from WAITING │
         │            │ Restoring from    │
         └────────────┤ checkpoint        │
                      └────────┬──────────┘
                               │
                               ▼
                        ┌──────────────┐
                        │   ACTIVE     │
                        │ Resume code  │
                        │ generation   │
                        └──────┬───────┘
                               │
                        (work complete)
                               │
                               ▼
                        ┌──────────────┐
                        │ COMPLETED    │
                        │ Changes ok   │
                        └──────────────┘


    ALTERNATIVE PATH (Collaboration):
    
         ┌─────────────────────────────────┐
         │ COLLABORATE                     │
         │ Developers agreed to work       │
         │ together on the same file       │
         └─────────────┬───────────────────┘
                       │
                       ▼
         ┌─────────────────────────────────┐
         │ COORDINATED                     │
         │ Joint work result obtained      │
         │ Collaboration complete          │
         └─────────────┬───────────────────┘
                       │
                       ▼
         ┌─────────────────────────────────┐
         │ COMPLETED                       │
         │ Both devs finished, changes ok  │
         └─────────────────────────────────┘
```

### Lock Behavior by State

- **ACTIVE:** No lock if first developer on file (LOW risk). Lock held if developer acquired it on queue.
- **LOCKED:** Lock acquired by current developer prevents this developer from proceeding. Risk level: HIGH.
- **WAITING:** Developer queued with saved checkpoint. Lock held by previous developer. Queue position tracked.
- **COLLABORATE:** Lock suspended for duration of collaboration. Both developers can work together.
- **COMPLETED:** Lock released automatically. If queue exists, next developer promoted to RESUMED.
- **LOCK_REMOVED:** Event fired. Signals next waiting developer to wake up.
- **RESUMED:** Developer wakes from checkpoint. Lock acquired for this developer.
- **COORDINATED:** Collaboration lock released. Returns to normal queue if other developers waiting.

### Risk Levels by State

| State | Risk Level | Rationale |
|-------|-----------|-----------|
| ACTIVE (first dev) | LOW | Single developer on file → safe to proceed, no lock |
| ACTIVE (queued dev) | MEDIUM/HIGH | Developer has acquired lock from queue → can generate once lock held |
| LOCKED | HIGH | Conflict detected, current developer blocked from generating |
| WAITING | HIGH | Developer paused, must wait for lock holder to complete |
| COMPLETED | LOW | Work finished, lock released, ready for next developer |
| RESUMED | MEDIUM | Resuming from checkpoint, lock just acquired, ready to continue |
| COLLABORATE | MEDIUM | Joint work in progress, lock suspended for both developers |
| COORDINATED | LOW | Collaboration complete, ready to release locks |

### Transitions Triggered by Events

#### ACTIVE → LOCKED
- **Event:** `check_for_conflicts()` detects HIGH risk conflict
- **Condition:** Another developer already on same file with overlapping intent (HIGH risk)
- **Action:** State marked as LOCKED, decision options provided to developer
- **Result:** Developer must choose: WAIT (save checkpoint) or COLLABORATE

#### ACTIVE → COMPLETED
- **Event:** Developer marks work complete via `neo_log_activity(status='completed')`
- **Condition:** Developer finished generating code
- **Action:** Update activity log, fire LOCK_REMOVED event, promote next queued developer
- **Result:** Lock released, any waiting developers notified

#### LOCKED → WAITING
- **Event:** Developer chooses WAIT option
- **Condition:** Developer prefers to pause rather than collaborate
- **Action:** Save generation checkpoint, set state to WAITING, subscribe to lock_removed event
- **Result:** Developer sleeps, checkpoint persisted, awaits wake-up signal

#### LOCKED → COLLABORATE
- **Event:** Developer chooses COLLABORATE option
- **Condition:** Developer prefers joint work over waiting alone
- **Action:** Notify both developers, set state to COLLABORATE, establish shared context
- **Result:** Both developers coordinate and work together on same file

#### WAITING → RESUMED
- **Event:** Lock holder completes work (fires LOCK_REMOVED event)
- **Condition:** Waiting developer subscribed to event and receives notification
- **Action:** Restore generation checkpoint, set state to RESUMED, acquire lock for this developer
- **Result:** Developer wakes up, resumes from exact checkpoint, can continue generation

#### RESUMED → ACTIVE
- **Event:** Developer continues generating from checkpoint
- **Condition:** Checkpoint restored, lock acquired, ready to proceed
- **Action:** Resume code generation from saved context
- **Result:** Developer can now generate code (lock held exclusively for them)

#### COLLABORATE → COORDINATED
- **Event:** Both developers reach agreement on shared approach
- **Condition:** Collaboration discussion complete
- **Action:** Merge changes, update shared state, set state to COORDINATED
- **Result:** Ready to complete work without conflict

#### COORDINATED → COMPLETED
- **Event:** Joint work finishes
- **Condition:** Both developers publish coordinated changes
- **Action:** Release locks, fire LOCK_REMOVED event
- **Result:** Lock released, next waiting developer promoted

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

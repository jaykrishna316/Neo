# Neo Collaborative Workflow System

**Complete end-to-end collaborative development system with lock-based conflict prevention, activity logging, auto-approver assignment, and support for both AI agents and human developers.**

## Quick Start (2 Steps)

```bash
# Terminal 1: Start the Activity Log Server
python3 .claude/activity_log_server.py

# Terminal 2: Run any test
python3 .claude/test_complete_end_to_end.py
```

## What This Does

Dev1 and Dev2 work on the same file sequentially:
- Dev1 acquires exclusive lock → edits → creates PR
- Dev2 is notified and can review
- Dev2 gets auto-approver role automatically
- PR merges with both as required approvers

**Result: No merge conflicts, complete audit trail, automated approvals.**

## Test Scripts (Pick One)

### 1. Lock Mechanism Demo (5 min)
```bash
python3 .claude/test_actual_file_editing.py
```
Shows:
- Dev1 acquires lock ✓
- Dev2 tries to edit → BLOCKED ✓
- Dev2 receives notification ✓
- Dev1 releases lock → Dev2 acquires ✓

### 2. Complete End-to-End Workflow (7 min)
```bash
python3 .claude/test_complete_end_to_end.py
```
Shows:
- Dev1 edits → creates PR #42
- Dev2 reviews → merges Dev1's changes
- Dev2 edits → creates PR #43
- Auto-approvers assigned: [dev1, dev2]
- Both approve and PR merges to main

### 3. Agent vs Human Workflows (5 min)
```bash
python3 .claude/test_agent_vs_human.py
```
Shows:
- Agent (Claude): Auto-pulls, auto-reviews, auto-merges, continues editing
- Human: Gets interactive options (pull/ignore/review)
- Mixed team: Agents and humans working together

## How It Works

### The Lock Mechanism

```
Before any coding:         Must call /api/start_editing
    ↓
Only one dev at a time:   Lock is exclusive per file:function
    ↓
Others are queued:        Other devs get "BLOCKED" response
    ↓
Dev finishes:             Calls /api/finish_editing → lock released
    ↓
Next in queue notified:   Automatically woken up via notifications
    ↓
Result:                   ZERO merge conflicts
```

### The Activity Log

Every action is recorded:
```
- Who started editing?
- When did they start?
- What changes did they make?
- When did they finish?
- Who reviewed the PR?
- Who approved?
- When was it merged?
```

This creates a **complete audit trail** for compliance, debugging, and understanding.

### Agent vs Human

**Agents (Claude):**
```
PR notification
    ↓
Auto-pull dev1's changes
    ↓
Auto-review (no delay)
    ↓
Auto-merge if good
    ↓
Acquire lock immediately
    ↓
Continue editing
```

**Humans:**
```
PR notification
    ↓
See options:
  [1] Pull and review
  [2] Ignore and skip
  [3] See detailed diff
    ↓
Make choice
    ↓
Acquire lock based on choice
    ↓
Continue editing or request changes
```

## API Endpoints

### Start/Stop Editing
```bash
# Acquire lock
POST /api/start_editing
{
  "developer": "dev1",
  "file_path": "test2devs.py",
  "function_name": "process_data"
}

# Release lock
POST /api/finish_editing
{
  "developer": "dev1",
  "file_path": "test2devs.py",
  "function_name": "process_data",
  "branch": "feature/dev1-changes",
  "pr_link": "https://github.com/..."
}
```

### PR Management
```bash
# Create PR and record in activity log
POST /api/create_pr
{
  "developer": "dev1",
  "file_path": "test2devs.py",
  "function_name": "process_data",
  "pr_number": 42,
  "pr_link": "https://github.com/...",
  "branch": "feature/dev1-changes"
}

# Get options (agent or human)
GET /api/review_options?developer=dev2&file_path=test2devs.py&function_name=process_data

# Agent auto-processes
POST /api/agent_auto_process
{
  "developer": "claude_agent",
  "file_path": "test2devs.py",
  "function_name": "process_data"
}

# Human chooses action
POST /api/complete_review
{
  "developer": "dev2",
  "file_path": "test2devs.py",
  "function_name": "process_data",
  "action": "merge"  # or "discard"
}

# Merge to main (auto-approvers assigned)
POST /api/merge_to_main
{
  "developer": "dev2",
  "file_path": "test2devs.py",
  "function_name": "process_data",
  "pr_number": 43,
  "merge_commit_sha": "abc123"
}
```

### Notifications
```bash
# Subscribe to notifications
POST /api/subscribe
{
  "developer": "dev2",
  "channel": "polling",
  "endpoint": ""
}

# Poll for new notifications
GET /api/notifications?developer=dev2

# Get workflow state
GET /api/workflow/state?file_path=test2devs.py&function_name=process_data
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Activity Log Server                  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │         Lock Management (Per File:Function)       │  │
│  │  - Only one dev editing at a time               │  │
│  │  - Others queued and notified                   │  │
│  │  - Automatic lock release                       │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │      Workflow State Machine (9 States)           │  │
│  │  AVAILABLE → EDITING → CONFLICT_WAITING →        │  │
│  │  PENDING_REVIEW → BOTH_DONE → IN_PR → APPROVED   │  │
│  │  → MERGED                                        │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │    Multi-Channel Notifications                   │  │
│  │  - Webhook                                       │  │
│  │  - Email                                         │  │
│  │  - Slack                                         │  │
│  │  - Polling (IDE integration)                     │  │
│  └──────────────────────────────────────────────────┘  │
│                                                         │
│  ┌──────────────────────────────────────────────────┐  │
│  │    Activity Log (Persistent JSON Storage)        │  │
│  │  - All state transitions                         │  │
│  │  - All code changes                              │  │
│  │  - All approvals                                 │  │
│  │  - Complete audit trail                          │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
        ↑                                   ↓
        │                                   │
    Dev IDE                          GitHub / Main
    (start_editing)                  (auto-approvers)
    (finish_editing)                 (auto-merge)
    (notifications)                  (PR tracking)
```

## Files

### Core System
- `.claude/activity_log_server.py` - REST API server (900+ lines)
- `.claude/workflow_state_machine.py` - State machine (9 states)
- `.claude/notification_manager.py` - Multi-channel notifications
- `.claude/activity_log_client.py` - Client library

### Tests
- `.claude/test_actual_file_editing.py` - Lock mechanism
- `.claude/test_complete_end_to_end.py` - Full workflow
- `.claude/test_agent_vs_human.py` - Agent vs human
- `test2devs.py` - Shared test file

### Documentation
- `.claude/SYSTEM_SUMMARY.md` - Complete overview
- `.claude/COMPLETE_WORKFLOW_GUIDE.md` - 700+ line guide
- `.claude/AGENT_VS_HUMAN_GUIDE.md` - Agent vs human workflows
- `.claude/TEST_WITH_CLAUDE.md` - Testing guide
- `.claude/README.md` - This file

## Key Features

✅ **Lock-Based Conflict Prevention**
- No merge conflicts possible
- Serialized editing enforced

✅ **Complete Activity Log**
- Every action recorded
- Full audit trail
- State history preserved

✅ **Multi-Channel Notifications**
- Webhook, Email, Slack, Polling
- IDE integration via polling
- Real-time awareness

✅ **State Machine Validation**
- 9-state lifecycle
- Invalid transitions prevented
- State history maintained

✅ **Agent + Human Support**
- Agents auto-process
- Humans get interactive options
- Mixed teams supported

✅ **Auto-Approver Assignment**
- Automatically detected contributors
- All become required approvers
- No manual configuration

## Deployment

### Local Testing
```bash
python3 .claude/activity_log_server.py
# Runs on http://localhost:5000
```

### Production Deployment
```bash
# Expose via ngrok (temporary)
ngrok http 5000

# Or deploy server to:
# - AWS Lambda + API Gateway
# - Heroku
# - Azure Functions
# - Docker container

# Then distribute VS Code extension and register developers
```

## Next Steps

1. **Run the tests** to see the system in action
2. **Read the guides** for detailed understanding
3. **Deploy to production** when ready
4. **Register developers** (agent/human type)
5. **Scale to your team**

## Architecture Benefits

| Aspect | Before | After |
|--------|--------|-------|
| Merge Conflicts | Frequent | Zero (impossible) |
| Approver Assignment | Manual | Automatic |
| Audit Trail | Scattered | Complete |
| Agent Integration | N/A | First-class |
| Lock Conflicts | Manual resolution | Automatic queue |
| Developer Coordination | Async/error-prone | Automatic notifications |

## Support

For detailed information, see:
- **Getting Started**: `TEST_WITH_CLAUDE.md`
- **Architecture**: `SYSTEM_SUMMARY.md`
- **Workflows**: `COMPLETE_WORKFLOW_GUIDE.md`
- **Agent vs Human**: `AGENT_VS_HUMAN_GUIDE.md`

---

**Neo: Collaborative development, simplified.**

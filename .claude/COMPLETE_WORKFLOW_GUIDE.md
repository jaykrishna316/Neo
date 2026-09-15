# Complete Neo Collaborative Development Workflow

**All 5 Phases: Notification System → State Machine → IDE Integration**

---

## Overview

This is a complete workflow coordination system that ensures developers working on the same code:

1. **Know about each other** (notifications)
2. **Can't work at the same time** (state machine prevents conflicts)
3. **Get woken up when it's their turn** (notifications)
4. **Auto-pull each other's changes** (IDE integration)
5. **Both get added as approvers** (Git Bridge integration)

---

## Architecture

```
Dev 1 (IDE)          Activity Log Server          Dev 2 (IDE)
    ↓                      ↓                           ↓
  start_editing() ──→ Acquire Lock ──→ Notify Dev2 (BLOCKED)
     ↓                      ↓                           ↓
  Editing Code              ↓                      Waiting...
     ↓                      ↓                           ↓
  finish_editing() ─→ Release Lock ────→ Notify Dev2 (WOKEN UP)
     ↓                      ↓                           ↓
  Commit & Push             ↓                    Auto-Pull Dev1's
     ↓                      ↓                           ↓
  Create PR                 ↓                    Review Dev1
     ↓                      ↓                           ↓
  Auto-add reviewers ──→ Both must approve
     ↓                      ↓
  Merge to main             ↓
     ↓                      ↓
  Activity log complete     ✓
```

---

## Quick Start (Complete)

### Prerequisites

```bash
# Install server dependencies
pip install flask requests

# VS Code extension
# - Create directory: ~/.vscode/extensions/neo-activity-monitor/
# - Copy package.json and extension.js there
# - Run: npm install in that directory
```

### Setup

**Terminal 1: Start Activity Log Server**
```bash
cd /path/to/Neo
python3 .claude/activity_log_server.py
```

**Terminal 2: Expose to Internet**
```bash
ngrok http 5000
# Output: https://abc123.ngrok.io
export ACTIVITY_LOG_SERVER="https://abc123.ngrok.io"
```

**VS Code: Configure Neo Extension**

Settings → Extensions → Neo Activity Monitor
```json
{
  "neo.serverUrl": "https://abc123.ngrok.io",
  "neo.developer": "dev1"
}
```

**Or set environment variable:**
```bash
export ACTIVITY_LOG_SERVER="https://abc123.ngrok.io"
export NEO_DEVELOPER="dev1"
```

---

## Phase 3: Notification System

### How It Works

Developers subscribe to notifications. When state changes, they're notified via:
- **Webhook**: HTTP callback to your server
- **Email**: Direct email notification
- **Slack**: Slack webhook
- **Polling**: Developer polls for updates (built into IDE)

### Subscribe to Notifications

```bash
curl -X POST http://localhost:5000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "developer": "dev1",
    "channel": "webhook",
    "endpoint": "https://your-server.com/notify",
    "notify_on": ["lock_blocked", "lock_released", "review_requested"]
  }'
```

### Notification Types

| Type | When | Data |
|------|------|------|
| `lock_acquired` | Dev starts editing | developer, file, function |
| `lock_blocked` | Another dev tries to edit | blocking_dev, queue_position |
| `lock_released` | Dev finishes & releases | developer, file, function |
| `review_requested` | Time for next dev | from_dev, branch, pr_link |
| `approval_needed` | PR created | pr_number, developers |
| `approved` | Dev approved | developer, file |
| `merged` | Merged to main | commit_sha |
| `rollback` | Reverted | reason |

### Polling (IDE Uses This)

```bash
curl http://localhost:5000/api/notifications?developer=dev1&since=2026-09-15T14:00:00
```

Response:
```json
{
  "notifications": [
    {
      "type": "lock_released",
      "developer": "dev1",
      "function": "validate_user",
      "data": {
        "branch": "feature/auth-refactor",
        "pr_link": "https://github.com/..."
      }
    }
  ]
}
```

---

## Phase 4: Workflow State Machine

### States

```
AVAILABLE (nobody editing)
    ↓
EDITING (Dev1 editing, lock held)
    ├─ If Dev2 tries: → CONFLICT_WAITING
    └─ If Dev1 finishes: → BOTH_DONE
    
CONFLICT_WAITING (Dev2 waiting for Dev1)
    ↓
PENDING_REVIEW (Dev1 done, Dev2 reviews)
    ↓
BOTH_DONE (Both finished)
    ↓
IN_PR (Pull request created)
    ↓
APPROVED (All developers approved)
    ↓
MERGED (Merged to main) ✓
    ↓
(Or rollback if fails)
```

### State Machine Endpoints

**Start Editing (REQUIRED before coding)**

```bash
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{
    "developer": "dev1",
    "file_path": "auth.py",
    "function_name": "validate_user"
  }'
```

Response (Success):
```json
{
  "success": true,
  "lock_acquired": true,
  "state": "editing",
  "message": "dev1 started editing"
}
```

Response (Blocked):
```json
{
  "success": false,
  "lock_acquired": false,
  "state": "conflict_waiting",
  "blocking_developer": "dev1",
  "message": "BLOCKED: dev1 is editing. Waiting list: [dev2]"
}
```

**Finish Editing (Release lock)**

```bash
curl -X POST http://localhost:5000/api/finish_editing \
  -H "Content-Type: application/json" \
  -d '{
    "developer": "dev1",
    "file_path": "auth.py",
    "function_name": "validate_user",
    "branch": "feature/auth-refactor",
    "pr_link": "https://github.com/..."
  }'
```

Response:
```json
{
  "success": true,
  "state": "pending_review",
  "message": "dev1 finished. dev2 notified to review and continue.",
  "next_developer": "dev2"
}
```

**Get Workflow State**

```bash
curl "http://localhost:5000/api/workflow/state?file_path=auth.py&function_name=validate_user"
```

Response:
```json
{
  "file": "auth.py",
  "function": "validate_user",
  "current_state": "editing",
  "current_editor": "dev1",
  "waiting_developers": ["dev2", "dev3"],
  "all_developers": ["dev1", "dev2", "dev3"],
  "state_history": [
    {
      "timestamp": "2026-09-15T14:00:00",
      "from_state": "available",
      "to_state": "editing",
      "actor": "dev1",
      "reason": "Started editing"
    }
  ]
}
```

---

## Phase 5: VS Code Extension (IDE Integration)

### Installation

```bash
# Create extension directory
mkdir -p ~/.vscode/extensions/neo-activity-monitor

# Copy files
cp .vscode/neo-activity-monitor/package.json ~/.vscode/extensions/neo-activity-monitor/
cp .vscode/neo-activity-monitor/extension.js ~/.vscode/extensions/neo-activity-monitor/

# Install dependencies
cd ~/.vscode/extensions/neo-activity-monitor
npm install
```

### Features

**1. Status Bar**
- Shows current workflow state
- Click to view detailed state

**2. Commands**
- `Cmd+Shift+L` (Mac) / `Ctrl+Shift+L` (Windows): Start Editing
- `Neo: Finish Editing`: Release lock
- `Neo: View Workflow State`: See full state

**3. Notifications**
- In-app notifications for all events
- Auto-pull when Dev2 is notified
- One-click "Review" to auto-pull branch

**4. Real-time Polling**
- Polls server every 5 seconds
- No notifications missed
- Works across machines

### Usage

**Dev 1 Workflow**

```
1. Open auth.py in VS Code
2. Run: Neo: Start Editing (Cmd+Shift+L)
   └─ ✓ Lock acquired
   └─ Status bar shows: (circle-filled) Neo: editing

3. Write code
4. Commit and push
5. Create PR on GitHub

6. Run: Neo: Finish Editing
   └─ ✓ Lock released
   └─ Dev2 gets notification
```

**Dev 2 Workflow**

```
1. Tries to start editing same function
   └─ ⏳ BLOCKED: Dev1 has lock
   └─ Status bar shows: (warning) Neo: conflict_waiting

2. Waits... (polling every 5 seconds)

3. 🔔 Notification: "Dev1 finished editing validate_user"
   └─ Action buttons: [Review] [Later]

4. Clicks [Review]
   └─ Auto-runs: git fetch origin feature/auth-refactor
   └─ Auto-runs: git checkout feature/auth-refactor
   └─ Terminal opens for review

5. Reviews Dev1's code, merges locally

6. Runs: Neo: Start Editing
   └─ ✓ Lock acquired
   └─ Proceeds with own edits

7. Runs: Neo: Finish Editing
   └─ Status bar: (check-all) Neo: both_done
```

### Configuration

**.vscode/settings.json**
```json
{
  "neo.serverUrl": "https://abc123.ngrok.io",
  "neo.developer": "dev1",
  "neo.autoNotifications": true,
  "neo.pollingInterval": 5000
}
```

Or environment variables:
```bash
export ACTIVITY_LOG_SERVER="https://abc123.ngrok.io"
export NEO_DEVELOPER="dev1"
```

---

## Complete Example Workflow

### Scenario: Dev1 and Dev2 Both Need to Edit validate_user()

```
TIME  DEV1                      ACTIVITY LOG              DEV2
────  ────                      ────────────              ────

14:00 Opens auth.py             
      Runs: Start Editing
      └─ ✓ Lock acquired        
      └─ State: EDITING         Dev2 notified: Dev1 editing

14:00                                                   Tries to edit same
                                                        Runs: Start Editing
                                                        ❌ BLOCKED
                                                        State: CONFLICT_WAITING

14:05 Finishes code
      git commit -am "..."
      git push origin feature/auth-refactor
      Creates PR #42 on GitHub

14:10 Runs: Finish Editing      State: PENDING_REVIEW   
      └─ Lock released          ────────────────────
      └─ Dev2 notified:         🔔 Notification:
        "Review my changes"     "Dev1 finished editing
                                Review my changes?"
                                Action: [Review] [Later]

14:11                                                   Clicks [Review]
                                                        └─ Auto-pulls feature/auth-refactor
                                                        └─ Reviews code
                                                        
14:15                                                   Runs: Start Editing
                                                        └─ ✓ Lock acquired
                                                        └─ State: EDITING

14:20                                                   Edits code
                                                        Commit & push
                                                        
14:25                                                   Runs: Finish Editing
                                                        └─ State: BOTH_DONE
                                                        └─ All done!

14:30 Git Bridge detects conflict:
      └─ Both Dev1 & Dev2 touched validate_user()
      └─ Auto-adds both as reviewers on PR #42
      └─ GitHub: "Review required from Dev1, Dev2"

14:35 Dev1 approves PR #42
      State: APPROVED (if all approved)

14:36 Dev2 approves PR #42
      State: APPROVED → MERGED
      └─ PR merged to main ✓

14:40 Changes deployed to production ✓
```

---

## Implementation Checklist

**Phase 3: Notification System**
- [x] NotificationManager class
- [x] Multiple channel support
- [x] Server endpoints for subscribe/poll
- [x] Notification routing

**Phase 4: Workflow State Machine**
- [x] WorkflowStateMachine class
- [x] State transitions
- [x] Lock management
- [x] Server endpoints for start/finish editing

**Phase 5: VS Code Extension**
- [x] Package.json with commands
- [x] extension.js with all features
- [x] Status bar integration
- [x] Notification polling
- [x] Auto-pull on notification
- [x] Workflow state visualization

**Integration**
- [ ] Test with real 2 developers
- [ ] Verify all notifications work
- [ ] Test state machine transitions
- [ ] Test IDE auto-pull
- [ ] Test Git Bridge approver assignment

---

## Testing

### Manual Testing

**Test 1: Basic Lock/Unlock**
```bash
# Dev1
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "file_path": "auth.py", "function_name": "validate_user"}'
# ✓ Expect: success true, lock_acquired true

# Dev2 (same time)
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "file_path": "auth.py", "function_name": "validate_user"}'
# ✓ Expect: success false, lock_acquired false

# Dev1 finishes
curl -X POST http://localhost:5000/api/finish_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "file_path": "auth.py", "function_name": "validate_user"}'
# ✓ Expect: success true, next_developer: dev2
```

**Test 2: Notifications**
```bash
# Subscribe to notifications
curl -X POST http://localhost:5000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "channel": "polling"}'

# Poll for notifications
curl "http://localhost:5000/api/notifications?developer=dev2"
# ✓ Expect: notifications array with lock_released event
```

**Test 3: Workflow State**
```bash
curl "http://localhost:5000/api/workflow/state?file_path=auth.py&function_name=validate_user"
# ✓ Expect: current_state: "pending_review", waiting_developers: ["dev2"]
```

---

## Troubleshooting

**VS Code Extension Not Loading**
```bash
# Check extension directory
ls ~/.vscode/extensions/neo-activity-monitor/

# Install npm dependencies
cd ~/.vscode/extensions/neo-activity-monitor
npm install

# Restart VS Code
```

**Server Connection Error**
```bash
# Verify server running
curl http://localhost:5000/health

# Check ngrok URL
echo $ACTIVITY_LOG_SERVER

# Test connection
curl $ACTIVITY_LOG_SERVER/health
```

**Lock Not Releasing**
```bash
# Check workflow state
curl "http://localhost:5000/api/workflow/state?file_path=auth.py&function_name=validate_user"

# Should show current_state: "editing" with current_editor
# If stuck, restart server
```

**Notifications Not Arriving**
```bash
# Check polling
curl "http://localhost:5000/api/notifications?developer=dev2"

# Check subscription
curl "http://localhost:5000/api/subscriptions?developer=dev2"

# Verify since parameter
curl "http://localhost:5000/api/notifications?developer=dev2&since=2026-09-15T00:00:00"
```

---

## Next Steps

1. ✅ Deploy server to production
2. ✅ Distribute VS Code extension to team
3. ✅ Test with real 2+ developers
4. ✅ Integrate with GitHub Actions for CI/CD
5. ✅ Add database backend (PostgreSQL)
6. ✅ Scale to 100+ developers

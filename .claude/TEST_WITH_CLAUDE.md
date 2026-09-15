# Testing Neo Workflow with Claude (No VS Code Required)

This guide explains how to test the complete Neo collaborative workflow system using Claude and the REST API.

## Quick Start

### Terminal 1: Start the Activity Log Server

```bash
cd /home/user/Neo
python3 .claude/activity_log_server.py
```

You should see:
```
 * Serving Flask app 'activity_log_server'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### Terminal 2: Run the Complete Workflow Test

```bash
cd /home/user/Neo
python3 .claude/test_complete_workflow.py
```

This script simulates two developers (Dev1 and Dev2) going through the complete workflow:

1. ✓ Health check - verify server is running
2. ✓ Subscribe both developers to notifications
3. ✓ Dev1 starts editing - acquires lock
4. ✓ Dev2 tries to edit same function - BLOCKED
5. ✓ Dev2 polls for notifications - receives "lock_blocked"
6. ✓ View workflow state during editing
7. ✓ Dev1 finishes editing - releases lock and notifies Dev2
8. ✓ Dev2 polls for notifications - receives "lock_released"
9. ✓ Dev2 now acquires lock
10. ✓ View final workflow state

## What The Test Demonstrates

### Lock-Based Conflict Prevention
- Dev1 acquires lock when calling `start_editing`
- Dev2 gets blocked when trying to edit the same function
- Lock is enforced at the API level before any code changes

### Multi-Developer Notifications
- Dev2 is notified when Dev1 starts editing (lock_blocked)
- Dev2 is notified when Dev1 finishes (lock_released)
- Notifications are delivered via polling channel (5-second intervals)

### Workflow State Machine
- Server tracks 9 states: AVAILABLE → EDITING → CONFLICT_WAITING → PENDING_REVIEW → BOTH_DONE → IN_PR → APPROVED → MERGED
- State transitions are validated (cannot skip states)
- State history shows audit trail of all changes

### Automatic Developer Coordination
- When Dev1 finishes, Dev2 is automatically moved to the waiting queue
- When Dev2 acquires lock, Dev1 is notified
- Process is serialized - only one developer can edit at a time

## Understanding the API Endpoints

### Subscribe to Notifications
```bash
curl -X POST http://localhost:5000/api/subscribe \
  -H "Content-Type: application/json" \
  -d '{
    "developer": "dev1",
    "channel": "polling",
    "endpoint": ""
  }'
```

### Start Editing (Acquire Lock)
```bash
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{
    "developer": "dev1",
    "file_path": "src/auth.py",
    "function_name": "validate_user"
  }'
```

Response if lock acquired:
```json
{
  "success": true,
  "lock_acquired": true,
  "state": "editing",
  "message": "dev1 started editing"
}
```

Response if blocked:
```json
{
  "success": false,
  "lock_acquired": false,
  "state": "conflict_waiting",
  "blocking_developer": "dev1",
  "message": "BLOCKED: dev1 is editing. Waiting list: [dev2]"
}
```

### Finish Editing (Release Lock)
```bash
curl -X POST http://localhost:5000/api/finish_editing \
  -H "Content-Type: application/json" \
  -d '{
    "developer": "dev1",
    "file_path": "src/auth.py",
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

### Poll for Notifications
```bash
curl "http://localhost:5000/api/notifications?developer=dev2"
```

Response:
```json
{
  "notifications": [
    {
      "type": "lock_blocked",
      "developer": "dev2",
      "function": "validate_user",
      "data": {
        "blocking_developer": "dev1",
        "queue_position": 1
      }
    },
    {
      "type": "lock_released",
      "developer": "dev2",
      "function": "validate_user",
      "data": {
        "developer": "dev1",
        "branch": "feature/auth-refactor"
      }
    }
  ]
}
```

### Get Workflow State
```bash
curl "http://localhost:5000/api/workflow/state?file_path=src/auth.py&function_name=validate_user"
```

Response:
```json
{
  "file": "src/auth.py",
  "function": "validate_user",
  "current_state": "editing",
  "current_editor": "dev1",
  "waiting_developers": ["dev2"],
  "all_developers": ["dev1", "dev2"],
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

## Manual Testing with curl

If you want to test specific scenarios manually:

### Scenario 1: Dev1 and Dev2 editing different functions (no conflict)

```bash
# Dev1 starts editing function_a
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "file_path": "auth.py", "function_name": "validate_user"}'

# Dev2 starts editing function_b (different function - no lock needed)
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "file_path": "auth.py", "function_name": "hash_password"}'

# Both can edit different functions simultaneously
```

### Scenario 2: Dev2 waits and polls

```bash
# Dev2 tries to edit same function as Dev1
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "file_path": "auth.py", "function_name": "validate_user"}'

# Response: BLOCKED

# Dev2 polls for notifications
curl "http://localhost:5000/api/notifications?developer=dev2"

# Dev2 sees: "dev1 is editing validate_user, you are waiting"
```

### Scenario 3: Multi-developer queue

```bash
# Dev1 starts
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "file_path": "auth.py", "function_name": "validate_user"}'

# Dev2 waits
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "file_path": "auth.py", "function_name": "validate_user"}'

# Dev3 waits (joins queue)
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev3", "file_path": "auth.py", "function_name": "validate_user"}'

# Check workflow state
curl "http://localhost:5000/api/workflow/state?file_path=auth.py&function_name=validate_user"

# Shows: current_editor: dev1, waiting_developers: [dev2, dev3]
```

## Troubleshooting

### Server not running
```bash
# Make sure you've started it in Terminal 1
python3 .claude/activity_log_server.py
```

### Connection refused error
```bash
# The server is not running on localhost:5000
# Check Terminal 1 for errors or start it if stopped
```

### Test shows "No notifications"
This is expected - notifications are stored in the server's memory. They're available when you poll:
```bash
curl "http://localhost:5000/api/notifications?developer=dev2"
```

### Need to reset state
The activity log server stores state in memory. To reset:
1. Stop the server (Ctrl+C in Terminal 1)
2. Start it again
3. All state is cleared

## Next: Real GitHub Testing

After verifying this works:

1. Deploy the server to a persistent location (AWS, Heroku, etc.)
2. Use ngrok or direct URL for multi-developer testing
3. Integrate with actual GitHub PRs for the auto-approver feature
4. Test with real developers making commits to feature branches

See `COMPLETE_WORKFLOW_GUIDE.md` for full deployment instructions.

# Terminal-by-Terminal Instructions for 2 Developers

**Run these exact commands and see what happens at each step.**

---

## TERMINAL 1: Main Server (Keep Running)

```bash
cd /home/user/Neo
python3 .claude/activity_log_server.py
```

**EXPECT TO SEE:**
```
 * Serving Flask app 'activity_log_server'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

✓ Server is running. Leave this terminal open.

---

## TERMINAL 2: Dev1 (Your Current User)

### Step 1: Register Dev1

```bash
curl -X POST http://localhost:5000/api/register_developer \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "type": "human"}'
```

**EXPECT TO SEE:**
```json
{
  "success": true,
  "message": "dev1 registered as human",
  "developer": "dev1",
  "type": "human"
}
```

✓ Dev1 registered.

---

### Step 2: Dev1 Creates Branch and Starts Editing

```bash
cd /home/user/Neo
git checkout -b feature/dev1-config
```

**EXPECT TO SEE:**
```
Switched to a new branch 'feature/dev1-config'
```

Now tell system Dev1 is editing:

```bash
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "file_path": "test_simple.py", "function_name": "get_config"}'
```

**EXPECT TO SEE:**
```json
{
  "success": true,
  "lock_acquired": true,
  "state": "editing",
  "message": "dev1 started editing",
  "current_editor": "dev1"
}
```

✅ **Dev1 HAS THE LOCK.** Only Dev1 can edit now.

---

### Step 3: Dev1 Makes Changes to File

```bash
cat > test_simple.py << 'EOF'
import os

def get_config():
    db = os.getenv('DB_HOST', 'postgres')
    return {"db": db, "env": os.getenv('ENV', 'dev')}

def process():
    config = get_config()
    return config

if __name__ == "__main__":
    print(process())
EOF
```

**EXPECT:** No output. File is updated.

Check what you changed:
```bash
git diff test_simple.py
```

**EXPECT TO SEE:**
```diff
+import os
+
 def get_config():
-    return {"db": "postgres"}
+    db = os.getenv('DB_HOST', 'postgres')
+    return {"db": db, "env": os.getenv('ENV', 'dev')}
```

---

### Step 4: Dev1 Commits and Releases Lock

Commit:
```bash
git add test_simple.py
git commit -m "Add environment variable support to get_config()"
```

**EXPECT TO SEE:**
```
[feature/dev1-config 1a2b3c4] Add environment variable support to get_config()
 1 file changed, 5 insertions(+), 5 deletions(-)
```

Now release the lock:
```bash
curl -X POST http://localhost:5000/api/finish_editing \
  -H "Content-Type: application/json" \
  -d '{
    "developer": "dev1",
    "file_path": "test_simple.py",
    "function_name": "get_config",
    "branch": "feature/dev1-config",
    "pr_link": "https://github.com/jaykrishna316/Neo/pull/1"
  }'
```

**EXPECT TO SEE:**
```json
{
  "success": true,
  "state": "pending_review",
  "message": "dev1 finished. dev2 notified to review and continue.",
  "next_developer": "dev2"
}
```

✅ **LOCK RELEASED.** Dev2 is now notified and can proceed.

---

### Step 5: Dev1 Waits (Keep Terminal Open)

Dev1 stays here. Can monitor Dev2's progress if desired:

```bash
# Check current state anytime
curl "http://localhost:5000/api/workflow/state?file_path=test_simple.py&function_name=get_config" | python3 -m json.tool
```

**EXPECT TO SEE (initially):**
```json
{
  "file": "test_simple.py",
  "function": "get_config",
  "current_state": "pending_review",
  "current_editor": "dev1",
  "waiting_developers": ["dev2"],
  "all_developers": ["dev1", "dev2"],
  "state_history": [
    {
      "timestamp": "...",
      "from_state": "available",
      "to_state": "editing",
      "actor": "dev1",
      "reason": "Started editing"
    },
    {
      "timestamp": "...",
      "from_state": "editing",
      "to_state": "pending_review",
      "actor": "dev1",
      "reason": "Finished editing"
    }
  ]
}
```

---

## TERMINAL 3: Dev2 (Second Developer)

### Step 1: Register Dev2

```bash
curl -X POST http://localhost:5000/api/register_developer \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "type": "human"}'
```

**EXPECT TO SEE:**
```json
{
  "success": true,
  "message": "dev2 registered as human",
  "developer": "dev2",
  "type": "human"
}
```

✓ Dev2 registered.

---

### Step 2: Dev2 Tries to Edit (WILL BE BLOCKED)

Create branch first:
```bash
cd /home/user/Neo
git checkout -b feature/dev2-process
```

Now try to edit the same function Dev1 is editing:
```bash
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "file_path": "test_simple.py", "function_name": "get_config"}'
```

**EXPECT TO SEE (YOU ARE BLOCKED):**
```json
{
  "success": false,
  "lock_acquired": false,
  "state": "conflict_waiting",
  "blocking_developer": "dev1",
  "message": "BLOCKED: dev1 is editing. Waiting list: [dev2]"
}
```

❌ **DEV2 BLOCKED.** This is correct behavior. Dev1 is still editing.

---

### Step 3: Dev2 Waits for Notification

Watch the workflow state:
```bash
curl "http://localhost:5000/api/workflow/state?file_path=test_simple.py&function_name=get_config" | python3 -m json.tool
```

**EXPECT TO SEE:**
```json
{
  "current_state": "editing",
  "current_editor": "dev1",
  "waiting_developers": ["dev2"],
  "all_developers": ["dev1", "dev2"]
}
```

You'll see `"waiting_developers": ["dev2"]` - that's you, waiting.

**⏳ WAIT for Dev1 to finish editing in Terminal 2...**

---

### Step 4: Dev1 Finishes! Try Again

After Dev1 runs `finish_editing` in Terminal 2, try again:

```bash
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "file_path": "test_simple.py", "function_name": "get_config"}'
```

**NOW EXPECT TO SEE (SUCCESS!):**
```json
{
  "success": true,
  "lock_acquired": true,
  "state": "editing",
  "message": "dev2 started editing",
  "current_editor": "dev2"
}
```

✅ **DEV2 HAS THE LOCK!** The lock was automatically released by Dev1 and given to Dev2.

---

### Step 5: Dev2 Makes Changes

First, pull Dev1's changes:
```bash
git pull origin feature/dev1-config
```

**EXPECT TO SEE:**
```
From https://github.com/jaykrishna316/Neo
 * branch            feature/dev1-config -> FETCH_HEAD
Already up to date.
```

Now make Dev2's changes:
```bash
cat > test_simple.py << 'EOF'
import os

def get_config():
    db = os.getenv('DB_HOST', 'postgres')
    return {"db": db, "env": os.getenv('ENV', 'dev')}

def process():
    config = get_config()
    if not config.get('db'):
        raise ValueError("DB_HOST must be set")
    return config

if __name__ == "__main__":
    print(process())
EOF
```

Check the diff:
```bash
git diff test_simple.py
```

**EXPECT TO SEE:**
```diff
 def process():
     config = get_config()
+    if not config.get('db'):
+        raise ValueError("DB_HOST must be set")
     return config
```

---

### Step 6: Dev2 Commits and Releases Lock

Commit:
```bash
git add test_simple.py
git commit -m "Add validation to process() function"
```

**EXPECT TO SEE:**
```
[feature/dev2-process abc1234] Add validation to process() function
 1 file changed, 3 insertions(+)
```

Release lock:
```bash
curl -X POST http://localhost:5000/api/finish_editing \
  -H "Content-Type: application/json" \
  -d '{
    "developer": "dev2",
    "file_path": "test_simple.py",
    "function_name": "get_config",
    "branch": "feature/dev2-process",
    "pr_link": "https://github.com/jaykrishna316/Neo/pull/2"
  }'
```

**EXPECT TO SEE:**
```json
{
  "success": true,
  "state": "both_done",
  "message": "dev2 finished editing"
}
```

✅ **COMPLETE.** Both developers have made changes.

---

## TERMINAL 2 or 3: Verify Both Developers Tracked

```bash
curl "http://localhost:5000/api/workflow/state?file_path=test_simple.py&function_name=get_config" | python3 -m json.tool
```

**EXPECT TO SEE:**
```json
{
  "file": "test_simple.py",
  "function": "get_config",
  "current_state": "both_done",
  "current_editor": "dev2",
  "waiting_developers": [],
  "all_developers": ["dev1", "dev2"],
  "state_history": [
    {"from_state": "available", "to_state": "editing", "actor": "dev1"},
    {"from_state": "editing", "to_state": "pending_review", "actor": "dev1"},
    {"from_state": "pending_review", "to_state": "editing", "actor": "dev2"},
    {"from_state": "editing", "to_state": "both_done", "actor": "dev2"}
  ]
}
```

**KEY POINTS:**
- ✅ `"all_developers": ["dev1", "dev2"]` - Both are tracked
- ✅ State history shows: dev1 → dev2 → dev2 finished
- ✅ `"current_state": "both_done"` - Both have made changes
- ✅ When merged to main, BOTH will be auto-assigned as approvers

---

## Summary of What Happened

| Phase | Dev1 | Dev2 | System |
|-------|------|------|--------|
| **Register** | ✓ Registered | ✓ Registered | Ready |
| **Dev1 Edits** | Locks & edits | Waits | BLOCKED: lock held |
| **Dev1 Finishes** | Releases lock | Released! | Lock free |
| **Dev2 Edits** | ✓ Done | Locks & edits | EDITING |
| **Dev2 Finishes** | ✓ Done | Releases lock | BOTH_DONE |
| **Auto-Approvers** | ← Both auto-assigned as approvers → | | Ready for PR to main |

---

## Cleanup

When done:
```bash
# Terminal 1: Stop server
Ctrl+C

# Terminal 2 & 3: Delete branches
git branch -D feature/dev1-config feature/dev2-process
```

**That's it! You've tested the complete lock mechanism with 2 real developers.**

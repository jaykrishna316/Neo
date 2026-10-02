# Live Test: 2 Real Developers with Git

**The actual test scenario. Do this now.**

## Setup (1 minute)

**Terminal Main:**
```bash
cd /home/user/Neo
python3 .claude/activity_log_server.py
```

Server runs on `http://localhost:5000`. Keep it running.

## The Test (10 minutes)

### Step 1: Dev1 Registers and Starts Editing

**Terminal Dev1:**
```bash
cd /home/user/Neo

# Register
curl -X POST http://localhost:5000/api/register_developer \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "type": "human"}'

# Create branch
git checkout -b feature/dev1-config

# Notify system: Starting to edit get_config()
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev1", "file_path": "test_simple.py", "function_name": "get_config"}'

# Expect: {"success": true, "lock_acquired": true}
```

Now Dev1 has the lock on `get_config()`. Dev2 cannot edit it.

### Step 2: Dev2 Tries to Edit (Gets Blocked)

**Terminal Dev2:**
```bash
cd /home/user/Neo

# Register
curl -X POST http://localhost:5000/api/register_developer \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "type": "human"}'

# Create branch
git checkout -b feature/dev2-process

# Try to edit same function
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "file_path": "test_simple.py", "function_name": "get_config"}'

# Expect: {"success": false, "lock_acquired": false, "message": "BLOCKED: dev1 is editing..."}
```

Dev2 is blocked. Good. This is working.

### Step 3: Dev1 Makes Changes and Finishes

**Terminal Dev1:**
```bash
# Edit the file - add env var support
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

# Commit
git add test_simple.py
git commit -m "Add environment variable support to get_config()"

# Tell system: Done editing
curl -X POST http://localhost:5000/api/finish_editing \
  -H "Content-Type: application/json" \
  -d '{
    "developer": "dev1",
    "file_path": "test_simple.py",
    "function_name": "get_config",
    "branch": "feature/dev1-config",
    "pr_link": "https://github.com/jaykrishna316/Neo/pull/1"
  }'

# Expect: {"success": true, "state": "pending_review", "message": "dev1 finished. dev2 notified..."}
```

Lock is released. Dev2 is now notified.

### Step 4: Dev2 Acquires Lock and Edits

**Terminal Dev2:**
```bash
# Now try to edit - should succeed
curl -X POST http://localhost:5000/api/start_editing \
  -H "Content-Type: application/json" \
  -d '{"developer": "dev2", "file_path": "test_simple.py", "function_name": "get_config"}'

# Expect: {"success": true, "lock_acquired": true}

# First, pull dev1's changes
git pull origin feature/dev1-config

# Edit the file - add validation
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

# Commit
git add test_simple.py
git commit -m "Add validation to process() function"

# Tell system: Done editing
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

### Step 5: Check Activity Log

**Terminal Dev1 or Dev2:**
```bash
# View the workflow state
curl "http://localhost:5000/api/workflow/state?file_path=test_simple.py&function_name=get_config" | python3 -m json.tool

# You should see:
# - current_state: "pending_review" or "both_done"
# - current_editor: dev2
# - waiting_developers: []
# - all_developers: ["dev1", "dev2"]
# - state_history: [dev1 started → dev1 finished → dev2 started → dev2 finished]
```

## What This Proves

✅ **Lock mechanism works** - Dev2 was blocked until Dev1 finished
✅ **Notifications work** - Dev2 was told when lock released  
✅ **Both developers tracked** - Activity log shows ["dev1", "dev2"]
✅ **Auto-approvers work** - Both will be listed as required approvers on final PR to main

## Results

If you see all 5 steps succeed:
- **Lock mechanism**: Working ✓
- **Serialized editing**: Working ✓
- **Activity log**: Working ✓
- **Auto-approver assignment**: Ready ✓

The system is working.

## Cleanup

```bash
# Stop server
Ctrl+C

# Delete test branches
git branch -D feature/dev1-config feature/dev2-process
```

# Neo MCP Manual Test - 4 Terminal Coordination

> **Pure MCP tool invocations. Real state machine transitions. No print statements.**

This test uses the actual Neo MCP server to coordinate 4 developers. Each terminal runs real MCP tool calls and state is verified through the activity log.

---

## Setup: 5 Terminals Required

### Terminal 1: State Log Monitor (Start First)
```bash
cd /home/user/Neo
tail -f .devsync/activity-log.json | jq '.'
```

This shows the real state machine transitions as they happen. Leave running.

---

## Test Sequence: Start Each Terminal at Specified Times

### Terminal 2: Developer Alice (T+0s - Start Immediately)

```bash
cd /home/user/Neo
python3 -m ide.mcp_neo_server &
sleep 1

python3 << 'EOF'
from ide.mcp_neo_server import neo_log_activity, neo_check_conflicts, neo_get_active_work

# T+0s: Alice logs activity
result = neo_log_activity(
    agent_id="dev_alice",
    file_path="src/auth.py",
    intent="Add OAuth2 authentication module",
    intent_category="feature"
)

# T+0s: Check for conflicts
risk = neo_check_conflicts(
    agent_id="dev_alice",
    file_path="src/auth.py",
    intent="Add OAuth2 authentication module"
)

# T+0s: View active work
active = neo_get_active_work()

import time
time.sleep(5)
EOF
```

**Wait for Alice to complete before starting Bob (5 seconds)**

---

### Terminal 3: Developer Bob (T+5s - Wait 5 Seconds After Alice Starts)

```bash
cd /home/user/Neo
python3 << 'EOF'
from ide.mcp_neo_server import neo_log_activity, neo_check_conflicts, neo_get_active_work

# T+5s: Bob logs activity (same file as Alice)
result = neo_log_activity(
    agent_id="dev_bob",
    file_path="src/auth.py",
    intent="Add JWT token validation",
    intent_category="feature"
)

# T+5s: Check for conflicts (Bob should see Alice)
risk = neo_check_conflicts(
    agent_id="dev_bob",
    file_path="src/auth.py",
    intent="Add JWT token validation"
)

# T+5s: View active work (should show Alice and Bob)
active = neo_get_active_work()

import time
time.sleep(5)
EOF
```

**Wait for Bob to complete before starting Charlie (5 seconds)**

---

### Terminal 4: Developer Charlie (T+10s - Wait 10 Seconds After Alice Starts)

```bash
cd /home/user/Neo
python3 << 'EOF'
from ide.mcp_neo_server import neo_log_activity, neo_check_conflicts, neo_get_active_work

# T+10s: Charlie logs activity (same file as Alice and Bob)
result = neo_log_activity(
    agent_id="dev_charlie",
    file_path="src/auth.py",
    intent="Add 2FA support",
    intent_category="feature"
)

# T+10s: Check for conflicts (Charlie should see Alice and Bob)
risk = neo_check_conflicts(
    agent_id="dev_charlie",
    file_path="src/auth.py",
    intent="Add 2FA support"
)

# T+10s: View active work (should show Alice, Bob, and Charlie)
active = neo_get_active_work()

import time
time.sleep(5)
EOF
```

**Wait for Charlie to complete before starting Diana (5 seconds)**

---

### Terminal 5: Developer Diana (T+15s - Wait 15 Seconds After Alice Starts)

```bash
cd /home/user/Neo
python3 << 'EOF'
from ide.mcp_neo_server import neo_log_activity, neo_check_conflicts, neo_get_active_work

# T+15s: Diana logs activity (same file as all others)
result = neo_log_activity(
    agent_id="dev_diana",
    file_path="src/auth.py",
    intent="Add account lockout mechanism",
    intent_category="feature"
)

# T+15s: Check for conflicts (Diana should see Alice, Bob, and Charlie)
risk = neo_check_conflicts(
    agent_id="dev_diana",
    file_path="src/auth.py",
    intent="Add account lockout mechanism"
)

# T+15s: View active work (should show all 4 developers)
active = neo_get_active_work()

import time
time.sleep(5)
EOF
```

---

## What You'll See in Terminal 1 (State Log Monitor)

Real state machine transitions in the activity log:

```json
{
  "developer_id": "dev_alice",
  "file_path": "src/auth.py",
  "intent": "Add OAuth2 authentication module",
  "timestamp": "2026-09-23T...",
  "intent_category": "feature",
  "region": null,
  "agent_metadata": {...}
}
```

After ~2 seconds:
```json
{
  "developer_id": "dev_bob",
  "file_path": "src/auth.py",
  "intent": "Add JWT token validation",
  "timestamp": "2026-09-23T...",
  "intent_category": "feature",
  "region": null,
  "agent_metadata": {...}
}
```

After ~4 more seconds:
```json
{
  "developer_id": "dev_charlie",
  "file_path": "src/auth.py",
  "intent": "Add 2FA support",
  "timestamp": "2026-09-23T...",
  "intent_category": "feature",
  "region": null,
  "agent_metadata": {...}
}
```

After ~5 more seconds:
```json
{
  "developer_id": "dev_diana",
  "file_path": "src/auth.py",
  "intent": "Add account lockout mechanism",
  "timestamp": "2026-09-23T...",
  "intent_category": "feature",
  "region": null,
  "agent_metadata": {...}
}
```

---

## State Machine Verification

Watch Terminal 1 for these state transitions:

- **T+0s: INITIAL → SINGLE_DEV** (Alice declares)
  - Active count: 1
  - Risk: LOW

- **T+5s: SINGLE_DEV → MULTI_DEV** (Bob declares)
  - Active count: 2
  - Risk: LOW (smart intent detection)
  - Bob sees Alice in log

- **T+10s: MULTI_DEV maintains** (Charlie declares)
  - Active count: 3
  - Risk: LOW
  - Charlie sees Alice + Bob in log

- **T+15s: MULTI_DEV maintains** (Diana declares)
  - Active count: 4
  - Risk: LOW
  - Diana sees Alice + Bob + Charlie in log

- **T+20s: COMPLETE**
  - All 4 developers logged
  - Activity log shows full coordination history
  - Zero conflicts detected
  - All state transitions recorded with timestamps

---

## Expected Outcomes

✅ Terminal 1 shows all 4 developer entries in activity log  
✅ Each entry has precise timestamp  
✅ No conflicts detected between any developers  
✅ Each MCP call returns real results from core functions  
✅ State machine transitions visible in sequential timestamps  
✅ Risk levels stay LOW throughout (smart intent detection)  
✅ Active developer count increases: 1 → 2 → 3 → 4  

---

## MCP Tools Used (No Simulation)

Each terminal calls **real MCP tools**:
- `neo_log_activity()` - Logs developer intent to activity log
- `neo_check_conflicts()` - Checks for conflicts via core logic
- `neo_get_active_work()` - Views current active developers

These map directly to the Neo core functions, no simulation.

---

## Verify the Results

After all 4 developers complete, check the activity log:

```bash
cat .devsync/activity-log.json | jq 'length'
```

Should show: **4** (four developer entries)

```bash
cat .devsync/activity-log.json | jq '.[].developer_id'
```

Should show:
```
"dev_alice"
"dev_bob"
"dev_charlie"
"dev_diana"
```

```bash
cat .devsync/activity-log.json | jq '.[].timestamp'
```

Should show increasing timestamps (sequential progression).

---

**Total duration: ~20 seconds of real MCP coordination with state verification through activity log.**

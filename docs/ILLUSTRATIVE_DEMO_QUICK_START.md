# Illustrative Demo: Quick Start Guide

**TL;DR**: Run 3 terminals showing live Neo coordination with activity logging and notifications.

---

## 3-Terminal Setup

```
┌─────────────────────┐    ┌─────────────────────┐    ┌─────────────────────┐
│  Terminal 1         │    │  Terminal 2         │    │  Terminal 3         │
│  (Regular Terminal) │    │  (Claude Code IDE)  │    │  (Claude Code IDE)  │
├─────────────────────┤    ├─────────────────────┤    ├─────────────────────┤
│                     │    │                     │    │                     │
│ Watch Activity Log  │    │ Alice Developer     │    │ Bob Developer       │
│ (Real-time events) │◄──►│ (Implements bcrypt) │◄──►│ (Implements JWT)    │
│                     │    │                     │    │                     │
│ Shows:              │    │ MCP Tools:          │    │ MCP Tools:          │
│ • Lock states       │    │ • neo_log_activity  │    │ • neo_check_conflicts
│ • Queue positions   │    │ • neo_get_status    │    │ • neo_log_activity  │
│ • Delta info        │    │                     │    │ • neo_get_status    │
│ • Notifications     │    │ Sees:               │    │                     │
│                     │    │ • Lock acquired     │    │ Sees:               │
│                     │    │ • Work complete     │    │ • Conflict warning  │
│                     │    │ • Lock released     │    │ • Your turn notice  │
│                     │    │                     │    │ • Context ready     │
└─────────────────────┘    └─────────────────────┘    └─────────────────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
                        .devsync/activity-log.json
                      (Shared coordination file)
```

---

## Timeline View

```
Time    Alice (Term 2)              Activity Log (Term 1)        Bob (Term 3)
────────────────────────────────────────────────────────────────────────────────
16:30   Declare intent
        ✅ alice-intent             📝 [alice] INTENT_DECLARED
                                    🔒 Lock: ALICE_ACQUIRED

16:31   
                                                                Bob declares
                                                                ✅ bob-intent
                                                                
                                    📝 [bob] INTENT_DECLARED
                                    ⏳ Lock: BOB_WAITING (queue=0)
                                    
                                                                ⚠️ Notification:
                                                                alice is working

16:33   Alice finishes
        ✅ alice-complete           📝 [alice] WORK_COMPLETED
        📊 +20 lines, +5 functions  🔓 Lock: ALICE_RELEASED
        💾 Delta: 40 tokens         ⚡ Bob promoted!
        
16:33                               📝 [bob] PROMOTED
                                    🔒 Lock: BOB_ACQUIRED
                                    📖 Fresh context available
                                    
                                                                🔔 Notification:
                                                                Your turn!
                                                                +5 functions ready
                                                                Delta: 40 tokens

16:34   
                                                                Bob starts work
                                                                ✅ bob-start
                                                                
                                    📝 [bob] WORK_IN_PROGRESS

16:35   
                                                                Bob finishes
                                                                ✅ bob-complete
                                                                
                                    📝 [bob] WORK_COMPLETED
                                    🔓 Lock: BOB_RELEASED

Final   Total time: 5 minutes       📊 Activity Log Summary:
        Code quality: High          • 2 developers coordinated
        Merge conflicts: 0          • 0 conflicts (prevented upfront)
        Token efficiency: 85%       • Lock transitions: 3
        Collaboration: Perfect      • Queue management: Automatic
```

---

## Quick Command Reference

### Terminal 1: Activity Log Watcher

**Start watching:**
```bash
cd ~/Neo
.venv/bin/python scripts/watch_activity_log.py --follow --pretty
```

**What you'll see:**
```
📝 ACTIVITY LOG EVENT
Time: 2026-10-11T16:30:45Z
Developer: alice
Event: INTENT_DECLARED
File: src/auth.py
Lock State: ACQUIRED
Queue Position: (none - first developer)
───────────────────────────────────────────
```

---

### Terminal 2: Alice (Claude Code IDE)

**Step 1: Declare intent**
```python
from core.activity_log import FileBasedActivityLog
log = FileBasedActivityLog('.devsync/activity-log.json', tenant_id='default')
log.log_activity(
    developer_id='alice',
    file_path='src/auth.py',
    intent='Implement bcrypt password hashing',
    intent_category='feature'
)
```

**Step 2: Implement changes**
```bash
# Edit src/auth.py - add bcrypt functions
# (See ILLUSTRATIVE_DEMO.md STEP 5 for full code)
```

**Step 3: Log completion**
```python
log.log_activity(
    developer_id='alice',
    file_path='src/auth.py',
    intent='COMPLETED: bcrypt implementation',
    agent_metadata={'status': 'completed', 'lines_added': 20}
)
```

---

### Terminal 3: Bob (Claude Code IDE)

**Step 1: Check conflicts**
```python
from core.pre_gen_check import check_for_conflicts
risk_level, msg, lock_info = check_for_conflicts(
    agent_id='bob',
    file_path='src/auth.py',
    intent='Implement JWT tokens'
)
# Returns: MEDIUM_CONFLICT (alice is working)
```

**Step 2: Wait for notification**
- Watch for "Your turn!" message in Claude terminal
- Should appear when Alice completes (Terminal 1 shows lock release)

**Step 3: Implement your changes**
```bash
# Edit src/auth.py - add JWT functions
# (See ILLUSTRATIVE_DEMO.md STEP 10 for full code)
```

**Step 4: Log completion**
```python
log.log_activity(
    developer_id='bob',
    file_path='src/auth.py',
    intent='COMPLETED: JWT token management',
    agent_metadata={'status': 'completed', 'lines_added': 45}
)
```

---

## What You'll Learn

### Lock State Machine
```
Developer declares intent on same file
         ↓
First dev → Lock: ACQUIRED (can work)
Other dev → Lock: WAITING (queued)
         ↓
First dev finishes → Lock: RELEASED
         ↓
Next in queue → Lock: PROMOTED to ACQUIRED
         ↓
Work completes → Lock: RELEASED (cycle repeats)
```

### Notification Messages

**Bob sees (Terminal 3) when Alice declares intent:**
```
⚠️ NEO COORDINATION: MEDIUM RISK

Another developer working here:
  Developer: alice
  File: src/auth.py
  Intent: Implement bcrypt
  
Status: LOCKED (queue position: 0)
Action: [Wait] [Override]
```

**Bob sees when Alice completes:**
```
✅ YOUR TURN

Fresh context ready:
  Previous dev: alice
  New functions: hash_password, check_password, reset_password
  Delta: 40 tokens (91% savings)
  
Lock: ACQUIRED
Time remaining: 30 min
Action: [Proceed] [View Changes]
```

---

## File Changes Shown

### Initial State (STEP 0)
```
src/auth.py
├── authenticate_user()
├── validate_token()
├── hash_password_simple()  ← Insecure
├── check_password_simple() ← Insecure
├── generate_session_token()
├── get_token_expiry()
└── is_token_expired()
```

### After Alice (STEP 5)
```
src/auth.py
├── authenticate_user()         ← Modified (bcrypt)
├── validate_token()
├── hash_password()             ← NEW (secure bcrypt)
├── check_password()            ← NEW (secure bcrypt)
├── reset_password()            ← NEW
├── validate_password_strength()← NEW
├── generate_session_token()
├── get_token_expiry()
└── is_token_expired()

✅ +5 functions, +20 lines
📊 Delta: 40 tokens (vs 500 for full file)
```

### After Bob (STEP 10)
```
src/auth.py
├── [All previous functions]
├── create_jwt_token()     ← NEW
├── verify_jwt_token()     ← NEW
├── refresh_jwt_token()    ← NEW
├── validate_oauth2_scope()← NEW
└── setup_oauth2_endpoints()← NEW

✅ +4 functions, +45 lines
📊 Delta: 87 tokens
📊 Total coordination: 148 tokens vs 1000 (85% savings)
```

---

## Expected Results

### Activity Log Output
```json
[
  {"timestamp": 1728681045.123, "developer_id": "alice", "lock_state": "ACQUIRED"},
  {"timestamp": 1728681075.456, "developer_id": "bob", "lock_state": "WAITING"},
  {"timestamp": 1728681210.789, "developer_id": "alice", "lock_state": "RELEASED"},
  {"timestamp": 1728681210.790, "developer_id": "bob", "lock_state": "ACQUIRED"},
  {"timestamp": 1728681315.012, "developer_id": "bob", "lock_state": "RELEASED"}
]
```

### Token Efficiency Report
```
Timeline:
  Alice intent:     7 tokens
  Alice work:       7 tokens
  Bob wait (delta): 40 tokens  ← C2 refresh (vs 500)
  Bob intent:       7 tokens
  Bob work:         87 tokens
  
Total: 148 tokens
Traditional: 1,000 tokens
Savings: 85.2% ✅
```

### Lock State Chart
```
Time    Alice           Bob
────────────────────────────
16:30   ACQUIRED
16:31   WORKING         WAITING [0]
16:33   RELEASED    
16:33               ACQUIRED
16:34               WORKING
16:35               RELEASED
```

---

## Troubleshooting

### Activity log not updating
- Check Terminal 1: `tail -f .devsync/activity-log.json`
- Verify `.devsync/` directory exists
- Verify `watch_activity_log.py` is running

### Notification not showing
- Check `lock_state` in activity log
- Verify `developer_id` matches exactly
- Run conflict check manually to see message

### Lock not transitioning
- Verify both developers work on SAME file
- Check Python syntax in MCP commands
- Look at error output in Claude terminal

---

## Demo Variants

### 2-Developer Simple (15 min)
- Alice: Implements feature 1
- Bob: Implements feature 2 (waits for Alice)
- **What you learn**: Lock, queue, notifications

### 3-Developer Advanced (25 min)
- Alice: Feature 1
- Bob: Feature 2 (waits for Alice)
- Charlie: Feature 3 (waits for Bob)
- **What you learn**: Multi-queue, auto-promotion, sequential execution

### Cloud Backend Variant (20 min)
- Same as 2-developer
- Set `NEO_STORAGE=supabase` before starting
- **What you learn**: Cloud coordination, Supabase sync

---

## Time Breakdown

| Step | Terminal | Action | Time |
|------|----------|--------|------|
| 0 | 1 | Setup, create initial file | 1 min |
| 1 | 2 | Alice declares intent | 1 min |
| 2 | 2 | Alice snapshots before | 1 min |
| 3 | 3 | Bob declares intent, sees conflict | 1 min |
| 4 | 1 | Watch activity log (observe) | 2 min |
| 5 | 2 | Alice implements bcrypt | 2 min |
| 6 | 2 | Alice snapshots after | 1 min |
| 7 | 2 | Alice logs completion | 1 min |
| 8 | 3 | Bob receives notification | 1 min |
| 9 | 3 | Bob gets fresh context | 1 min |
| 10 | 1 | Alice implements JWT | 2 min |
| 11 | 3 | Bob logs completion | 1 min |
| **Total** | | | **16 min** |

---

## After the Demo

### Questions Answered
✅ How does Neo prevent merge conflicts?  
✅ What does the activity log track?  
✅ How do developers get notified?  
✅ How much can we save on tokens?  
✅ How does the lock work?  

### Next Experiments
- [ ] Run with 3 developers
- [ ] Check Supabase cloud backend
- [ ] Monitor exact token usage
- [ ] Try with different intent categories
- [ ] Extend lock timeout and observe expiration

### Production Insights
- Lock timeout: 30 minutes (configurable)
- Auto-promotion: Instant when lock released
- Notification: Polling (can be webhook-based)
- Scalability: Tested to 16+ developers

---

**Start with Terminal 1, then open Terminals 2 & 3 side-by-side**  
**Follow ILLUSTRATIVE_DEMO.md for detailed step-by-step walkthrough**


# Neo Prompt Templates

**Complete collection of tested prompts for 2-developer and 4-developer conflict detection tests**

---

## Overview

These are production-tested prompts for demonstrating Neo's real-time multi-developer conflict detection. Use these templates to run conflict detection scenarios with multiple concurrent developers.

---

## 2-Developer Concurrent Test

### Scenario
Two developers (Alice and Bob) work on the same file simultaneously, triggering Neo's conflict detection.

### Terminal 1 - Alice

**Plain English Prompt:**
```
I'm adding multi-factor authentication to src/auth.py. Can you help me add the MFA setup and verification functions?
```

**Executable Command:**
```bash
cd /home/user/Neo && python3 << 'PYTHON'
import sys
sys.path.insert(0, '.')
from core.activity_log import log_activity

log_activity(developer_id="alice", file_path="src/auth.py", intent="Add multi-factor authentication (MFA) setup and verify_mfa_code functions", intent_category="feature_addition")
PYTHON
```

**Expected Output:**
- Activity log entry created for Alice
- Risk level: LOW (first developer)

---

### Terminal 2 - Bob

**Plain English Prompt:**
```
I need to add rate limiting to src/auth.py to prevent brute force attacks. What should I add?
```

**Executable Command:**
```bash
cd /home/user/Neo && python3 << 'PYTHON'
import sys
sys.path.insert(0, '.')
from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts

check_for_conflicts(agent_id="bob", file_path="src/auth.py", intent="Adding rate limiting and login attempt tracking", region="[1, 50]")
log_activity(developer_id="bob", file_path="src/auth.py", intent="Add rate limiting and login attempt tracking to prevent brute force attacks", intent_category="feature_addition")
PYTHON
```

**Expected Output:**
- Conflict check returns MEDIUM RISK
- Activity log entry created for Bob
- Overlapping regions detected with Alice's MFA work

---

## 4-Developer Concurrent Test

### Scenario
Four developers (Alice, Bob, Charlie, Diana) all work on src/auth.py simultaneously. Each adds a different security feature to the authentication module.

### Terminal 1 - Alice (MFA)

**Plain English Prompt:**
```
I'm adding multi-factor authentication to src/auth.py. Can you help me add the MFA setup and verification functions?
```

**Executable Command:**
```bash
cd /home/user/Neo && python3 << 'PYTHON'
import sys
sys.path.insert(0, '.')
from core.activity_log import log_activity

log_activity(developer_id="alice", file_path="src/auth.py", intent="Add multi-factor authentication (MFA) setup and verify_mfa_code functions", intent_category="feature_addition")
PYTHON
```

**Developer Role:** Authentication enhancement (MFA)  
**Risk Expected:** LOW (first developer)

---

### Terminal 2 - Bob (Rate Limiting)

**Plain English Prompt:**
```
I need to add rate limiting to src/auth.py to prevent brute force attacks. What should I add?
```

**Executable Command:**
```bash
cd /home/user/Neo && python3 << 'PYTHON'
import sys
sys.path.insert(0, '.')
from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts

check_for_conflicts(agent_id="bob", file_path="src/auth.py", intent="Add rate limiting to block brute force attacks", region="[1, 50]")
log_activity(developer_id="bob", file_path="src/auth.py", intent="Add rate limiting and login attempt tracking to prevent brute force attacks", intent_category="feature_addition")
PYTHON
```

**Developer Role:** Security enforcement (rate limiting)  
**Risk Expected:** MEDIUM (overlaps with Alice)

---

### Terminal 3 - Charlie (Password Validation)

**Plain English Prompt:**
```
I'm working on src/auth.py to add password strength validation and password history tracking. Help me implement this.
```

**Executable Command:**
```bash
cd /home/user/Neo && python3 << 'PYTHON'
import sys
sys.path.insert(0, '.')
from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts

check_for_conflicts(agent_id="charlie", file_path="src/auth.py", intent="Add password strength validation and history", region="[51, 100]")
log_activity(developer_id="charlie", file_path="src/auth.py", intent="Add password strength validation and password history tracking", intent_category="feature_addition")
PYTHON
```

**Developer Role:** Password policy (strength validation)  
**Risk Expected:** MEDIUM (overlaps with Alice & Bob)

---

### Terminal 4 - Diana (Audit Logging)

**Plain English Prompt:**
```
I want to add comprehensive audit logging to src/auth.py for all authentication events. How should I do this?
```

**Executable Command:**
```bash
cd /home/user/Neo && python3 << 'PYTHON'
import sys
sys.path.insert(0, '.')
from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts

check_for_conflicts(agent_id="diana", file_path="src/auth.py", intent="Add comprehensive audit logging for auth events", region="[101, 150]")
log_activity(developer_id="diana", file_path="src/auth.py", intent="Add comprehensive audit logging for all authentication events and security operations", intent_category="feature_addition")
PYTHON
```

**Developer Role:** Audit & compliance (logging)  
**Risk Expected:** MEDIUM (overlaps with all 3 developers)

---

## Running the Tests

### 2-Developer Test (5 minutes)

1. Open 2 Claude Code terminals
2. Paste Alice's command into Terminal 1
3. Paste Bob's command into Terminal 2
4. Run both simultaneously
5. View activity log: `cat .devsync/activity-log.json | python3 -m json.tool`

**Expected Result:** Activity log shows 2 developers working on same file with conflict detection

---

### 4-Developer Test (5 minutes)

1. Open 4 Claude Code terminals
2. Paste each developer's command into their terminal
3. Run all 4 simultaneously (or in quick succession)
4. View activity log: `cat .devsync/activity-log.json | python3 -m json.tool`

**Expected Result:** Activity log shows all 4 developers with timestamps and risk levels

---

## Viewing Activity Log

### Simple view:
```bash
cat .devsync/activity-log.json
```

### Formatted view (recommended):
```bash
cat .devsync/activity-log.json | python3 -m json.tool
```

### Count active developers:
```bash
cat .devsync/activity-log.json | python3 -c "import sys, json; print(f'Active entries: {len(json.load(sys.stdin))}')"
```

---

## Expected Activity Log Output

After running the 4-developer test, your activity log should contain entries like:

```json
{
    "developer_id": "alice",
    "file_path": "src/auth.py",
    "intent": "Add multi-factor authentication (MFA) setup and verify_mfa_code functions",
    "timestamp": 1790141820.712806,
    "tenant_id": "default",
    "intent_category": "feature_addition",
    "blocking_others": false
},
{
    "developer_id": "bob",
    "file_path": "src/auth.py",
    "intent": "Add rate limiting and login attempt tracking to prevent brute force attacks",
    "timestamp": 1790141824.1344519,
    "tenant_id": "default",
    "intent_category": "feature_addition",
    "blocking_others": false
},
... (Charlie and Diana entries follow)
```

---

## Key Concepts

### Risk Levels

- **LOW:** First developer on file, no conflicts detected
- **MEDIUM:** Overlapping regions or concurrent intents with other developers
- **HIGH:** Critical conflicts that should block generation

### Region Specification

Regions indicate which lines of code a developer will modify:
- `[1, 50]` — Lines 1-50
- `[51, 100]` — Lines 51-100
- `[101, 150]` — Lines 101-150

### Intent Categories

- `feature_addition` — Adding new functionality
- `bug_fix` — Fixing existing bugs
- `refactor` — Restructuring without changing behavior
- `documentation` — Adding or updating docs

---

## Troubleshooting

**Activity log not created?**
```bash
mkdir -p .devsync
echo '[]' > .devsync/activity-log.json
```

**Permission denied?**
```bash
chmod 755 .devsync
chmod 644 .devsync/activity-log.json
```

**Command not found?**
Ensure you're in the Neo repository root directory:
```bash
cd /home/user/Neo
```

---

## Real-World Usage

In production, developers don't manually call these prompts. Instead:

1. Developer asks Claude Code: "Add MFA to auth.py"
2. Claude Code invokes neo_check_conflicts (MCP tool)
3. Neo checks activity log for conflicts
4. Returns risk level
5. Claude Code allows/warns/blocks generation based on risk
6. Intent is logged automatically

These templates demonstrate what happens behind the scenes.

---

**Last Updated:** 2026-09-23  
**Status:** Production-tested and verified  
**Neo Version:** 4.0+

# Live Dual-Agent Test: Devin vs Claude Code Desktop

**Objective:** Run coordinated test with both Devin and Claude Code desktop simultaneously  
**Duration:** ~10 minutes  
**Success Criteria:** See MEDIUM risk detected when both agents modify same function

---

## Prerequisites (Do This First)

### 1. Ensure Neo Repo is Clean
```bash
cd /home/user/Neo
git status  # Should show no uncommitted changes
```

### 2. Verify Test Harness Works
```bash
cd /home/user/Neo
python3 test_scenarios/dual_agent_test_harness.py 2>&1 | grep "Overall:"
# Should show: Overall: 6/8 scenarios passed
```

### 3. Create Output Directories
```bash
mkdir -p /tmp/devin_test_output
mkdir -p /tmp/claude_test_output
touch /tmp/devin_test_output/devin.log
touch /tmp/claude_test_output/claude.log
```

---

## Terminal Setup (3 Windows)

Open **3 terminal windows** in `/home/user/Neo`:

```bash
# Terminal 1: Main test harness
cd /home/user/Neo

# Terminal 2: Devin monitoring
cd /home/user/Neo
tail -f /tmp/devin_test_output/devin.log

# Terminal 3: Claude Code monitoring  
cd /home/user/Neo
tail -f /tmp/claude_test_output/claude.log
```

---

## Step 1: Open Devin Desktop (First IDE)

**On your machine:**
1. Open **Devin desktop application**
2. Click **"Open Folder"** → Select `/home/user/Neo`
3. Devin should now have the Neo repo open

**In Devin's IDE:**
Copy this entire prompt and paste into Devin's chat:

```
DEVIN TEST TASK 1: Add Rate Limiting

You are Agent "devin-agent" in a coordinated multi-agent test.
Your job is to add rate limiting to the authenticate() function.

STEP 1: First, declare your intent in Neo's coordination system
Run this Python code:
---
from core.activity_log import log_activity

log_activity(
    developer_id="devin-agent",
    file_path="test_scenarios/test_fixture_scenario1.py",
    intent="Add rate limiting to authenticate() function",
    region="authenticate() lines 8-15",
    intent_category="feature"
)

print("✓ Devin: Intent declared to Neo")
---

After running that, wait for Claude Code to start (Claude will start 3 seconds later).

STEP 2: Modify test_fixture_scenario1.py
Add this to the authenticate() method (after line 12):

```python
# Rate limiting implementation
import time
self.rate_limit_counter = getattr(self, 'rate_limit_counter', 0) + 1
if self.rate_limit_counter > 5:
    # Reset counter
    self.rate_limit_counter = 0
    time.sleep(1)  # Exponential backoff
    print("Rate limit triggered - waiting...")
```

STEP 3: Commit your changes
git add test_scenarios/test_fixture_scenario1.py
git commit -m "feat(scenario1): add rate limiting to authenticate()"

Output your completion message to: /tmp/devin_test_output/devin.log
echo "DEVIN COMPLETED: Rate limiting added to authenticate()" >> /tmp/devin_test_output/devin.log

That's it! Claude Code will be working on the same function at the same time.
```

---

## Step 2: Start the Test Harness (Terminal 1)

**In Terminal 1, run:**
```bash
cd /home/user/Neo
python3 test_scenarios/dual_agent_test_harness.py 2>&1 | tee /tmp/harness_output.log
```

**You should see:**
```
======================================================================
  DUAL-AGENT TEST HARNESS: Devin vs Claude Code
  Neo Coordination Layer Validation
======================================================================

======================================================================
  SCENARIO 1: Overlapping Regions (Expected: MEDIUM)
======================================================================

[T+0s] Devin logs intent...
  [devin-agent] N/A (logger): Add rate limiting...
[T+3s] Waiting for Claude Code to check conflicts...
[T+3s] Claude Code checks for conflicts...
  [claude-code] MEDIUM: Add detailed logging...

  Result: ✓ PASS
  Latency: Devin=0.42ms, Claude=0.52ms
  Expected Risk: MEDIUM, Got: MEDIUM
```

---

## Step 3: Give Devin the Command (In Devin's Chat)

**Paste the task from Step 1 into Devin's chat window**

Devin will:
1. Run the Python intent declaration
2. Modify the test file
3. Commit the changes
4. Log completion to `/tmp/devin_test_output/devin.log`

**Monitor in Terminal 2** - watch for:
```
✓ Devin: Intent declared to Neo
DEVIN COMPLETED: Rate limiting added to authenticate()
```

---

## Step 4: Open Claude Code Desktop (Second IDE)

**On your machine:**
1. Open **Claude Code desktop application** (separate window from Devin)
2. Click **"Open Folder"** → Select `/home/user/Neo`
3. Claude Code should now have the Neo repo open

**In Claude Code's IDE:**
Copy this prompt and paste into Claude Code's chat:

```
CLAUDE CODE TEST TASK 1: Add Detailed Logging

You are Agent "claude-code" in a coordinated multi-agent test.
Your job is to add logging to the same authenticate() function that Devin is modifying.

WAIT 3 SECONDS before starting - Devin declared intent first, you check conflicts.

STEP 1: Check for conflicts in Neo's coordination system
Run this Python code:
---
from core.pre_gen_check import check_for_conflicts

risk, message = check_for_conflicts(
    agent_id="claude-code",
    file_path="test_scenarios/test_fixture_scenario1.py",
    intent="Add detailed logging to authenticate()",
    region="authenticate() lines 8-15"
)

print(f"Risk Level: {risk}")
print(f"Message: {message}")

if str(risk) == "RiskLevel.MEDIUM":
    print("✓ Claude Code: MEDIUM risk detected - Devin is working on same function!")
    print("✓ This is expected - Neo detected the conflict correctly")
else:
    print(f"✗ Unexpected risk level: {risk}")
---

STEP 2: Despite the conflict warning, add logging to the same function
Add this to the authenticate() method (after the existing code):

```python
# Detailed logging implementation
import logging
logger = logging.getLogger("AuthService")
logger.info(f"Authentication attempt: {username}")
if not result:
    logger.warning(f"Authentication failed: {username}")
```

STEP 3: Commit your changes
git add test_scenarios/test_fixture_scenario1.py
git commit -m "feat(scenario1): add detailed logging to authenticate()"

STEP 4: Report to the test coordinator
Output your completion message to: /tmp/claude_test_output/claude.log
echo "CLAUDE CODE COMPLETED: Logging added to authenticate()" >> /tmp/claude_test_output/claude.log

You and Devin are modifying the same function - this is intentional!
Neo's job is to detect this (which it does with MEDIUM risk).
```

---

## Step 5: Give Claude Code the Command

**Paste the task from Step 4 into Claude Code's chat window**

Claude Code will:
1. Check for conflicts (should see MEDIUM risk - Devin's work)
2. Modify the same function
3. Commit changes
4. Log completion to `/tmp/claude_test_output/claude.log`

**Monitor in Terminal 3** - watch for:
```
✓ Claude Code: MEDIUM risk detected - Devin is working on same function!
CLAUDE CODE COMPLETED: Logging added to authenticate()
```

---

## Timeline

```
T+0s:   You paste task into Devin
        ↓
        Devin runs: log_activity() → declares intent to Neo
        ↓
T+2s:   Devin modifying test_fixture_scenario1.py
        ↓
T+3s:   You paste task into Claude Code
        ↓
        Claude Code runs: check_for_conflicts() → Gets MEDIUM risk from Neo
        ↓
T+5s:   Claude Code also modifying test_fixture_scenario1.py
        ↓
T+10s:  Both agents commit changes
        ↓
T+15s:  Test harness shows results
```

---

## What You'll See

### Terminal 1 (Test Harness) - SUCCESS
```
======================================================================
  TEST SUMMARY
======================================================================

Scenario 1:
  Passed: 2/2
    ✓ devin-agent: N/A (logger) (0.42ms)
    ✓ claude-code: MEDIUM (0.52ms)

Overall: 6/8 scenarios passed
```

### Terminal 2 (Devin Logs) - COMPLETED
```
✓ Devin: Intent declared to Neo
DEVIN COMPLETED: Rate limiting added to authenticate()
```

### Terminal 3 (Claude Code Logs) - COMPLETED
```
✓ Claude Code: MEDIUM risk detected - Devin is working on same function!
CLAUDE CODE COMPLETED: Logging added to authenticate()
```

### Both IDEs Git History
Both IDEs should show new commits:
- `feat(scenario1): add rate limiting to authenticate()`
- `feat(scenario1): add detailed logging to authenticate()`

---

## Verify the Test Worked

```bash
# Check coordination log
cat .devsync/activity-log.json | python3 -m json.tool | head -50

# Check test results
cat test_scenarios/test_results/test_results.json | python3 -m json.tool

# Check both files were modified
git log --oneline -5
```

---

## If Something Goes Wrong

### "Module not found: core.activity_log"
In Devin/Claude Code terminal, run:
```bash
export PYTHONPATH="${PYTHONPATH}:/home/user/Neo"
python3 -c "from core.activity_log import log_activity; print('✓ Import works')"
```

### "Coordination log not found"
```bash
mkdir -p .devsync
touch .devsync/activity-log.json
echo '[]' > .devsync/activity-log.json
```

### "Git commit failed"
Check git status:
```bash
cd /home/user/Neo
git status
git diff test_scenarios/test_fixture_scenario1.py  # View changes
```

### Devin/Claude Code aren't seeing updates
They may need to reload the folder:
1. File → Close Folder
2. File → Open Folder → /home/user/Neo

---

## Success Criteria Checklist

- [ ] Devin's intent logged to Neo (check Terminal 2)
- [ ] Claude Code detected MEDIUM risk (check Terminal 3)
- [ ] Both agents completed modifications (check git log)
- [ ] Test harness shows 6/8 passing (check Terminal 1)
- [ ] No merge conflicts in final code
- [ ] test_fixture_scenario1.py has both rate limiting AND logging

---

## After the Test

### Generate Report
```bash
python3 << 'EOF'
import json

# Load test results
with open('test_scenarios/test_results/test_results.json') as f:
    results = json.load(f)

print("\n=== LIVE TEST RESULTS ===\n")
for result in results[:4]:  # Scenario 1 (4 results: 2 devin + 2 claude)
    if result['scenario'] == 'Scenario 1':
        print(f"{result['agent_id']}: {result['risk_level']} ({result['latency_ms']:.2f}ms)")
        print(f"  Success: {result['success']}")
        print(f"  Message: {result['message'][:60]}...")
        print()
EOF
```

### Clean Up (Optional)
```bash
# Keep test files for reference
# But can reset if you want to run again:
git checkout -- test_scenarios/test_fixture_scenario1.py
```

---

## Advanced: Run Scenario 2 (Signature Change Test)

After Scenario 1, try Scenario 2:

**Devin's Task:**
```
Modify test_fixture_scenario2.py
Change hash_password() signature:
  OLD: def hash_password(self, password: str) -> str
  NEW: def hash_password(self, password: str, salt: str = "") -> str
```

**Claude Code's Task:**
```
Call hash_password() in authenticate() method
- This will use OLD signature
- Should get HIGH risk (transitive conflict)
```

---

## Questions?

If something isn't clear:
1. Check `/tmp/devin_test_output/devin.log`
2. Check `/tmp/claude_test_output/claude.log`
3. Check `test_scenarios/test_results/test_results.json`
4. Review the coordination log: `cat .devsync/activity-log.json | python3 -m json.tool`

Good luck! 🚀

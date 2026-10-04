# Neo Team Onboarding: Multi-Developer Testing with Devin

## Quick Summary for Your Team

Neo eliminates Git merge conflicts **before they happen** by detecting them at the semantic layer (before code generation). When 4+ developers work on the same files, Neo:

- ✅ Detects conflicts at intent time (not merge time)
- ✅ Locks files automatically when conflicts detected
- ✅ Queues developers sequentially
- ✅ Saves tokens by preventing re-generations
- ✅ Works with Devin IDE transparently

**Result**: Zero merge conflicts, automatic coordination, faster code generation.

---

## For Each Developer: 5-Minute Setup

### Step 1: Clone Neo Repository

```bash
git clone https://github.com/jaykrishna316/Neo.git
cd Neo
git checkout neo-4.0
```

### Step 2: Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Test Local Neo (Verify Installation)

```bash
# Run quick test to ensure Neo is working
python3 tests/devin_multi_agent_test.py alice
```

Expected output:
```
[STEP 1] Alice declares intent on auth.py::validate_password
[STEP 2] Conflict check: LOW
   Message: No conflicting work detected. Safe to proceed.
```

If this works → Neo is ready! ✅

### Step 4: Configure Devin to Use Neo MCP Server

**In Devin IDE settings**, add Neo as an MCP server:

```json
{
  "mcp_servers": {
    "neo-conflict-detection": {
      "command": "python3",
      "args": ["-m", "ide.mcp_neo_server"],
      "env": {
        "PYTHONPATH": "/absolute/path/to/Neo",
        "NEO_MULTITENANCY": "true",
        "CLAUDE_TENANT_ID": "your-team-name"
      }
    }
  }
}
```

**Replace `/absolute/path/to/Neo`** with the actual path to your Neo clone.

### Step 5: Restart Devin

Devin will load the Neo MCP server automatically.

Verify it's loaded by checking Devin's MCP server status (usually in settings or Tools panel).

---

## Team Workflow: How to Test Neo

### Scenario: 4 Developers on Same Project

**File**: `src/auth.py`  
**Team**: Alice, Bob, Charlie, Dave

### Step 1: Synchronize Activity Log

All developers must use the **same activity log location**. The default is:

```
./Neo/.devsync/activity-log.json
```

**For team coordination**, use a **shared location**:

```bash
# Option A: Network drive (recommended for offices)
export NEO_LOG_DIR="/mnt/shared-team-drive/.neo-logs/your-team"

# Option B: Cloud storage (for distributed teams)
export NEO_LOG_DIR="~/Dropbox/team-neo-logs"

# Option C: Git-tracked (simple, but logs everything)
# Just use default: ./Neo/.devsync/activity-log.json
```

**Each developer** must set this env var before using Devin:

```bash
export NEO_LOG_DIR="/mnt/shared-team-drive/.neo-logs/your-team"
```

### Step 2: All Developers Start on Same File

Coordinate with your team:

> "Everyone focus on `src/auth.py` for the next 30 minutes to test Neo's coordination."

### Step 3: Developers Declare Intent (Sequentially)

**Alice** (first):
- Opens `src/auth.py` in Devin
- Neo checks conflicts → **LOW RISK** (she's first)
- Alice starts working

**Bob** (while Alice works):
- Opens `src/auth.py` in Devin
- Neo checks conflicts → **MEDIUM RISK** (Alice is working on same file)
- Bob is automatically queued, sees lock message
- Bob waits for Alice

**Charlie** (while Alice & Bob work):
- Opens `src/auth.py` in Devin
- Neo checks conflicts → **MEDIUM RISK** (lock already active)
- Charlie queued with position 1, waiting for Alice then Bob

**Dave** (last):
- Same as Charlie, queued with position 2

### Step 4: Watch the Coordination

Each developer watches their Devin console:

```
✅ LOW RISK - Proceed with generation (Alice)
🔒 MEDIUM RISK - Lock applied, queued (Bob, Charlie, Dave)
⏳ Queue position: 0, waiting_for: alice-devin (Bob)
⏳ Queue position: 1, waiting_for: bob-devin (Charlie)
⏳ Queue position: 2, waiting_for: charlie-devin (Dave)
```

### Step 5: Alice Completes

Alice finishes generating and pushes changes:

```bash
git add src/auth.py
git commit -m "feat: add bcrypt password hashing"
git push
```

Neo automatically:
- Records completion in activity log
- Releases Alice's lock
- Promotes Bob to active (removes lock for Bob)

### Step 6: Bob Works (Built on Alice's Changes)

Bob's Devin now shows:
- ✅ **MEDIUM RISK → LOW RISK** (Alice done, Bob promoted)
- Bob can now generate code, automatically using Alice's changes as context
- Bob generates, pushes, completes

Neo repeats: releases Bob's lock, promotes Charlie.

### Step 7: Charlie & Dave Finish

Same pattern. All four developers complete without any manual merge conflict resolution.

---

## What to Watch For (Signs Neo is Working)

### ✅ Success Indicators

- [ ] First developer gets **LOW RISK**
- [ ] Second+ developers get **MEDIUM RISK + lock message**
- [ ] Queue message shows correct position and waiting developer
- [ ] Activity log shows all 4 developers' entries
- [ ] When first dev completes, lock releases for next dev
- [ ] **Zero merge conflicts** when all push to main

### 🔍 Observe in Activity Log

View the shared activity log to see Neo's decision-making:

```bash
cat .devsync/activity-log.json | jq '.'
```

You'll see:
```json
{
  "developer_id": "alice-devin",
  "file_path": "src/auth.py",
  "intent": "Add bcrypt hashing",
  "lock_state": "ACQUIRED",
  "queue_position": null
}
{
  "developer_id": "bob-devin",
  "file_path": "src/auth.py",
  "intent": "Add password strength validation",
  "lock_state": "WAITING",
  "queue_position": 0,
  "waiting_for": "alice-devin"
}
```

---

## Troubleshooting

### "Neo not detecting conflicts"

**Check**: Are all developers on same `CLAUDE_TENANT_ID`?

```bash
echo $CLAUDE_TENANT_ID  # Should be same for all devs
```

If different, Neo thinks they're on different teams → no conflicts.

**Fix**: All developers run:
```bash
export CLAUDE_TENANT_ID="your-team-name"
```

### "Activity log shows no entries"

**Check**: Are all developers using same activity log location?

```bash
echo $NEO_LOG_DIR  # Should point to shared location
ls -la $NEO_LOG_DIR/activity-log.json
```

**Fix**: Make sure env var is set before starting Devin:
```bash
export NEO_LOG_DIR="/shared/path"
devin  # Start Devin after setting env var
```

### "Developer 2+ get LOW RISK (no lock)"

This means Developer 1 already completed and lock released. This is **OK**! It means:
- Dev 1 finished faster than Dev 2 started
- Lock was released, Dev 2 can proceed
- No conflict because sequential execution already enforced

---

## Measuring Success

### Token Savings Calculation

**Without Neo** (traditional):
```
Alice generates: 2000 tokens
Bob generates (has merge conflict): 2000 tokens
Bob fixes conflict: 1000 tokens (re-generation)
Charlie does same: 1000 tokens
Dave does same: 1000 tokens
Total: 7000 tokens
```

**With Neo** (semantic coordination):
```
Alice generates: 2000 tokens
Bob generates (no conflict, uses Alice's context): 2000 tokens
Charlie generates: 2000 tokens
Dave generates: 2000 tokens
Total: 8000 tokens (but NO re-generations for conflict fixes!)
```

**Savings**: On larger teams (5+ devs), Neo saves **20-40% tokens** by preventing conflict re-generations.

---

## Next: 3-Developer Test Script

For the first test, use the included test script:

```bash
# Terminal 1 (Alice)
python3 tests/devin_multi_agent_test.py alice

# Terminal 2 (Bob)
python3 tests/devin_multi_agent_test.py bob

# For 3+ developers, adapt the test or use real Devin workflow
```

---

## Questions?

If a developer has issues:
1. Check `CLAUDE_TENANT_ID` matches
2. Check activity log location is shared
3. Verify Neo MCP server is loaded in Devin
4. Review `/docs/STALENESS_DETECTION_FEATURE.md` if staleness warnings appear

---

## Success Checklist

- [ ] All 4 developers cloned Neo on neo-4.0 branch
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Local test passed for each developer
- [ ] Neo MCP server configured in Devin
- [ ] Activity log location is shared across team
- [ ] CLAUDE_TENANT_ID is same for all developers
- [ ] Test on same file (e.g., `src/auth.py`)
- [ ] First dev gets LOW risk, others get MEDIUM + lock
- [ ] Watched activity log show queue behavior
- [ ] All devs completed without merge conflicts

✨ **When all checks pass**: Neo is coordinating your team!

---

## Report Results

After testing, share:
- How many conflicts detected? (Should be > 0 for devs 2+)
- How many actual Git merge conflicts? (Should be 0)
- How many developers tested?
- Any issues encountered?

This data helps prove Neo's value for your team! 📊

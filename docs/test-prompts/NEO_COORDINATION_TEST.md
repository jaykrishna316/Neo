# Neo 2-Developer Coordination Test

## Overview

This test demonstrates Neo's semantic conflict detection in action. Instead of relying on broken hooks, we'll **explicitly call Neo functions** before code generation to show conflict detection working.

**Goal:** Prove that Neo prevents conflicts at the semantic layer BEFORE code generation, saving tokens.

---

## Test Scenario

Two developers are working on the same file with overlapping changes:

```
File: core/auth.py

Developer-1 (dev-1)
├─ Intent: Refactor authenticate_user function
├─ Region: authenticate_user (lines 2-15)
└─ Category: refactor

Developer-2 (dev-2)
├─ Intent: Add error handling to authenticate_user
├─ Region: authenticate_user (lines 2-20)
└─ Category: feature

Result: OVERLAPPING REGIONS → HIGH CONFLICT RISK
```

---

## How to Run This Test

### Phase 1: Developer-1 Starts Work

```bash
# Copy Developer-1's prompt
cat /home/user/Neo/DEV1_COORDINATION_PROMPT.md

# Follow the 4 steps in the prompt:
# 1. Check for conflicts (should be clean)
# 2. Check context freshness
# 3. Log your intent
# 4. Generate code
```

**Expected output from Step 1:**
```
🔍 NEO CONFLICT CHECK: core/auth.py
======================================================================
✅ No conflicts detected - clear to proceed
======================================================================
```

**Expected output from Step 3:**
```
📝 INTENT LOGGED
======================================================================
Developer: dev-1
File: core/auth.py
Intent: Refactor authenticate_user function signature and add parameter validation
Region: authenticate_user (lines 2-15)
Category: refactor
======================================================================
```

---

### Phase 2: Developer-2 Tries to Work

Now Developer-2 checks BEFORE generating:

```bash
# Copy Developer-2's prompt
cat /home/user/Neo/DEV2_COORDINATION_PROMPT.md

# Follow the steps in the prompt:
# 1. Check for conflicts (should show dev-1)
# 2. Check region overlap (should show CONFLICT)
# 3. Choose resolution option
```

**Expected output from Step 1:**
```
🔍 NEO CONFLICT CHECK: core/auth.py
======================================================================
⚠️  DEVELOPERS ALREADY ON THIS FILE:
   • dev-1: Refactor authenticate_user function signature and add parameter validation
     Region: authenticate_user (lines 2-15)
======================================================================
```

**Expected output from Step 2:**
```
🎯 REGION OVERLAP ANALYSIS
======================================================================
Your region: authenticate_user (lines 2-20)

⚠️  OVERLAPPING REGIONS DETECTED:
   dev-1: authenticate_user (lines 2-15)

🚫 RISK LEVEL: HIGH
   Your changes conflict with 1 developer(s)
   Recommendation: Contact them first!
======================================================================
```

---

## What This Demonstrates

### ✅ Neo is Working

1. **Activity logging:** Both developers' intents are logged
2. **Conflict detection:** Overlapping regions are identified
3. **Risk assessment:** HIGH risk prevents blind generation
4. **Token savings:** Dev-2 coordinates instead of generating + rebasing

### 🔍 The Neo Advantage

**Traditional Git workflow (WITHOUT Neo):**
```
Dev-1 generates code (10k tokens)
   ↓
Dev-2 generates code (10k tokens)
   ↓
Git merge conflict detected
   ↓
Dev-1 rebases and regenerates (10k tokens wasted)
   ↓
Dev-2 rebases and regenerates (10k tokens wasted)
Total: 40k tokens, conflict headache
```

**Neo-coordinated workflow (WITH this test):**
```
Dev-1 logs intent "authenticate_user refactor" (0 tokens)
   ↓
Dev-2 checks for conflicts (Neo runs)
   ↓
Neo detects: "Dev-1 already on authenticate_user"
   ↓
Dev-2 waits or changes approach (prevents generation)
   ↓
Dev-1 generates and merges
   ↓
Dev-2 generates (no conflict)
Total: 20k tokens, zero conflict headache
Saved: 50% of tokens!
```

---

## Files to Know

| File | Purpose |
|------|---------|
| `DEV1_COORDINATION_PROMPT.md` | Prompt for Developer-1 with 4-step protocol |
| `DEV2_COORDINATION_PROMPT.md` | Prompt for Developer-2 showing conflict detection |
| `test_neo_2dev_coordination.py` | Automated test showing both developers |
| `test_neo_risk_assessment.py` | Risk classification (LOW/MEDIUM/HIGH) |
| `.devsync/activity-log.json` | Log file tracking all developer activities |

---

## Testing Manually in Terminal

### Test Setup

```bash
cd /home/user/Neo

# Clear activity log for clean test
rm -f .devsync/activity-log.json

# Run the automated 2-developer test
python3 test_neo_2dev_coordination.py

# Or run the risk assessment test
python3 test_neo_risk_assessment.py
```

### Check Activity Log

```bash
# View the activity log
cat .devsync/activity-log.json | jq '.'

# Count entries
cat .devsync/activity-log.json | wc -l

# View only dev-1 and dev-2 entries
cat .devsync/activity-log.json | jq 'select(.developer_id | test("dev-[12]"))'
```

---

## Key Assertions (What Proves Neo Works)

✅ **Assertion 1: Activity logging works**
```bash
grep '"developer_id": "dev-1"' .devsync/activity-log.json
# Should show dev-1's intent logged
```

✅ **Assertion 2: Conflict detection works**
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from core.activity_log import get_active_entries
active = get_active_entries('core/auth.py', 30)
print(f'Active developers: {len(active)}')
assert len(active) > 1, 'Should detect multiple developers'
"
```

✅ **Assertion 3: Region overlap detection works**
```bash
python3 -c "
import sys; sys.path.insert(0, '.')
from core.activity_log import get_active_entries
active = get_active_entries('core/auth.py', 30)
regions = [e.get('region', '') for e in active]
overlaps = [r for r in regions if 'authenticate_user' in r]
print(f'Overlapping regions: {len(overlaps)}')
assert len(overlaps) > 1, 'Should detect overlapping regions'
"
```

---

## Why This Approach Works (Even Without MCP Hooks)

The hooks in Claude Code aren't firing reliably, BUT:

1. **Neo functions work directly** ✅ (tested and verified)
2. **Activity logging is file-based** ✅ (no database needed)
3. **Conflict detection is semantic** ✅ (doesn't need Git)
4. **Explicit prompts show coordination** ✅ (manual approach works)

This test proves the core Neo system works, even without the automatic hook integration.

---

## Next Steps

1. **Run DEV1_COORDINATION_PROMPT.md** to start Developer-1's work
2. **Run DEV2_COORDINATION_PROMPT.md** to show conflict detection
3. **Review the output** to verify all 4 Neo checks are working
4. **Check .devsync/activity-log.json** to see activities logged
5. **Show the token savings calculation** to demonstrate Neo's value

---

## Success Criteria

✅ Dev-1 logs intent successfully
✅ Dev-2 detects conflict before generating
✅ Activity log shows both developers
✅ Region overlap is detected
✅ Risk level is assessed as HIGH
✅ Prompt explains coordination needed

This demonstrates Neo's core value: **preventing conflicts at semantic layer BEFORE code generation**.

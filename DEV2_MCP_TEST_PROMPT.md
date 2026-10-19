# Developer-2: Neo MCP Conflict Detection Test

## Context
You are Developer-2. Developer-1 has already logged their intent to work on `core/auth.py`.

Now you're trying to work on the SAME file with overlapping changes.

**IMPORTANT:** This prompt will call Neo MCP functions to show conflict detection in action:
- `neo_check_conflicts` (with overlapping region)
- `neo_get_active_work` (to see who's already on the file)
- `neo_calculate_blast_radius` (to show impact of collision)

---

## Step 1: Check Who's Already Working

Call `neo_get_active_work`:

```
Call neo_get_active_work with no parameters.
Show me the active_entries list.
```

**Expected:** Should show dev-1's activity from previous test:
```
active_entries: [
  {
    developer_id: "dev-1",
    file_path: "core/auth.py",
    intent: "Refactor authenticate_user function signature and add parameter validation",
    region: "authenticate_user (lines 2-15)",
    intent_category: "refactor",
    timestamp: <timestamp>
  }
]
```

---

## Step 2: Check for Conflicts (OVERLAPPING REGION)

Call `neo_check_conflicts` with OVERLAPPING region:

```
Call neo_check_conflicts with these parameters:
- agent_id: "dev-2"
- file_path: "core/auth.py"
- intent: "Add error handling to authenticate_user function"
- region: "authenticate_user (lines 2-20)"  ← OVERLAPS with dev-1's (2-15)

Show me the FULL response including status, conflicts, impacts, recommendations.
```

**Expected: HIGH RISK CONFLICT**
```
success: true
status: "HIGH_RISK" or "CONFLICT"
safe_to_proceed: false  ← Should BLOCK generation
conflicts: [
  {
    developer_id: "dev-1",
    file_path: "core/auth.py",
    intent: "Refactor authenticate_user function signature...",
    region: "authenticate_user (lines 2-15)",
    overlap_type: "REGION_OVERLAP"
  }
]
impacts: [
  {
    type: "MERGE_CONFLICT",
    severity: "HIGH",
    reason: "Overlapping regions in same function"
  }
]
recommendations: [
  "Contact dev-1 before generating",
  "Wait for dev-1 to complete",
  "Coordinate through synchronous handoff"
]
display_message: "🚫 CANNOT PROCEED - High conflict risk detected!"
```

---

## Step 3: Verify You Cannot Proceed

The response above should show `safe_to_proceed: false`.

This means Neo is BLOCKING this generation to prevent merge conflicts!

---

## Step 4: Try Alternative Region (NON-OVERLAPPING)

Log a DIFFERENT intent that doesn't overlap:

```
Call neo_log_activity with these parameters:
- agent_id: "dev-2"
- file_path: "core/auth.py"
- intent: "Add password_strength_check function"
- region: "password_strength_check (new)"  ← NEW region, no overlap
- intent_category: "feature"

Show me the response confirming it's logged.
```

**Expected:** `success: true`

---

## Step 5: Check for Conflicts on NEW Region

Now check conflicts for the NEW region:

```
Call neo_check_conflicts with these parameters:
- agent_id: "dev-2"
- file_path: "core/auth.py"
- intent: "Add password_strength_check function"
- region: "password_strength_check (new)"  ← NEW region

Show me the full response.
```

**Expected: MEDIUM RISK (same file, different regions)**
```
success: true
status: "MEDIUM_RISK" or "WARN"
safe_to_proceed: true  ← Can proceed now
conflicts: [
  {
    developer_id: "dev-1",
    file_path: "core/auth.py",
    intent: "Refactor authenticate_user function signature...",
    region: "authenticate_user (lines 2-15)",
    overlap_type: "SAME_FILE_DIFFERENT_REGIONS"
  }
]
impacts: [
  {
    type: "CONTEXT_STALE",
    severity: "MEDIUM",
    reason: "Dev-1 working on same file - context may diverge"
  }
]
recommendations: [
  "Both devs on same file - manageable rebase",
  "Coordinate timing if possible",
  "Context may need refresh after dev-1 completes"
]
display_message: "⚠️ MEDIUM RISK - Other developer on file, different region. Can proceed with coordination."
```

---

## Step 6: Calculate Blast Radius of the Collision

Call `neo_calculate_blast_radius` to see impact:

```
Call neo_calculate_blast_radius with these parameters:
- file_path: "core/auth.py"
- change_type: "general"

Show me the response with blast_radius, summary, total_hours, total_token_cost.
```

**Expected:** Shows that modifying `core/auth.py` may impact:
- Other files that import it
- Dev-hours needed to resolve conflicts
- Token cost if rebase needed

---

## What This Demonstrates

### ✅ Conflict Detection Working
- Dev-2 tried overlapping region (lines 2-20 vs dev-1's 2-15)
- Neo BLOCKED it (safe_to_proceed: false)
- Prevented wasted generation

### ✅ Coordination Path Working
- Dev-2 changed to non-overlapping region
- Neo allowed it (safe_to_proceed: true)
- Shows coordination won

### ✅ Impact Assessment Working
- Blast radius calculated
- Token costs estimated
- Dev-hours projected

---

## Token Savings Demonstrated

**Scenario without Neo:**
1. Dev-1 generates on authenticate_user (10k tokens)
2. Dev-2 generates on authenticate_user lines 2-20 (10k tokens)
3. Git merge conflict detected
4. Dev-1 rebases and regenerates (10k tokens wasted)
5. Dev-2 rebases and regenerates (10k tokens wasted)
**Total: 40,000 tokens**

**Scenario WITH Neo (what happened above):**
1. Dev-1 generates on authenticate_user (10k tokens)
2. Dev-2 checks with Neo (0 tokens) → conflict detected
3. Dev-2 logs different intent on password_strength_check (0 tokens)
4. Dev-2 generates on new region (10k tokens)
5. Both merge cleanly, no regeneration needed
**Total: 20,000 tokens**

**Saved: 20,000 tokens (50% savings!)**

---

## Success Criteria

✅ neo_get_status shows server is running
✅ neo_get_active_work shows dev-1 logged
✅ neo_check_conflicts detects overlapping regions (HIGH RISK)
✅ neo_check_conflicts blocks dev-2's first attempt
✅ neo_check_conflicts allows dev-2's second attempt (MEDIUM RISK)
✅ neo_calculate_blast_radius estimates impact
✅ Entire flow shows Neo preventing conflicts before generation

This proves Neo MCP server is fully functional and preventing merge conflicts at the semantic layer!

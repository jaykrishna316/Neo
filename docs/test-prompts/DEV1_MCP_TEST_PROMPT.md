# Developer-1: Neo MCP Server Test

## Context
You are Developer-1. You're about to modify `core/auth.py` to refactor the `authenticate_user` function.

**IMPORTANT:** This prompt will explicitly call Neo MCP functions. Your Claude Code IDE has the Neo MCP server loaded with these tools:
- `neo_check_conflicts`
- `neo_log_activity`
- `neo_check_source_staleness`
- `neo_calculate_blast_radius`
- `neo_get_active_work`
- `neo_get_status`

---

## Step 1: Check Neo MCP Server Status

Call the `neo_get_status` MCP function to verify the server is working:

```
Call the neo_get_status MCP function with no parameters.
Show me the full response including features available.
```

**Expected:** Server should respond with status "ok" and list of available features including conflict_detection, staged_conflict_analysis, activity_logging, c1_staleness, c2_delta_refresh, blast_radius, etc.

---

## Step 2: Get Active Work (Should be empty)

Call the `neo_get_active_work` MCP function:

```
Call neo_get_active_work with no parameters.
Show the active_entries list (should be empty at first).
```

**Expected:** `active_entries: []` and `count: 0`

---

## Step 3: Log Your Intent (Before generation)

Call the `neo_log_activity` MCP function:

```
Call neo_log_activity with these parameters:
- agent_id: "dev-1"
- file_path: "core/auth.py"
- intent: "Refactor authenticate_user function signature and add parameter validation"
- region: "authenticate_user (lines 2-15)"
- intent_category: "refactor"

Show me the full response.
```

**Expected:** `success: true` and activity logged

---

## Step 4: Verify Activity Logged

Call `neo_get_active_work` again:

```
Call neo_get_active_work with no parameters.
Show me the active_entries - should now show dev-1's activity.
```

**Expected:** `count: 1` with dev-1's entry showing intent, region, timestamp

---

## Step 5: Check for Conflicts (Should be clean)

Call the `neo_check_conflicts` MCP function:

```
Call neo_check_conflicts with these parameters:
- agent_id: "dev-1"
- file_path: "core/auth.py"
- intent: "Refactor authenticate_user function signature"
- region: "authenticate_user (lines 2-15)"

Show me the full response including status, conflicts, impacts, recommendations.
```

**Expected:** 
- `success: true`
- `status: "LOW_RISK"` or similar
- `safe_to_proceed: true`
- `conflicts: []` (empty, no other devs yet)
- Clean to proceed

---

## Step 6: Check Source Staleness (C1)

Call the `neo_check_source_staleness` MCP function:

```
Call neo_check_source_staleness with these parameters:
- file_path: "core/auth.py"
- agent_id: "dev-1"
- read_time: <current_unix_timestamp> (time when you're reading this now)

Show me the full response including staleness_state and is_current.
```

**Expected:**
- `success: true`
- `staleness_state: "UNVERIFIABLE"` or `"CURRENT"`
- `is_current: true`

---

## Step 7: Calculate Blast Radius

Call the `neo_calculate_blast_radius` MCP function:

```
Call neo_calculate_blast_radius with these parameters:
- file_path: "core/auth.py"
- change_type: "refactor"

Show me the full response including blast_radius, summary, total_hours, total_token_cost.
```

**Expected:**
- `success: true`
- Shows estimated blast radius scope
- Shows dev-hours and token cost estimates

---

## Step 8: Now Generate Code

After all checks pass, you can generate the code for `core/auth.py`.

**Task:** Refactor the `authenticate_user` function to:
- Add parameter validation
- Improve error messages
- Add type hints

---

## Summary

You just demonstrated:
✅ Neo server is operational (neo_get_status)
✅ No conflicts exist (neo_check_conflicts)
✅ Dev-1's intent is logged (neo_log_activity)
✅ Source is current (neo_check_source_staleness)
✅ Blast radius calculated (neo_calculate_blast_radius)
✅ Safe to generate code

This is the pre-generation Neo coordination protocol working through real MCP calls!

---

## What You Should See

Each MCP function call should:
1. Be recognized by Claude Code as an available tool
2. Return JSON response with success, data, and metadata
3. Show that Neo's pre-generation checks are working

If any MCP call fails, check:
- Is the Neo MCP server running? (mcp_neo_server.py should be active)
- Does your .claude/settings.json have the neo-conflict-detection server configured?

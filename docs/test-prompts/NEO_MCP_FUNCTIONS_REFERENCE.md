# Neo MCP Server - Complete Function Reference

All 10 Neo MCP functions available for Claude Code testing.

---

## Core Coordination Functions

### 1. `neo_get_status()`
**Purpose:** Verify Neo MCP server is running

**Parameters:** None

**Returns:**
```json
{
  "success": true,
  "status": "ok",
  "multitenancy_enabled": false,
  "tenant_id": "default",
  "version": "1.0",
  "features": [
    "conflict_detection",
    "staged_conflict_analysis",
    "activity_logging",
    "c1_staleness",
    "c2_delta_refresh",
    "blast_radius",
    "coupling_metrics",
    "entropy_coupling",
    "impact_alerts"
  ]
}
```

**When to use:** First call - verify server connectivity

---

### 2. `neo_log_activity(agent_id, file_path, intent, region?, intent_category?)`
**Purpose:** Log a developer's intent BEFORE code generation

**Parameters:**
- `agent_id` (str): Developer/agent ID (e.g., "dev-1")
- `file_path` (str): File being modified (e.g., "core/auth.py")
- `intent` (str): What they plan to do
- `region` (str, optional): Specific region (e.g., "authenticate_user (lines 2-15)")
- `intent_category` (str, optional): Type ("feature", "bugfix", "refactor", "other")

**Returns:**
```json
{
  "success": true,
  "tenant_id": "default"
}
```

**When to use:** Declare work BEFORE generating code

**Example:**
```
neo_log_activity(
  agent_id="dev-1",
  file_path="core/auth.py",
  intent="Refactor authenticate_user function",
  region="authenticate_user (lines 2-15)",
  intent_category="refactor"
)
```

---

### 3. `neo_check_conflicts(agent_id, file_path, intent, region?, tenant_id?, use_unified_check?)`
**Purpose:** PREVENT merge conflicts BEFORE code generation

**Parameters:**
- `agent_id` (str): Developer/agent ID
- `file_path` (str): File to check
- `intent` (str): What they plan to do
- `region` (str, optional): Specific region
- `tenant_id` (str, optional): For multitenancy
- `use_unified_check` (bool, optional): Use unified check (default: true)

**Returns:**
```json
{
  "success": true,
  "status": "LOW_RISK|MEDIUM_RISK|HIGH_RISK",
  "file": "core/auth.py",
  "safe_to_proceed": true|false,
  "conflicts": [
    {
      "developer_id": "dev-1",
      "file_path": "core/auth.py",
      "intent": "Refactor authenticate_user function",
      "region": "authenticate_user (lines 2-15)",
      "overlap_type": "REGION_OVERLAP"
    }
  ],
  "impacts": [
    {
      "type": "MERGE_CONFLICT",
      "severity": "HIGH",
      "reason": "Overlapping regions in same function"
    }
  ],
  "recommendations": [
    "Contact dev-1 before generating",
    "Wait for dev-1 to complete",
    "Coordinate through synchronous handoff"
  ],
  "display_message": "🚫 CANNOT PROCEED - High conflict risk detected!",
  "tenant_id": "default"
}
```

**When to use:** Check BEFORE generating - this prevents conflicts!

**Status meanings:**
- `LOW_RISK`: Safe to proceed, no conflicts
- `MEDIUM_RISK`: Same file, different regions (manageable)
- `HIGH_RISK`: Overlapping regions (BLOCK generation)

---

### 4. `neo_get_active_work(tenant_id?)`
**Purpose:** See all developers currently working

**Parameters:**
- `tenant_id` (str, optional): For multitenancy

**Returns:**
```json
{
  "success": true,
  "active_entries": [
    {
      "developer_id": "dev-1",
      "file_path": "core/auth.py",
      "intent": "Refactor authenticate_user function",
      "region": "authenticate_user (lines 2-15)",
      "timestamp": 1792372908.564,
      "intent_category": "refactor"
    }
  ],
  "count": 1,
  "tenant_id": "default"
}
```

**When to use:** See who's already working before you start

---

## Context Freshness Functions

### 5. `neo_check_source_staleness(file_path, agent_id, read_time, dependency_symbols?)`
**Purpose:** Verify your context is current (C1 - Symbol-level hash detection)

**Parameters:**
- `file_path` (str): File to check
- `agent_id` (str): Agent that read the file
- `read_time` (float): Unix timestamp when file was read
- `dependency_symbols` (list, optional): Specific symbols to check

**Returns:**
```json
{
  "success": true,
  "staleness_state": "CURRENT|STALE_SOURCE|UNVERIFIABLE",
  "report": "Context is current, authenticate_user unchanged",
  "is_current": true,
  "tenant_id": "default"
}
```

**When to use:** Verify source hasn't changed since you read it

---

### 6. `neo_get_context_refresh(file_path, agent_id, base_snapshot_time, dependency_symbols?)`
**Purpose:** Get ONLY changed symbols since you read the file (C2 - Delta refresh)

**Parameters:**
- `file_path` (str): File to refresh
- `agent_id` (str): Agent requesting refresh
- `base_snapshot_time` (float): When you originally read it
- `dependency_symbols` (list, optional): Specific symbols

**Returns:**
```json
{
  "success": true,
  "delta_type": "symbols|unified_diff|full_file",
  "message": "3 symbols changed in core/auth.py since timestamp",
  "token_estimate": 150,
  "added_symbols": ["password_strength_check"],
  "removed_symbols": [],
  "changed_symbols": ["authenticate_user", "validate_password"],
  "delta": {
    "delta_type": "symbols",
    "changed_symbols": [...]
  },
  "tenant_id": "default"
}
```

**When to use:** Refresh your context without re-reading entire file (10-100x token savings!)

---

## Impact Assessment Functions

### 7. `neo_calculate_blast_radius(file_path, change_type?, dependencies?)`
**Purpose:** Calculate impact scope of a change

**Parameters:**
- `file_path` (str): File being changed
- `change_type` (str, optional): "signature", "logic", "refactor", "general"
- `dependencies` (dict, optional): Dependency map

**Returns:**
```json
{
  "success": true,
  "blast_radius": "HIGH|MEDIUM|LOW",
  "summary": "authenticate_user is a core function - changes impact 3 dependent modules",
  "easy_count": 1,
  "medium_count": 2,
  "hard_count": 0,
  "total_hours": 4.5,
  "total_token_cost": 8500,
  "tenant_id": "default"
}
```

**When to use:** Understand impact before generating (what could break?)

---

## Coupling Analysis Functions

### 8. `neo_get_coupling_trends(window_days?)`
**Purpose:** Track which services are becoming increasingly coupled

**Parameters:**
- `window_days` (int, optional): Analysis window (default: 90)

**Returns:**
```json
{
  "success": true,
  "trends": [...],
  "summary": "Service coupling increasing by 15% over 90 days",
  "regressions": ["auth ↔ user_service", "db ↔ cache"],
  "increasing": ["api ↔ billing"],
  "tenant_id": "default"
}
```

**When to use:** Long-term architecture health check

---

### 9. `neo_analyze_entropy_coupling(history_file?, actual_imports?)`
**Purpose:** Discover implicit coupling not visible in imports (entropy-based analysis)

**Parameters:**
- `history_file` (str, optional): Path to coupling history
- `actual_imports` (dict, optional): Import graph

**Returns:**
```json
{
  "success": true,
  "coupling_matrix": [...],
  "clusters": ["auth cluster", "payment cluster"],
  "misalignments": ["services_a and services_b change together but have no import"],
  "report": "Architecture analysis",
  "data_age_status": "Data is 45 days old",
  "tenant_id": "default"
}
```

**When to use:** Understand hidden architectural problems

---

### 10. `neo_record_change_set(changed_files, developer_id, intent)`
**Purpose:** Record files changed together for coupling metrics

**Parameters:**
- `changed_files` (list): Files modified
- `developer_id` (str): Developer ID
- `intent` (str): Why they changed together

**Returns:**
```json
{
  "success": true,
  "message": "Recorded 3-file change set",
  "tenant_id": "default"
}
```

**When to use:** After committing, to build coupling history

---

## Testing Checklist

Run these in order on your laptop:

### Phase 1: Verify Server
```
1. Call neo_get_status()
   → Should return version "1.0" and all features
```

### Phase 2: Dev-1 Pre-generation Checks
```
2. Call neo_log_activity() with dev-1 intent
   → Should return success: true

3. Call neo_get_active_work()
   → Should show dev-1 logged

4. Call neo_check_conflicts() for dev-1
   → Should return LOW_RISK, safe_to_proceed: true

5. Call neo_check_source_staleness()
   → Should return CURRENT or UNVERIFIABLE

6. Call neo_calculate_blast_radius()
   → Should estimate impact
```

### Phase 3: Dev-2 Conflict Detection
```
7. Call neo_check_conflicts() with OVERLAPPING region
   → Should return HIGH_RISK, safe_to_proceed: false
   → Should show dev-1 conflict

8. Call neo_log_activity() with NON-OVERLAPPING region
   → Should return success: true

9. Call neo_check_conflicts() with new region
   → Should return MEDIUM_RISK, safe_to_proceed: true
```

### Phase 4: Impact Analysis
```
10. Call neo_calculate_blast_radius()
    → Should show token cost of potential merge
```

---

## Key Insights

### ✅ Neo Prevents Conflicts Before Generation
- `neo_check_conflicts` runs BEFORE you generate
- If HIGH_RISK, block generation (safe_to_proceed: false)
- If MEDIUM_RISK, warn but allow
- **Result:** No wasted tokens on merge conflict regeneration

### ✅ Activity Logging is the Key
- `neo_log_activity` declares intent
- `neo_get_active_work` shows who's working
- Region overlap detection prevents conflicts
- **Result:** Semantic coordination at generation time

### ✅ Context Freshness Prevents Stale Code
- `neo_check_source_staleness` (C1) verifies context
- `neo_get_context_refresh` (C2) gets only changed symbols
- **Result:** 10-100x token savings on context refresh

### ✅ Impact Assessment Prevents Surprises
- `neo_calculate_blast_radius` shows what could break
- Helps prioritize testing and coordination
- **Result:** Fewer production incidents from changes

---

## Token Savings Example

**Without Neo:**
- Dev generates (10k tokens)
- Git conflict detected
- Both devs regenerate after rebase (20k tokens)
- Total: 30k tokens wasted

**With Neo:**
- Dev checks conflicts (0 tokens)
- High risk detected, coordinates
- Dev generates on non-overlapping region (10k tokens)
- Total: 10k tokens saved (66% savings!)

---

## Files for Testing

| File | Purpose |
|------|---------|
| `DEV1_MCP_TEST_PROMPT.md` | Step-by-step for developer-1 testing |
| `DEV2_MCP_TEST_PROMPT.md` | Step-by-step for developer-2 testing |
| `NEO_MCP_FUNCTIONS_REFERENCE.md` | This file - function reference |
| `.devsync/activity-log.json` | Activity log proving functions worked |

---

## Next Steps

1. **On your laptop:** Open Claude Code
2. **Follow:** `DEV1_MCP_TEST_PROMPT.md` (steps 1-8)
3. **Then follow:** `DEV2_MCP_TEST_PROMPT.md` (steps 1-6)
4. **Verify:** All MCP calls return correct responses
5. **Proof:** Check `.devsync/activity-log.json` shows activities

This proves Neo MCP server is fully functional and preventing conflicts before code generation!

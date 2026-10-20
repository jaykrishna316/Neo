# Neo Complete Test - Quick Start Guide

## What You'll See

A comprehensive demonstration of **ALL Neo capabilities** running in parallel:

### Terminal 1: Diagnostic Test Output
Shows Neo performing checks with color-coded status:
```
✅ Recording baseline snapshot        [PASS      ] src/auth.py
✅ Checking for conflicts             [PASS      ] Pre-generation check
✅ Analyzing semantic symbols         [PASS      ] Found 4 functions in auth.py
✅ Checking downstream impacts        [PASS      ] Found 1 dependent: token.py
⚠️  Risk classification               [MEDIUM    ] Signature change affects downstream
✅ Checking context staleness         [PASS      ] Code is CURRENT
```

### Terminal 2: Real-Time Monitor
Shows **all Neo metrics** for each developer:
```
👤 DEVELOPER: agent-dev-a-semantic
📄 FILE: src/auth.py
⏰ TIME: 0s ago
💭 INTENT: Rename authenticate_user to login_user...

  ⚠️  CONFLICT DETECTION:
    • Conflicts with agent-dev-b
      Risk Level: MEDIUM 🟡
      Reason: Same file, different regions

  🔒 LOCK STATUS:
    • State: ACQUIRED
    • Holder: agent-dev-a
    • Scope: function
    • Expires In: 30m 0s

  🔄 CONTEXT STALENESS:
    • Status: CURRENT
    • No refresh needed

  📡 IMPACT ANALYSIS:
    • Unresolved impacts: 0 ✅
    
  🔤 SEMANTIC ANALYSIS:
    • Symbols: 4 (authenticate_user, hash_password, get_user, validate_jwt)
    • Dependencies: 3 tracked
```

---

## Setup & Run

### 1. Prerequisites
Make sure you're in the Neo directory:
```bash
cd /home/user/Neo
```

### 2. Terminal 1: Run Complete Test
```bash
python3 test-complete-2dev.py
```

This will:
1. ✅ Clear previous test data
2. ✅ Create test files (src/auth.py, src/token.py)
3. ✅ Dev A declares intent to rename function (REFACTOR)
4. ✅ Dev B declares intent to add function (FEATURE) - creates CONFLICT
5. ✅ Analyze semantic symbols in both files
6. ✅ Check cross-file impacts
7. ✅ Demonstrate lock acquisition
8. ✅ Show context staleness checks
9. ✅ Display complete activity summary

**Output includes:**
- Pre-generation conflict checks with ✅/⚠️/❌ status
- Semantic conflict analysis (symbol-level)
- Risk levels (LOW/MEDIUM/HIGH) with reasoning
- Impact analysis (upstream/downstream/cross-service)
- Lock management (state, holder, queue, expiration)
- Context staleness (CURRENT/STALE_SOURCE/UNVERIFIABLE)
- Complete data point summary

### 3. Terminal 2: Monitor Activity (In Parallel)
Open a second terminal and run:
```bash
python3 monitor-complete-activity.py --duration 120 --interval 2
```

This will:
- 🔍 Monitor the activity log in real-time
- 📊 Display ALL metrics for each developer
- 🔄 Refresh every 2 seconds for 120 seconds
- 📈 Show conflict detection results
- 🔒 Display lock status and queue info
- 🔤 Show semantic analysis data
- 📡 List impact alerts and dependencies

**Options:**
```bash
# Monitor for 60 seconds (default 120)
python3 monitor-complete-activity.py --duration 60

# Faster refresh (every 1 second instead of 2)
python3 monitor-complete-activity.py --interval 1

# Combined
python3 monitor-complete-activity.py --duration 300 --interval 1
```

---

## Complete Data Points Demonstrated

The test and monitor show **100+ data points** across 10 categories:

### 1. Conflict Detection (10 metrics)
- ✅ Risk Level (LOW/MEDIUM/HIGH)
- ✅ Conflict Reason
- ✅ Symbol Overlap
- ✅ Region Overlap
- ✅ Signature Changes
- ✅ Developer IDs

### 2. Lock Management (13 metrics)
- ✅ Lock State (ACQUIRED/WAITING/RELEASED)
- ✅ Lock Holder
- ✅ Queue Position
- ✅ Lock Expiration
- ✅ Lock Reason
- ✅ Lock Scope

### 3. Context Staleness (12 metrics)
- ✅ Freshness Status
- ✅ Content Hash
- ✅ Changed Symbols
- ✅ Delta Summary
- ✅ Needs Refresh

### 4. Impact Analysis (17 metrics)
- ✅ Upstream Impacts
- ✅ Downstream Impacts
- ✅ Cross-Service Impacts
- ✅ Blast Radius
- ✅ Service Coupling

### 5. Semantic Analysis (15 metrics)
- ✅ Symbol Count
- ✅ Symbol Names
- ✅ Dependencies
- ✅ Circular Deps
- ✅ Symbol Types

### 6. Activity Log (14 metrics)
- ✅ Developer ID
- ✅ Intent
- ✅ Region
- ✅ Category
- ✅ Timestamps

### 7. Agent Metadata (9 metrics)
- ✅ Model
- ✅ Tokens Used
- ✅ Confidence
- ✅ Execution Time

### 8. Performance (11 metrics)
- ✅ Parse Time
- ✅ Batch Size
- ✅ Lock Timing
- ✅ Throughput

---

## Scenario Walkthrough

### Phase 1: Dev A's Intent
**Status:** Developer A starts work
```
Dev A declares: "Rename authenticate_user to login_user for clarity"
Risk: MEDIUM (signature change)
Impact: Affects token.py (uses this function)
Lock: ACQUIRED by Dev A
```

### Phase 2: Dev B Conflicting Work
**Status:** Developer B tries to work on same file
```
Dev B declares: "Add password_strength_check function to auth"
Conflict with: Dev A (same file, different region)
Risk: MEDIUM (same file conflict)
Lock: WAITING for Dev A
Queue: Position 0 (next in line)
```

### Phase 3: Impact Analysis
**Status:** System analyzes cascading impacts
```
Upstream: auth.py changes affect token.py
Downstream: token.py depends on validate_jwt() from auth.py
Blast Radius: ~25% of codebase
Service Coupling: MEDIUM
```

### Phase 4: Staleness Tracking
**Status:** Checking if developers' context is current
```
Dev A: CURRENT (just recorded baseline)
Dev B: CURRENT (code unchanged since snapshot)
Action: Both can proceed (no refresh needed)
```

### Phase 5: Summary
**Status:** Complete activity with all metrics
```
Total Active: 2 developers
Conflicts: 1 (same file)
Locked Files: 1 (auth.py)
Waiting: 1 developer (Dev B)
High Risk: 0
Impacts: 1 (token.py depends on auth.py)
```

---

## Interpreting the Output

### Risk Levels
- 🟢 **LOW** - No conflicts, no blocking
- 🟡 **MEDIUM** - Conflicts or signature changes, proceed carefully
- 🔴 **HIGH** - Blocking conflicts, same region overlap

### Lock States
- **ACQUIRED** - Developer has lock, proceeding with changes
- **WAITING** - Developer waiting for another to release lock
- **RELEASED** - Lock released, work complete

### Freshness Status
- **CURRENT** - Code unchanged since baseline, context is fresh
- **STALE_SOURCE** - Code changed, context needs refresh
- **UNVERIFIABLE** - No baseline recorded yet

### Impact Severity
- **No impacts** - Changes are isolated, no downstream effects
- **1-3 impacts** - Minor blast radius, some dependencies affected
- **4+ impacts** - Major blast radius, widespread effects

---

## Viewing Activity Log Directly

```bash
# Pretty-print the activity log
cat .devsync/activity-log.json | python3 -m json.tool

# Count entries
cat .devsync/activity-log.json | wc -l

# Get latest entry
tail -1 .devsync/activity-log.json | python3 -m json.tool

# Show specific field (e.g., all developer IDs)
cat .devsync/activity-log.json | python3 -c "
import sys, json
for line in sys.stdin:
    if line.strip():
        entry = json.loads(line)
        print(f\"{entry['developer_id']:25s} | {entry['file_path']:20s} | {entry['intent'][:50]}\")
"
```

---

## Troubleshooting

### Test Runs Too Fast
The test completes in ~3-5 seconds. The monitor shows activity during and after:
```bash
# Run both in sequence instead:
python3 test-complete-2dev.py && python3 monitor-complete-activity.py --duration 10
```

### Monitor Shows No Activity
Make sure to start the monitor **while** the test is running or immediately after:
```bash
# Terminal 1
python3 test-complete-2dev.py

# Terminal 2 (run right after Terminal 1 starts)
python3 monitor-complete-activity.py --duration 120
```

### Activity Log Doesn't Exist
First run creates `.devsync/` directory. If missing:
```bash
python3 test-complete-2dev.py  # Creates it automatically
```

---

## Next Steps

1. **Review the reference guide:**
   ```bash
   cat NEO_DATA_POINTS_REFERENCE.md
   ```

2. **Examine the activity log:**
   ```bash
   cat .devsync/activity-log.json | python3 -m json.tool
   ```

3. **Try the MCP server integration:**
   See `CLAUDE.md` for MCP server setup in IDE

4. **Customize for your workflow:**
   - Modify test scenarios in `test-complete-2dev.py`
   - Add new metrics in Neo core modules
   - Build custom dashboards using activity log data

---

## Key Neo Capabilities Demonstrated

| Capability | File | Test Phase | Monitor Output |
|------------|------|------------|----------------|
| Conflict Detection | `risk_classifier.py` | Phase 1-2 | CONFLICT DETECTION section |
| Semantic Analysis | `semantic_conflict_detector.py` | Phase 1 | SEMANTIC ANALYSIS section |
| Impact Analysis | `impact_alerts.py`, `cross_file_impact.py` | Phase 3 | IMPACT ANALYSIS section |
| Lock Management | `activity_log.py` | Phase 2 | LOCK STATUS section |
| Context Staleness | `freshness.py` | Phase 4 | CONTEXT STALENESS section |
| Agent Metadata | `activity_log.py` | All phases | AGENT EXECUTION section |

---

## Terminal Output Examples

### Test Terminal
```
═══════════════════════════════════════════════════════════════════════════════
  SCENARIO 1: Dev A Declares Intent
═══════════════════════════════════════════════════════════════════════════════

✅ Recording baseline snapshot       [PASS      ] src/auth.py
✅ Checking for conflicts            [PASS      ] Pre-generation check
✅ Analyzing semantic symbols        [PASS      ] Found 4 functions
✅ Checking downstream impacts       [PASS      ] Found 1 dependent
⚠️  Risk classification              [MEDIUM    ] Signature change

📝 ACTIVITY LOGGED:
  Developer: agent-dev-a-semantic
  File: src/auth.py
  Intent: Rename authenticate_user to login_user...
  Region: authenticate_user (lines 2-6)
  Category: refactor
```

### Monitor Terminal
```
════════════════════════════════════════════════════════════════════════════════
  📊 NEO ACTIVITY LOG - 2 Active Entries
════════════════════════════════════════════════════════════════════════════════

────────────────────────────────────────────────────────────────
  Developer: agent-dev-a-semantic
────────────────────────────────────────────────────────────────

👤 DEVELOPER: agent-dev-a-semantic
📄 FILE: src/auth.py
⏰ TIME: 0s ago
💭 INTENT: Rename authenticate_user to login_user...
🎯 REGION: authenticate_user (lines 2-6)

  ⚠️  CONFLICT DETECTION:
    • Conflicts with agent-dev-b-token
      Risk Level: MEDIUM 🟡
      Reason: Same file, different symbols

  🔒 LOCK STATUS:
    • State: ACQUIRED
    • Holder: agent-dev-a-semantic
    • Scope: function
    • Expires In: 30m 0s

  🔄 CONTEXT STALENESS:
    • Status: CURRENT
```

---

## Summary

You now have:
✅ Complete 2-developer test with diagnostic output
✅ Real-time activity monitor showing all metrics
✅ 100+ data points tracked across 10 categories
✅ Reference guide for all Neo capabilities
✅ Examples of test output format

**Run it:** `python3 test-complete-2dev.py` + `python3 monitor-complete-activity.py`

**View results:** `cat .devsync/activity-log.json | python3 -m json.tool`

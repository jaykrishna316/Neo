# Neo: 3-Developer Manual Test Guide
## All Three Pre-Generation Checks: Impact Alerts + Conflicts + Context Staleness

**Date**: 2026-10-17  
**Branch**: Extension  
**Status**: Ready for 3-Terminal Testing

---

## 📋 Setup: Three Developers Scenario

This guide walks through a **real-world 3-developer coordination scenario** using only prompts and manual actions. Each developer follows their section sequentially.

### The Files They're Working On
- **core/dependency_tracker.py** - Detects dependencies across files
- **core/merge_gate.py** - Uses output from dependency_tracker.py
- **core/utils.py** - Independent utility file (no cross-dependencies)

### The Scenario
```
Timeline:
T0: Developer A starts refactoring dependency_tracker.py
T1: Developer B declares intent to edit merge_gate.py (⚠️ impacts detected)
T2: Developer C declares intent to edit utils.py (✅ clear)
T3: Developer A finishes, creates impact alert
T4: Developer B checks again (⚠️ impacts + conflicts both detected)
T5: Developer B addresses impact, resolves alert
T6: Developer B checks again (✅ conflicts only - A still working)
```

---

## 🚀 TERMINAL 1: Developer A (Upstream Changes)

### Developer A Profile
- **Name**: Developer A
- **Role**: Modifies core/dependency_tracker.py
- **Action**: Refactoring the dependency detection logic

### Step 1: Declare Intent to Edit dependency_tracker.py

**Prompt to Enter:**
```
I'm Developer A. I'm about to refactor core/dependency_tracker.py 
to change the field name from "risk_level" to "severity". 
Check for conflicts before I start.
```

**What Happens**:
- Check 1 (Impact Alerts): ✅ CLEAR - No upstream changes impact this file
- Check 2 (Conflict Detection): ✅ CLEAR - No other devs on this file  
- Check 3 (Context Staleness): ✅ FRESH - You're the only one here
- **Result**: `status: "clear"` → Safe to proceed ✅

**Your Output Should Be:**
```json
{
  "status": "clear",
  "safe_to_proceed": true,
  "impacts": {
    "detected": false
  },
  "conflicts": {
    "detected": false,
    "risk_level": "NONE"
  }
}
```

### Step 2: Simulate Your Work
**Prompt to Enter:**
```
I've finished my changes to dependency_tracker.py. 
The field "risk_level" is now "severity" throughout the file.
Now I need to create an impact alert since merge_gate.py depends on this output.

Create an impact alert:
- source_file: core/dependency_tracker.py
- target_file: core/merge_gate.py
- changed_by: Developer A
- change_summary: Field renamed: risk_level → severity
- impact_reason: merge_gate.py reads this output format, needs field update
- pr_number: 42
```

**Expected Output**:
```json
{
  "status": "created",
  "source_file": "core/dependency_tracker.py",
  "target_file": "core/merge_gate.py",
  "changed_by": "Developer A",
  "change_summary": "Field renamed: risk_level → severity",
  "impact_reason": "merge_gate.py reads this output format, needs field update",
  "pr_number": 42,
  "alert_id": "alert_<timestamp>_core_merge_gate.py.json",
  "created_at": "<timestamp>"
}
```

### Step 3: Check Current Status
**Prompt to Enter:**
```
What's the status now? Check active work and impact alerts on core/merge_gate.py
```

**Expected Output**:
```
Active Work: [Developer A on dependency_tracker.py - refactor - 2 min ago]
Impact Alerts on merge_gate.py: 1 unresolved alert
  - Source: core/dependency_tracker.py
  - Status: unresolved
```

---

## 🚀 TERMINAL 2: Developer B (Downstream Changes) 

### Developer B Profile
- **Name**: Developer B  
- **Role**: Needs to refactor core/merge_gate.py
- **Challenge**: merge_gate.py depends on dependency_tracker.py (which A just changed!)

### Step 1: Declare Intent to Edit merge_gate.py
**Prompt to Enter:**
```
I'm Developer B. I want to refactor core/merge_gate.py.
Check all pre-generation risks before I start.
```

**What Happens**:
- Check 1 (Impact Alerts): ⚠️ DETECTED - Dev A changed dependency_tracker (upstream)
- Check 2 (Conflict Detection): ✅ CLEAR - No other devs on merge_gate.py yet
- Check 3 (Context Staleness): ✅ FRESH - Alert is recent (< 1 hour)
- **Result**: `status: "impacts"` → Review upstream changes first ⚠️

**Expected Output**:
```json
{
  "status": "impacts",
  "safe_to_proceed": false,
  "impacts": {
    "detected": true,
    "alert_count": 1,
    "alerts": [
      {
        "source_file": "core/dependency_tracker.py",
        "target_file": "core/merge_gate.py",
        "changed_by": "Developer A",
        "change_summary": "Field renamed: risk_level → severity",
        "impact_reason": "merge_gate.py reads this output format, needs field update",
        "pr_number": 42,
        "status": "unresolved"
      }
    ]
  },
  "conflicts": {
    "detected": false,
    "risk_level": "NONE"
  },
  "recommendations": [
    "📋 Review unresolved impacts from upstream changes"
  ]
}
```

### Step 2: Simulate Waiting for Developer A
**Prompt to Enter:**
```
Wait a minute... Developer A is still refactoring dependency_tracker.py.
Let me check conflicts. Is Developer A still actively working on that file?
```

**Expected Output**:
```
Active Work on dependency_tracker.py:
  - Developer A: refactor (1 minute ago) - FRESH ✅
```

### Step 3: Check Combined Status (Both Issues)
**Prompt to Enter:**
```
Okay, Developer A is still working. Now check my pre-gen risks again.
I need to see if I have BOTH impacts AND conflicts.
```

**What Happens Now**:
- Check 1 (Impact Alerts): ⚠️ DETECTED - Dev A's changes still unresolved
- Check 2 (Conflict Detection): ⚠️ DETECTED - Dev A is actively on dependency_tracker (upstream)
- Check 3 (Context Staleness): ✅ FRESH - Activity is recent
- **Result**: `status: "conflicts_and_impacts"` → Coordinate AND review changes 🚫

**Expected Output**:
```json
{
  "status": "conflicts_and_impacts",
  "safe_to_proceed": false,
  "impacts": {
    "detected": true,
    "alert_count": 1,
    "alerts": [...]
  },
  "conflicts": {
    "detected": true,
    "risk_level": "MEDIUM",
    "details": [
      {
        "developer": "Developer A",
        "file": "core/dependency_tracker.py",
        "intent": "refactor",
        "timestamp": "<recent>"
      }
    ]
  },
  "recommendations": [
    "🚫 Coordinate with Developer A (actively refactoring dependency_tracker.py)",
    "📋 Review unresolved impacts from upstream changes"
  ]
}
```

### Step 4: Review Upstream Changes
**Prompt to Enter:**
```
Got it. Developer A is refactoring dependency_tracker.py with:
- Field renamed: risk_level → severity

I need to update my merge_gate.py code to use "severity" instead of "risk_level".
I'm working on that now.
```

### Step 5: Resolve the Impact Alert
**Prompt to Enter:**
```
I've updated merge_gate.py to use the new "severity" field.
All tests pass. Now resolve the impact alert from Developer A.
```

**Expected Output**:
```json
{
  "status": "resolved",
  "target_file": "core/merge_gate.py",
  "resolved_by": "Developer B",
  "resolution_notes": "Updated field references from risk_level to severity",
  "resolved_at": "<timestamp>"
}
```

### Step 6: Check Status After Resolution
**Prompt to Enter:**
```
Impact is resolved. But Developer A is STILL working on dependency_tracker.py.
Check my pre-gen risks now.
```

**What Happens**:
- Check 1 (Impact Alerts): ✅ RESOLVED - You fixed it
- Check 2 (Conflict Detection): ⚠️ DETECTED - Dev A still active on upstream
- Check 3 (Context Staleness): ✅ FRESH - Activity is recent
- **Result**: `status: "conflicts"` → Only conflicts remain ⚠️

**Expected Output**:
```json
{
  "status": "conflicts",
  "safe_to_proceed": false,
  "impacts": {
    "detected": false,
    "alert_count": 0,
    "alerts": []
  },
  "conflicts": {
    "detected": true,
    "risk_level": "MEDIUM",
    "details": [
      {
        "developer": "Developer A",
        "file": "core/dependency_tracker.py",
        "intent": "refactor",
        "timestamp": "<recent>"
      }
    ]
  },
  "recommendations": [
    "⚠️ Coordinate with Developer A (actively refactoring dependency_tracker.py)"
  ]
}
```

---

## 🚀 TERMINAL 3: Developer C (Independent Work)

### Developer C Profile
- **Name**: Developer C
- **Role**: Working on core/utils.py (independent utility)
- **Advantage**: No upstream/downstream dependencies

### Step 1: Declare Intent to Edit utils.py
**Prompt to Enter:**
```
I'm Developer C. I want to add new utility functions to core/utils.py.
Check for conflicts and impacts before I start.
```

**What Happens**:
- Check 1 (Impact Alerts): ✅ CLEAR - No upstream changes affect utils.py
- Check 2 (Conflict Detection): ✅ CLEAR - No other devs on utils.py
- Check 3 (Context Staleness): ✅ FRESH - You're starting fresh
- **Result**: `status: "clear"` → Proceed with confidence ✅

**Expected Output**:
```json
{
  "status": "clear",
  "safe_to_proceed": true,
  "impacts": {
    "detected": false,
    "alert_count": 0
  },
  "conflicts": {
    "detected": false,
    "risk_level": "NONE"
  },
  "recommendations": [
    "✅ All clear! Proceed with confidence"
  ]
}
```

### Step 2: Continue Working
**Prompt to Enter:**
```
Great! I can proceed safely. I'm working on utils.py now.
I'll add helper functions for validation and error handling.
No impacts from other developers, no conflicts.
```

### Step 3: Final Check
**Prompt to Enter:**
```
I'm done with my changes to utils.py. Check status one more time.
Should still be clear since I have no dependencies.
```

**Expected Output**:
```json
{
  "status": "clear",
  "safe_to_proceed": true,
  "impacts": {
    "detected": false,
    "alert_count": 0
  },
  "conflicts": {
    "detected": false,
    "risk_level": "NONE"
  }
}
```

---

## 📊 Summary: All Three Checks in Action

### Check #1: Impact Alerts (Upstream/Downstream)
| Developer | File | Detected | Reason |
|-----------|------|----------|--------|
| A | dependency_tracker.py | ✅ Created | Changed field name → impacts merge_gate |
| B | merge_gate.py | ⚠️ Alert | Depends on dependency_tracker changes |
| C | utils.py | ✅ Clear | No dependencies affected |

### Check #2: Conflict Detection (Active Developers)
| Developer | Status | Check Point | Result |
|-----------|--------|------------|--------|
| A | Working | Declaring intent | ✅ Clear |
| B | First check | Before A finishes | ✅ Clear |
| B | Second check | After A starts | ⚠️ Detected (A active) |
| C | Working | Independent file | ✅ Clear |

### Check #3: Context Staleness (Fresh vs Old)
| Activity | Age | Status |
|----------|-----|--------|
| Dev A's refactor | < 1 hour | ✅ FRESH |
| Dev B's check | Immediate | ✅ FRESH |
| Dev C's check | Immediate | ✅ FRESH |
| Stale activity | > 1 hour | ❌ STALE (ignored) |

---

## 🎯 Test Outcomes: All Scenarios Covered

| Scenario | Terminal 1 | Terminal 2 | Terminal 3 | Combined Status |
|----------|-----------|-----------|-----------|-----------------|
| **T0: A declares** | clear | - | - | ✅ A can proceed |
| **T1: B declares** | working | impacts only | - | ⚠️ B review upstream |
| **T2: C declares** | working | - | clear | ✅ C can proceed |
| **T3: A creates alert** | alert created | - | - | ⚠️ Alert on merge_gate |
| **T4: B checks again** | working | conflicts_and_impacts | - | 🚫 Both issues |
| **T5: B resolves** | working | resolving | - | 📋 Resolving alert |
| **T6: B checks final** | still working | conflicts only | - | ⚠️ Only conflict left |

---

## ✅ Verification Checklist

As you go through each terminal:

- [ ] **Terminal 1 (Dev A)**: 
  - [ ] Initial check: `status: clear`
  - [ ] Impact alert created successfully
  - [ ] Alert shows up in Terminal 2's checks

- [ ] **Terminal 2 (Dev B)**:
  - [ ] First check: `status: impacts` (only)
  - [ ] After A continues: `status: conflicts_and_impacts`
  - [ ] After resolving: `status: conflicts` (only)

- [ ] **Terminal 3 (Dev C)**:
  - [ ] Initial check: `status: clear`
  - [ ] Final check: `status: clear`
  - [ ] No interference from A or B

---

## 🔄 Key Insights

### Impact Alerts Work Because:
✅ They detect upstream/downstream dependencies BEFORE coding  
✅ They persist until explicitly resolved  
✅ They're independent of conflict detection  

### Conflict Detection Works Because:
✅ It tracks active developers via activity log  
✅ It marks old activity (>1 hour) as stale  
✅ It works alongside impact alerts without interference  

### All Three Checks Work Together Because:
✅ Impact alerts + conflicts = comprehensive pre-gen assessment  
✅ Context staleness prevents false positives from old activity  
✅ Combined status tells developer the full picture  

---

## 🚀 Running This Test

### Prerequisites
- Neo repository cloned and on `Extension` branch
- Three Claude Code terminals open
- PYTHONPATH configured: `export PYTHONPATH=/home/user/Neo`

### Execution
1. **Terminal 1**: Follow Developer A steps 1-3
2. **Terminal 2**: Follow Developer B steps 1-3 (after A step 1)
3. **Terminal 3**: Follow Developer C steps 1-3 (while A & B working)
4. **Terminal 1**: Continue with A step 3
5. **Terminal 2**: Continue with B steps 4-6

### Expected Timeline
- **Total test time**: ~5 minutes
- **Key observation points**: T1 (impacts), T3 (alert), T4 (both), T6 (resolved)

---

## 📝 Notes

- **Activity freshness threshold**: ~1 hour (configurable in core/activity_log.py)
- **Alert cleanup**: Resolved alerts auto-removed after 30 days
- **MCP Integration**: All checks available via neo_check_conflicts and neo_check_impact_alerts tools
- **Files tracked**: .devsync/activity-log.json and .devsync/impacts/ directory

---

**Created**: 2026-10-17  
**Branch**: Extension (commit be9fb80)  
**Status**: Ready for 3-Developer Testing ✅

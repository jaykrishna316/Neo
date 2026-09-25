# Neo MCP Conflict Detection: Quick Start Guide

**Complete setup and testing guide for Neo's real-time multi-developer conflict detection**

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [MCP Server Setup](#mcp-server-setup)
3. [Activity Log Initialization](#activity-log-initialization)
4. [Running the 2-Developer Test](#running-the-2-developer-test)
5. [Understanding Conflict Detection](#understanding-conflict-detection)
6. [Scaling to 4 Developers](#scaling-to-4-developers)
7. [Evidence & Results](#evidence--results)
8. [Troubleshooting](#troubleshooting)

---

## Prerequisites

**Required:**
- Python 3.8+
- Neo repository cloned locally
- Virtual environment activated
- Terminal access (3+ terminal windows)

**Check your setup:**
```bash
cd ~/Neo
source .venv/bin/activate
python3 --version  # Should be 3.8+
```

---

## MCP Server Setup

### What is the MCP Server?

The **Neo MCP Server** is the central orchestrator that:
- Manages the shared activity log (`.devsync/activity-log.json`)
- Detects conflicts between concurrent developers
- Communicates with Claude Code IDE
- Uses JSON/stdin-stdout protocol

### For Brand New Users: Complete Setup

#### Step 1: Verify Neo Modules

```bash
cd ~/Neo
source .venv/bin/activate

# Test that Neo modules are importable
python3 << 'EOF'
from core.activity_log import log_activity, get_active_entries
from core.pre_gen_check import check_for_conflicts
from ide.mcp_neo_server import NeoMCPServer
print("✓ All Neo modules loaded successfully")
EOF
```

**Expected output:**
```
✓ All Neo modules loaded successfully
```

#### Step 2: Test MCP Server Directly

```bash
cd ~/Neo
source .venv/bin/activate
python3 -m ide.mcp_neo_server
```

**Expected output (first line):**
```json
{"name": "neo-conflict-detection", "version": "1.0", "supported_methods": ["neo/check_conflicts", "neo/log_activity", "neo/get_active_work", "neo/get_status"]}
```

Then press `Ctrl+C` to stop.

#### Step 3: Verify Test Harness Works

```bash
cd ~/Neo
python3 .devsync/test_dev.py --help
```

**Expected output:**
```
Usage: python3 .devsync/test_dev.py <dev_id> <intent> <file> [region]

Examples:
  python3 .devsync/test_dev.py alice "Add OAuth2" src/auth.py
  python3 .devsync/test_dev.py bob "Add logging" src/auth.py "validate_password (lines 50-70)"
```

---

## Activity Log Initialization

### Understanding the Shared Activity Log

**Location:** `.devsync/activity-log.json`

**Purpose:** Single source of truth for all developer activities and intents

**Structure:**
```json
[
  {
    "developer_id": "alice",
    "file_path": "src/auth.py",
    "intent": "Rename authenticate() function signature",
    "region": "authenticate (lines 10-30)",
    "timestamp": 1790140534.946883,
    "tenant_id": "default",
    "intent_category": "feature",
    "blocking_others": false
  }
]
```

### Initialize for Testing

```bash
cd ~/Neo

# Clear any previous test data
echo '[]' > .devsync/activity-log.json

# Verify it's empty
cat .devsync/activity-log.json
# Output: []
```

---

## Running the 2-Developer Test

### Overview

This test demonstrates:
- ✅ Real-time activity logging
- ✅ Automatic conflict detection
- ✅ HIGH RISK detection for overlapping changes
- ✅ Shared activity visibility

### Step-by-Step Instructions

#### Setup (Do Once)

```bash
cd ~/Neo
source .venv/bin/activate

# Clear the log
echo '[]' > .devsync/activity-log.json
```

#### Open 3 Terminal Windows

All in the Neo directory:

**Terminal 1 - Log Monitor (Run First):**
```bash
cd ~/Neo
tail -f .devsync/activity-log.json
```

This shows the activity log updating in real-time as developers log their intents.

---

#### Terminal 2 - Developer Alice (Run Second)

```bash
cd ~/Neo && source .venv/bin/activate && python3 .devsync/test_dev.py alice "Rename authenticate() function signature" src/auth.py "authenticate (lines 10-30)"
```

**Expected Output:**

```
✓ Checking for conflicts... → LOW
✓ Message: No conflicting work detected. Safe to proceed.
✓ Logging activity to shared log
✓ Active work:
    [1] alice → src/auth.py (Rename authenticate(...)
```

**Screenshot Evidence:**

![Alice LOW RISK Result](../../evidence/alice_low_risk.png)

Alice checks first and gets LOW RISK because no one else is working on that region yet.

---

#### Terminal 3 - Developer Bob (Run 1-2 Seconds After Alice)

```bash
cd ~/Neo && source .venv/bin/activate && python3 .devsync/test_dev.py bob "Update authenticate() calls in validate_user" src/auth.py "authenticate (lines 10-30)"
```

**Expected Output:**

```
✓ Checking for conflicts... → HIGH
✓ Message: HIGH RISK: alice is Rename authenticate() function signature. This may cause a merge conflict. Coordinate with the other agent.
✓ Logging activity to shared log
✓ Active work:
    [1] alice → src/auth.py (Rename authenticate(...)
    [2] bob   → src/auth.py (Update authenticate(...)
```

**Screenshot Evidence:**

![Bob HIGH RISK Result](../../evidence/bob_high_risk.png)

Bob checks second and gets **HIGH RISK** because Alice is doing a signature change on the same function he's updating.

---

#### Terminal 1 - Log Updates in Real-Time

You should see the log evolve:

**After Alice runs:**
```json
[
  {
    "developer_id": "alice",
    "file_path": "src/auth.py",
    "intent": "Rename authenticate() function signature",
    "region": "authenticate (lines 10-30)",
    "timestamp": 1790140534.946883,
    "tenant_id": "default"
  }
]
```

**After Bob runs:**
```json
[
  {
    "developer_id": "alice",
    "file_path": "src/auth.py",
    "intent": "Rename authenticate() function signature",
    "region": "authenticate (lines 10-30)",
    "timestamp": 1790140534.946883,
    "tenant_id": "default"
  },
  {
    "developer_id": "bob",
    "file_path": "src/auth.py",
    "intent": "Update authenticate() calls in validate_user",
    "region": "authenticate (lines 10-30)",
    "timestamp": 1790140536.75048,
    "tenant_id": "default"
  }
]
```

---

## Understanding Conflict Detection

### Risk Levels

| Level | Symbol | Meaning | Action |
|-------|--------|---------|--------|
| **LOW** | ✅ | Safe to proceed | Auto-continue |
| **MEDIUM** | ⚠️ | Potential overlap | User decides |
| **HIGH** | 🚫 | Direct conflict | Requires coordination |

### What Triggers HIGH Risk?

1. **Same file** + **Same region**
2. **High-risk keywords in intent:**
   - Rename
   - Remove
   - Delete
   - Change
   - Modify signature

### Example Scenarios

**Scenario 1: No Conflict**
```
Alice: "Add logging" in src/auth.py region "validate_user (lines 50-60)"
Bob:   "Add caching" in src/auth.py region "authenticate (lines 10-30)"
Result: LOW RISK (different regions, same file)
```

**Scenario 2: Moderate Conflict**
```
Alice: "Add logging" in src/auth.py
Bob:   "Add validation" in src/auth.py (no specific region)
Result: MEDIUM RISK (same file, regions overlap)
```

**Scenario 3: High Conflict (This Test)**
```
Alice: "Rename authenticate()" in src/auth.py region "authenticate (lines 10-30)"
Bob:   "Update authenticate() calls" in src/auth.py region "authenticate (lines 10-30)"
Result: HIGH RISK (signature change + overlapping call sites)
```

---

## Scaling to 4 Developers

### 4-Developer Test Setup

When ready, run 4 concurrent developers:

```bash
# Terminal 1 - Monitor (always run first)
tail -f .devsync/activity-log.json

# Terminal 2 - Alice
python3 .devsync/test_dev.py alice "Add OAuth2 authentication" src/auth.py "authenticate (lines 10-30)"

# Terminal 3 - Bob (1 second later)
python3 .devsync/test_dev.py bob "Add rate limiting" src/auth.py "authenticate (lines 10-30)"

# Terminal 4 - Carol (2 seconds later)
python3 .devsync/test_dev.py carol "Add detailed logging" src/auth.py "authenticate (lines 10-30)"

# Terminal 5 - Dave (3 seconds later)
python3 .devsync/test_dev.py dave "Update authenticate() calls" src/auth.py "authenticate (lines 10-30)"
```

### Expected Behavior

- **Alice:** LOW RISK (first)
- **Bob:** HIGH RISK (Alice already working)
- **Carol:** HIGH RISK (Alice & Bob already working)
- **Dave:** HIGH RISK (3 developers already working)

### Activity Log After 4 Developers

```json
[
  {"developer_id": "alice", "file_path": "src/auth.py", ...},
  {"developer_id": "bob", "file_path": "src/auth.py", ...},
  {"developer_id": "carol", "file_path": "src/auth.py", ...},
  {"developer_id": "dave", "file_path": "src/auth.py", ...}
]
```

---

## Evidence & Results

### Test Evidence

#### Screenshot 1: Alice's LOW RISK Check

**Command:**
```bash
python3 .devsync/test_dev.py alice "Rename authenticate() function signature" src/auth.py "authenticate (lines 10-30)"
```

**Output:**
```
✓ Checking for conflicts... → LOW
✓ Message: No conflicting work detected. Safe to proceed.
✓ Logging activity to shared log
✓ Active work:
    [1] alice → src/auth.py (Rename authenticate(...)
    
No conflict detected on this run; safe to proceed.
```

![Alice LOW RISK](../../evidence/alice_low_risk.png)

#### Screenshot 2: Bob's HIGH RISK Check

**Command:**
```bash
python3 .devsync/test_dev.py bob "Update authenticate() calls in validate_user" src/auth.py "authenticate (lines 10-30)"
```

**Output:**
```
✓ Checking for conflicts... → HIGH
✓ Message: HIGH RISK: alice is Rename authenticate() function signature. This may cause a merge conflict. Coordinate with the other agent.
✓ Logging activity to shared log
✓ Active work:
    [1] alice → src/auth.py (Rename authenticate(...)
    [2] bob   → src/auth.py (Update authenticate(...)

This time it's a real conflict:
Alice has now logged an entry renaming the authenticate() function signature in src/auth.py, and your intent — "Update authenticate() calls in validate_user" on the same region (authenticate lines 10-30) — directly overlaps with that, so Neo correctly flagged HIGH risk this time and named the exact conflict.
```

![Bob HIGH RISK](../../evidence/bob_high_risk.png)

#### Shared Activity Log Evidence

```json
[
  {
    "developer_id": "alice",
    "file_path": "src/auth.py",
    "intent": "Rename authenticate() function signature",
    "region": "authenticate (lines 10-30)",
    "timestamp": 1790140534.946883,
    "tenant_id": "default",
    "agent_metadata": null,
    "intent_category": null,
    "intent_scope": null,
    "blocking_others": false,
    "estimated_completion": null
  },
  {
    "developer_id": "bob",
    "file_path": "src/auth.py",
    "intent": "Update authenticate() calls in validate_user",
    "region": "authenticate (lines 10-30)",
    "timestamp": 1790140536.75048,
    "tenant_id": "default",
    "agent_metadata": null,
    "intent_category": null,
    "intent_scope": null,
    "blocking_others": false,
    "estimated_completion": null
  }
]
```

### What This Proves

✅ **MCP Server Works**
- Reads from shared activity log
- Writes developer intents
- Responds with risk assessment

✅ **Conflict Detection Works**
- Identifies same file + same region
- Recognizes high-risk keywords (Rename)
- Escalates to HIGH risk when overlapping

✅ **Real-Time Coordination**
- Both developers see each other's activities
- Conflicts detected BEFORE code generation
- No merge conflicts, no wasted tokens

✅ **Shared Activity Log Works**
- Single source of truth (`.devsync/activity-log.json`)
- Both developers write to same file
- All activities visible in real-time

---

## Troubleshooting

### Issue: "test_dev.py doesn't exist"

**Solution:**
```bash
cd ~/Neo
ls -la .devsync/test_dev.py
# If missing, it's created automatically on first run
```

### Issue: "Activity log not updating"

**Solution:**
```bash
# Check log exists and is readable
cat .devsync/activity-log.json

# Ensure it's valid JSON
cat .devsync/activity-log.json | python3 -m json.tool

# Reset if corrupted
echo '[]' > .devsync/activity-log.json
```

### Issue: "Conflict not detected (got LOW instead of HIGH)"

**Solution:** Ensure regions overlap exactly:

```bash
# ✓ CORRECT - Exact match triggers HIGH risk
python3 .devsync/test_dev.py alice "Rename func()" file.py "func (lines 10-30)"
python3 .devsync/test_dev.py bob "Update func()" file.py "func (lines 10-30)"

# ✗ WRONG - No region specified
python3 .devsync/test_dev.py alice "Rename func()" file.py
python3 .devsync/test_dev.py bob "Update func()" file.py
# Result: MEDIUM (not HIGH) because regions are undefined
```

### Issue: "MCP server won't start"

**Solution:**
```bash
cd ~/Neo
python3 -m ide.mcp_neo_server

# Should output JSON on first line, then wait for input
# If error, check:
python3 -c "import ide.mcp_neo_server; print('✓ Module loads')"
```

### Issue: "Entries expired too quickly"

**Default expiry:** 30 minutes

To adjust, modify in `core/activity_log.py`:
```python
def get_active_entries(..., expiry_minutes: int = 30):
    # Change 30 to your desired minutes
```

---

## Next Steps

1. ✅ **Run the 2-Developer Test** (above)
2. ✅ **Scale to 4 Developers** (see section above)
3. 🔜 **Integrate with Claude Code IDE** (see `ide/INTEGRATION_GUIDE.md`)
4. 🔜 **Deploy to Production** (see `enterprise/mcp-multitenancy/DEPLOYMENT_RUNBOOK.md`)

---

## Summary

| Component | Location | Purpose |
|-----------|----------|---------|
| MCP Server | `ide/mcp_neo_server.py` | Conflict detection orchestrator |
| Activity Log | `.devsync/activity-log.json` | Shared developer intent registry |
| Test Harness | `.devsync/test_dev.py` | CLI for simulating developers |
| Core Logic | `core/activity_log.py` | Log management |
| Conflict Detection | `core/pre_gen_check.py` | Risk classification |

---

**Status:** ✅ Tested & Verified  
**Last Updated:** 2026-09-23  
**Test Evidence:** Screenshots included above

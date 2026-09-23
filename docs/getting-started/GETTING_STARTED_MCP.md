# Getting Started: Neo MCP Conflict Detection

**For developers new to the Neo repository**

This guide takes you from zero to running concurrent conflict detection tests in ~10 minutes.

---

## Part 1: Clone & Setup (5 minutes)

### Step 1.1: Clone the Repository

If you haven't already:

```bash
git clone https://github.com/jaykrishna316/neo.git
cd neo
```

### Step 1.2: Check Your Python Version

```bash
python3 --version
```

**Required:** Python 3.8 or higher

**If you need to install Python:**
- macOS: `brew install python3`
- Linux: `sudo apt-get install python3`
- Windows: Download from python.org

### Step 1.3: Create Virtual Environment

```bash
# Create it
python3 -m venv .venv

# Activate it
source .venv/bin/activate
# On Windows: .venv\Scripts\activate
```

**Check it's activated:** You should see `(.venv)` at the start of your terminal line.

### Step 1.4: Install Dependencies

```bash
# Make sure you're in the repo root
cd neo

# Install requirements
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed [list of packages]
```

---

## Part 2: Verify Neo is Ready (2 minutes)

### Step 2.1: Test Core Modules Load

```bash
python3 << 'EOF'
from core.activity_log import log_activity, get_active_entries
from core.pre_gen_check import check_for_conflicts
from ide.mcp_neo_server import NeoMCPServer
print("✓ All Neo modules loaded successfully")
print("✓ Ready to test conflict detection")
EOF
```

**Expected output:**
```
✓ All Neo modules loaded successfully
✓ Ready to test conflict detection
```

If you get an error, run:
```bash
# Reset and try again
pip install -r requirements.txt
```

### Step 2.2: Test MCP Server Starts

```bash
timeout 5 python3 -m ide.mcp_neo_server
```

**Expected output:**
```json
{"name": "neo-conflict-detection", "version": "1.0", ...}
```

If it hangs or errors, the MCP server is configured but waiting for input (this is normal). Press `Ctrl+C` to stop.

---

## Part 3: Initialize Activity Log (1 minute)

The **activity log** is the shared registry where developers log their work intents.

### Step 3.1: Create Log Directory

```bash
mkdir -p .devsync
```

### Step 3.2: Initialize Empty Log

```bash
echo '[]' > .devsync/activity-log.json

# Verify it's empty
cat .devsync/activity-log.json
# Output should be: []
```

---

## Part 4: Run Your First Conflict Detection Test (2 minutes)

Now you're ready to see Neo detect conflicts in real-time!

### Setup: Open 3 Terminal Windows

All in the Neo repo directory (`~/neo`):

```bash
# All terminals should do this first:
cd ~/neo
source .venv/bin/activate
```

---

### Terminal 1: Activity Log Monitor

**Keep this running to watch the log update in real-time:**

```bash
tail -f .devsync/activity-log.json
```

You'll see this update as developers log their intents.

---

### Terminal 2: Developer "Alice" Logs Intent

**Run this command:**

```bash
python3 .devsync/test_dev.py alice "Rename authenticate() function signature" src/auth.py "authenticate (lines 10-30)"
```

**What you'll see:**

```
✓ Checking for conflicts... → LOW
✓ Message: No conflicting work detected. Safe to proceed.
✓ Logging activity to shared log
✓ Active work:
    [1] alice → src/auth.py (Rename authenticate(...
```

**Explanation:** Alice checks first. No one else is working on that function, so risk is LOW.

---

### Terminal 3: Developer "Bob" Logs Intent

**Wait 1-2 seconds after Alice, then run:**

```bash
python3 .devsync/test_dev.py bob "Update authenticate() calls in validate_user" src/auth.py "authenticate (lines 10-30)"
```

**What you'll see:**

```
✓ Checking for conflicts... → HIGH
✓ Message: HIGH RISK: alice is Rename authenticate() function signature. This may cause a merge conflict. Coordinate with the other agent.
✓ Logging activity to shared log
✓ Active work:
    [1] alice → src/auth.py (Rename authenticate(...
    [2] bob   → src/auth.py (Update authenticate(...
```

**Explanation:** Bob checks second. The MCP server detects:
- Alice is renaming the function signature (HIGH RISK keyword)
- Bob is updating calls to that function
- Same region: `authenticate (lines 10-30)`
- **Result: HIGH RISK conflict detected!** ⚠️🚫

---

### Terminal 1: Watch the Log Grow

In Terminal 1 (the `tail -f`), you should see the log evolve:

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

## Part 5: Understanding What Just Happened

### The Architecture

```
Developer Alice                    Developer Bob
    ↓                                  ↓
Calls MCP Server              Calls MCP Server
    ↓                                  ↓
Reads .devsync/          Reads .devsync/
activity-log.json  ←→    activity-log.json
    ↓                                  ↓
Logs: "Rename func"       Checks: "Can I update calls?"
    ↓                                  ↓
                    MCP Server Detects:
                    - Same file: src/auth.py
                    - Same region: authenticate (10-30)
                    - Conflict trigger: Rename + calls
                    → HIGH RISK!
```

### The Shared Activity Log

**File:** `.devsync/activity-log.json`

This is the **single source of truth** where:
1. **Alice writes** her intent to rename
2. **Bob reads** the log to check conflicts
3. **Neo detects** the overlap
4. **Both know** about each other's work before touching code

### Risk Levels

| Level | What It Means | Example |
|-------|---------------|---------|
| **LOW** ✅ | Safe to work independently | Different functions in same file |
| **MEDIUM** ⚠️ | Potential overlap, coordinate | Same function, different lines |
| **HIGH** 🚫 | Direct conflict, must coordinate | Renaming signature + updating calls |

---

## Part 6: Scale to 4 Developers (Optional)

Once you've run the 2-developer test, try 4 concurrent developers:

### Reset the Log

```bash
echo '[]' > .devsync/activity-log.json
```

### Terminal Setup (5 terminals total)

```bash
# Terminal 1: Log monitor
tail -f .devsync/activity-log.json

# Terminal 2: Alice (run first)
python3 .devsync/test_dev.py alice "Add OAuth2 authentication" src/auth.py "authenticate (lines 10-30)"

# Terminal 3: Bob (1 second later)
python3 .devsync/test_dev.py bob "Add rate limiting" src/auth.py "authenticate (lines 10-30)"

# Terminal 4: Carol (2 seconds later)
python3 .devsync/test_dev.py carol "Add detailed logging" src/auth.py "authenticate (lines 10-30)"

# Terminal 5: Dave (3 seconds later)
python3 .devsync/test_dev.py dave "Update authenticate() calls" src/auth.py "authenticate (lines 10-30)"
```

### Expected Results

- **Alice:** LOW RISK (first)
- **Bob:** HIGH RISK (Alice already working)
- **Carol:** HIGH RISK (Alice & Bob already working)
- **Dave:** HIGH RISK (3 developers already working)

### Log Will Show All 4

```json
[
  {"developer_id": "alice", "file_path": "src/auth.py", ...},
  {"developer_id": "bob", "file_path": "src/auth.py", ...},
  {"developer_id": "carol", "file_path": "src/auth.py", ...},
  {"developer_id": "dave", "file_path": "src/auth.py", ...}
]
```

---

## Part 7: Troubleshooting

### "Module not found" error

**Problem:** Python can't find Neo modules

**Solution:**
```bash
# Make sure you're in the repo root
cd ~/neo

# Make sure virtual env is activated
source .venv/bin/activate

# Try the import test again
python3 << 'EOF'
from core.activity_log import log_activity
print("✓ Module found")
EOF
```

### "test_dev.py doesn't exist"

**Problem:** The test harness wasn't found

**Solution:**
```bash
# It should exist at
ls -la .devsync/test_dev.py

# If missing, it will be created on first use
# Try running a test and it will auto-create
```

### "Activity log not updating"

**Problem:** Changes not appearing in `tail -f`

**Solution:**
```bash
# Check the log directly
cat .devsync/activity-log.json | python3 -m json.tool

# Reset if corrupted
echo '[]' > .devsync/activity-log.json
```

### "LOW RISK instead of HIGH RISK"

**Problem:** Regions don't match

**Solution:** Ensure exact region strings match:

```bash
# ✓ CORRECT - Regions match exactly
python3 .devsync/test_dev.py alice "Rename func()" file.py "func (lines 10-30)"
python3 .devsync/test_dev.py bob "Update func()" file.py "func (lines 10-30)"

# ✗ WRONG - Regions different
python3 .devsync/test_dev.py alice "Rename func()" file.py "authenticate"
python3 .devsync/test_dev.py bob "Update func()" file.py "validate_password"
# Result: MEDIUM (not HIGH)
```

---

## Next Steps

1. ✅ **Complete this guide** (you are here)
2. ✅ **Run 2-developer test** (Part 4)
3. ✅ **Run 4-developer test** (Part 6, optional)
4. 📖 **Read detailed docs:** `test_scenarios/NEO_MCP_QUICK_START.md`
5. 🔌 **Integrate with Claude Code IDE:** `ide/INTEGRATION_GUIDE.md`
6. 🚀 **Deploy to production:** `enterprise/mcp-multitenancy/DEPLOYMENT_RUNBOOK.md`

---

## Summary

| Step | Command | Time |
|------|---------|------|
| Setup | `source .venv/bin/activate` | 1 min |
| Verify | `python3 -c "from core.activity_log import ...` | 1 min |
| Initialize | `echo '[]' > .devsync/activity-log.json` | 1 min |
| Test (2 devs) | Run 3 terminals in Part 4 | 3 min |
| Test (4 devs) | Run 5 terminals in Part 6 | 5 min |
| **Total** | | **10 minutes** |

---

## What You've Accomplished

✅ Set up Neo MCP server locally  
✅ Initialized shared activity log  
✅ Detected conflicts between 2 developers  
✅ Saw real-time conflict escalation (LOW → HIGH)  
✅ Verified coordination before code generation  
✅ (Optional) Scaled to 4 concurrent developers  

**You're now ready to:**
- Integrate Neo into Claude Code IDE
- Deploy Neo to your team
- Use real-time conflict detection in your workflow

---

## Questions?

1. Check `test_scenarios/NEO_MCP_QUICK_START.md` for detailed docs
2. Review the screenshots showing Alice & Bob conflict detection
3. Check `core/` for the actual conflict detection logic
4. Check `ide/` for MCP server implementation

**Branch:** main (Neo 4.0)  
**Status:** ✅ Production Ready  
**Last Updated:** 2026-09-23

# Neo MCP Testing & Setup

**Quick links for testing Neo's real-time conflict detection**

---

## 🚀 Quick Start (10 minutes)

**For developers new to Neo:**

→ **Start here:** [`GETTING_STARTED_MCP.md`](GETTING_STARTED_MCP.md)

This guide takes you from zero to running conflict detection tests in 10 minutes with:
- Virtual environment setup
- Module verification
- Activity log initialization
- 2-developer conflict test
- 4-developer scaling test

---

## 📚 Detailed Testing Guide

**For developers who want deep understanding:**

→ **Full documentation:** [`test_scenarios/NEO_MCP_QUICK_START.md`](test_scenarios/NEO_MCP_QUICK_START.md)

Includes:
- Complete MCP architecture explanation
- Activity log structure and purpose
- Risk level classification
- Conflict detection scenarios
- Screenshot evidence
- Troubleshooting guide
- Enterprise deployment info

---

## 🏗️ What is Neo?

Neo is a **real-time multi-developer conflict detection system** that prevents:
- ❌ Merge conflicts
- ❌ Breaking changes
- ❌ Wasted AI tokens

By detecting conflicts **BEFORE** code generation.

---

## ✅ What You Can Test

### 2-Developer Conflict Test

Demonstrates:
- Alice logs intent (LOW RISK)
- Bob checks conflicts (HIGH RISK detected)
- Shared activity log in action
- Real-time coordination

**Time:** 2 minutes  
**Setup:** 3 terminals  
**Evidence:** Screenshots included

### 4-Developer Scaling Test

Demonstrates:
- 4 concurrent developers
- Escalating conflict detection
- Shared log visibility
- Risk accumulation

**Time:** 5 minutes  
**Setup:** 5 terminals  
**Evidence:** Full log included

---

## 📋 Prerequisites

```bash
# Check Python version
python3 --version
# Required: 3.8+

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## 🧪 Run Tests

### Quickest Test (2 developers, 2 minutes)

```bash
# Terminal 1: Monitor the shared log
tail -f .devsync/activity-log.json

# Terminal 2: Developer Alice (run first)
python3 .devsync/test_dev.py alice "Rename authenticate() function signature" src/auth.py "authenticate (lines 10-30)"

# Terminal 3: Developer Bob (run 1 second after Alice)
python3 .devsync/test_dev.py bob "Update authenticate() calls in validate_user" src/auth.py "authenticate (lines 10-30)"
```

**Expected:** Bob gets HIGH RISK warning about Alice's work

### Full 4-Developer Test (5 minutes)

```bash
# Reset log first
echo '[]' > .devsync/activity-log.json

# Terminal 1: Monitor log
tail -f .devsync/activity-log.json

# Terminal 2: Alice
python3 .devsync/test_dev.py alice "Add OAuth2 authentication" src/auth.py "authenticate (lines 10-30)"

# Terminal 3: Bob (1 sec later)
python3 .devsync/test_dev.py bob "Add rate limiting" src/auth.py "authenticate (lines 10-30)"

# Terminal 4: Carol (2 sec later)
python3 .devsync/test_dev.py carol "Add detailed logging" src/auth.py "authenticate (lines 10-30)"

# Terminal 5: Dave (3 sec later)
python3 .devsync/test_dev.py dave "Update authenticate() calls" src/auth.py "authenticate (lines 10-30)"
```

**Expected:** All after Alice get HIGH RISK warnings

---

## 🎯 Test Evidence

### Screenshot 1: Alice's LOW RISK Check
```
✓ Checking for conflicts... → LOW
✓ No conflicting work detected. Safe to proceed.
✓ Logging activity to shared log
```

### Screenshot 2: Bob's HIGH RISK Check
```
✓ Checking for conflicts... → HIGH
✓ HIGH RISK: alice is Rename authenticate() function signature.
✓ This may cause a merge conflict. Coordinate with the other agent.
```

### Shared Activity Log
```json
[
  {
    "developer_id": "alice",
    "file_path": "src/auth.py",
    "intent": "Rename authenticate() function signature",
    "region": "authenticate (lines 10-30)",
    "timestamp": 1790140534.946883
  },
  {
    "developer_id": "bob",
    "file_path": "src/auth.py",
    "intent": "Update authenticate() calls in validate_user",
    "region": "authenticate (lines 10-30)",
    "timestamp": 1790140536.75048
  }
]
```

---

## 🏭 Components

| Component | Location | Purpose |
|-----------|----------|---------|
| **MCP Server** | `ide/mcp_neo_server.py` | Orchestrates conflict detection |
| **Activity Log** | `.devsync/activity-log.json` | Shared developer intent registry |
| **Test Harness** | `.devsync/test_dev.py` | CLI for simulating developers |
| **Core Logic** | `core/activity_log.py` | Activity logging |
| **Conflict Detection** | `core/pre_gen_check.py` | Risk classification |

---

## 📖 Documentation Files

| File | Purpose | Audience |
|------|---------|----------|
| **`GETTING_STARTED_MCP.md`** | Setup from scratch | New developers |
| **`test_scenarios/NEO_MCP_QUICK_START.md`** | Deep technical guide | Developers & engineers |
| **`ide/INTEGRATION_GUIDE.md`** | Claude Code IDE integration | IDE integrators |
| **`ide/README.md`** | Quick IDE reference | IDE users |
| **`enterprise/mcp-multitenancy/README.md`** | Enterprise deployment | DevOps/SREs |

---

## 🚨 Common Issues

### "Modules not found"
```bash
# Make sure you're in repo root and venv activated
cd ~/neo
source .venv/bin/activate
pip install -r requirements.txt
```

### "Activity log not updating"
```bash
# Reset it
echo '[]' > .devsync/activity-log.json

# Check it's there
cat .devsync/activity-log.json
```

### "LOW RISK instead of HIGH"
Ensure regions match exactly:
```bash
# Both must use same region string
"authenticate (lines 10-30)"  # Both commands
"authenticate (lines 10-30)"
```

### "MCP server won't start"
```bash
# Test it directly
python3 -m ide.mcp_neo_server
# Should output JSON init response, then wait for input
# Ctrl+C to stop
```

---

## 🎓 Learning Path

1. **10 min:** `GETTING_STARTED_MCP.md` - Get running
2. **20 min:** Run 2-developer test (this page)
3. **30 min:** Run 4-developer test (this page)
4. **1 hour:** Read `test_scenarios/NEO_MCP_QUICK_START.md` - Deep dive
5. **2 hours:** Read `ide/INTEGRATION_GUIDE.md` - IDE integration
6. **4 hours:** Read enterprise docs - Production deployment

---

## ✨ What's Working

✅ **MCP Server** - Real-time conflict orchestration  
✅ **Shared Activity Log** - Single source of truth  
✅ **Conflict Detection** - Automatic risk classification  
✅ **Real-time Coordination** - Developers see each other  
✅ **2-Developer Tests** - Proven with screenshots  
✅ **4-Developer Tests** - Scaling verified  
✅ **Documentation** - Complete setup guides  

---

## 🔗 Next Steps

- **Test it locally:** `GETTING_STARTED_MCP.md`
- **Understand it deeply:** `test_scenarios/NEO_MCP_QUICK_START.md`
- **Integrate with IDE:** `ide/INTEGRATION_GUIDE.md`
- **Deploy to production:** `enterprise/mcp-multitenancy/DEPLOYMENT_RUNBOOK.md`

---

**Branch:** main (Neo 4.0)  
**Status:** ✅ Production Ready  
**Last Updated:** 2026-09-23

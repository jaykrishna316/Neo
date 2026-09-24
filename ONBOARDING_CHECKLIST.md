# Neo MCP Onboarding Checklist

**For new developers joining the project**

---

## ✅ Before You Start

- [ ] Python 3.8+ installed (`python3 --version`)
- [ ] Git cloned (`git clone https://github.com/jaykrishna316/neo.git`)
- [ ] You're on `main` branch (`git branch`)
- [ ] 15 minutes available for onboarding
- [ ] 3+ terminal windows ready

---

## ✅ Phase 1: Environment Setup (5 minutes)

- [ ] Navigate to repo: `cd ~/neo`
- [ ] Create venv: `python3 -m venv .venv`
- [ ] Activate venv: `source .venv/bin/activate`
- [ ] Install deps: `pip install -r requirements.txt`
- [ ] Verify: `python3 -c "from core.activity_log import log_activity; print('✓')'"`

---

## ✅ Phase 2: Initialize Testing (2 minutes)

- [ ] Create log dir: `mkdir -p .devsync`
- [ ] Reset log: `echo '[]' > .devsync/activity-log.json`
- [ ] Verify empty: `cat .devsync/activity-log.json` (should output `[]`)

---

## ✅ Phase 3: Run 2-Developer Test (3 minutes)

**Terminal 1 - Activity Log Monitor:**
```bash
tail -f .devsync/activity-log.json
```

**Terminal 2 - Developer Alice (run first):**
```bash
python3 .devsync/test_dev.py alice "Rename authenticate() function signature" src/auth.py "authenticate (lines 10-30)"
```

Expected output:
```
✓ Checking for conflicts... → LOW
✓ No conflicting work detected. Safe to proceed.
```

**Terminal 3 - Developer Bob (run 1 second after Alice):**
```bash
python3 .devsync/test_dev.py bob "Update authenticate() calls in validate_user" src/auth.py "authenticate (lines 10-30)"
```

Expected output:
```
✓ Checking for conflicts... → HIGH
✓ HIGH RISK: alice is Rename authenticate() function signature.
```

- [ ] Alice's check shows LOW RISK
- [ ] Bob's check shows HIGH RISK
- [ ] Terminal 1 shows both entries in log
- [ ] Test completed successfully

---

## ✅ Phase 4: Understand the System (3 minutes)

- [ ] Read: `cat .devsync/activity-log.json` - See the shared log
- [ ] Understand: Alice first (LOW), Bob second (HIGH) due to conflict
- [ ] Realize: No merge conflicts because conflict detected BEFORE generation

---

## ✅ Documentation to Review

**Quick Reference (5 min):**
- [ ] `MCP_TESTING.md` - Hub with all links

**New Developer Setup (10 min):**
- [ ] `GETTING_STARTED_MCP.md` - Complete setup guide

**Deep Technical Dive (30 min):**
- [ ] `test_scenarios/NEO_MCP_QUICK_START.md` - Full technical guide with screenshots

**IDE Integration (20 min):**
- [ ] `ide/INTEGRATION_GUIDE.md` - How to integrate with Claude Code IDE

---

## ✅ Key Concepts to Understand

**Activity Log** (`.devsync/activity-log.json`)
- [ ] Single shared registry for all developers
- [ ] Contains: developer_id, file_path, intent, region, timestamp
- [ ] Visible to all developers in real-time

**MCP Server** (`ide/mcp_neo_server.py`)
- [ ] Orchestrates conflict detection
- [ ] Runs as subprocess started by Claude Code
- [ ] Provides 4 methods: check_conflicts, log_activity, get_active_work, get_status

**Risk Levels**
- [ ] LOW: Safe to proceed independently
- [ ] MEDIUM: Potential overlap, coordinate
- [ ] HIGH: Direct conflict, must coordinate

**Test Harness** (`.devsync/test_dev.py`)
- [ ] CLI for simulating developers
- [ ] Usage: `python3 .devsync/test_dev.py <dev_id> <intent> <file> [region]`
- [ ] Automatically calls check_conflicts and log_activity

---

## ✅ After Onboarding

### If you want to integrate with Claude Code IDE:

1. Read: `ide/INTEGRATION_GUIDE.md`
2. Add to `~/.claude/mcp_servers.json`:
```json
{
  "neo-conflict-detection": {
    "command": "python3",
    "args": ["-m", "ide.mcp_neo_server"],
    "env": {
      "NEO_MULTITENANCY": "false",
      "CLAUDE_TENANT_ID": "default"
    }
  }
}
```
3. Restart Claude Code IDE
4. Neo will run automatically before code generation

### If you want to run 4-developer test:

```bash
# Reset log
echo '[]' > .devsync/activity-log.json

# Terminal 1: Monitor
tail -f .devsync/activity-log.json

# Terminal 2-5: Developers (with 1 sec delays)
python3 .devsync/test_dev.py alice "Add OAuth2" src/auth.py "authenticate (lines 10-30)"
python3 .devsync/test_dev.py bob "Add rate limiting" src/auth.py "authenticate (lines 10-30)"
python3 .devsync/test_dev.py carol "Add logging" src/auth.py "authenticate (lines 10-30)"
python3 .devsync/test_dev.py dave "Update calls" src/auth.py "authenticate (lines 10-30)"
```

### If you hit issues:

1. Check: `GETTING_STARTED_MCP.md` - Troubleshooting section
2. Check: `test_scenarios/NEO_MCP_QUICK_START.md` - Troubleshooting section
3. Verify: Python version, venv activated, deps installed

---

## ✅ Success Criteria

You've successfully completed onboarding when you can:

- [ ] Activate venv and import Neo modules
- [ ] Initialize empty activity log
- [ ] Run 2-developer test and see:
  - Alice gets LOW RISK (first)
  - Bob gets HIGH RISK (conflict detected)
- [ ] View shared activity log with both entries
- [ ] Understand the conflict detection flow
- [ ] Explain why HIGH RISK was detected
- [ ] Know where to find documentation

---

## 📞 Quick Help

| Issue | Solution |
|-------|----------|
| "Module not found" | `pip install -r requirements.txt` |
| "Activity log not updating" | `echo '[]' > .devsync/activity-log.json` |
| "LOW RISK instead of HIGH" | Ensure regions match exactly |
| "MCP server won't start" | Check Python path and permissions |

---

## 🎓 Learning Resources

**Available immediately:**
- ✅ `GETTING_STARTED_MCP.md` - Beginner guide
- ✅ `MCP_TESTING.md` - Test hub
- ✅ This file - Onboarding checklist

**In the repo:**
- ✅ `test_scenarios/NEO_MCP_QUICK_START.md` - Technical deep dive
- ✅ `ide/INTEGRATION_GUIDE.md` - IDE integration
- ✅ `ide/README.md` - Quick reference
- ✅ `enterprise/mcp-multitenancy/README.md` - Enterprise setup

---

## ⏱️ Time Breakdown

| Phase | Time | Task |
|-------|------|------|
| **Setup** | 5 min | Python, venv, deps |
| **Initialize** | 2 min | Create log dir |
| **Test** | 3 min | Run 2-dev test |
| **Learn** | 5 min | Review docs |
| **Total** | **15 min** | Ready to contribute |

---

## ✨ Next Steps

1. ✅ Complete this checklist
2. ✅ Run the 2-developer test
3. ✅ Review `GETTING_STARTED_MCP.md`
4. 🔜 Integrate with Claude Code IDE (optional)
5. 🔜 Run 4-developer test (optional)
6. 🔜 Review enterprise deployment docs (optional)

---

## 📝 Notes

**Branch:** main (Neo 4.0)  
**Status:** ✅ Production Ready  
**Test Evidence:** Screenshots in docs  
**Last Updated:** 2026-09-23

---

## Confirmation

When you've completed this checklist:

```bash
# Verify everything works
cd ~/neo
source .venv/bin/activate

# Quick test
python3 .devsync/test_dev.py alice "Test intent" src/test.py "test_region"

# You should see:
# ✓ Checking for conflicts...
# ✓ Logging activity...
# ✓ Active work...
```

**You're now fully onboarded to Neo!** 🎉

---

**Questions?** Check the documentation files or review the test results.

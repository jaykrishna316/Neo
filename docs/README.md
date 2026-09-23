# Neo Documentation

Complete guides for setting up, testing, and using Neo's real-time multi-developer conflict detection.

---

## 📂 Documentation Structure

```
docs/
├── getting-started/          ← Start here if new to Neo
│   ├── GETTING_STARTED_MCP.md        (10 min end-to-end setup)
│   └── ONBOARDING_CHECKLIST.md       (Phase-based checklist)
│
├── testing/                  ← Testing and validation guides
│   ├── MCP_TESTING.md                (Quick test commands)
│   ├── NEO_MCP_QUICK_START.md        (Technical deep dive)
│   └── MCP_MANUAL_TEST.md            (Manual testing guide)
│
└── guides/                   ← Additional reference guides
    └── (Coming soon)
```

---

## 🎯 Quick Navigation by Use Case

### I'm New to Neo
**Goal:** Get up and running in 10 minutes

1. Read: [`getting-started/GETTING_STARTED_MCP.md`](getting-started/GETTING_STARTED_MCP.md)
2. Follow: Step-by-step setup (Python, venv, deps)
3. Run: 2-developer conflict detection test
4. Understand: How the system works

**Time:** 10 minutes | **Effort:** Low | **Outcome:** Working test

---

### I Need to Test Neo
**Goal:** Verify Neo works with quick tests

1. Read: [`testing/MCP_TESTING.md`](testing/MCP_TESTING.md)
2. Run: 2-dev or 4-dev test commands
3. View: Test results and evidence
4. Confirm: System is working

**Time:** 5 minutes | **Effort:** Low | **Outcome:** Test results

---

### I Want to Understand the System Deeply
**Goal:** Learn Neo's architecture and design

1. Read: [`testing/NEO_MCP_QUICK_START.md`](testing/NEO_MCP_QUICK_START.md)
2. Understand: MCP architecture
3. Review: Conflict detection logic
4. Study: Risk classification system

**Time:** 30 minutes | **Effort:** Medium | **Outcome:** Deep knowledge

---

### I'm Onboarding a New Team Member
**Goal:** Get someone fully up to speed

1. Give them: [`getting-started/ONBOARDING_CHECKLIST.md`](getting-started/ONBOARDING_CHECKLIST.md)
2. Have them: Follow phase-by-phase
3. Verify: Success criteria at each phase
4. Complete: Full onboarding (15 min)

**Time:** 15 minutes | **Effort:** Guided | **Outcome:** Team member ready

---

## 📚 Document Index

| Document | Purpose | Audience | Time |
|----------|---------|----------|------|
| **GETTING_STARTED_MCP.md** | Brand-new setup guide | New developers | 10 min |
| **ONBOARDING_CHECKLIST.md** | Structured onboarding | Team leads | 15 min |
| **MCP_TESTING.md** | Test hub & commands | QA/testing | 5 min |
| **NEO_MCP_QUICK_START.md** | Technical reference | Engineers | 30 min |
| **MCP_MANUAL_TEST.md** | Manual test procedures | Advanced users | 20 min |

---

## 🗂️ Folder Organization

### `getting-started/`
For developers joining the project or setting up for the first time.

**Files:**
- `GETTING_STARTED_MCP.md` — Complete 10-minute setup
- `ONBOARDING_CHECKLIST.md` — Structured onboarding

**When to use:**
- First time using Neo
- Setting up new development environment
- Onboarding new team members

---

### `testing/`
For testing, validation, and understanding Neo's conflict detection.

**Files:**
- `MCP_TESTING.md` — Quick tests and commands
- `NEO_MCP_QUICK_START.md` — Deep technical guide
- `MCP_MANUAL_TEST.md` — Manual testing procedures

**When to use:**
- Verifying Neo works
- Understanding conflict detection
- Debugging issues
- Writing tests

---

### `guides/` (Coming soon)
Additional guides for advanced topics.

**Planned:**
- IDE integration guide
- Cloud deployment guide
- Contributing guide
- API reference

---

## ✅ Which Document Should I Read?

**Answer these questions:**

1. **Have you used Neo before?**
   - NO → Start with [`getting-started/GETTING_STARTED_MCP.md`](getting-started/GETTING_STARTED_MCP.md)
   - YES → Skip to question 2

2. **Do you want to run tests?**
   - YES → Read [`testing/MCP_TESTING.md`](testing/MCP_TESTING.md)
   - NO → Go to question 3

3. **Do you need to understand the system deeply?**
   - YES → Read [`testing/NEO_MCP_QUICK_START.md`](testing/NEO_MCP_QUICK_START.md)
   - NO → You're done! Neo is ready to use

4. **Are you onboarding someone?**
   - YES → Use [`getting-started/ONBOARDING_CHECKLIST.md`](getting-started/ONBOARDING_CHECKLIST.md)
   - NO → See above

---

## 🚀 Getting Help

**If you...**

| Issue | Solution |
|-------|----------|
| Don't know where to start | Read [GETTING_STARTED_MCP.md](getting-started/GETTING_STARTED_MCP.md) |
| Want to run a quick test | Use [MCP_TESTING.md](testing/MCP_TESTING.md) |
| Need to understand conflict detection | Study [NEO_MCP_QUICK_START.md](testing/NEO_MCP_QUICK_START.md) |
| Are onboarding a team member | Follow [ONBOARDING_CHECKLIST.md](getting-started/ONBOARDING_CHECKLIST.md) |
| Hit a technical problem | Check troubleshooting in [NEO_MCP_QUICK_START.md](testing/NEO_MCP_QUICK_START.md) |

---

## 📖 Reading Order by Role

### For a Developer (First Time)
1. [`GETTING_STARTED_MCP.md`](getting-started/GETTING_STARTED_MCP.md) — Setup (10 min)
2. [`MCP_TESTING.md`](testing/MCP_TESTING.md) — Verify (5 min)
3. [`NEO_MCP_QUICK_START.md`](testing/NEO_MCP_QUICK_START.md) — Deep dive (30 min)

### For a QA/Tester
1. [`MCP_TESTING.md`](testing/MCP_TESTING.md) — Test hub (5 min)
2. [`NEO_MCP_QUICK_START.md`](testing/NEO_MCP_QUICK_START.md) — Scenarios (30 min)
3. [`MCP_MANUAL_TEST.md`](testing/MCP_MANUAL_TEST.md) — Advanced (20 min)

### For a Team Lead/Manager
1. [`ONBOARDING_CHECKLIST.md`](getting-started/ONBOARDING_CHECKLIST.md) — Checklist (5 min)
2. [`MCP_TESTING.md`](testing/MCP_TESTING.md) — Proof (5 min)
3. [`NEO_MCP_QUICK_START.md`](testing/NEO_MCP_QUICK_START.md) — Reference (30 min)

---

## 📊 Documentation Summary

| Level | Time | Goal | Start With |
|-------|------|------|------------|
| **Beginner** | 10 min | Get running | [GETTING_STARTED_MCP.md](getting-started/GETTING_STARTED_MCP.md) |
| **Intermediate** | 15 min | Verify it works | [MCP_TESTING.md](testing/MCP_TESTING.md) |
| **Advanced** | 30 min | Understand deeply | [NEO_MCP_QUICK_START.md](testing/NEO_MCP_QUICK_START.md) |
| **Onboarding** | 15 min | Team member ready | [ONBOARDING_CHECKLIST.md](getting-started/ONBOARDING_CHECKLIST.md) |

---

## 🎯 Success Indicators

**After reading the docs, you should be able to:**

- ✅ Set up Neo in your development environment
- ✅ Run a 2-developer conflict detection test
- ✅ Understand how conflict detection works
- ✅ Explain risk levels (LOW/MEDIUM/HIGH)
- ✅ Use the shared activity log
- ✅ Onboard new team members
- ✅ Debug common issues

---

## 💡 Pro Tips

1. **Start small:** Begin with [`GETTING_STARTED_MCP.md`](getting-started/GETTING_STARTED_MCP.md) even if you have experience
2. **Run tests early:** Verify Neo works on your system with [`MCP_TESTING.md`](testing/MCP_TESTING.md)
3. **Reference as needed:** Use [`NEO_MCP_QUICK_START.md`](testing/NEO_MCP_QUICK_START.md) as a reference guide
4. **Share checklists:** Use [`ONBOARDING_CHECKLIST.md`](getting-started/ONBOARDING_CHECKLIST.md) for new team members

---

## 📞 Questions?

Refer to the troubleshooting sections in:
- [`GETTING_STARTED_MCP.md`](getting-started/GETTING_STARTED_MCP.md#troubleshooting) — Common setup issues
- [`NEO_MCP_QUICK_START.md`](testing/NEO_MCP_QUICK_START.md#troubleshooting) — Technical issues

---

**Status:** ✅ Complete documentation  
**Last Updated:** 2026-09-23  
**Branch:** main (Neo 4.0)

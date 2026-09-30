# Neo Demonstrations: Side-by-Side Comparison

Quick reference for choosing which demo approach fits your needs.

## Three Approaches

| Aspect | Automatic Demo | Guided Demo | Manual Test |
|--------|---|---|---|
| **What it is** | Pre-scripted, auto-play | Step-by-step with pauses | You control everything |
| **Terminals** | Auto-open (5 or 7) | Auto-open (5 or 7) | Manual setup |
| **Pacing** | Fixed timeline | User controls (press Enter) | Full control |
| **Duration** | 2-3 minutes | 10-15 minutes | 20-30 minutes |
| **Explanation** | Minimal | Rich (step-by-step) | Self-guided |
| **Best for** | Quick demo, CI/CD | Learning, understanding | Deep testing |
| **Effort** | 1 minute setup | 1 minute setup | 5-10 min setup |

---

## Detailed Comparison

### 🚀 Automatic Demo

**Command:**
```bash
./scripts/launch_2dev_demo.sh      # 5 terminals
./scripts/launch_3dev_demo.sh      # 7 terminals
```

**How it works:**
- Launches multiple terminals
- Runs on fixed timeline (T+0s, T+1s, T+4s, etc.)
- All terminals run simultaneously
- Activity log updates in real-time
- Watchers monitor queue positions

**Timeline (2-dev):**
- T+0s: Alice declares intent
- T+1s: Bob declares intent (lock applies)
- T+4s: Alice publishes code
- T+5s: Bob gets fresh context
- T+7s: Bob publishes code
- T+8s: Demo complete

**What you see:**
- ✅ Terminals open automatically
- ✅ Activity log changing in real-time
- ✅ Lock states transitioning
- ✅ Queue positions updating
- ✅ Conflict prevention in action
- ✅ Fresh context flowing to next dev

**Best for:**
- Demos to stakeholders
- Quick verification (3 min)
- CI/CD automation
- Visual proof of concept

**Limitations:**
- Fixed timeline (can't pause)
- Hard to read details while running
- Terminal positioning varies by OS

**Success looks like:**
```
✅ Demo Complete
Alice: published (+20, -5)
Bob: published (+15, -0)
Conflicts: 0
Result: PASSED
```

---

### 📖 Guided Demo

**Command:**
```bash
./scripts/launch_guided_2dev_demo.sh     # 5 terminals, 12 min
./scripts/launch_guided_3dev_demo.sh     # 7 terminals, 15 min
```

**How it works:**
- Launches numbered terminals
- Main terminal explains each step
- Developers run on YOUR schedule (press Enter)
- Explanations at each stage
- Shows what to look for
- Provides key insights

**Timeline (user-controlled):**
- Press Enter: Alice declares
- Press Enter: Bob declares (lock appears)
- Press Enter: Alice completes
- Press Enter: Bob gets context
- Press Enter: Bob completes
- ~12 minutes total

**What you see:**
- ✅ Step 1: Alice declares → "What's happening" explanation
- ✅ Step 2: Bob declares → Queue position appears
- ✅ Step 3: Lock transitions → Guided walkthrough
- ✅ Step 4: Context flows → Explanation of staleness detection
- ✅ Step 5: Bob completes → Dependency chain shown
- ✅ Throughout: "What to look for" in each terminal

**Best for:**
- Learning how Neo works
- Understanding each step
- Onboarding new team members
- Detailed walkthrough
- Pause and inspect at any point

**Advantages:**
- YOU control the pacing
- Rich explanations
- Can pause and read activity log
- Can modify workflow mid-test
- Step-by-step learning

**Limitations:**
- Takes longer (12-15 min)
- More setup than automatic
- Not for quick demos

**Success looks like:**
```
STEP 1: Alice Declares Intent
✓ What's happening: ...
✓ What to look for: Terminal 1 shows entry
✓ Key insight: Single dev = no lock

[Press Enter to continue]

STEP 2: Bob Declares Intent
✓ Conflict detected
✓ Lock applied
✓ Bob queued at position 0

[Continue through 5 steps]

RESULT: 0 conflicts, 2 developers, full coordination
```

---

### 🛠️ Manual Terminal Test

**Setup (5-10 minutes):**
```bash
# Terminal 1: Neo server
python -m cli.neo_server --clear

# Terminal 2: Alice watcher
export NEO_DEVELOPER=alice
python -m cli.file_watcher alice

# Terminal 3: Bob watcher
export NEO_DEVELOPER=bob
python -m cli.file_watcher bob

# Terminal 4+: Declare intent and edit files
python -m cli.neo_client declare alice src/auth.py "Add OAuth2"
vim src/auth.py  # Make changes, watcher detects
```

**How it works:**
- You set up terminals manually
- File watchers monitor for changes
- You declare intent via CLI
- You edit files with your editor
- Watcher detects changes
- Activity log updates automatically
- You control everything

**What you test:**
- ✅ Real file watcher detection
- ✅ Intent declaration flows
- ✅ Lock behavior with actual file operations
- ✅ Context aggregation between developers
- ✅ Real Git operations (if enabled)
- ✅ Production-readiness validation

**Best for:**
- Deep understanding
- Testing production setup
- CI/CD integration
- Custom workflows
- Detailed validation
- Long-running tests

**Advantages:**
- Real file operations
- Full control
- Can pause anywhere
- Can modify mid-test
- Can add 4th, 5th developer
- Production-ready validation
- Repeatable testing

**Limitations:**
- Takes 20-30 minutes
- More manual setup
- Requires multiple terminals
- More complex to follow

**Success looks like:**
```
Terminal 1 (Neo Server):
✓ Server listening on :9999
✓ Activity log: 1 entry from alice
✓ Activity log: 3 entries (alice + lock + bob)
✓ Lock detected at 2 developers

Terminal 2 (Alice Watcher):
✓ Watching: src/auth.py
✓ Intent: Add OAuth2
✓ Status: Editing

Terminal 4 (CLI):
✓ Alice declared intent
✓ Bob declared intent
✓ Risk: MEDIUM (conflict detected)
✓ Bob queued at position 0
```

---

## Choosing the Right Demo

### "Show me quickly (2 minutes)"
→ Use **Automatic Demo**
```bash
./scripts/launch_2dev_demo.sh
```

### "I want to understand Neo (10 minutes)"
→ Use **Guided Demo**
```bash
./scripts/launch_guided_2dev_demo.sh
```

### "I need to validate production readiness (20 minutes)"
→ Use **Manual Test**
```bash
# See docs/LOCAL_TWO_DEVELOPER_TEST.md
```

### "I want to see it work with 3 developers (15 minutes)"
→ Use **Guided 3-Dev Demo**
```bash
./scripts/launch_guided_3dev_demo.sh
```

---

## Common Questions

**Q: Which should I do first?**  
A: Start with Automatic Demo (2 min), then Guided Demo (10 min), then Manual Test (20 min). Each builds understanding.

**Q: Can I run multiple demos?**  
A: Yes! Each clears the activity log before starting, so no conflicts.

**Q: What if terminals don't open?**  
A: Try Manual Test instead (no auto-opening required).

**Q: Can I pause the Automatic Demo?**  
A: No, but you can use Guided Demo for step-by-step control.

**Q: How do I clean up after a demo?**  
A: Activity log is ephemeral. Just close terminals. No cleanup needed.

---

## Full Guides

- [DEMO_GUIDE.md](DEMO_GUIDE.md) - All demo options
- [GUIDED_DEMO_README.md](GUIDED_DEMO_README.md) - Guided demo walkthrough
- [docs/LOCAL_TWO_DEVELOPER_TEST.md](docs/LOCAL_TWO_DEVELOPER_TEST.md) - Manual test detailed guide
- [docs/CLAUDE_CODE_TWO_DEVELOPER_TEST.md](docs/CLAUDE_CODE_TWO_DEVELOPER_TEST.md) - IDE + MCP server test

---

**Recommendation**: Start with Automatic Demo for quick understanding, then Guided Demo for learning. Both take < 20 minutes total.

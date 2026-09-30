# Guided Interactive Demo: Step-by-Step Neo in Action

Learn how Neo prevents merge conflicts through guided walkthrough with real terminals.

## Overview

This guide walks you through Neo's 2-developer and 3-developer coordination workflows step-by-step. At each step, you control the pacing by pressing Enter.

**Duration**: 10-15 minutes  
**Best for**: Understanding how Neo works  
**Requirements**: 5-7 terminal windows (opened automatically)

---

## Quick Start

```bash
# 2-Developer Demo (5 terminals, 12 minutes)
./scripts/launch_guided_2dev_demo.sh

# 3-Developer Demo (7 terminals, 15 minutes)
./scripts/launch_guided_3dev_demo.sh
```

---

## What You'll See in 2-Developer Demo

### Step 1: Alice Declares Intent (30 seconds)
**What's happening:**
- Alice declares intent to refactor password validation
- Activity log shows 1 entry
- No lock yet (only 1 developer)

**What to look for:**
- Terminal 1: Activity log viewer showing alice's entry
- Terminal 2: Alice's status showing "intent declared"
- Risk level: LOW ✅ (no conflict)

**Key insight:** Single developer = no coordination needed

---

### Step 2: Bob Declares Intent (30 seconds)
**What's happening:**
- Bob declares intent on same file
- Conflict detected (2 developers on same region)
- Lock applies automatically
- Bob gets queued

**What to look for:**
- Terminal 1: Activity log updated with lock state
- Terminal 3: Bob's status showing "QUEUED"
- Risk level: MEDIUM ⚠️ (conflict detected)
- Queue position: 0 (Bob is next)

**Key insight:** 2+ developers = automatic lock, sequential workflow

---

### Step 3: Alice Publishes Code (2 seconds)
**What's happening:**
- Alice completes her work
- Changes published (+20 lines, -5 lines)
- Delta recorded in activity log

**What to look for:**
- Terminal 1: Alice's entry marked "COMPLETED"
- Terminal 2: Shows "Code published"
- New entry shows lines_added and lines_removed

**Key insight:** Completion recorded with delta (40 tokens vs 500)

---

### Step 4: Bob Gets Fresh Context (2 seconds)
**What's happening:**
- Bob notified that Alice finished
- Fresh context loaded (Alice's changes)
- Bob's staleness cleared
- Bob promoted to active

**What to look for:**
- Terminal 1: Bob's entry shows lock_state="ACQUIRED"
- Terminal 3: Bob's status "Fresh context loaded"
- Shows Alice's changes: +20 lines, -5 lines

**Key insight:** Context flows automatically, staleness prevented

---

### Step 5: Bob Publishes Code (2 seconds)
**What's happening:**
- Bob completes work (built on Alice's changes)
- Marks `built_on="alice"` in metadata
- 0 conflicts detected

**What to look for:**
- Terminal 1: Bob's entry marked "COMPLETED"
- Terminal 3: Shows "Code published"
- Dependency chain: alice → bob

**Key insight:** Sequential workflow = zero conflicts, automatic coordination

---

## What You'll See in 3-Developer Demo

Same flow as 2-dev, but with Charlie added:

### Step 1: Alice Declares (no lock)
- Risk: LOW ✅

### Step 2: Bob Declares (lock applies)
- Risk: MEDIUM ⚠️
- Bob queued at position 0

### Step 3: Charlie Declares (lock active)
- Risk: LOW ✅ (different region)
- Charlie queued at position 1
- Waiting for Bob

### Step 4: Alice Completes
- Publishes delta
- Bob promoted to position 0

### Step 5: Bob Gets Fresh Context
- Sees Alice's changes
- Proceeds with work

### Step 6: Bob Completes
- Built on Alice
- Charlie promoted to position 0

### Step 7: Charlie Gets Fresh Context
- Sees Alice + Bob's changes
- Proceeds with work

### Step 8: Charlie Completes
- Built on Bob
- Dependency chain: alice → bob → charlie
- **0 conflicts, 3 developers, full coordination**

---

## Key Insights

### Lock Mechanism
- **1 developer**: No lock (risk: LOW)
- **2+ developers**: Lock applies (risk: MEDIUM or HIGH)
- **Sequential**: Next dev waits, then promoted
- **Auto-promotion**: When previous dev completes

### Context Staleness
- Detected when > 300ms old
- Auto-refresh triggered
- Delta sent (40 tokens) not full file (500 tokens)
- Bob/Charlie see fresh context before starting

### Conflict Prevention
- Risk assessed at intent declaration
- Lock prevents simultaneous edits
- Sequential workflow = zero conflicts
- No manual merge resolution needed

### Token Savings
- Alice: ~7 tokens (declare + complete)
- Bob: ~7 tokens (context + complete)
- Charlie: ~7 tokens (context + complete)
- **Total**: ~21 tokens
- **vs Traditional Git**: 6,000+ tokens (re-reading entire files)
- **Savings**: 99.65%

---

## Troubleshooting

### Issue: "Terminals didn't open"
**Solution**: Check if your system supports terminal automation.
- macOS: Uses AppleScript (may require permissions)
- Linux: Uses gnome-terminal or xterm
- Windows: Not supported yet (see manual test instead)

### Issue: "Activity log not updating"
**Solution**: Wait a few seconds, the watchers refresh every 2 seconds

### Issue: "Queue position not showing"
**Solution**: All developers may have completed. Run again with fresh log:
```bash
python -c "from core.activity_log import clear_log; clear_log()"
```

---

## Next Steps

After the demo:

1. **Understand the code**
   - Read: `docs/LOCAL_TESTING.md`
   - See: `core/coordination_machine.py` (lock logic)

2. **Run the tests**
   - `python tests/test_two_developer_coordination.py`
   - `python tests/test_three_developer_coordination.py`

3. **Test with real editing**
   - See: `docs/LOCAL_TWO_DEVELOPER_TEST.md`
   - Run Neo server + file watchers

4. **Deploy to your team**
   - See: `docs/CLAUDE_CODE_TWO_DEVELOPER_TEST.md` (IDE integration)
   - Configure MCP server in `.claude/settings.json`

---

## Video Walkthrough (Planned)

Coming soon: Step-by-step video showing exactly what to look for at each stage.

---

For more details, see:
- [DEMO_GUIDE.md](DEMO_GUIDE.md) - All demo approaches
- [README.md](README.md) - Full documentation
- [docs/LOCAL_TESTING.md](docs/LOCAL_TESTING.md) - Comprehensive testing guide

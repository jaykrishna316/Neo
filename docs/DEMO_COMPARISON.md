# Neo Demo Options: Choose Your Learning Style

## Three Demo Approaches

Neo provides three ways to see multi-developer coordination in action:

### 1. 🚀 Automatic Demo (Fastest - 2-3 minutes)
**Best for**: Quick verification, CI/CD, demos at meetups

```bash
./launch_2dev_demo.sh      # 5 terminals, auto-runs
./launch_3dev_demo.sh      # 7 terminals, auto-runs
```

**What you get**:
- Terminals open automatically
- Developers run on fixed timeline (T+0s, T+1s, T+4s, etc.)
- Activity log updates in real-time
- All 5 or 7 windows run in parallel
- See the full workflow end-to-end

**Learning curve**: ⭐ (just watch)

**Documentation**: See `DEMO_GUIDE.md`

---

### 2. 📖 Guided Interactive Demo (Ideal for Learning - 10-15 minutes)
**Best for**: Learning, onboarding, understanding the mechanism

```bash
./launch_guided_2dev_demo.sh      # 5 terminals, step-by-step
./launch_guided_3dev_demo.sh      # 7 terminals, step-by-step
```

**What you get**:
- Numbered terminals (Terminal 1, 2, 3, etc.)
- Main guidance terminal with step-by-step instructions
- Press Enter to advance to next step
- At each step:
  - 📍 What's happening (explanation)
  - 👁️ What to look for (in each terminal)
  - 💡 Key insights (why Neo does this)
- Complete timeline with annotations
- Full explanations of queue progression

**Learning curve**: ⭐⭐⭐ (guided learning)

**Documentation**: See `GUIDED_DEMO_README.md`

**Example: Step 2 of 2-Dev Demo**
```
═══════════════════════════════════════════════════════════════
STEP 2: Bob Declares Intent (Lock Applied)
═══════════════════════════════════════════════════════════════

📍 What's happening:
   Bob declares intent on same file (auth.py) → Conflict detected!
   Lock applies automatically to prevent wasted code generation

👁️ What to look for:

  Terminal 1 (Activity Log):
    • Watch for Bob's entry appearing
    • Bob's lock_state: WAITING
    • queue_position: 1 (first in queue, waiting for alice)

  Terminal 3 (Developer Bob):
    • ⏱️  [T+1s] Declaring intent...
    • ⏱️  [T+2s] Checking for conflicts...
    • ⚠️  Risk Level: MEDIUM
    • 🔒 Queue Position: 1
    • ⏳ Waiting for: alice

💡 Key insight:
   This is the key Neo feature:
   • Bob doesn't start generating code
   • Bob waits for Alice to finish
   • This prevents merge conflicts and wasted tokens

Press Enter to continue...
```

---

### 3. 🛠️ Manual Terminal Test (Most Thorough - 20-30 minutes)
**Best for**: Deep understanding, CI/CD validation, integration testing

Requires running multiple terminal windows manually with server and file watchers.

**What you get**:
- Full Neo server running
- File watcher detection
- Real editing with vim/nano/VS Code
- Can pause and inspect at any point
- Can modify workflow mid-test
- Full control over timing and content

**Learning curve**: ⭐⭐⭐⭐ (comprehensive)

**Documentation**: See `docs/LOCAL_TWO_DEVELOPER_TEST.md`

---

## Quick Comparison

| Feature | Automatic | Guided | Manual |
|---------|-----------|--------|--------|
| **Setup Time** | 1 min | 1 min | 5-10 min |
| **Run Time** | 2-3 min | 10-15 min | 20-30 min |
| **Terminals Open** | Auto | Auto | Manual |
| **Pacing** | Fixed timeline | User-controlled | Full control |
| **Guidance** | Self-guided | Step-by-step | Documentation |
| **Activity Log** | Real-time | Real-time | Real file ops |
| **Best For** | Quick demo | Learning | Deep testing |
| **Can Pause** | ✅ (between terminals) | ✅ (press Enter) | ✅ (anytime) |
| **Can Modify** | ❌ | ❌ | ✅ |

---

## What Each Demo Shows

### Automatic Demo
1. All terminals open at once
2. Developers run on timer (fast playback)
3. Activity log updates in real-time
4. Watch the full workflow end-to-end
5. See lock states and queue positions

**Best for**: Understanding the big picture quickly

### Guided Demo
1. Terminals open one by one
2. Each step explained before it runs
3. Main terminal tells you what to look for
4. You control pacing (press Enter)
5. Learn why at each step
6. Understand queue progression

**Best for**: Deep understanding and onboarding

### Manual Test
1. You control everything
2. Run server in terminal 1
3. File watchers in terminals 2-3
4. Declare intent manually
5. Edit files and watch detection
6. Can pause/inspect/modify

**Best for**: Validation and advanced testing

---

## Recommended Learning Path

### For First-Time Users
1. **Start**: Guided 2-Dev Demo (10 min)
   ```bash
   ./launch_guided_2dev_demo.sh
   ```
   → Understand the basics with explanations

2. **Explore**: Guided 3-Dev Demo (12 min)
   ```bash
   ./launch_guided_3dev_demo.sh
   ```
   → See queue progression

3. **Verify**: Automatic Demo (3 min)
   ```bash
   ./launch_2dev_demo.sh
   ```
   → Quick verification of understanding

### For Integration Testing
1. **Quick Check**: Automatic Demo (3 min)
   ```bash
   ./launch_2dev_demo.sh
   ```
   → Verify workflow works

2. **Thorough Test**: Manual Terminal Test (30 min)
   ```bash
   docs/LOCAL_TWO_DEVELOPER_TEST.md
   ```
   → Full validation with real operations

### For CI/CD Integration
```bash
# Just run automatic demos (no user input needed)
./launch_2dev_demo.sh
# Check activity log was created correctly
test -f .devsync/activity-log.json && echo "PASS" || echo "FAIL"
```

---

## Terminal Numbering (Guided Demos)

### 2-Dev Guided Demo (5 Terminals)
```
┌─ Terminal 1: Activity Log Viewer
│  └─ Real-time JSON updates
│
├─ Terminal 2: Developer Alice
│  └─ Declares intent, generates, publishes
│
├─ Terminal 3: Developer Bob
│  └─ Declares intent, waits, then generates
│
├─ Terminal 4: Watcher Alice
│  └─ Monitors Alice's conflict state
│
└─ Terminal 5: Watcher Bob
   └─ Monitors Bob's queue position and lock state
```

### 3-Dev Guided Demo (7 Terminals)
```
┌─ Terminal 1: Activity Log Viewer
│  └─ Real-time monitoring of all developers
│
├─ Terminal 2: Developer Alice (goes first)
├─ Terminal 3: Developer Bob (goes second)
├─ Terminal 4: Developer Charlie (goes third)
│  └─ Queue progression: Alice → Bob → Charlie
│
├─ Terminal 5: Watcher Alice
├─ Terminal 6: Watcher Bob
└─ Terminal 7: Watcher Charlie
   └─ Each watches their developer's state
```

---

## Key Insights from Each Demo

### Automatic Demo Shows
- **Speed**: How fast coordination happens (3 seconds for full workflow)
- **Concurrency**: Multiple terminals active simultaneously
- **Real-time updates**: Activity log updates as events happen
- **Lock states**: ACQUIRED, WAITING, RELEASED transitions

### Guided Demo Shows
- **Why Bob waits**: Explains conflict prevention
- **Lock holder isolation**: Why Alice doesn't see Bob as conflict
- **Token savings**: How delta refresh saves 90%+ tokens
- **Queue progression**: How queue automatically promotes developers
- **Context freshness**: How Bob builds on Alice's work

### Manual Test Shows
- **Real server coordination**: Not just simulation
- **File watcher detection**: Actual file system monitoring
- **Flexible timing**: Can test edge cases
- **State inspection**: Can pause and check state anytime
- **Production readiness**: Proves it works in real scenarios

---

## Which Should You Use?

**Choose Guided if you...**
- Are new to Neo
- Want to understand HOW it works
- Are onboarding your team
- Want explanations at each step
- Have 10-15 minutes

**Choose Automatic if you...**
- Already understand the basics
- Want quick verification
- Are in a hurry (2-3 min)
- Need CI/CD automation
- Want the spectacle

**Choose Manual if you...**
- Need production validation
- Want to test edge cases
- Can modify the workflow
- Have 30+ minutes
- Need to verify with real file ops

---

**Recommendation**: Start with **Guided 2-Dev Demo**, then explore **Automatic Demo**, then use **Manual Test** for validation.

Each gives you a different angle on Neo's coordination mechanism!

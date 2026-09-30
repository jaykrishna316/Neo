# Neo Guided Interactive Demo

Interactive step-by-step demos with terminal numbering and guidance.

## Quick Start

### 2-Developer Guided Demo (5 Terminals)

```bash
./launch_guided_2dev_demo.sh
```

Opens 5 numbered Terminal windows and guides you through each step with:
- Terminal numbering for easy reference
- Step-by-step instructions in the main terminal
- What to look for in each terminal
- Press Enter to advance to next step
- Full explanations of Neo's coordination mechanism

**Timeline:**
- **STEP 1**: Developer Intent Declaration (Alice & Bob)
- **STEP 2**: Bob Declares Intent (Lock Applied)
- **STEP 3**: Alice Checks Conflicts (No conflicts for lock holder)
- **STEP 4**: Alice Generates & Publishes (Lock Released)
- **STEP 5**: Bob Gets Fresh Context & Starts Generating
- **STEP 6**: Bob Publishes (Workflow Complete)

### 3-Developer Guided Demo (7 Terminals)

```bash
./launch_guided_3dev_demo.sh
```

Opens 7 numbered Terminal windows and guides you through queue progression with:
- Terminal numbering (1 = Activity Log, 2-4 = Developers, 5-7 = Watchers)
- Queue position tracking (Who's locked, who's waiting, in what order)
- Automatic promotion when developers complete
- Guided view of context flow from Alice → Bob → Charlie

**Timeline:**
- **STEP 1**: Alice Declares Intent (First Developer - No Lock)
- **STEP 2**: Bob Declares Intent (Gets Queued)
- **STEP 3**: Charlie Declares Intent (Queued Behind Bob)
- **STEP 4**: Alice Completes → Bob Promoted
- **STEP 5**: Bob Generates Based on Alice's Work
- **STEP 6**: Bob Publishes → Charlie Promoted
- **STEP 7**: Charlie Generates & Publishes (Complete)

## Terminal Layout Reference

### 2-Developer Demo
```
Terminal 1 │ Activity Log Viewer
           │ (Real-time JSON updates with lock states)
───────────┼─────────────────────────────────────────
Terminal 2 │ Developer Alice
Terminal 3 │ Developer Bob
Terminal 4 │ Watcher Alice
Terminal 5 │ Watcher Bob
```

### 3-Developer Demo
```
Terminal 1 │ Activity Log Viewer
───────────┼─────────────────────────────────────────
Terminal 2 │ Developer Alice
Terminal 3 │ Developer Bob
Terminal 4 │ Developer Charlie
───────────┼─────────────────────────────────────────
Terminal 5 │ Watcher Alice
Terminal 6 │ Watcher Bob
Terminal 7 │ Watcher Charlie
```

## How to Use

1. **Run the script**:
   ```bash
   ./launch_guided_2dev_demo.sh
   # or
   ./launch_guided_3dev_demo.sh
   ```

2. **Read the initial instructions** - Shows window layout and overview

3. **For each step**:
   - Read the guidance text in the main terminal
   - Look at the specific terminals mentioned
   - Watch for the specific outputs described
   - Press Enter when ready to proceed to next step

4. **Follow what to look for**:
   - Each step shows exactly which terminals to watch
   - Explains what output you should see
   - Points out key events (lock states, queue positions, etc.)
   - Explains the "why" behind what's happening

5. **After complete**:
   - Terminal windows stay open for further inspection
   - Check activity log: `cat .devsync/activity-log.json | python -m json.tool`
   - Close individual terminals when done

## What You'll Learn

### From the 2-Developer Demo

1. **Lock Mechanism**: How Neo applies locks when conflicts detected
2. **Queue Position**: Bob gets position 1 when waiting
3. **Lock Holder Isolation**: Alice doesn't see Bob as a conflict (he's just waiting)
4. **Fresh Context**: Bob gets delta from activity log, not full file re-read
5. **Automatic Promotion**: Bob promoted when Alice releases lock
6. **Token Savings**: 1,000s of tokens saved vs traditional Git

### From the 3-Developer Demo

1. **Queue Progression**: Alice → Bob → Charlie order maintained
2. **Automatic Promotion Chain**: Each completion promotes next developer
3. **Position Tracking**: Queue positions update as developers complete
4. **Context Aggregation**: Later developers build on all predecessors
5. **Scaling**: System handles 3+ developers smoothly
6. **Zero Conflicts**: All prevented at semantic layer

## Key Neo Concepts Demonstrated

### Lock States
- **ACQUIRED**: Developer has the lock (can generate safely)
- **WAITING**: Developer waiting for lock holder to complete
- **RELEASED**: Lock released (only shown in history)

### Queue Position
- **Position 0**: Next in queue (will get lock when current holder finishes)
- **Position 1+**: Further back in queue
- **null**: Not in queue (either has lock or no conflicts)

### Risk Levels
- **LOW**: No conflicts detected (safe to generate)
- **MEDIUM**: Conflicts detected (must wait)
- **HIGH**: Critical conflicts (blocked)

### Activity Log Shows
- Developer declarations
- Lock state transitions
- Queue positions
- Timestamp of each event
- Context changes (lines added/removed)

## Troubleshooting

### Terminals don't open
**Problem**: `open -a Terminal` fails on non-macOS
**Solution**: Edit the script to use `gnome-terminal`, `xterm`, or `konsole`

### Script won't start
**Problem**: Permission denied
**Solution**: `chmod +x launch_guided_*dev_demo.sh`

### Activity log not showing
**Problem**: No entries appearing
**Solution**: Give developers a moment to start (check timer in launcher output)

### Can't read fast enough
**Problem**: Text scrolling too quickly
**Solution**: Press Ctrl-C in the guidance terminal to pause, then resume by pressing Enter

## Comparing Guided vs. Automatic

| Aspect | Guided Demo | Automatic Demo |
|--------|------------|----------------|
| **Pacing** | User controls (press Enter) | Automatic timeline |
| **Guidance** | Yes, step-by-step | Self-guided (DEMO_GUIDE.md) |
| **Learning** | Better for understanding | Better for quick demo |
| **Speed** | 5-10 minutes per demo | 1-2 minutes per demo |
| **Terminals** | Numbered with clear layout | Simple opening |
| **Best For** | Learning, onboarding, first-time | Quick verification, CI/CD |

## Next Steps After Demo

1. **Manual Testing**: Try `docs/LOCAL_TWO_DEVELOPER_TEST.md`
2. **Unit Tests**: `pytest tests/test_phase2_waiting_agent_fix.py -v`
3. **IDE Integration**: Configure MCP server in Claude Code
4. **Scaling**: Try with more developers by extending the scripts

## Activity Log Inspection

After demo completes, check the complete activity log:

```bash
# Pretty-print the activity log
cat .devsync/activity-log.json | python -m json.tool

# Count entries by developer
python -c "
import json
with open('.devsync/activity-log.json') as f:
    data = json.load(f)
    devs = {}
    for entry in data:
        dev = entry.get('developer_id')
        devs[dev] = devs.get(dev, 0) + 1
    print(f'Total entries: {len(data)}')
    for dev, count in sorted(devs.items()):
        print(f'  {dev}: {count} entries')
"

# Show lock state transitions
python -c "
import json
with open('.devsync/activity-log.json') as f:
    data = json.load(f)
    print('Lock State Timeline:')
    for i, entry in enumerate(data):
        dev = entry.get('developer_id')
        lock = entry.get('lock_state', 'N/A')
        queue = entry.get('queue_position', '')
        intent = entry.get('intent', '')
        print(f'{i+1}. {dev}: {lock} (intent: {intent})')
        if queue != '':
            print(f'   └─ Queue position: {queue}')
"
```

## Design Philosophy

The guided demos follow Neo's core principle: **prevent conflicts BEFORE they happen**.

Rather than fixing merge conflicts after generation, Neo:
1. Detects intent at declaration time
2. Classifies conflict risk semantically
3. Queues developers automatically
4. Provides fresh context at right time
5. Prevents any code generation conflicts

The guided demos make this flow visible at every step.

---

**Status**: ✅ Production-Ready  
**Best For**: Learning, onboarding, understanding Neo's coordination  
**Time Required**: 10-15 minutes per demo  

See `DEMO_GUIDE.md` for the automated (non-guided) version.

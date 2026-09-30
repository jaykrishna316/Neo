# Neo Multi-Developer Demo Guide

This guide explains how to run the Neo coordination demo with multiple Terminal windows showing real-time developer workflow and conflict detection.

## Quick Start

### 2-Developer Demo (5 Terminal Windows)

```bash
./launch_2dev_demo.sh
```

This opens 5 Terminal windows:
- **Terminal 1**: Activity Log Viewer (real-time monitoring)
- **Terminal 2**: Developer Alice (declares intent, checks conflicts, generates code)
- **Terminal 3**: Developer Bob (waits for Alice, gets context, generates code)
- **Terminal 4**: Watcher Alice (monitors Alice's conflicts)
- **Terminal 5**: Watcher Bob (monitors Bob's queue position)

**Timeline:**
- **T+0s**: Alice declares intent on `auth.py` → Risk: LOW (no conflict, no lock)
- **T+1s**: Bob declares intent on same file → Risk: MEDIUM (conflict detected, Bob gets queued)
- **T+4s**: Alice publishes code (lock released)
- **T+5s**: Bob gets fresh context from Alice's changes
- **T+7s**: Bob publishes code (both developers done)

### 3-Developer Demo (7 Terminal Windows)

```bash
./launch_3dev_demo.sh
```

This opens 7 Terminal windows:
- **Terminal 1**: Activity Log Viewer
- **Terminal 2-4**: Developers Alice, Bob, Charlie
- **Terminal 5-7**: Watchers Alice, Bob, Charlie

**Timeline:**
- **T+0s**: Alice declares intent → Risk: LOW
- **T+1s**: Bob declares intent → Risk: MEDIUM (queued behind Alice)
- **T+2.5s**: Charlie declares intent → Risk: MEDIUM (queued behind Bob)
- **T+4s**: Alice publishes (lock released to Bob)
- **T+5s**: Bob starts generating (Alice's context available)
- **T+7s**: Bob publishes (lock released to Charlie)
- **T+8.5s**: Charlie starts generating (Alice + Bob context available)
- **T+11.5s**: Charlie publishes (all done)

## What You'll See

### Activity Log Viewer Window

Shows real-time updates of developer activity:
```
📊 ACTIVITY LOG VIEWER (Updated: 14:23:45)
================================================

Total Entries: 3

DEVELOPER ACTIVITY:

  👤 ALICE
     📄 File: auth.py
     💭 Intent: Add bcrypt password hashing
     🔒 Lock State: ACQUIRED

  👤 BOB
     📄 File: auth.py
     💭 Intent: Add JWT token support
     🔒 Lock State: WAITING (Queue: 0)
```

### Developer Window

Shows developer workflow:
```
👤 DEVELOPER: ALICE
====================================================
📄 Workspace: auth.py
💭 Task: Add bcrypt password hashing

⏱️  [T+0s] Declaring intent to modify auth.py...
✅ Intent logged

⏱️  [T+1s] Checking for conflicts...
✅ Risk Level: LOW
   Message: No conflicts detected

⏱️  [T+3s] Generating code...
   ✏️  Generated: password_hash() function
   ✏️  Generated: verify_hash() function
   ✏️  Generated: bcrypt integration

⏱️  [T+4s] Publishing changes...
✅ Code published to repository
```

### Watcher Window

Shows conflict monitoring:
```
👁️  WATCHER: BOB
====================================================
📊 Monitoring conflicts for: bob@auth.py

⏱️  [T+1s] Initial check
   Risk = MEDIUM | Queue Position: 0

⏱️  [T+5s] Retry after Alice completes
   Risk = LOW ✅
   Lock released - Bob can proceed!
```

## How It Works

### Phase 2 Fix: Lock Holder Isolation

The key feature demonstrated is that **lock holders don't see waiting developers as conflicts**.

When Alice holds the lock on `auth.py`:
- Alice checks conflicts → Sees no issues (Bob is just waiting, not conflicting)
- Bob checks conflicts → Sees Alice as holding lock, gets MEDIUM risk and queued
- Watchers see the queue state and monitor for lock release

This prevents wasted code generation cycles:
- Alice generates code without worrying about Bob
- Bob waits instead of generating potentially conflicting code
- When Alice finishes, Bob gets fresh context and generates

### Lock States Tracked

Each developer entry in the activity log has:
- **`lock_state`**: ACQUIRED, WAITING, or RELEASED
- **`lock_holder`**: Developer ID holding the lock
- **`queue_position`**: Position in queue if waiting (0 = next to acquire)
- **`waiting_for`**: Developer ID this one is waiting for

### Real-Time Coordination

1. **Intent Declaration** → logged to `.devsync/activity-log.json`
2. **Conflict Check** → Pre-generation check (no wasted tokens)
3. **Lock Acquisition** → ACQUIRED or WAITING state
4. **Queue Position** → Updated in real-time
5. **Context Merge** → Fresh context available when lock released
6. **Code Generation** → Happens only when safe
7. **Lock Release** → Next developer promoted automatically

## Files Overview

### Launcher Scripts
- `launch_2dev_demo.sh` - Opens 5 Terminal windows for 2-developer demo
- `launch_3dev_demo.sh` - Opens 7 Terminal windows for 3-developer demo

### Individual Scripts (in `bin/`)
- `activity_log_viewer.sh` - Real-time activity log monitor
- `developer_alice.sh` - Developer Alice workflow
- `developer_bob.sh` - Developer Bob workflow
- `developer_charlie.sh` - Developer Charlie workflow
- `watcher_alice.sh` - Monitors Alice's conflicts
- `watcher_bob.sh` - Monitors Bob's conflicts
- `watcher_charlie.sh` - Monitors Charlie's conflicts

## Customization

### Run Individual Scripts Manually

You can also run individual scripts in any Terminal:

```bash
# Terminal 1: Monitor activity log
./bin/activity_log_viewer.sh

# Terminal 2 (separate): Developer Alice
./bin/developer_alice.sh

# Terminal 3 (separate): Developer Bob
./bin/developer_bob.sh
```

### Modify Timings

Edit the Python code in each script to adjust timing:
- `time.sleep(N)` controls delays between steps
- Modify intent messages to test different scenarios
- Add more developers by copying developer/watcher scripts

### Extend to More Developers

1. Create `bin/developer_dave.sh` and `bin/watcher_dave.sh`
2. Update `launch_*dev_demo.sh` to open the new scripts
3. Adjust timings if needed (each developer should declare intent sequentially)

## Troubleshooting

### No Terminal Windows Open

**Problem**: `open -a Terminal` fails on non-macOS or in WSL
**Solution**: Edit launcher script to use `gnome-terminal`, `xterm`, or `konsole` instead

### Scripts Not Executable

**Problem**: Permission denied when running launcher
**Solution**: 
```bash
chmod +x launch_2dev_demo.sh launch_3dev_demo.sh
```

### Activity Log Not Showing

**Problem**: No entries in Activity Log Viewer
**Solution**: Ensure developers are actually running (check other Terminal windows)

### Python Module Errors

**Problem**: "ModuleNotFoundError: No module named 'core'"
**Solution**: Ensure you're running from the Neo project directory and Python path includes `.`

## Expected Results

### After Running 2-Developer Demo

```
✅ Alice declares intent (T+0s)
✅ Bob declares intent (T+1s) and gets queued
✅ Activity log shows WAITING state for Bob
✅ Alice publishes (T+4s)
✅ Bob's watcher sees lock release
✅ Bob gets fresh context (T+5s)
✅ Bob publishes (T+7s)
✅ Activity log shows sequence of events with lock states
```

### After Running 3-Developer Demo

```
✅ All 3 developers declare intent sequentially
✅ Alice: ACQUIRED (no lock)
✅ Bob: WAITING (queue position 0)
✅ Charlie: WAITING (queue position 1)
✅ Alice publishes → Bob promoted
✅ Bob publishes → Charlie promoted
✅ Charlie publishes
✅ Activity log shows complete queue progression
```

## Verification Checklist

- [ ] Multiple Terminal windows opened (not just panes)
- [ ] Activity log shows real-time updates
- [ ] Developers show timing and workflow steps
- [ ] Watchers monitor and report lock state changes
- [ ] Lock states transition: LOW → MEDIUM → LOW
- [ ] Queue positions update as developers complete
- [ ] No duplicate entries in activity log
- [ ] Fresh context available to waiting developers

## Next Steps

After verifying the demo works:

1. **Run Unit Tests**: `pytest tests/test_phase2_waiting_agent_fix.py -v`
2. **Run All Tests**: `python run_parallel_tests.sh`
3. **Check Integration**: Verify MCP server loads in Claude Code IDE
4. **Merge to Main**: Push changes to main branch when ready for release

---

**For Questions**: Check `CLAUDE.md` for Neo architecture overview and MCP server configuration.

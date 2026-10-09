# Neo Activity Log Watcher

Real-time monitoring of multi-developer coordination with live activity log updates.

---

## Quick Start (3 Terminals)

### Terminal 1: Watch Activity Log
```bash
cd Neo
python3 watch_activity_log.py
```

This terminal will show:
- ✅ Real-time activity updates
- 🔒 Lock state changes
- ⏳ Queue positions
- ✓ Developer completions

### Terminal 2: Alice (First Developer)
```bash
cd Neo
python3 tests/devin_multi_agent_test.py alice
```

You'll see:
- Alice declares intent on `auth.py`
- LOW RISK (first developer, no conflicts)
- Alice works for 5 seconds
- Alice completes

### Terminal 3: Bob (Second Developer)
**Start while Alice is still working:**
```bash
cd Neo
python3 tests/devin_multi_agent_test.py bob
```

You'll see:
- Bob declares intent on same file
- MEDIUM RISK (Alice working on same file)
- **LOCK APPLIED** (queued for Alice to finish)
- Bob waits for lock release
- Lock releases when Alice completes
- Bob proceeds with fresh context

---

## Watch Terminal Output

As developers work, the watch terminal updates continuously:

```
==================================================
NEO ACTIVITY LOG WATCHER - 15:32:45 (elapsed: 3.2s)
==================================================

📊 Summary:
   Total entries: 4
   Developers: alice, bob
   Completed: 0
   With locks: 2 (waiting: 1)

📝 Activity Log:
  1. [15:32:42] alice        auth.py         Refactor password validation...
  2. [15:32:42] alice        auth.py         Lock acquired on region...
  3. [15:32:43] bob          auth.py         Add password strength...
  4. [15:32:43] bob          auth.py         Waiting for lock held by alice...

🔒 Lock Details:
   alice        HOLDS lock (holder=alice, reason=MEDIUM_CONFLICT)
   bob          WAITS queue[0] for alice
```

---

## Understanding the Output

### Summary Section
- **Total entries**: Number of activity log entries
- **Developers**: Who is working (names extracted from entries)
- **Completed**: How many developers finished
- **With locks**: How many entries have lock state
  - `waiting`: Developers queued for locks

### Activity Log Section
Each line shows:
```
[TIMESTAMP] DEVELOPER FILE INTENT [LOCK_STATE] [QUEUE_INFO] [STATUS]
```

- `[15:32:42]` - When activity occurred
- `alice` - Developer ID
- `auth.py` - File being modified
- `Refactor password...` - What they're trying to do
- `[ACQUIRED]` - Lock state (ACQUIRED, WAITING, RELEASED)
- `[Q:0]` - Queue position if waiting
- `[✓ DONE]` - Mark if completed

### Lock Details Section
Shows who holds locks and who's waiting:

```
alice        HOLDS lock (holder=alice, reason=MEDIUM_CONFLICT)
bob          WAITS queue[0] for alice
```

- **HOLDS lock**: Developer has exclusive lock
- **WAITS queue[N]**: Developer queued at position N
  - `queue[0]` = next in line
  - `queue[1]` = 2nd in line, etc.

---

## Multi-Developer Testing (3 Developers)

Run the 3-developer test to see queue behavior:

### Terminal 1: Watch
```bash
python3 watch_activity_log.py
```

### Terminal 2: Alice
```bash
python3 tests/test_three_developer_coordination.py alice
```

### Terminal 3: Bob
**Wait 1-2 seconds, then:**
```bash
python3 tests/test_three_developer_coordination.py bob
```

### Terminal 4: Charlie (Optional)
**Wait 1-2 more seconds, then:**
```bash
python3 tests/test_three_developer_coordination.py charlie
```

You'll see:
1. Alice: LOW RISK (first dev)
2. Bob: MEDIUM RISK (queued at position 0)
3. Charlie: MEDIUM RISK (queued at position 1)
4. Alice completes → Bob promoted (queue updates)
5. Bob completes → Charlie promoted
6. Charlie completes → All done, 0 conflicts

---

## Staleness Detection Demo

To see staleness detection in action:

### Terminal 1: Watch
```bash
python3 watch_activity_log.py
```

### Terminal 2: Alice (Long Work)
```bash
python3 tests/devin_staleness_test.py alice
```

Alice will work for 15 seconds. Watch terminal shows entries getting older.

### Terminal 3: Bob (Staleness Watcher)
**Start while Alice is working:**
```bash
python3 tests/devin_staleness_test.py bob
```

Bob will detect staleness (entries > 300ms old) and auto-refresh. Watch terminal updates as staleness grows and Alice's completion is detected.

---

## Troubleshooting

### Watch terminal shows no entries
**Problem**: Activity log file doesn't exist yet
**Solution**: Start a developer test first (alice/bob), watch will see updates

### Watch terminal stops updating
**Problem**: Activity log watcher crashed
**Solution**: Restart with `python3 watch_activity_log.py`

### Entries show old timestamps
**Problem**: Tests are slow or lagging
**Solution**: This is normal. Staleness detection handles this.

### Can't see lock state changes
**Problem**: Developer finished too quickly
**Solution**: Run the 15-second staleness test instead of the 5-second quick test

---

## Architecture

The watcher parses the activity log directly:

```
Developer Process 1
        ↓
        ├─→ Logs activity to .devsync/activity-log.json
        ↓
Developer Process 2
        ↓
        ├─→ Logs activity to .devsync/activity-log.json
        ↓
        ↓
Watch Terminal Reads (every 500ms)
        ↓
        ├─→ Parses entries
        ├─→ Extracts lock state
        ├─→ Shows real-time updates
```

---

## Tips

1. **Position Terminals Side-by-Side**
   - Watch terminal on left
   - Developer terminals on right
   - See updates in real-time

2. **Monitor Lock Transitions**
   - Watch as lock state changes from ACQUIRED → WAITING → ACQUIRED
   - Queue positions update as developers complete

3. **Follow the Flow**
   - First developer: FREE (no locks)
   - Second dev: LOCKED (queued)
   - Third dev: LOCKED (queued behind 2nd)
   - As each completes, next one is promoted

4. **Understand Token Savings**
   - Watch shows how context flows between developers
   - No wasted re-generations (0 conflicts guaranteed)

---

## Advanced: Custom Activity Log Path

```bash
# If using custom log directory
python3 watch_activity_log.py --log-path /custom/path/activity-log.json
```

Note: The default watcher script uses `.devsync/activity-log.json` only. For custom paths, edit the script.

---

## Reference

See `docs/TEAM_ONBOARDING_DEVIN.md` for full team coordination workflows.

---

## What's Next

After seeing the activity log watcher in action:

1. **Try Multi-Team Isolation** (when available)
   - Multiple teams using same Neo instance
   - Activity log watcher shows only your team

2. **Cloud-Based Monitoring** (Phase 2)
   - Real-time sync across laptops
   - Watcher connects to Supabase cloud activity log
   - Multi-laptop coordination without file sharing

3. **IDE Integration** (Phase 3)
   - Developers use Claude Code IDE
   - Conflict checks happen automatically
   - Activity log watcher shows IDE coordination

---

**Run the watcher and see Neo coordinate developers in real-time! 🚀**

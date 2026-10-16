# Running 2-Developer Test in Claude Terminals
## See Blocking and Lock Coordination in Real-Time

This guide shows how to run the actual 2-developer coordination test using Claude terminals, where you can see **exactly where Bob gets blocked** and watch the activity log update live.

---

## What You'll See

```
Alice declares intent on auth.py
  ↓ (no lock, only 1 developer)

Bob checks for conflicts
  ↓ (Risk=MEDIUM, alice is working on same region)

Bob declares intent
  ↓ (Lock acquired for alice)
  🚫 Bob is now BLOCKED, queue_position=0, waiting_for="alice"

Alice completes work (writes +20 lines, -5 lines)
  ↓ (lock released)

Bob now sees fresh context
  ✅ Bob can now proceed, building on Alice's changes

Bob completes work (writes +15 lines)
  ↓
✅ TEST PASSED: 0 conflicts
```

---

## Setup: Three Claude Terminals

You'll need **3 Claude Code terminals** open simultaneously:

1. **Terminal 1** - Watcher (monitor activity log in real-time)
2. **Terminal 2** - Alice (first developer)
3. **Terminal 3** - Bob (second developer)

---

## Terminal 1: Activity Log Watcher (Watch Updates Live)

**Create a new Claude terminal and paste this:**

```bash
cd /home/user/Neo && python3 scripts/watch_activity_log.py
```

**What you'll see:**

```
==================================================
NEO ACTIVITY LOG WATCHER
==================================================

Showing where code is BLOCKED (⏳) and LOCKED (🔒):
  ⏳ BLOCKED = Developer waiting for another's lock
  🔒 LOCKED  = Developer holding the lock
  ✅ DONE    = Developer completed work

--------------------------------------------------
Time     | Status     | Developer  | Intent
--------------------------------------------------
16:00:05 | 🔒 LOCKED  | alice      | Refactor password validation...
16:00:06 | ⏳ BLOCKED  | bob        | Waiting for lock held by alice...
16:00:15 | ✅ DONE    | alice      | COMPLETED: Refactored password...
16:00:16 |            | bob        | Add password strength checking...
16:00:22 | ✅ DONE    | bob        | COMPLETED: Added password strength...

[SUMMARY] 🔒 0 locked ⏳ 0 waiting ✅ 2 done | Total entries: 7
```

---

## Terminal 2: Alice (First Developer)

**Create a new Claude terminal with this prompt:**

```
You are Alice, a developer in the Neo coordination test.

Your task:
1. Run: python3 tests/test_two_developer_coordination.py

2. Watch the output carefully and tell me:
   - When does your lock get acquired?
   - Can you see Bob waiting in the activity log?
   - When you complete, does Bob get fresh context?

3. Show me the conflict check result before you declare intent

4. Report back when you're done with:
   - How many lines you added
   - How many lines you removed
   - Whether any conflicts were detected
```

**Alice will run the test and see output like:**

```
✓ STEP 1: Dev A Declares Intent
  Alice declared intent on auth.py. Log now has 1 entry/entries. 
  No lock yet (only 1 developer).

✓ STEP 2: Dev B Declares Intent (Lock Should Apply)
  Risk level: MEDIUM. Message: alice is Refactor password validation...
  Bob declared intent on auth.py. Lock status: ACTIVE (4 devs on same file)
  
✓ STEP 3: Dev A Completes Work and Publishes
  Alice completed her work. Changes: +20 lines, -5 lines.

[SUMMARY] Alice's work:
  Lines added: 20
  Lines removed: 5
  Conflicts detected: 0
```

---

## Terminal 3: Bob (Second Developer)

**Create a new Claude terminal, but WAIT until Alice has run at least STEP 1**

Then paste this prompt:

```
You are Bob, a developer in the Neo coordination test.

Important: Alice should have already declared intent on auth.py (check the watcher).

Your task:
1. First, check the activity log to see Alice's lock:
   cat .devsync/activity-log.json | python3 -m json.tool | head -30

2. Tell me what you see:
   - Does Alice have a lock_state="ACQUIRED"?
   - Do you have a lock_state="WAITING"?
   - What is your queue_position?

3. Wait for Alice to complete, then:
   cat .devsync/activity-log.json | python3 -m json.tool | grep -A 5 "alice.*completed"

4. Tell me:
   - Alice's lines_added and lines_removed
   - When Alice released the lock
   - What is your queue_position now?

5. Finally, run: python3 tests/test_two_developer_coordination.py

6. Report when done:
   - Were you blocked until Alice completed?
   - Did you see fresh context from Alice?
   - How many conflicts were detected?
```

**Bob will see:**

```
✓ STEP 1: Initial State
  Alice is already working (lock_state=ACQUIRED)
  Bob is queued (lock_state=WAITING, queue_position=0)

✓ STEP 2: Alice Completes
  Alice's changes: +20 lines, -5 lines
  Lock released

✓ STEP 3: Bob Gets Fresh Context
  Fresh context from Alice's changes loaded
  Bob can now proceed

✓ STEP 4: Bob Completes
  Bob completed work. Changes: +15 lines, -0 lines.
  Built on: alice
  Conflicts: 0
```

---

## What's Happening Under the Hood

**In Terminal 1 (Watcher):**
You'll see the activity log grow in real-time:

```
[1] alice declares intent
    └─ No lock (only 1 developer)

[2-3] alice gets lock + bob sees conflict
    ├─ alice: lock_state=ACQUIRED
    └─ bob: lock_state=WAITING, queue_position=0

[4] alice completes
    ├─ alice: agent_metadata.status=completed, +20, -5
    └─ bob: still waiting for alice to release

[5-6] bob gets context + declares
    └─ bob: intent changes, no longer WAITING

[7] bob completes
    └─ bob: agent_metadata.status=completed, +15, -0, built_on="alice"

Final: 0 conflicts detected ✅
```

---

## Where Bob Is Blocked (Exact Details)

**Bob's blocking entry in the activity log:**

```json
{
  "developer_id": "bob",
  "file_path": "auth.py",
  "intent": "Waiting for lock held by alice",
  "region": "validate_password",
  "timestamp": 1791103637.100,
  "lock_state": "WAITING",           ← Bob CANNOT write
  "lock_holder": "alice",            ← Waiting for this person
  "lock_acquired_at": 1791103636.947,
  "lock_expires_at": 1791105436.947, ← Lock expires in 30 min
  "queue_position": 0,               ← Bob is next in queue
  "waiting_for": "alice"             ← Cannot proceed until alice releases
}
```

**Once Alice completes:**

```json
{
  "developer_id": "bob",
  "file_path": "auth.py",
  "intent": "Add password strength checking",
  "region": "validate_password",
  "lock_state": null,               ← Bob's lock is released
  "queue_position": null,            ← Bob is no longer waiting
  "agent_metadata": {
    "status": "completed",
    "lines_added": 15,
    "lines_removed": 0,
    "conflicts_detected": 0,        ← ZERO conflicts
    "built_on": "alice"             ← Built on Alice's work
  }
}
```

---

## Timeline of Events

| Time | Event | Result |
|------|-------|--------|
| T+0s | Alice declares intent on auth.py | Log: 1 entry, no lock |
| T+1s | Alice gets lock (neo_check_conflicts detects conflict) | alice.lock_state = ACQUIRED |
| T+1s | Bob declares intent on auth.py | bob.lock_state = WAITING, queue_position = 0 |
| T+10s | Alice completes her work (+20, -5) | Lock released, bob can proceed |
| T+11s | Bob sees Alice's changes in activity log | Bob.queue_position becomes valid |
| T+15s | Bob completes his work (+15, -0) | built_on="alice", conflicts=0 |
| **T+15s** | **TEST PASSES** | **0 conflicts detected** |

---

## Verification: How to Know It's Working

### Terminal 1 (Watcher) shows:

```
16:00:06 | ⏳ BLOCKED  | bob        | Waiting for lock held by alice...
```

This means:
- ✅ Bob's entry is in the activity log
- ✅ Bob's lock_state = "WAITING"
- ✅ Bob is blocked from writing

### Terminal 2 (Alice) completes:

```
✓ STEP 3: Dev A Completes Work and Publishes
  Alice completed her work. Changes: +20 lines, -5 lines.
```

This means:
- ✅ Alice released the lock
- ✅ Bob should now see fresh context

### Terminal 3 (Bob) completes:

```
✓ STEP 5: Dev B Completes Work (With A's Context Integrated)
  Bob completed his work (built on Alice's changes). Changes: +15 lines, -0 lines.
```

This means:
- ✅ Bob was released from queue
- ✅ Bob received fresh context
- ✅ Bob built on Alice's work
- ✅ 0 conflicts detected

---

## Common Observations

### "Why does Terminal 1 show updates every 0.5 seconds?"
- The watcher checks the activity log file every 500ms
- So you see updates within ~500ms of Alice or Bob writing

### "Why is Bob's queue_position=0?"
- queue_position shows Bob is **next in line**
- If a 3rd developer (Charlie) joined, their queue_position would be 1

### "What if Alice takes 10 seconds to complete?"
- Bob just waits in the queue
- The watcher shows `⏳ BLOCKED` the whole time
- Once Alice completes, Bob is immediately unblocked

### "What if Bob doesn't see Alice's changes?"
- Check the activity log: does Alice have `"agent_metadata": {"status": "completed"}`?
- If not, Alice hasn't truly completed yet
- Bob's built_on="alice" only works if Alice has completed

---

## Next: Run All Three in Parallel

1. Open Terminal 1 (Watcher) → Start watching
2. Open Terminal 2 (Alice) → Paste prompt, wait for it to start
3. Open Terminal 3 (Bob) → Paste prompt

You'll see the coordination happen live:
- Alice locks the file
- Bob gets queued
- Alice completes
- Bob proceeds
- Both complete with 0 conflicts ✅

---

## Troubleshooting

### "Terminal 3 shows 'Lock held by alice' but Alice finished"
**Solution:**
- Run: `cat .devsync/activity-log.json | python3 -m json.tool | tail -30`
- Check if Alice's completion entry is there
- If not, Alice's test might still be running

### "Terminal 1 (Watcher) shows no updates"
**Solution:**
- Make sure it's running the watch script
- Check: `ls -la .devsync/activity-log.json` (does it exist?)
- If not, run either Alice or Bob's test first

### "Bob sees conflicts detected"
**Solution:**
- This shouldn't happen with the test
- If it does, check Alice actually completed before Bob started
- Try clearing and re-running: `python -c "from core.activity_log import clear_log; clear_log()"`

---

## What You're Proving

✅ **Lock acquisition works** - Alice holds lock at 2 developers  
✅ **Queue system works** - Bob waits in queue_position 0  
✅ **Context refresh works** - Bob sees Alice's +20 lines  
✅ **Sequential execution prevents conflicts** - 0 conflicts detected  

This is how Neo prevents merge conflicts: **through semantic coordination, not line-based diffing.**

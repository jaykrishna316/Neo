# Claude Code test: intent, lock, stale context, breaking change

Two Claude Code sessions, alice and bob, in the same repo folder. You send prompts only.
Neo's steps appear in each terminal as `Neo: ...` lines.

## Setup

```bash
cd ~/Neo
git checkout Extension && git pull origin Extension
scripts/reset_claude_test.sh
```

Terminal A (alice):

```bash
NEO_DEVELOPER=alice claude
```

Terminal B (bob):

```bash
NEO_DEVELOPER=bob claude
```

Start both before sending any prompt.

## Why alice runs `sleep`

The lock is released when a session's turn ends. Bob's attempt to edit has to happen while alice's turn is still running, so alice's prompt tells her to wait with `sleep`. Without it, bob's edit will not be blocked.

## Steps

### Phase 0: bob reads the file (terminal B)

> Read src/auth.py and tell me what authenticate() does. Don't change anything.

Expect: `Neo: bob read src/auth.py; baseline saved for the staleness check`

### Phase 1: alice edits and waits (terminal A)

> In src/auth.py, change authenticate(user) so it is authenticate(user, password) and returns whether password equals 'ok'. Don't change any other file. Then run `sleep 120` in bash, and tell me when it finishes.

Expect in terminal A:
- `Neo: intent set for alice: "In src/auth.py, change authenticate(user)..."` (check 1)
- `Neo: freshness check on src/auth.py: CURRENT`
- `Neo: conflict check: LOW`
- `Neo: lock on src/auth.py taken by alice; held until the task ends` (check 2)
- After the edit: `Neo: Breaking change in src/auth.py: ...` naming the changed signature, and `Neo: files that import src/auth.py: test-scenarios/services/payment.py` (check 4)

### Phase 2: bob tries to edit while alice is waiting (terminal B)

**2a.** Send:

> Add a JWT fallback to authenticate() in src/auth.py.

Expect: blocked as stale (check 3):
`Neo: src/auth.py changed after you last read it. Read the file again, then retry the edit.`

**2b.** Send:

> Read src/auth.py again.

Expect: `Neo: bob read src/auth.py; baseline saved for the staleness check`

**2c.** Send the same prompt again:

> Add a JWT fallback to authenticate() in src/auth.py.

Expect: blocked by the lock (check 1 and check 2):
- `Neo: intent set for bob: "Add a JWT fallback to authenticate() in src/auth.py."`
- `Neo: freshness check on src/auth.py: CURRENT`
- `Neo: conflict check: MEDIUM` or `HIGH`, naming alice
- `Neo: src/auth.py is locked by alice. bob is queued behind them.`

### Phase 3: alice's turn ends (terminal A)

Let alice's `sleep` finish and her turn end.

Expect in terminal A:
- `Neo: task ended: lock on src/auth.py released by alice`
- `Neo: bob is next in the queue and now holds the lock on src/auth.py` (check 2)

### Phase 4: bob edits (terminal B)

> Add a JWT fallback to authenticate() in src/auth.py.

Expect: `Neo: lock on src/auth.py taken by bob; held until the task ends`. Bob is not blocked as stale, because his re-read in 2b came after alice's edit. The code itself doesn't matter for this check.

## Pass / fail

| Check | Pass when |
|---|---|
| 1. Intent and conflict | Each prompt shows `intent set for <name>`, and bob's blocked attempt shows a conflict level other than LOW |
| 2. Lock and queue | Bob is blocked and queued with alice named; after alice's turn, bob is promoted and then allowed |
| 3. Stale context | Bob's edit after alice's change is blocked with `changed after you last read it`, and allowed after re-reading |
| 4. Breaking change | Alice's post-edit output names the changed signature and lists `payment.py` as importing it |

## Known wording issue

Check 4 reports the change as `Parameter order changed` even when a parameter was added. The message names the change correctly, but the label is wrong.

## After the test

```bash
git checkout -- src/auth.py
```

This restores the repo's version of `src/auth.py`. `scripts/reset_claude_test.sh` overwrites `test-scenarios/services/payment.py` on the next run.

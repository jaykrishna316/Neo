# Claude Code test: intent, stale context, breaking change, downstream gate

Two Claude Code sessions, alice and bob, in the same repo folder. You send prompts only.
Neo's steps appear in each terminal as `Neo: ...` lines.

This terminal test does not check the lock queue. A lock lasts only until its holder's
turn ends, and a Claude turn can't be held open for a fixed time, so Bob can't reliably
attempt an edit while Alice still holds the lock. The lock queue and hand-off are covered
by the hook tests: `tests/test_intent_lock.py` and `tests/test_neo_hook.py`.

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

## Steps

### Phase 0: bob reads the file (terminal B)

> Read src/auth.py and tell me what authenticate() does. Don't change anything.

Expect: `Neo: bob read src/auth.py; baseline saved for the staleness check`

### Phase 1: alice changes the signature (terminal A)

> In src/auth.py, change authenticate(user) so it is authenticate(user, password) and returns whether password equals 'ok'. Don't change any other file.

Expect in terminal A:
- `Neo: intent set for alice: "In src/auth.py, change authenticate(user)..."` (check 1)
- `Neo: freshness check on src/auth.py: CURRENT`
- `Neo: conflict check: HIGH` or `MEDIUM`, with the breaking-change reason
- `Neo: lock on src/auth.py taken by alice; held until the task ends`
- After the edit: `Neo: Breaking change in src/auth.py` naming the signature change (check 4)
- `Neo: files that import src/auth.py: test-scenarios/services/payment.py`
- `Neo: downstream breakage: test-scenarios/services/payment.py will break - line 4: authenticate(user) is missing 'password'`
- Then `Neo: task ended: lock on src/auth.py released by alice` when her turn ends

Alice does not fix payment.py. That's the point of the test.

### Phase 2: bob tries to edit src/auth.py (terminal B)

Bob's edits are checked in this order: stale read, downstream breakage, then the lock.

**2a.** Send:

> Without reading src/auth.py again, add a JWT fallback to authenticate() in src/auth.py.

Expect: blocked as stale (check 3):
`Neo: src/auth.py changed after you last read it. Read the file again, then retry the edit.`

If Claude reports `Error editing file` and no Neo line, Claude's copy of the file is out of date and the hook never ran. Send 2b anyway, then go on. Check 3 then needs another attempt.

**2b.** Send:

> Read src/auth.py again.

Expect: `Neo: bob read src/auth.py; baseline saved for the staleness check`

**2c.** Send the same prompt as 2a:

> Without reading src/auth.py again, add a JWT fallback to authenticate() in src/auth.py.

Expect: blocked by the downstream breakage (check 5):
- `Neo: downstream breakage on src/auth.py: callers do not match the current signature`
- `Neo: test-scenarios/services/payment.py line 4: authenticate(user) is missing 'password'`

**2d.** Send:

> Update test-scenarios/services/payment.py so pay() takes a password and passes it to authenticate(). Don't change any other file.

Expect: `Neo: downstream breakage resolved: test-scenarios/services/payment.py now matches src/auth.py`

**2e.** Send:

> Add a JWT fallback to authenticate() in src/auth.py.

Expect: allowed, with the lock now taken by bob because alice's turn ended:
- `Neo: freshness check on src/auth.py: CURRENT`
- `Neo: lock on src/auth.py taken by bob; held until the task ends`

Stop after 2e. Bob's JWT code is only for this test. Don't keep it.

## Pass / fail

| Check | Pass when |
|---|---|
| 1. Intent and conflict | Alice's prompt shows `intent set for alice`, and her edit shows a conflict level other than LOW |
| 2. Lock | Alice's lock is taken and released at the end of her turn; bob takes the lock after it (2e). Queueing is covered by the hook tests |
| 3. Stale context | Bob's edit after alice's change is blocked with `changed after you last read it` (2a) |
| 4. Breaking change | Alice's post-edit output names the changed signature and lists `payment.py` as importing it |
| 5. Downstream gate | Bob is blocked by `downstream breakage` before any lock message (2c), and the block clears after `payment.py` is fixed (2d) |

## Known wording issue

Check 4 reports the change as `Parameter order changed` even when a parameter was added. The message names the change correctly, but the label is wrong.

## After the test

```bash
git checkout -- src/auth.py test-scenarios/services/payment.py
```

`scripts/reset_claude_test.sh` rewrites both files at the start of each run.

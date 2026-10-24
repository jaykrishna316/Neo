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

## Why alice makes two changes

Claude Code checks its own copy of a file before the hook runs. If alice changes the text
bob is about to edit, bob's edit fails inside Claude Code, the hook never runs, and the
stale block can't be shown.

So alice first adds a function at the end of the file, which leaves `authenticate()`
unchanged. Bob's edit then reaches the hook, and the stale block fires. Alice's breaking
change comes second.

## Steps

### Phase 0: bob reads the file (terminal B)

> Read src/auth.py and tell me what authenticate() does. Don't change anything.

Expect: `Neo: bob read src/auth.py; baseline saved for the staleness check`

### Phase 1a: alice adds an unrelated function (terminal A)

> Add a function logout(user) at the end of src/auth.py that returns None. Don't change any other file.

Expect in terminal A:
- `Neo: intent set for alice: "Add a function logout(user)..."`
- `Neo: lock on src/auth.py taken by alice; held until the task ends`
- `Neo: no breaking change; no files import src/auth.py` or the list of importers, with no downstream breakage

### Phase 2a: bob's edit is stale (terminal B)

> Add a JWT fallback to authenticate() in src/auth.py. Don't change any other file.

Expect: blocked as stale (check 3):
`Neo: src/auth.py changed after you last read it. Read the file again, then retry the edit.`

Bob's edit is blocked before the lock check, so alice's lock isn't involved here.

### Phase 1b: alice changes the signature (terminal A)

> In src/auth.py, change authenticate(user) so it is authenticate(user, password) and returns whether password equals 'ok'. Don't change any other file.

Expect in terminal A:
- `Neo: freshness check on src/auth.py: CURRENT`
- `Neo: conflict check: HIGH` or `MEDIUM`, with the breaking-change reason (check 1)
- `Neo: Breaking change in src/auth.py` naming the signature change (check 4)
- `Neo: files that import src/auth.py: test-scenarios/services/payment.py`
- `Neo: downstream breakage: test-scenarios/services/payment.py will break - line 4: authenticate(user) is missing 'password'`

Alice does not fix payment.py. That's the point of the test.

### Phase 2b: bob re-reads (terminal B)

> Read src/auth.py again.

Expect: `Neo: bob read src/auth.py; baseline saved for the staleness check`

### Phase 2c: bob is blocked by the downstream breakage (terminal B)

> Add a JWT fallback to authenticate() in src/auth.py. Don't change any other file.

Expect: blocked by the downstream breakage (check 5), before the lock is checked:
- `Neo: downstream breakage on src/auth.py: callers do not match the current signature`
- `Neo: test-scenarios/services/payment.py line 4: authenticate(user) is missing 'password'`

### Phase 2d: bob fixes the caller (terminal B)

> Update test-scenarios/services/payment.py so pay() takes a password and passes it to authenticate(). Don't change any other file.

Expect: `Neo: downstream breakage resolved: test-scenarios/services/payment.py now matches src/auth.py`

### Phase 2e: bob's edit is allowed (terminal B)

> Add a JWT fallback to authenticate() in src/auth.py. Don't change any other file.

Expect: allowed, with the lock taken by bob because alice's turn ended:
- `Neo: freshness check on src/auth.py: CURRENT`
- `Neo: lock on src/auth.py taken by bob; held until the task ends`

Stop after 2e. Bob's JWT code is only for this test. Don't keep it.

## Pass / fail

| Check | Pass when |
|---|---|
| 1. Intent and conflict | Each prompt shows `intent set for <name>`, and alice's breaking edit shows a conflict level other than LOW |
| 2. Lock | Alice's lock is taken and released at the end of her turn; bob takes the lock after it (2e). Queueing is covered by the hook tests |
| 3. Stale context | Bob's edit after alice's unrelated change is blocked with `changed after you last read it` (2a) |
| 4. Breaking change | Alice's signature change names the changed signature and lists `payment.py` as importing it (1b) |
| 5. Downstream gate | Bob is blocked by `downstream breakage` before any lock message (2c), and the block clears after `payment.py` is fixed (2d) |

If 2a shows `Error editing file` with no Neo line, Claude re-read the file before editing. Send 2b, then continue. Check 3 then needs another attempt.

## Known wording issue

Check 4 reports the change as `Parameter order changed` even when a parameter was added. The message names the change correctly, but the label is wrong.

## After the test

```bash
git checkout -- src/auth.py
```

`test-scenarios/services/payment.py` isn't tracked by git, so it can't be restored with `git checkout`. `scripts/reset_claude_test.sh` rewrites it at the start of each run.

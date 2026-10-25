# Test Neo in your own repo

This guide installs Neo's Claude Code hooks into a repo and checks that they run there.
Then it runs a short coordination demo, using prompts only.

Replace `~/path/to/your-repo` with your repo's path.

## 1. Install the hooks (terminal)

```bash
git clone --depth 1 https://github.com/jaykrishna316/Neo ~/neo-src
bash ~/neo-src/scripts/install_neo.sh ~/path/to/your-repo
cd ~/path/to/your-repo
ls .neo/scripts/
grep -c "python3 .neo/scripts/" .claude/settings.json
```

Expect: the list shows `neo_hook.py`, `neo_update_check.py` and `neo_repo_demo.sh`. The count is `7`.

## 2. Start Claude Code with a developer name (terminal)

```bash
cd ~/path/to/your-repo && NEO_DEVELOPER=alice claude
```

Neo does nothing unless `NEO_DEVELOPER` is set. If you see no `Neo:` lines at all, this is the first thing to check.

## 3. Check the hooks are loaded (in Claude Code)

Type `/hooks`. Neo's entries should be listed under PreToolUse, PostToolUse, UserPromptSubmit, Stop and SessionStart.

## 4. Check the prompt hook (in Claude Code)

Send:

```
What is 2 + 2?
```

Expect: `Neo: intent set for alice: "What is 2 + 2?"`

In another terminal, run `ls ~/path/to/your-repo/.neo_state/`. You should see `intent_alice.txt`.

## 5. Check the read hook (in Claude Code)

Send, using any file in your repo:

```
Read README.md and tell me the first heading. Don't change anything.
```

Expect: `Neo: alice read README.md; baseline saved for the staleness check`

`ls .neo_state/` should now also show an `alice_README.json` file.

## 6. Set up the coordination demo (terminal)

```bash
cd ~/path/to/your-repo
.neo/scripts/neo_repo_demo.sh setup
```

This adds a `neo_demo/` folder with two files, `pricing.py` and `checkout.py`. It also leaves a breaking change open, as if a previous developer had changed `price()` and stopped before updating `checkout.py`.

## 7. You, in Claude Code (Terminal A)

Start a new session with a different name:

```bash
cd ~/path/to/your-repo && NEO_DEVELOPER=me claude
```

Send these prompts in order.

**a. Intent and inherited breakage.** Send:
```
Read neo_demo/pricing.py. Then add a docstring to price() in neo_demo/pricing.py. Don't change any other file.
```
Expect: `intent set for me`, then `downstream breakage on neo_demo/pricing.py` naming `checkout.py`. The edit is blocked.

**b. Fix the caller, which takes the lock.** Send:
```
Update neo_demo/checkout.py so total() takes a tax_rate and passes it to price(). Don't change any other file.
```
Expect: `lock on neo_demo/checkout.py taken by me`, then `downstream breakage resolved`.

Then repeat the prompt from step a. Expect: the edit goes through, with `lock on neo_demo/pricing.py taken by me`.

If Claude asks you to choose between fixing the caller and disabling the hook, choose to fix the caller. Don't disable the hook, because then the test checks nothing.

## 8. A teammate changes the file (terminal)

Run this after step 7b, so that `checkout.py` is already fixed:

```bash
cd ~/path/to/your-repo
.neo/scripts/neo_repo_demo.sh teammate
```

Expect: `Teammate added discount() to neo_demo/pricing.py.`

## 9. Stale context, then the change (Terminal A)

**c. Stale block.** Send:
```
Without reading neo_demo/pricing.py again, change the first line of the docstring of price() to "Price one item including tax." Make the edit now. Don't change any other file.
```
Expect: `neo_demo/pricing.py changed after you last read it`. If Claude reports `Error editing file` instead, send `Read neo_demo/pricing.py again.` and try once more.

**d. Read again, then change.** Send:
```
Read neo_demo/pricing.py again, then make the docstring change. Don't change any other file.
```
Expect: `lock on neo_demo/pricing.py taken by me`, then the edit logged. When the turn ends, expect `task ended: … released by me`.

## 10. Clean up (terminal)

```bash
cd ~/path/to/your-repo
.neo/scripts/neo_repo_demo.sh cleanup
```

Expect: `Demo removed`. The `neo_demo/` folder is deleted, and the demo's Neo state is cleared.

## What passed

| Check | Pass when |
|---|---|
| Hooks installed | `grep` returns `7` |
| Hooks loaded | `/hooks` lists Neo's entries |
| Intent | Each prompt shows `intent set for <name>` |
| Downstream impact | Step 7a is blocked by `downstream breakage`, and step 7b clears it |
| Locking | Step 7b takes and releases the lock on `checkout.py`; step 9d takes and releases it on `pricing.py` |
| Stale context | Step 9c is blocked with `changed after you last read it` |

The lock queue (a second developer waiting for the lock) is not covered by this single-developer test.

## Troubleshooting

- **No `Neo:` lines:** check that `NEO_DEVELOPER` was set when Claude started, and run `/hooks`.
- **Claude edits a file the prompt didn't name:** press Esc and check which file it was.
- **Claude answers without editing:** tell it to make the edit with the Edit tool, then repeat the prompt.

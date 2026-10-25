# Working with Munder Difflin and Neo: guide and multi-agent test design

Written for future sessions. It records what we learned, what works, and the test that shows Neo blocking and queueing agents in real time.

## 1. What is proven, and what is not

Proven in single-developer runs in the Munder Difflin app (Jim, Pam):
- Intent is recorded from each prompt (`intent set for <name>`).
- A broken caller blocks an edit to the changed file and is named (`downstream breakage ... line N`).
- Fixing the caller clears the block (`downstream breakage resolved`).
- A change made after a read is blocked as stale (`changed after you last read it`), confirmed in the session transcript as `STALE_SOURCE`.
- A permitted edit takes the lock, logs the edit, and releases the lock when the turn ends.

Proven by tests (not yet in the app):
- Two developers queue on a file; the second is blocked and handed the lock (hook tests).
- A blocked edit can wait up to 120 seconds for the lock (`NEO_LOCK_WAIT_SECONDS`), then go ahead (tests/test_lock_wait.py, on the `Extension` branch as commit cb9ba1a, not yet on `main`).

Not yet shown:
- Several agents in the app at the same time, blocked in real time.
- Token savings.
- Git conflicts being avoided across agent worktrees (in the app, each agent has its own worktree, so conflicts only appear at merge).

## 2. Working with Munder Difflin

**What the app is.** A desktop app that runs coding agents (here: Claude Code) as terminal processes. Each agent has a name, a provider and model, a folder, and an isolation setting. Repo: https://github.com/HarnessMD/munder-difflin. Our fork: https://github.com/jaykrishna316/munder-difflin (branch `neo-coordination`).

**Adding an agent.**
- Click + next to AGENTS. Name, Provider: Claude Code, Model: Haiku 4.5 (Opus uses the allowance too fast), Folder: the repo, Isolation: "Own branch and worktree".
- The app creates a git worktree for the agent: `~/BinaryMind94/worktrees/<name>-<id>`. Find it with `git -C <repo> worktree list`. The folder can't be changed after adding; archive and re-add instead.
- A new worktree is created from the repo's current `main`. Commit anything that should be shared before adding agents.

**Giving each agent a Neo name and hooks.**
1. Install Neo into the worktree: `bash ~/neo-src/scripts/install_neo.sh <worktree>` (clone `~/neo-src` from `--branch Extension`, not `main`, while Extension is ahead).
2. Make the hook paths absolute, or `cd` inside a subfolder breaks them:
   `sed -i '' "s#python3 .neo/scripts/#python3 <worktree>/.neo/scripts/#g" <worktree>/.claude/settings.json`
   Expect 8 hook lines containing the worktree path.
3. Write `<worktree>/.claude/settings.local.json` with `{"env": {"NEO_DEVELOPER": "<name>"}}`. Use a lowercase name.
4. Restart the agent (Restart now), then send `Run echo $NEO_DEVELOPER in bash...`. It must reply with the name.

**Things that broke runs, and the fix.**
- Relative hook paths (`python3 .neo/...`) fail once an agent runs `cd code`. Use absolute paths (step 2 above).
- The installer keeps old absolute entries and adds relative ones, so hooks run twice. Restore `.claude/settings.json` from git before reinstalling (`git -C <wt> checkout -- .claude/settings.json`).
- A Stop hook that fails leaves the lock held. Release it by hand: `echo '{}' | NEO_DEVELOPER=<name> python3 .neo/scripts/neo_hook.py stop` (run from the worktree root).
- A breakage record from before a Neo fix stays in `.neo_state/breakages.json` and keeps blocking. Remove the stale entry by hand.
- Resetting files (`git checkout -- code`) while an agent is running makes it re-read and report "file reverted". Reset only before starting an agent's task.
- Agents often reply "already done" without editing. Check the file (`git status`, `cat`) and the log, and force the edit with "Use the Edit tool now".
- Claude sometimes re-reads a file before editing. That skips the stale check. This is why the stale block shows only on some runs.

**Watching.** A watcher terminal shows the lock log. Example (colored, shows Waiting and Acquired):
```
while true; do clear; grep -E "Lock|Waiting" ~/neo-shared-state/devsync/activity-log.json | tail -8 | cut -c1-200; sleep 1; done
```
In the single-developer runs, Neo writes to each worktree's `.devsync` and `.neo_state`, because no shared state folder is set. Multi-agent runs need the shared folder (see section 4).

**Measuring tokens.** Each agent's transcript is in `~/.claude/projects/<worktree path with / replaced by ->/<session>.jsonl`. Find the newest with `ls -t`. Run `~/neo_token_report.py <file>` (a copy lives in the sandbox scratchpad; the script is on branch `feature/token-report`). Sum input, cache creation, cache reads, output. Report cache reads separately: they dominate the total and don't cost the same.

**Git and pushes.**
- Pushing to the fork needs the Claude GitHub App installed on jaykrishna316 (https://github.com/apps/claude/installations/select_target). Until then pushes are refused.
- GitHub rejected a commit with a private email address; use `jaykrishna316@users.noreply.github.com` as the author.
- Always ask before pushing to `Extension` or `main`.

## 3. Single-developer test (done)

Setup: `neo-readme-test` repo with `neo_demo/pricing.py` and `neo_demo/checkout.py` (see `.neo/scripts/neo_repo_demo.sh setup|teammate|cleanup`). Steps as run by Jim: read, blocked edit, fix caller, teammate change, stale edit blocked, re-read and edit. Results are in the post draft.

## 4. Multi-agent real-time test: design

**Goal.** Show, live on screen, that a developer or agent waiting on a file is blocked, queued, and then handed the lock, while the file's owner works. And measure what happens without Neo.

**Prerequisites.**
- Neo from `Extension` at commit 352fbb0 or later (includes the lock wait and the session-start scan). Install into each agent's worktree.
- A shared state folder for all agents, so they see each other's locks: `~/neo-shared-state`. Add to each agent's `settings.local.json`:
  `{"env": {"NEO_DEVELOPER": "<name>", "NEO_STATE_DIR": "/Users/<you>/neo-shared-state", "NEO_ACTIVITY_LOG_DIR": "/Users/<you>/neo-shared-state/devsync"}}`
- Note: the agents still work in separate worktrees, so Git conflicts only appear when branches merge. Neo's lock and queue are the part that works across worktrees (paths are relative to each worktree).
- The watcher terminal running.

**Agents and tasks.** Three agents on the `code/` folder of `neo-readme-test`:
- **Kevin (owner, holds the lock):** the eight-step task (add `tax_rate` to `price()`, pass it through `total()`, add docstrings, add `format_total()`, add module docstrings). It takes several minutes, so the lock is held for that long.
- **Kelly (waiter):** `In code/checkout.py, add a discount argument to total() with a default of 0, and subtract it from the sum. If Neo says the file is locked or you are queued, wait; don't retry, don't change other files.`
- **Jim (second waiter):** a third task on `code/checkout.py`, sent after Kelly is queued, so the queue has two places.

**Timeline (what should happen).**
1. T0: send Kevin's task. The watcher shows `Lock acquired` for `code/pricing.py` from kevin.
2. T0 + 10–20 s (while Kevin is still on step 2–4): send Kelly's task. Her hook logs `WAITING` and her chat says `is locked by kevin … waiting up to 120 seconds`. The watcher countdown runs (`kelly WAITING N/120 s`).
3. T0 + 30 s: send Jim's task. He queues behind Kelly (queue position 2).
4. Kevin finishes: `Lock released` for both files. Kelly is promoted; her edit proceeds and her chat says `kevin's turn ended after N seconds`. Then Kelly finishes and Jim is promoted.
5. Each agent's edit is logged; the run ends with three merged or unmerged branches.

If Kevin's turn is shorter than the gap between sends, Kelly's hook sees no lock and proceeds. Then the test shows nothing about blocking. Add steps to Kevin's task until his turn lasts longer than the gap.

**Baseline (no Neo) for comparison.** Same tasks, same timing, no NEO_DEVELOPER in any agent's settings. Expect: Kelly and Jim edit at the same time, the branches conflict in `code/checkout.py`, and the merged code fails to import. Record:
- time per agent (first to last transcript timestamp),
- tokens per agent (report script),
- Git conflict (`git merge` output), and whether tests pass after the merge,
- for the Neo run: number of blocks, total wait time per agent, queue order.

**Pass criteria for the Neo run.**
- Kelly and Jim each show a WAITING line and a countdown, and neither edits before Kevin releases.
- The watcher shows the promotion order: Kevin, then Kelly, then Jim.
- Each chat shows its Neo lines (intent, block or wait, handoff).
- Tests pass on the merged result, or the report says exactly which step failed.

**Controls and honesty.**
- Run each setup at least twice. LLM behaviour varies; report the spread, not one run.
- Use fresh agents (archive, re-add) for each run so transcripts are separate. Don't reset code while any agent is running.
- Say in any post which steps were automatic (hooks) and which were typed by a person.
- Report token totals with cache reads separated.

**Known limits to state.**
- The lock lasts as long as the holder's turn. Waiting is capped at 120 s (configurable). A holder who runs longer than that blocks the waiter with a message instead.
- Coordination covers agents on one machine. Across machines it needs the Neo server, which the hooks don't use yet.
- Neo blocks overlapping edits it can see. It doesn't judge whether an edit is correct.

## 5. Open decisions

- Whether the lock should be held for a fixed minimum (for example 120 s) after an edit, so short turns can't slip in. Current behaviour: the lock lasts for the whole turn.
- Whether lock-wait and session-scan go to `main` (currently on `Extension` only; `main` is at 1d41ef7).
- Whether the Neo integration into Munder Difflin (a toggle and the hook merge) gets built on the fork (`neo-coordination` branch). It needs the GitHub App before it can be pushed.
- Whether to keep the Braxis and Neo-repo demos public, or move them to docs only.

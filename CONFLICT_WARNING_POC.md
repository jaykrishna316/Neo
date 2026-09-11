# Pre-Generation Conflict Warning POC

A minimal proof of concept for detecting when two developers (or their agents) are working on the same file locally, before code generation proceeds.

## How It Works

### 1. Activity Log (`activity_log.py`)

- Maintains a shared JSON log at `.devsync/activity-log.json`
- Each entry records:
  - `developer_id`: Who is working
  - `file_path`: Which file
  - `intent`: A short description of what they're changing and why
  - `region`: Optional identifier of the specific function/class/region (e.g., `"login_user function (lines 20-40)"`)
  - `timestamp`: When the work started

**Why JSON + local file?**
- Zero network latency (required for < 100ms check)
- Works in local dev workflows without server
- Simple to inspect and debug
- Supports any two developers/agents sharing the filesystem

### 2. Risk Classifier (`risk_classifier.py`)

Given two developers' work on the same file, classifies risk as:

#### **LOW**
- Non-overlapping regions (different functions/classes) AND
- No signature changes detected
- **Action:** Silent (only logged, no UI)

#### **MEDIUM**
- Overlapping regions (same function/class), OR
- Signature/structural changes without direct region overlap
- **Action:** Dismissible, non-blocking note before generation

#### **HIGH**
- Overlapping region AND signature/removal changes detected
- **Action:** Confirmation prompt (blocks generation until user confirms)

**Heuristic Details:**
- **Region overlap:** Line-range comparison (if both specify lines), or symbolic name matching
- **Signature changes:** Keyword detection for "rename," "remove," "refactor," "delete," etc.
- **Limitations:** See section below

### 3. Pre-Generation Check (`pre_gen_check.py`)

Before an agent/developer generates code:

1. Read the activity log
2. Filter entries for the same file path
3. Exclude expired entries (default: 30 minutes)
4. Classify risk from first conflicting entry
5. Return risk level + optional message
6. Handle response (silence, warn, or block)

**Speed:** Local JSON read + in-memory filtering/classification ≈ 5-10ms (fast enough)

### 4. CLI Simulation (`cli_simulation.py`)

Two simulated developer sessions with a harness that demonstrates:
- Starting work (log intent)
- Attempting code generation (pre-check + response)
- Scenarios covering all risk levels, expiry, and multi-developer cases

## Running the POC

```bash
python3 cli_simulation.py
```

This runs five scenarios end-to-end:
1. **Overlapping regions** (MEDIUM risk) → note + proceed
2. **Non-overlapping regions** (LOW risk) → silent proceed
3. **Signature change** (HIGH risk) → confirmation required
4. **Entry expiry** → stale entries ignored
5. **Multiple developers** → first conflict detected

## Limitations of the Heuristic

**The risk classifier is intentionally simple and has known limitations:**

1. **No semantic understanding:** Cannot distinguish between:
   - Touching a file to fix whitespace vs. breaking an interface
   - A utility function that nobody uses vs. a core dependency
   - Two changes that use different parts of the AST

2. **Keyword-based signature detection is fragile:**
   - False positives: "Refactor to remove redundant code" triggers HIGH risk
   - False negatives: Structural changes without keywords go undetected
   - Real fix: AST parsing (Python) or semantic analysis, but slow

3. **Region matching is crude:**
   - Line ranges are brittle (adding/deleting lines shifts everything)
   - Symbolic names require exact match (e.g., "authenticate" ≠ "auth")
   - No understanding of function call chains or transitive dependencies

4. **No cross-file analysis:** Two developers editing different files that import from each other aren't detected as conflicting.

5. **Expiry is global:** All entries expire after 30 minutes, regardless of whether the developer is actively working. A developer paused for a break gets their entry expired.

**These are acceptable for a POC because:**
- The interaction loop (log intent → check → respond) is proven sound
- A real system would replace the heuristic with semantic analysis without changing the outer loop
- False positives (warn when unnecessary) are better than false negatives (miss real conflicts)
- Developers can always dismiss MEDIUM warnings and confirm HIGH ones

## What Worked

✓ **The core loop:** Start work → log intent → check before generating → tier-appropriate response  
✓ **Speed:** Local check is imperceptible (no network, minimal compute)  
✓ **Simplicity:** The entire POC is ~500 lines of straightforward Python  
✓ **Flexibility:** Region specification is optional, so it works for coarse-grained scenarios too  
✓ **Expiry:** Entries naturally age out, preventing stale noise  

## What Would Be Needed for Production

1. **Semantic analysis** to replace keyword-based heuristics:
   - Use AST parsing to detect actual signature changes (Python), or LSP for other languages
   - Track function/class definitions and usages to catch transitive dependencies
   - Understand scope (private vs. exported)

2. **Smarter region matching:**
   - Use tree-sitter or language-specific parsers to identify which functions/classes are touched
   - Understand the call graph to detect indirect conflicts

3. **Incremental log updates:**
   - Developers should send periodic "still working" heartbeats to keep entries alive
   - Alternatively, hook into file-change events (fsnotify, watchman) to auto-update timestamps

4. **Multi-file detection:**
   - Track imports and cross-file dependencies
   - Warn if Dev A is renaming an exported symbol that Dev B is about to call

5. **Integration with real tools:**
   - Hook into Claude Code, Cursor, Devin pre-generation
   - Tie log entries to actual LSP sessions or editor instances
   - Persist across network in distributed setups

6. **Better UX:**
   - Show a diff preview in the warning (what does Dev A's change look like?)
   - Offer a "view their intent and changes" link
   - Allow users to manually resolve or mark as safe

## Verdict

**Would this be useful in practice?**

Yes, with caveats:

- **For teams in one office (shared filesystem):** The proof-of-concept loop is genuinely helpful. False positives on MEDIUM risk are tolerable; developers will quickly learn to dismiss or resolve them. The system catches real oversights.

- **For distributed teams:** Would need a network sync layer. The local-only assumption breaks, but the core logic ports cleanly.

- **For AI agents:** High confidence. Agents lack human intuition and often don't ask "is someone else changing this?" A log-based check fits naturally into a pre-generation step and is cheaper than a failed merge/rebase later.

- **Blocker:** Only if the heuristic is smarter (semantic analysis). Keyword detection will frustrate developers with false positives if deployed as-is.

**Real-world friction point:** Developers working on different machines won't see the log. A central or synced log (even just S3-backed, checking occasionally) would be needed. This wasn't in scope for the POC.

## File Structure

```
.devsync/
  activity-log.json       (shared activity log)

activity_log.py           (log read/write)
risk_classifier.py        (risk assessment logic)
pre_gen_check.py          (pre-generation check + response handling)
cli_simulation.py         (runnable demo with scenarios)

CONFLICT_WARNING_POC.md   (this file)
```

## Next Steps to Explore

1. **Add AST parsing** to detect actual signature changes (Python: ast module)
2. **Track function calls** to find transitive dependencies
3. **Add git integration** to compare staged/unstaged changes with intent log
4. **Implement file watches** to auto-update timestamps when developers touch files
5. **Test with real IDE hooks** (Claude Code, VS Code extension)
6. **Measure latency** in a realistic multi-file project

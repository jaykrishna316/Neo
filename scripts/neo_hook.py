#!/usr/bin/env python3
"""Claude Code hook for Neo coordination.

  prompt  UserPromptSubmit: save the prompt as this session's intent.
  pre     PreToolUse (Edit/Write): the first edit takes the file's lock. Block if
          another session holds it, or if the file changed since this session last read it.
  post    PostToolUse (Edit/Write): check the change for breaking changes and downstream
          dependents, log it, and save the new baseline. The lock is kept.
  read    PostToolUse (Read): save what this session saw.
  bash    PostToolUse (Bash): treat files changed by shell commands as edits.
  stop    Stop: the task ended. Release this developer's locks and promote the next.

Each session names itself with NEO_DEVELOPER. Without it, every mode does nothing.
NEO_INTENT overrides the intent saved from the prompt.
Exit code 2 blocks the tool call and shows the message to the session.
"""

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core import activity_log  # noqa: E402
from core.activity_log import log_activity  # noqa: E402
from core.blast_radius import BlastRadiusCalculator  # noqa: E402
from core.breaking_change_detector import has_breaking_changes  # noqa: E402
from core.call_compat import broken_calls  # noqa: E402
from core.freshness import check_freshness, get_base_snapshot, record_read  # noqa: E402
from core.lock_manager import LockManager  # noqa: E402
from core.pre_gen_check import check_for_conflicts  # noqa: E402
from core.risk_classifier import RiskLevel  # noqa: E402

MODES = ("prompt", "pre", "post", "read", "bash", "stop", "start")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".devsync", ".neo_state"}


def _state_dir():
    return Path(os.environ.get("NEO_STATE_DIR", ".neo_state"))


def _repo_root_of(file_path):
    """The top of the git worktree that holds this file, or None outside git."""
    folder = file_path.parent
    while not folder.is_dir() and folder != folder.parent:
        folder = folder.parent
    result = subprocess.run(["git", "-C", str(folder), "rev-parse", "--show-toplevel"],
                            capture_output=True, text=True)
    top = result.stdout.strip()
    return Path(top) if result.returncode == 0 and top else None


def _relative_file_path(hook_input):
    """The file's path inside its own worktree, so every worktree of one repo agrees on it."""
    path = (hook_input.get("tool_input") or {}).get("file_path")
    if not path:
        return None
    absolute = Path(path).resolve()
    root = _repo_root_of(absolute) or REPO
    try:
        return str(absolute.relative_to(root))
    except ValueError:
        return path


def _emit_pre(reason):
    """Allow the tool call and show the reason to the session."""
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": reason,
    }}))


def _notify(steps, extra=None):
    """Show each Neo step in the Claude terminal, as the hook's system message."""
    out = dict(extra or {})
    if steps:
        out["systemMessage"] = "\n".join(f"Neo: {step}" for step in steps)
    if out:
        print(json.dumps(out))


def _block(steps):
    """Block the tool call. The steps and the reason are shown in the terminal."""
    print("\n".join(f"Neo: {step}" for step in steps), file=sys.stderr)
    return 2


def prompt(developer, hook_input):
    text = (hook_input.get("prompt") or "").strip()
    if not text:
        return 0
    state = _state_dir()
    state.mkdir(parents=True, exist_ok=True)
    (state / f"intent_{developer}.txt").write_text(text[:300])
    _notify([f"intent set for {developer}: \"{text[:120]}\""])
    return 0

def _saved_intent(developer):
    path = _state_dir() / f"intent_{developer}.txt"
    return path.read_text().strip() if path.exists() else None


def _python_paths(root):
    """Every .py file in the project, as resolved paths, skipping excluded folders."""
    return [path.resolve() for path in _python_files(root)]


def _bound_module(importer, stem, repo_files):
    """The file that `import <stem>` in importer refers to, or None.

    A module name can be shared by files in different folders (code/pricing.py and
    neo_demo/pricing.py). An import binds to the file in its own folder, or else the
    nearest parent folder that has one. A name used only once binds to that file.
    """
    matches = [path for path in repo_files if path.stem == stem]
    if len(matches) <= 1:
        return matches[0] if matches else None
    for folder in [importer.parent, *importer.parents]:
        for path in matches:
            if path.parent == folder:
                return path
    return None


def scan_dependents(file_path):
    """Files in the project that import this file's module."""
    root = Path.cwd().resolve()
    target = Path(file_path).resolve()
    module = target.stem
    pattern = re.compile(
        rf"^\s*(from\s+{re.escape(module)}\s+import|import\s+{re.escape(module)}\b)", re.M
    )
    repo_files = _python_paths(root)
    found = []
    # Prune skipped folders while walking. Listing every file first (rglob) took
    # about 18 seconds on a repo with a large .venv, past the hook's time limit.
    for path in repo_files:
        if path == target:
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if pattern.search(text) and _bound_module(path, module, repo_files) == target:
            found.append(str(path.relative_to(root)))
    return sorted(found)


def analyze_change(file_path, old_content, new_content):
    """Return (breaking_changes, dependents, lines) for one change."""
    breaking = []
    if old_content is not None and new_content is not None and old_content != new_content:
        _changed, breaking = has_breaking_changes(old_content, new_content, file_path)
    dependents = scan_dependents(file_path)
    lines = []
    for change in breaking:
        lines.append(f"Breaking change in {file_path}: {change.details} (severity {change.severity})")
    if dependents:
        report = BlastRadiusCalculator({file_path: dependents}).calculate(
            file_path, "signature" if breaking else "general"
        )
        lines.append(f"Files that import {file_path}: {', '.join(dependents)}")
        lines.append(
            f"Blast radius: {report.total_dependents} files, "
            f"about {report.total_estimated_hours:.1f} hours, about {report.total_token_cost} tokens "
            f"(estimates)"
        )
    return breaking, dependents, lines


def _breaks_path():
    return _state_dir() / "breakages.json"


def _load_breaks():
    path = _breaks_path()
    return json.loads(path.read_text()) if path.exists() else []


def _save_breaks(records):
    path = _breaks_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2))


def _same_file(a, b):
    return os.path.normpath(os.path.abspath(a)) == os.path.normpath(os.path.abspath(b))


def _problems_for(source, importer, symbols):
    """Calls in importer that no longer match source's current signatures."""
    try:
        new_source = Path(source).read_text()
        importer_text = Path(importer).read_text()
    except (OSError, UnicodeDecodeError):
        return []
    return [f"line {line}: {call} {problem}"
            for line, call, problem in broken_calls(importer_text, Path(source).stem,
                                                    new_source, symbols)]


def refresh_breakages(file_path, breaking, dependents):
    """Record the downstream breakages this edit causes, and resolve the ones it fixes.

    Returns the steps to show in the terminal.
    """
    steps = []
    records = _load_breaks()
    if breaking:
        symbols = {c.symbol for c in breaking}
        for record in records:
            if _same_file(record["source"], file_path):
                symbols.update(record["symbols"])
        records = [r for r in records if not _same_file(r["source"], file_path)]
        for dependent in dependents:
            problems = _problems_for(file_path, dependent, symbols)
            if problems:
                records.append({"source": file_path, "importer": dependent,
                                "symbols": sorted(symbols), "problems": problems})
                steps.append(f"downstream breakage: {dependent} will break - " + "; ".join(problems))

    kept = []
    for record in records:
        if _same_file(record["source"], file_path) or _same_file(record["importer"], file_path):
            problems = _problems_for(record["source"], record["importer"], record["symbols"])
            if not problems:
                steps.append(f"downstream breakage resolved: {record['importer']} now matches {record['source']}")
                continue
            record["problems"] = problems
        kept.append(record)
    _save_breaks(kept)
    return steps


def _log_breaking(developer, file_path, breaking):
    details = "; ".join(change.details for change in breaking)
    log_activity(developer_id=developer, file_path=file_path,
                 intent=f"Breaking change: {details}", intent_category="breaking-change")


def _lock_wait_seconds():
    return int(os.environ.get("NEO_LOCK_WAIT_SECONDS", "120"))


def _lock_holder(file_path):
    key = LockManager()._make_lock_key(file_path, None, "file")
    return ((LockManager()._get_current_lock(key)) or {}).get("lock_holder")


def _wait_for_lock(file_path, developer, limit):
    deadline = time.time() + limit
    while True:
        holder = _lock_holder(file_path)
        if holder in (None, developer):
            return True
        remaining = deadline - time.time()
        if remaining <= 0:
            return False
        time.sleep(min(2, remaining))


def _python_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name.endswith(".py"):
                yield Path(dirpath) / name


def scan_repo_breaks(root):
    """Callers anywhere in the repo that no longer match their function's current signature."""
    files = {}
    for path in _python_files(root):
        try:
            if path.stat().st_size <= 300_000:
                files[path] = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
    found = []
    for source_path, source_text in files.items():
        try:
            tree = ast.parse(source_text)
        except SyntaxError:
            continue
        symbols = {node.name for node in tree.body
                   if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        if not symbols:
            continue
        stem = re.escape(source_path.stem)
        importing = re.compile(rf"^\s*(from\s+{stem}\s+import|import\s+{stem}\b)", re.M)
        for importer_path, importer_text in files.items():
            if importer_path == source_path or not importing.search(importer_text):
                continue
            if _bound_module(importer_path, source_path.stem, list(files)) != source_path:
                continue
            problems = broken_calls(importer_text, source_path.stem, source_text, symbols)
            if problems:
                found.append({
                    "source": str(source_path.relative_to(root)),
                    "importer": str(importer_path.relative_to(root)),
                    "symbols": sorted(symbols),
                    "problems": [f"line {line}: {call} {problem}" for line, call, problem in problems],
                    "origin": "scan",
                })
    return found


def start(developer):
    """At session start: record and report callers in this repo that don't match their functions."""
    found = scan_repo_breaks(Path.cwd())
    kept = [r for r in _load_breaks() if r.get("origin") != "scan"]
    _save_breaks(kept + found)
    if not found:
        _notify([f"no broken callers found for {developer} in this repo"])
        return 0
    lines = [f"{r['importer']} {problem}" for r in found for problem in r["problems"]]
    steps = [f"found {len(lines)} call(s) that no longer match their function's signature:"] + lines[:10]
    context = "\n".join(
        ["Neo found calls in this repo that don't match their function's current signature."]
        + lines
        + ["Fix these calls before starting the task. Edits to the changed files stay blocked until they match."])
    print(json.dumps({
        "systemMessage": "\n".join(f"Neo: {step}" for step in steps),
        "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context},
    }))
    return 0


def pre(developer, file_path):
    steps = []
    freshness = check_freshness(developer, file_path)
    steps.append(f"freshness check on {file_path}: {freshness}")
    if freshness == "STALE_SOURCE":
        return _block(steps + [f"{file_path} changed after you last read it. "
                               f"Read the file again, then retry the edit."])

    blocking = [r for r in _load_breaks() if _same_file(r["source"], file_path)]
    if blocking:
        steps.append(f"downstream breakage on {file_path}: callers do not match the current signature")
        lines = [f"{r['importer']} {problem}" for r in blocking for problem in r["problems"]]
        return _block(steps + [f"{file_path} has a downstream breakage. Fix these callers before editing it:"]
                      + lines + ["Fix the calling file first, then retry the edit."])

    intent = os.environ.get("NEO_INTENT") or _saved_intent(developer) or f"Edit {file_path}"
    steps.append(f"intent for this edit: \"{intent[:120]}\"")
    risk, msg, lock_info = check_for_conflicts(
        agent_id=developer, file_path=file_path, intent=intent, region=None
    )
    steps.append(f"conflict check: {risk.value}" + ("" if risk == RiskLevel.LOW else f" - {msg}"))
    holder = (lock_info or {}).get("lock_holder")

    if holder and holder != developer:
        log_activity(
            developer_id=developer, file_path=file_path, intent=intent,
            lock_state="WAITING", lock_holder=holder,
            queue_position=(lock_info or {}).get("queue_position"),
            waiting_for=holder,
        )
        limit = _lock_wait_seconds()
        steps.append(f"{file_path} is locked by {holder}. {developer} is queued; "
                     f"waiting up to {limit} seconds for {holder}'s turn to end.")
        started = time.time()
        if not _wait_for_lock(file_path, developer, limit):
            return _block(steps + [f"{file_path} is still locked by {holder} after {limit} seconds. "
                                   f"{developer} is queued behind them. Do not edit this file until "
                                   f"{holder} completes."])
        steps.append(f"{holder}'s turn ended after {int(time.time() - started)} seconds. "
                     f"{developer} can take the lock on {file_path}.")

    # The first edit attempt on a file takes its lock. If the lock is taken, the
    # developer is queued, and the edit is blocked.
    lock = LockManager().acquire_lock(file_path, None, developer, "INTENT_LOCK")
    if not lock["success"]:
        return _block(steps + [f"{file_path} is locked by {lock['lock_holder']}. {developer} "
                               f"is queued behind them. Do not edit this file until "
                               f"{lock['lock_holder']} completes."])

    log_activity(
        developer_id=developer, file_path=file_path, intent=intent,
        lock_state="ACQUIRED", lock_holder=developer,
    )
    steps.append(f"lock on {file_path} taken by {developer}; held until the task ends")
    extra = None
    if risk != RiskLevel.LOW:
        extra = {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": msg,
        }}
    _notify(steps, extra)
    return 0

def post(developer, file_path):
    # The lock is kept until the task ends (see stop), so this only records the edit.
    base = get_base_snapshot(developer, file_path)
    old_content = getattr(base, "file_content", None) if base else None
    path = Path(file_path)
    new_content = path.read_text() if path.is_file() else None

    breaking, dependents, lines = analyze_change(file_path, old_content, new_content)
    if breaking:
        _log_breaking(developer, file_path, breaking)
    log_activity(developer_id=developer, file_path=file_path,
                 intent=f"Edit {file_path}", intent_category="code-generation")
    record_read(developer, file_path)

    steps = [f"edit to {file_path} by {developer} logged"]
    if breaking:
        steps.append(f"Breaking change in {file_path}: " + "; ".join(c.details for c in breaking))
    if dependents:
        steps.append(f"files that import {file_path}: {', '.join(dependents)}")
    elif not breaking:
        steps.append(f"no breaking change; no files import {file_path}")
    steps.extend(refresh_breakages(file_path, breaking, dependents))
    extra = {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                    "additionalContext": "\n".join(lines)}} if lines else None
    _notify(steps, extra)
    return 0

def _locked_by(developer):
    """Files on which this developer holds the lock right now."""
    lm = LockManager()
    files = set()
    for entry in activity_log.read_log():
        if entry.get("lock_state") == "ACQUIRED" and entry.get("lock_holder") == developer:
            files.add(entry["file_path"])
    held = []
    for path in sorted(files):
        lock = lm._get_current_lock(lm._make_lock_key(path, None, "file"))
        if lock and lock.get("lock_holder") == developer:
            held.append(path)
    return held


def stop(developer):
    """The task ended: release every lock this developer holds, and promote the next in line."""
    lm = LockManager()
    steps = []
    for path in _locked_by(developer):
        release = lm.release_lock(path, None, developer)
        log_activity(developer_id=developer, file_path=path,
                     intent=f"Work completed on {path}", intent_category="completion")
        steps.append(f"task ended: lock on {path} released by {developer}")
        nxt = release.get("next_lock_holder")
        if nxt:
            steps.append(f"{nxt} is next in the queue and now holds the lock on {path}")
    _notify(steps)
    return 0

def read(developer, file_path):
    record_read(developer, file_path)
    _notify([f"{developer} read {file_path}; baseline saved for the staleness check"])
    return 0

def _changed_files():
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
    if status.returncode != 0:
        return []
    paths = []
    for line in status.stdout.splitlines():
        entry = line[3:].strip()
        if " -> " in entry:
            entry = entry.split(" -> ")[-1]
        paths.append(entry)
    return paths


def bash(developer):
    steps = []
    notes = []
    for path_text in _changed_files():
        path = Path(path_text)
        if not path.is_file():
            continue
        try:
            current = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        base = get_base_snapshot(developer, path_text)
        if base is None:
            # Nothing was read before this change, so there is no baseline to compare with.
            record_read(developer, path_text)
            continue
        old_content = getattr(base, "file_content", None)
        if old_content == current:
            continue
        steps.append(f"shell change detected on {path_text}")

        lock_key = LockManager()._make_lock_key(path_text, None, "file")
        lock = LockManager()._get_current_lock(lock_key)
        holder = (lock or {}).get("lock_holder")
        if holder and holder != developer:
            warning = (f"{path_text} was changed from the shell while locked by {holder}. "
                       f"Tell {holder} before going further.")
            notes.append(warning)
            steps.append(f"warning: {warning}")

        breaking, _dependents, lines = analyze_change(path_text, old_content, current)
        if breaking:
            _log_breaking(developer, path_text, breaking)
            steps.append(f"breaking change in {path_text}: {len(breaking)} found")
        log_activity(developer_id=developer, file_path=path_text,
                     intent=f"Edit via shell: {path_text}", intent_category="code-generation")
        steps.append(f"shell edit logged for {developer} on {path_text}")
        record_read(developer, path_text)
        notes.extend(lines)

    extra = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "\n".join(notes)}} if notes else None
    _notify(steps, extra)
    return 0


def main(argv):
    mode = argv[1] if len(argv) > 1 else ""
    developer = os.environ.get("NEO_DEVELOPER")
    if not developer or mode not in MODES:
        return 0
    try:
        hook_input = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return 0
    if mode == "prompt":
        return prompt(developer, hook_input)
    if mode == "bash":
        return bash(developer)
    if mode == "start":
        return start(developer)
    if mode == "stop":
        return stop(developer)
    file_path = _relative_file_path(hook_input)
    if not file_path:
        return 0
    if mode == "read":
        return read(developer, file_path)
    if mode == "pre":
        return pre(developer, file_path)
    return post(developer, file_path)


if __name__ == "__main__":
    sys.exit(main(sys.argv))

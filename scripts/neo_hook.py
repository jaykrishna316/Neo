#!/usr/bin/env python3
"""Claude Code hook for Neo coordination.

  prompt  UserPromptSubmit: save the prompt as this session's intent.
  pre     PreToolUse (Edit/Write): declare intent. Block if another session holds the
          file's lock, or if the file changed since this session last read it.
  post    PostToolUse (Edit/Write): release the lock, check the change for breaking
          changes and downstream dependents, log it, and save the new baseline.
  read    PostToolUse (Read): save what this session saw.
  bash    PostToolUse (Bash): treat files changed by shell commands as edits.

Each session names itself with NEO_DEVELOPER. Without it, every mode does nothing.
NEO_INTENT overrides the intent saved from the prompt.
Exit code 2 blocks the tool call and shows the message to the session.
"""

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from core.activity_log import log_activity  # noqa: E402
from core.blast_radius import BlastRadiusCalculator  # noqa: E402
from core.breaking_change_detector import has_breaking_changes  # noqa: E402
from core.freshness import check_freshness, get_base_snapshot, record_read  # noqa: E402
from core.lock_manager import LockManager  # noqa: E402
from core.pre_gen_check import check_for_conflicts  # noqa: E402
from core.risk_classifier import RiskLevel  # noqa: E402

MODES = ("prompt", "pre", "post", "read", "bash")
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".devsync", ".neo_state"}


def _state_dir():
    return Path(os.environ.get("NEO_STATE_DIR", ".neo_state"))


def _relative_file_path(hook_input):
    path = (hook_input.get("tool_input") or {}).get("file_path")
    if not path:
        return None
    try:
        return str(Path(path).resolve().relative_to(REPO))
    except ValueError:
        return path


def _emit_pre(reason):
    """Allow the tool call and show the reason to the session."""
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "allow",
        "permissionDecisionReason": reason,
    }}))


def _emit_post(context):
    """Tell the session about the result of its tool call."""
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "additionalContext": context,
    }}))


def prompt(developer, hook_input):
    text = (hook_input.get("prompt") or "").strip()
    if text:
        state = _state_dir()
        state.mkdir(parents=True, exist_ok=True)
        (state / f"intent_{developer}.txt").write_text(text[:300])
    return 0


def _saved_intent(developer):
    path = _state_dir() / f"intent_{developer}.txt"
    return path.read_text().strip() if path.exists() else None


def scan_dependents(file_path):
    """Files in the project that import this file's module."""
    root = Path.cwd()
    module = Path(file_path).stem
    target = Path(file_path).resolve()
    pattern = re.compile(
        rf"^\s*(from\s+{re.escape(module)}\s+import|import\s+{re.escape(module)}\b)", re.M
    )
    found = []
    for path in root.rglob("*.py"):
        if any(part in SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        if path.resolve() == target:
            continue
        try:
            text = path.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if pattern.search(text):
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


def _log_breaking(developer, file_path, breaking):
    details = "; ".join(change.details for change in breaking)
    log_activity(developer_id=developer, file_path=file_path,
                 intent=f"Breaking change: {details}", intent_category="breaking-change")


def pre(developer, file_path):
    # The file changed after this session last read it: the context is stale.
    if check_freshness(developer, file_path) == "STALE_SOURCE":
        print(f"Neo: {file_path} changed after you last read it. Read the file again to "
              f"refresh your context, then retry the edit.", file=sys.stderr)
        return 2

    intent = os.environ.get("NEO_INTENT") or _saved_intent(developer) or f"Edit {file_path}"
    risk, msg, lock_info = check_for_conflicts(
        agent_id=developer, file_path=file_path, intent=intent, region=None
    )
    holder = (lock_info or {}).get("lock_holder")

    if holder and holder != developer:
        log_activity(
            developer_id=developer, file_path=file_path, intent=intent,
            lock_state="WAITING", lock_holder=holder,
            queue_position=(lock_info or {}).get("queue_position"),
            waiting_for=holder,
        )
        print(f"Neo: {file_path} is locked by {holder}. You are queued behind them. "
              f"Do not edit this file until {holder} completes.", file=sys.stderr)
        return 2

    log_activity(
        developer_id=developer, file_path=file_path, intent=intent,
        lock_state="ACQUIRED" if holder == developer else None, lock_holder=holder,
    )
    if risk != RiskLevel.LOW:
        _emit_pre(msg)
    return 0


def post(developer, file_path):
    base = get_base_snapshot(developer, file_path)
    old_content = getattr(base, "file_content", None) if base else None
    path = Path(file_path)
    new_content = path.read_text() if path.is_file() else None

    release = LockManager().release_lock(file_path, None, developer)
    breaking, _dependents, lines = analyze_change(file_path, old_content, new_content)
    if breaking:
        _log_breaking(developer, file_path, breaking)
    log_activity(developer_id=developer, file_path=file_path,
                 intent=f"Work completed on {file_path}", intent_category="completion")
    record_read(developer, file_path)

    if lines:
        _emit_post("\n".join(lines))
    nxt = release.get("next_lock_holder")
    if nxt:
        print(f"Neo: released {file_path}. {nxt} is next in the queue.", file=sys.stderr)
    return 0


def read(developer, file_path):
    record_read(developer, file_path)
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

        lock_key = LockManager()._make_lock_key(path_text, None, "file")
        lock = LockManager()._get_current_lock(lock_key)
        holder = (lock or {}).get("lock_holder")
        if holder and holder != developer:
            notes.append(f"{path_text} was changed from the shell while locked by {holder}. "
                         f"Tell {holder} before going further.")

        breaking, _dependents, lines = analyze_change(path_text, old_content, current)
        if breaking:
            _log_breaking(developer, path_text, breaking)
        log_activity(developer_id=developer, file_path=path_text,
                     intent=f"Edit via shell: {path_text}", intent_category="code-generation")
        record_read(developer, path_text)
        notes.extend(lines)

    if notes:
        _emit_post("\n".join(notes))
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

#!/usr/bin/env python3
"""Hand-off state for the two-developer workflow.

Stored in .devsync/workflow.json next to the activity log:

- inbox:    per-developer notifications
- contexts: what each developer's working context was built on
            (commit + file hash at declare time, reset at each hand-off)
- sessions: per file, the base commit and every contribution in order
            (who changed the file, at which commit, with which summary)

Hand-off sequence on a file:
  A completes  -> B's context is validated (expired if the file changed since
                  B declared) and reset to A's version; B is notified and
                  blocked from declare/complete until B refreshes
  B refreshes  -> B's disk must match A's version; the block is cleared
  B completes  -> A is notified with B's summary and diff
"""

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set

from core import activity_log

LOCK_GRANTED = "lock_granted"
WORK_COMPLETED = "work_completed"


def _state_path() -> Path:
    return Path(activity_log.ACTIVITY_LOG_DIR) / "workflow.json"


def _load() -> Dict:
    path = _state_path()
    if not path.exists():
        return {"inbox": [], "contexts": {}, "sessions": {}}
    return json.loads(path.read_text())


def _save(state: Dict) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2))


def file_hash(path: Path) -> Optional[str]:
    """sha256 of file content, or None if the file does not exist"""
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _ctx_key(developer_id: str, file_path: str) -> str:
    return f"{developer_id}|{file_path}"


# ---------- inbox ----------

def record_event(
    to: str,
    from_dev: str,
    event_type: str,
    file_path: str,
    message: str,
    summary: Optional[str] = None,
    diff: Optional[str] = None,
    refresh_required: bool = False,
    context_expired: bool = False,
    file_hash_value: Optional[str] = None,
) -> Dict:
    """Add an event to a developer's inbox."""
    state = _load()
    event = {
        "id": uuid.uuid4().hex[:12],
        "to": to,
        "from": from_dev,
        "type": event_type,
        "file_path": file_path,
        "message": message,
        "summary": summary,
        "diff": diff,
        "refresh_required": refresh_required,
        "context_expired": context_expired,
        "file_hash": file_hash_value,
        "acknowledged": False,
        "read": False,
        "timestamp": time.time(),
    }
    state["inbox"].append(event)
    _save(state)
    return event


def get_inbox(developer_id: str, unread_only: bool = False) -> List[Dict]:
    """Events for a developer, oldest first."""
    return [
        e for e in _load()["inbox"]
        if e["to"] == developer_id and (not unread_only or not e["read"])
    ]


def mark_read(developer_id: str, event_ids: List[str]) -> int:
    """Mark the given events as read. Returns how many changed."""
    state = _load()
    changed = 0
    for e in state["inbox"]:
        if e["to"] == developer_id and e["id"] in event_ids and not e["read"]:
            e["read"] = True
            changed += 1
    _save(state)
    return changed


def pending_refresh(developer_id: str, file_path: str) -> Optional[Dict]:
    """The unacknowledged refresh requirement for this developer and file, if any."""
    for e in reversed(_load()["inbox"]):
        if (e["to"] == developer_id and e["file_path"] == file_path
                and e["refresh_required"] and not e["acknowledged"]):
            return e
    return None


def acknowledge_refresh(developer_id: str, file_path: str) -> None:
    """Clear pending refresh requirements for this developer and file."""
    state = _load()
    for e in state["inbox"]:
        if (e["to"] == developer_id and e["file_path"] == file_path
                and e["refresh_required"] and not e["acknowledged"]):
            e["acknowledged"] = True
            e["read"] = True
    _save(state)


# ---------- context ----------

def set_context(developer_id: str, file_path: str, commit: Optional[str],
                file_hash_value: Optional[str]) -> None:
    """Record the baseline this developer's context was built on (at declare or refresh)."""
    state = _load()
    state["contexts"][_ctx_key(developer_id, file_path)] = {
        "commit": commit,
        "file_hash": file_hash_value,
        "updated_at": time.time(),
    }
    _save(state)


def get_context(developer_id: str, file_path: str) -> Optional[Dict]:
    return _load()["contexts"].get(_ctx_key(developer_id, file_path))


def validate_and_reset_context(developer_id: str, file_path: str, commit: Optional[str],
                               file_hash_value: Optional[str]) -> bool:
    """Validate the developer's context against the file's new version, then reset it.

    Returns True if the context had expired (the file changed since it was built).
    The context is reset to the new version either way.
    """
    old = get_context(developer_id, file_path)
    expired = old is None or old.get("file_hash") != file_hash_value
    set_context(developer_id, file_path, commit, file_hash_value)
    return expired


# ---------- file sessions ----------

def get_session(file_path: str) -> Optional[Dict]:
    return _load()["sessions"].get(file_path)


def open_session_if_needed(file_path: str, base_commit: Optional[str],
                           base_hash: Optional[str]) -> Dict:
    state = _load()
    session = state["sessions"].get(file_path)
    if session is None or session["status"] == "closed":
        session = {
            "status": "open",
            "base_commit": base_commit,
            "base_hash": base_hash,
            "contributions": [],
            "opened_at": time.time(),
        }
        state["sessions"][file_path] = session
        _save(state)
    return session


def add_contribution(file_path: str, developer_id: str, commit: Optional[str],
                     file_hash_value: Optional[str], summary: str,
                     diff: Optional[str]) -> Dict:
    state = _load()
    session = state["sessions"][file_path]
    session["contributions"].append({
        "developer": developer_id,
        "commit": commit,
        "file_hash": file_hash_value,
        "summary": summary,
        "diff": diff,
        "timestamp": time.time(),
    })
    _save(state)
    return session


def close_session(file_path: str) -> None:
    state = _load()
    if file_path in state["sessions"]:
        state["sessions"][file_path]["status"] = "closed"
        _save(state)


# ---------- participants ----------

def participants(file_path: str, exclude: Set[str]) -> Set[str]:
    """Developers who have logged activity on this file, minus excluded ones."""
    devs = {
        entry["developer_id"]
        for entry in activity_log.read_log()
        if entry.get("file_path") == file_path
    }
    return devs - exclude

#!/usr/bin/env python3
"""Per-developer inbox for the two-developer coordination workflow.

Events are stored in .devsync/inbox.json next to the activity log:
- lock_granted:   the file was released to you; you must refresh context first
- work_completed: a developer on the same file finished and submitted a summary

An event with refresh_required=True blocks the recipient from declaring intent
on, or completing work on, that file until they call refresh (acknowledge).
"""

import json
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Set

from core import activity_log

LOCK_GRANTED = "lock_granted"
WORK_COMPLETED = "work_completed"


def _inbox_path() -> Path:
    return Path(activity_log.ACTIVITY_LOG_DIR) / "inbox.json"


def _load() -> List[Dict]:
    path = _inbox_path()
    if not path.exists():
        return []
    return json.loads(path.read_text())


def _save(events: List[Dict]) -> None:
    path = _inbox_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(events, indent=2))


def record_event(
    to: str,
    from_dev: str,
    event_type: str,
    file_path: str,
    message: str,
    summary: Optional[str] = None,
    diff: Optional[str] = None,
    refresh_required: bool = False,
) -> Dict:
    """Add an event to a developer's inbox."""
    events = _load()
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
        "acknowledged": False,
        "read": False,
        "timestamp": time.time(),
    }
    events.append(event)
    _save(events)
    return event


def get_inbox(developer_id: str, unread_only: bool = False) -> List[Dict]:
    """Events for a developer, oldest first."""
    return [
        e for e in _load()
        if e["to"] == developer_id and (not unread_only or not e["read"])
    ]


def mark_read(developer_id: str, event_ids: List[str]) -> int:
    """Mark the given events as read. Returns how many changed."""
    events = _load()
    changed = 0
    for e in events:
        if e["to"] == developer_id and e["id"] in event_ids and not e["read"]:
            e["read"] = True
            changed += 1
    _save(events)
    return changed


def pending_refresh(developer_id: str, file_path: str) -> Optional[Dict]:
    """The unacknowledged refresh requirement for this developer and file, if any."""
    for e in reversed(_load()):
        if (e["to"] == developer_id and e["file_path"] == file_path
                and e["refresh_required"] and not e["acknowledged"]):
            return e
    return None


def acknowledge_refresh(developer_id: str, file_path: str) -> Optional[Dict]:
    """Clear pending refresh requirements for this developer and file.

    Returns the event that required the refresh (carries the summary and diff),
    or None if nothing was pending.
    """
    events = _load()
    latest = None
    for e in events:
        if (e["to"] == developer_id and e["file_path"] == file_path
                and e["refresh_required"] and not e["acknowledged"]):
            e["acknowledged"] = True
            e["read"] = True
            latest = e
    _save(events)
    return latest


def participants(file_path: str, exclude: Set[str]) -> Set[str]:
    """Developers who have logged activity on this file, minus excluded ones."""
    devs = {
        entry["developer_id"]
        for entry in activity_log.read_log()
        if entry.get("file_path") == file_path
    }
    return devs - exclude

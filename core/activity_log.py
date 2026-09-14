#!/usr/bin/env python3
"""Shared activity log for tracking developer intent on files.

Enhanced with support for:
- Agent metadata (model, tokens, confidence)
- Intent classification (category, scope, risk)
- Staged changes metadata
- Notifications and coordination
"""

import json
import os
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

LOG_DIR = Path(".devsync")
LOG_FILE = LOG_DIR / "activity-log.json"


@dataclass
class ActivityEntry:
    developer_id: str
    file_path: str
    intent: str
    region: Optional[str]  # e.g., "MyClass.method_name" or "lines 10-25"
    timestamp: float
    # Enhanced fields (optional)
    agent_metadata: Optional[Dict[str, Any]] = None
    intent_category: Optional[str] = None
    intent_scope: Optional[str] = None
    blocking_others: bool = False
    estimated_completion: Optional[int] = None

    def to_dict(self):
        return asdict(self)


def ensure_log_exists():
    """Ensure log directory and file exist."""
    LOG_DIR.mkdir(exist_ok=True)
    if not LOG_FILE.exists():
        LOG_FILE.write_text(json.dumps([]))


def log_activity(
    developer_id: str,
    file_path: str,
    intent: str,
    region: Optional[str] = None,
    agent_metadata: Optional[Dict[str, Any]] = None,
    intent_category: Optional[str] = None,
    intent_scope: Optional[str] = None,
    blocking_others: bool = False,
    estimated_completion: Optional[int] = None,
) -> ActivityEntry:
    """Log a developer's or agent's intent to work on a file.

    Args:
        developer_id: Developer or agent ID
        file_path: File being modified
        intent: What they intend to do
        region: Code region (e.g., "login_user (lines 20-40)")
        agent_metadata: Optional dict with agent info (model, tokens, etc.)
        intent_category: Optional category (feature/bugfix/refactor/chore)
        intent_scope: Optional scope (single-function/file/module)
        blocking_others: Whether this change blocks other developers
        estimated_completion: Estimated completion time in seconds
    """
    ensure_log_exists()

    entry = ActivityEntry(
        developer_id=developer_id,
        file_path=file_path,
        intent=intent,
        region=region,
        timestamp=time.time(),
        agent_metadata=agent_metadata,
        intent_category=intent_category,
        intent_scope=intent_scope,
        blocking_others=blocking_others,
        estimated_completion=estimated_completion,
    )

    entries = read_log()
    entries.append(entry.to_dict())

    LOG_FILE.write_text(json.dumps(entries, indent=2))
    return entry


def read_log() -> List[dict]:
    """Read all entries from the activity log."""
    ensure_log_exists()
    return json.loads(LOG_FILE.read_text())


def get_active_entries(
    file_path: Optional[str] = None,
    expiry_minutes: int = 30,
    developer_id: Optional[str] = None,
) -> List[dict]:
    """Get non-expired entries, optionally filtered by file or developer.

    Args:
        file_path: Optional file to filter by. If None, returns all active entries.
        expiry_minutes: How old entries can be before expiring
        developer_id: Optional developer to filter by
    """
    entries = read_log()
    now = time.time()
    expiry_seconds = expiry_minutes * 60

    active = []
    for entry in entries:
        age_seconds = now - entry["timestamp"]
        if age_seconds >= expiry_seconds:
            continue

        if file_path and entry["file_path"] != file_path:
            continue

        if developer_id and entry["developer_id"] != developer_id:
            continue

        active.append(entry)

    return active


def clear_log():
    """Clear the activity log (for testing)."""
    ensure_log_exists()
    LOG_FILE.write_text(json.dumps([]))


def log_entry_age_seconds(entry: dict) -> float:
    """Return age of an entry in seconds."""
    return time.time() - entry["timestamp"]


def get_blocking_entries(expiry_minutes: int = 30) -> List[dict]:
    """Get entries that are blocking other developers."""
    entries = get_active_entries(expiry_minutes=expiry_minutes)
    return [e for e in entries if e.get("blocking_others", False)]


def get_agent_entries(agent_id: str, expiry_minutes: int = 30) -> List[dict]:
    """Get all entries from a specific agent."""
    entries = get_active_entries(expiry_minutes=expiry_minutes)
    return [e for e in entries if e.get("developer_id") == agent_id]


def get_entries_by_category(
    category: str,
    expiry_minutes: int = 30,
) -> List[dict]:
    """Get entries by intent category (feature/bugfix/refactor/etc)."""
    entries = get_active_entries(expiry_minutes=expiry_minutes)
    return [e for e in entries if e.get("intent_category") == category]

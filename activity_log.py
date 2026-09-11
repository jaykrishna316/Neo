#!/usr/bin/env python3
"""Shared activity log for tracking developer intent on files."""

import json
import os
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List
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
) -> ActivityEntry:
    """Log a developer's intent to work on a file."""
    ensure_log_exists()

    entry = ActivityEntry(
        developer_id=developer_id,
        file_path=file_path,
        intent=intent,
        region=region,
        timestamp=time.time(),
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
    file_path: str,
    expiry_minutes: int = 30,
) -> List[dict]:
    """Get non-expired entries for a specific file."""
    entries = read_log()
    now = time.time()
    expiry_seconds = expiry_minutes * 60

    active = []
    for entry in entries:
        age_seconds = now - entry["timestamp"]
        if entry["file_path"] == file_path and age_seconds < expiry_seconds:
            active.append(entry)

    return active


def clear_log():
    """Clear the activity log (for testing)."""
    ensure_log_exists()
    LOG_FILE.write_text(json.dumps([]))


def log_entry_age_seconds(entry: dict) -> float:
    """Return age of an entry in seconds."""
    return time.time() - entry["timestamp"]

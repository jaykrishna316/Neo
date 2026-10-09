#!/usr/bin/env python3
"""File-based storage adapter for Neo activity log.

Implements StorageAdapter interface using local .devsync/activity-log.json.
Default for single-machine, local testing.
"""

import json
import time
from pathlib import Path
from typing import List, Optional, Dict, Any
from core.storage.base import StorageAdapter

LOG_DIR = Path(".devsync")
LOG_FILE = LOG_DIR / "activity-log.json"


class FileStorage(StorageAdapter):
    """File-based activity log storage (single machine)."""

    def __init__(self, log_file: Optional[Path] = None):
        """Initialize file storage.

        Args:
            log_file: Optional custom log file path (default .devsync/activity-log.json)
        """
        self.log_file = log_file or LOG_FILE
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_file.exists():
            self.log_file.write_text(json.dumps([], indent=2))

    def write_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Write entry to JSON file.

        Args:
            entry: Activity entry dict

        Returns:
            Entry with timestamp set
        """
        entries = self._read_raw()
        if "timestamp" not in entry:
            entry["timestamp"] = time.time()
        entries.append(entry)
        self._write_raw(entries)
        return entry

    def read_all(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read all entries, optionally filtered by tenant.

        Args:
            tenant_id: Optional tenant filter

        Returns:
            List of all entries (or tenant-filtered)
        """
        entries = self._read_raw()
        if tenant_id:
            return [e for e in entries if e.get("tenant_id", "default") == tenant_id]
        return entries

    def read_active(
        self,
        tenant_id: Optional[str] = None,
        file_path: Optional[str] = None,
        expiry_minutes: int = 30,
    ) -> List[Dict[str, Any]]:
        """Read non-expired entries.

        Args:
            tenant_id: Optional tenant filter
            file_path: Optional file path filter
            expiry_minutes: Age threshold in minutes

        Returns:
            List of active entries
        """
        entries = self._read_raw()
        now = time.time()
        expiry_seconds = expiry_minutes * 60

        active = []
        for entry in entries:
            age = now - entry.get("timestamp", now)
            if age >= expiry_seconds:
                continue

            if tenant_id and entry.get("tenant_id", "default") != tenant_id:
                continue

            if file_path and entry.get("file_path") != file_path:
                continue

            active.append(entry)

        return active

    def clear(self, tenant_id: Optional[str] = None) -> None:
        """Clear entries.

        Args:
            tenant_id: If set, clears only this tenant. If None, clears all.
        """
        if tenant_id:
            entries = self._read_raw()
            entries = [e for e in entries if e.get("tenant_id", "default") != tenant_id]
            self._write_raw(entries)
        else:
            self._write_raw([])

    def delete_entry(self, entry_id: str) -> bool:
        """Delete entry by timestamp (used as ID in file storage).

        Args:
            entry_id: Entry timestamp to delete

        Returns:
            True if found and deleted
        """
        entries = self._read_raw()
        original_len = len(entries)
        entries = [e for e in entries if str(e.get("timestamp")) != entry_id]
        if len(entries) < original_len:
            self._write_raw(entries)
            return True
        return False

    def query(
        self,
        filters: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query entries with filters.

        Args:
            filters: Dict of field -> value to match
            tenant_id: Optional tenant filter

        Returns:
            Matching entries
        """
        entries = self._read_raw()
        results = []

        for entry in entries:
            # Tenant filter
            if tenant_id and entry.get("tenant_id", "default") != tenant_id:
                continue

            # Apply all filters
            match = True
            for key, value in filters.items():
                if entry.get(key) != value:
                    match = False
                    break

            if match:
                results.append(entry)

        return results

    # Private helpers

    def _read_raw(self) -> List[Dict[str, Any]]:
        """Read raw JSON from file."""
        if not self.log_file.exists():
            return []
        try:
            content = self.log_file.read_text()
            if not content.strip():
                return []
            return json.loads(content)
        except (json.JSONDecodeError, ValueError):
            return []

    def _write_raw(self, entries: List[Dict[str, Any]]) -> None:
        """Write raw JSON to file."""
        self.log_file.write_text(json.dumps(entries, indent=2))

#!/usr/bin/env python3
"""Activity Log Adapter - Abstraction layer for file vs cloud storage.

Supports multiple backends:
- FILE: Local .devsync/activity-log.json (for testing)
- SUPABASE: Cloud PostgreSQL via Supabase (for production)
- MONGODB: Cloud MongoDB (future)
"""

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import asdict
from pathlib import Path

from .activity_log import ActivityEntry, DEFAULT_TENANT_ID, MULTITENANCY_ENABLED


class ActivityLogBackend(ABC):
    """Abstract base class for activity log storage backends."""

    @abstractmethod
    def read_log(self, tenant_id: str) -> List[ActivityEntry]:
        """Read all activity log entries for a tenant."""
        pass

    @abstractmethod
    def write_log(self, entries: List[ActivityEntry], tenant_id: str) -> None:
        """Write all activity log entries for a tenant."""
        pass

    @abstractmethod
    def append_entry(self, entry: ActivityEntry, tenant_id: str) -> None:
        """Append a single entry to the activity log."""
        pass

    @abstractmethod
    def clear_log(self, tenant_id: str) -> None:
        """Clear all entries from the activity log."""
        pass

    @abstractmethod
    def get_active_entries(self, tenant_id: str) -> List[ActivityEntry]:
        """Get all active (not completed) entries."""
        pass


class FileBackend(ActivityLogBackend):
    """File-based activity log (local .devsync/activity-log.json)."""

    def __init__(self):
        self.log_dir = Path(".devsync")
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _get_tenant_path(self, tenant_id: str) -> Path:
        """Get the activity log path for a tenant."""
        if not MULTITENANCY_ENABLED:
            return self.log_dir / "activity-log.json"

        tenant_dir = self.log_dir / "tenants" / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        return tenant_dir / "activity-log.json"

    def read_log(self, tenant_id: str) -> List[ActivityEntry]:
        """Read all entries from file-based log."""
        log_path = self._get_tenant_path(tenant_id)
        if not log_path.exists():
            return []

        try:
            with open(log_path, "r") as f:
                lines = f.readlines()

            entries = []
            for line in lines:
                if line.strip():
                    data = eval(line.strip())  # Using eval for dict compatibility
                    entries.append(ActivityEntry(**data))
            return entries
        except Exception:
            return []

    def write_log(self, entries: List[ActivityEntry], tenant_id: str) -> None:
        """Write all entries to file-based log."""
        log_path = self._get_tenant_path(tenant_id)
        with open(log_path, "w") as f:
            for entry in entries:
                f.write(str(asdict(entry)) + "\n")

    def append_entry(self, entry: ActivityEntry, tenant_id: str) -> None:
        """Append a single entry to file-based log."""
        log_path = self._get_tenant_path(tenant_id)
        with open(log_path, "a") as f:
            f.write(str(asdict(entry)) + "\n")

    def clear_log(self, tenant_id: str) -> None:
        """Clear file-based log."""
        log_path = self._get_tenant_path(tenant_id)
        if log_path.exists():
            log_path.unlink()

    def get_active_entries(self, tenant_id: str) -> List[ActivityEntry]:
        """Get active entries from file log."""
        entries = self.read_log(tenant_id)
        return [
            e for e in entries
            if not (e.agent_metadata and e.agent_metadata.get("status") == "completed")
        ]


class SupabaseBackend(ActivityLogBackend):
    """Supabase (PostgreSQL) activity log backend."""

    def __init__(self):
        """Initialize Supabase connection."""
        try:
            from supabase import create_client, Client
        except ImportError:
            raise ImportError(
                "supabase-py is required for cloud storage. "
                "Install with: pip install supabase-py"
            )

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")

        if not url or not key:
            raise ValueError(
                "SUPABASE_URL and SUPABASE_KEY environment variables required"
            )

        self.client: Client = create_client(url, key)

    def read_log(self, tenant_id: str) -> List[ActivityEntry]:
        """Read all entries from Supabase."""
        try:
            response = self.client.table("activity_log").select("*").eq(
                "tenant_id", tenant_id
            ).order("timestamp", desc=False).execute()

            entries = []
            for row in response.data:
                entry_data = {k: v for k, v in row.items() if k != "id"}
                entries.append(ActivityEntry(**entry_data))
            return entries
        except Exception as e:
            raise RuntimeError(f"Failed to read from Supabase: {e}")

    def write_log(self, entries: List[ActivityEntry], tenant_id: str) -> None:
        """Write all entries to Supabase (replace mode)."""
        try:
            # Delete existing entries for this tenant
            self.client.table("activity_log").delete().eq(
                "tenant_id", tenant_id
            ).execute()

            # Insert new entries
            for entry in entries:
                data = asdict(entry)
                self.client.table("activity_log").insert(data).execute()
        except Exception as e:
            raise RuntimeError(f"Failed to write to Supabase: {e}")

    def append_entry(self, entry: ActivityEntry, tenant_id: str) -> None:
        """Append a single entry to Supabase."""
        try:
            data = asdict(entry)
            self.client.table("activity_log").insert(data).execute()
        except Exception as e:
            raise RuntimeError(f"Failed to append to Supabase: {e}")

    def clear_log(self, tenant_id: str) -> None:
        """Clear all entries for a tenant in Supabase."""
        try:
            self.client.table("activity_log").delete().eq(
                "tenant_id", tenant_id
            ).execute()
        except Exception as e:
            raise RuntimeError(f"Failed to clear Supabase log: {e}")

    def get_active_entries(self, tenant_id: str) -> List[ActivityEntry]:
        """Get active entries from Supabase."""
        entries = self.read_log(tenant_id)
        return [
            e for e in entries
            if not (e.agent_metadata and e.agent_metadata.get("status") == "completed")
        ]


class ActivityLogAdapter:
    """Unified interface for activity log storage (file or cloud)."""

    _backend: ActivityLogBackend = None

    @classmethod
    def get_backend(cls) -> ActivityLogBackend:
        """Get the configured backend (file or cloud)."""
        if cls._backend is None:
            mode = os.getenv("ACTIVITY_LOG_MODE", "file").lower()

            if mode == "supabase":
                cls._backend = SupabaseBackend()
            elif mode == "file":
                cls._backend = FileBackend()
            else:
                raise ValueError(f"Unknown activity log mode: {mode}")

        return cls._backend

    @classmethod
    def read_log(cls, tenant_id: Optional[str] = None) -> List[ActivityEntry]:
        """Read all entries from the configured backend."""
        tenant = tenant_id or DEFAULT_TENANT_ID
        return cls.get_backend().read_log(tenant)

    @classmethod
    def write_log(
        cls, entries: List[ActivityEntry], tenant_id: Optional[str] = None
    ) -> None:
        """Write all entries to the configured backend."""
        tenant = tenant_id or DEFAULT_TENANT_ID
        cls.get_backend().write_log(entries, tenant)

    @classmethod
    def append_entry(cls, entry: ActivityEntry, tenant_id: Optional[str] = None) -> None:
        """Append a single entry to the configured backend."""
        tenant = tenant_id or DEFAULT_TENANT_ID
        cls.get_backend().append_entry(entry, tenant)

    @classmethod
    def clear_log(cls, tenant_id: Optional[str] = None) -> None:
        """Clear the activity log in the configured backend."""
        tenant = tenant_id or DEFAULT_TENANT_ID
        cls.get_backend().clear_log(tenant)

    @classmethod
    def get_active_entries(cls, tenant_id: Optional[str] = None) -> List[ActivityEntry]:
        """Get active entries from the configured backend."""
        tenant = tenant_id or DEFAULT_TENANT_ID
        return cls.get_backend().get_active_entries(tenant)

    @classmethod
    def set_backend_for_testing(cls, backend: ActivityLogBackend) -> None:
        """Override backend for testing purposes."""
        cls._backend = backend

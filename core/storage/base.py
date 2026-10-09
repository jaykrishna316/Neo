#!/usr/bin/env python3
"""Base storage adapter interface for Neo activity log."""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any


class StorageAdapter(ABC):
    """Abstract base class for activity log storage backends."""

    @abstractmethod
    def write_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Write a single activity entry.

        Args:
            entry: Activity entry dict with developer_id, file_path, intent, etc.

        Returns:
            The written entry with any server-generated fields (id, timestamp)
        """
        pass

    @abstractmethod
    def read_all(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read all entries, optionally filtered by tenant.

        Args:
            tenant_id: Optional tenant filter. If None, returns all entries.

        Returns:
            List of activity entries
        """
        pass

    @abstractmethod
    def read_active(
        self,
        tenant_id: Optional[str] = None,
        file_path: Optional[str] = None,
        expiry_minutes: int = 30,
    ) -> List[Dict[str, Any]]:
        """Read non-expired entries, optionally filtered.

        Args:
            tenant_id: Optional tenant filter
            file_path: Optional file path filter
            expiry_minutes: How old entries can be before expiring

        Returns:
            List of active (non-expired) entries
        """
        pass

    @abstractmethod
    def clear(self, tenant_id: Optional[str] = None) -> None:
        """Clear all entries (for testing).

        Args:
            tenant_id: Optional tenant filter. If None, clears all.
        """
        pass

    @abstractmethod
    def delete_entry(self, entry_id: str) -> bool:
        """Delete a specific entry by ID.

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def query(
        self,
        filters: Dict[str, Any],
        tenant_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Query entries with flexible filters.

        Args:
            filters: Dict of field -> value filters
            tenant_id: Optional tenant filter

        Returns:
            List of matching entries
        """
        pass

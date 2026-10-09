#!/usr/bin/env python3
"""Supabase cloud storage adapter for Neo activity log.

Implements StorageAdapter interface using Supabase PostgreSQL backend.
Enables multi-machine coordination and persistent data retention.
"""

import os
import time
from typing import List, Optional, Dict, Any
from core.storage.base import StorageAdapter

try:
    from supabase import create_client, Client
except ImportError:
    raise ImportError(
        "supabase-py is required for cloud storage. "
        "Install with: pip install supabase-py>=0.9.0"
    )


class SupabaseStorage(StorageAdapter):
    """Supabase-backed activity log storage (cloud multi-machine)."""

    def __init__(
        self,
        supabase_url: Optional[str] = None,
        supabase_key: Optional[str] = None,
        table_name: str = "neo_activity_log",
    ):
        """Initialize Supabase storage.

        Args:
            supabase_url: Supabase project URL (default from SUPABASE_URL env)
            supabase_key: Supabase service key (default from SUPABASE_KEY env)
            table_name: Supabase table name (default "neo_activity_log")

        Raises:
            ValueError: If URL or key not provided and env vars not set
        """
        self.url = supabase_url or os.getenv("SUPABASE_URL")
        self.key = supabase_key or os.getenv("SUPABASE_KEY")
        self.table_name = table_name

        if not self.url or not self.key:
            raise ValueError(
                "Supabase URL and key required. "
                "Set SUPABASE_URL and SUPABASE_KEY env vars or pass to __init__"
            )

        self.client: Client = create_client(self.url, self.key)

    def write_entry(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Write entry to Supabase.

        Args:
            entry: Activity entry dict

        Returns:
            Entry with server-generated ID and timestamp
        """
        if "timestamp" not in entry:
            entry["timestamp"] = time.time()

        result = self.client.table(self.table_name).insert(entry).execute()
        if result.data:
            return result.data[0] if isinstance(result.data, list) else result.data
        return entry

    def read_all(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Read all entries from Supabase.

        Args:
            tenant_id: Optional tenant filter

        Returns:
            List of all entries
        """
        query = self.client.table(self.table_name).select("*")

        if tenant_id:
            query = query.eq("tenant_id", tenant_id)

        result = query.order("timestamp", desc=False).execute()
        return result.data if result.data else []

    def read_active(
        self,
        tenant_id: Optional[str] = None,
        file_path: Optional[str] = None,
        expiry_minutes: int = 30,
    ) -> List[Dict[str, Any]]:
        """Read non-expired entries from Supabase.

        Args:
            tenant_id: Optional tenant filter
            file_path: Optional file path filter
            expiry_minutes: Age threshold in minutes

        Returns:
            List of active entries
        """
        now = time.time()
        min_timestamp = now - (expiry_minutes * 60)

        query = self.client.table(self.table_name).select("*").gte("timestamp", min_timestamp)

        if tenant_id:
            query = query.eq("tenant_id", tenant_id)

        if file_path:
            query = query.eq("file_path", file_path)

        result = query.order("timestamp", desc=False).execute()
        return result.data if result.data else []

    def clear(self, tenant_id: Optional[str] = None) -> None:
        """Clear entries from Supabase.

        Args:
            tenant_id: If set, clears only this tenant. If None, clears all.
        """
        if tenant_id:
            self.client.table(self.table_name).delete().eq("tenant_id", tenant_id).execute()
        else:
            # Warning: This deletes ALL data
            self.client.table(self.table_name).delete().neq("id", None).execute()

    def delete_entry(self, entry_id: str) -> bool:
        """Delete entry by ID from Supabase.

        Args:
            entry_id: Entry ID to delete

        Returns:
            True if deleted
        """
        result = self.client.table(self.table_name).delete().eq("id", entry_id).execute()
        return bool(result.data)

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
        query = self.client.table(self.table_name).select("*")

        if tenant_id:
            query = query.eq("tenant_id", tenant_id)

        for key, value in filters.items():
            query = query.eq(key, value)

        result = query.order("timestamp", desc=False).execute()
        return result.data if result.data else []

    @staticmethod
    def create_table_sql() -> str:
        """Get SQL to create the activity log table in Supabase.

        Returns SQL script for manual table creation.
        """
        return """
-- Create neo_activity_log table
CREATE TABLE IF NOT EXISTS neo_activity_log (
    id BIGSERIAL PRIMARY KEY,
    developer_id VARCHAR(255) NOT NULL,
    file_path VARCHAR(1024) NOT NULL,
    intent TEXT NOT NULL,
    region VARCHAR(255),
    timestamp DOUBLE PRECISION NOT NULL,
    tenant_id VARCHAR(255) DEFAULT 'default',

    -- Agent metadata
    agent_metadata JSONB,
    intent_category VARCHAR(50),
    intent_scope VARCHAR(50),
    blocking_others BOOLEAN DEFAULT FALSE,
    estimated_completion INTEGER,

    -- Lock fields
    lock_state VARCHAR(50),
    lock_holder VARCHAR(255),
    lock_acquired_at DOUBLE PRECISION,
    lock_expires_at DOUBLE PRECISION,
    lock_timeout_seconds INTEGER DEFAULT 1800,
    lock_reason VARCHAR(50),
    lock_scope VARCHAR(50),
    queue_position INTEGER,
    waiting_for VARCHAR(255),

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_developer_id ON neo_activity_log(developer_id);
CREATE INDEX idx_file_path ON neo_activity_log(file_path);
CREATE INDEX idx_tenant_id ON neo_activity_log(tenant_id);
CREATE INDEX idx_timestamp ON neo_activity_log(timestamp);
CREATE INDEX idx_lock_state ON neo_activity_log(lock_state);

-- Enable Row Level Security (optional, for multi-tenant isolation)
ALTER TABLE neo_activity_log ENABLE ROW LEVEL SECURITY;
"""

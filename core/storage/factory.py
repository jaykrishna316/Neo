#!/usr/bin/env python3
"""Storage factory for selecting appropriate backend based on configuration.

Provides a factory function to create storage adapters based on environment
configuration or explicit parameters.
"""

import os
from typing import Optional
from core.storage.base import StorageAdapter
from core.storage.file_storage import FileStorage


def get_storage(
    backend: Optional[str] = None,
    **kwargs
) -> StorageAdapter:
    """Get storage adapter based on configuration.

    Args:
        backend: Storage backend name ('file' or 'supabase').
                 Default from NEO_STORAGE_BACKEND env var or 'file'.
        **kwargs: Additional arguments passed to storage adapter

    Returns:
        Configured storage adapter instance

    Example:
        # Use file storage (default)
        storage = get_storage()

        # Use Supabase
        storage = get_storage('supabase')

        # Use specific backend with custom config
        storage = get_storage('file', log_file='./custom.json')
    """
    resolved_backend = backend or os.getenv("NEO_STORAGE_BACKEND", "file").lower()

    if resolved_backend == "file":
        return FileStorage(**kwargs)

    elif resolved_backend == "supabase":
        from core.storage.supabase_storage import SupabaseStorage
        return SupabaseStorage(**kwargs)

    elif resolved_backend == "mongodb":
        # MongoDB support coming in future phase
        raise NotImplementedError("MongoDB storage not yet implemented")

    else:
        raise ValueError(
            f"Unknown storage backend: {resolved_backend}. "
            f"Supported: file, supabase"
        )


def print_storage_info() -> None:
    """Print current storage configuration."""
    backend = os.getenv("NEO_STORAGE_BACKEND", "file").lower()
    print(f"Neo Storage Backend: {backend}")

    if backend == "supabase":
        url = os.getenv("SUPABASE_URL", "not set")
        print(f"  Supabase URL: {url[:30]}..." if len(url) > 30 else f"  Supabase URL: {url}")
    elif backend == "file":
        print("  File: .devsync/activity-log.json (local, single-machine)")

#!/usr/bin/env python3
"""Storage adapters for Neo activity log (file-based or cloud).

Supports multiple storage backends:
- FileStorage: Local file-based (default, for single machine)
- SupabaseStorage: Cloud-based with Supabase PostgreSQL
- MongoDBStorage: Document database with MongoDB (future)
"""

from core.storage.base import StorageAdapter
from core.storage.file_storage import FileStorage

__all__ = ["StorageAdapter", "FileStorage"]

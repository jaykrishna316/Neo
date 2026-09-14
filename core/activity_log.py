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

# Multitenancy configuration
MULTITENANCY_ENABLED = os.getenv("NEO_MULTITENANCY", "false").lower() == "true"
DEFAULT_TENANT_ID = os.getenv("CLAUDE_TENANT_ID", "default")

LOG_DIR = Path(".devsync")
LOG_FILE = LOG_DIR / "activity-log.json"


def get_tenant_log_path(tenant_id: Optional[str] = None) -> Path:
    """Get isolated activity log for a specific tenant.

    Args:
        tenant_id: Tenant ID (company). If None, uses DEFAULT_TENANT_ID.
                  If multitenancy is disabled, uses legacy .devsync/activity-log.json

    Returns:
        Path to tenant-specific activity-log.json
    """
    if not MULTITENANCY_ENABLED:
        return Path(".devsync/activity-log.json")  # Legacy single-tenant

    resolved_tenant = tenant_id or DEFAULT_TENANT_ID
    tenant_dir = Path(f".devsync/tenants/{resolved_tenant}")
    tenant_dir.mkdir(parents=True, exist_ok=True)

    # Write tenant marker for security validation
    marker = tenant_dir / ".tenant_id"
    if not marker.exists():
        marker.write_text(resolved_tenant)

    return tenant_dir / "activity-log.json"


def ensure_tenant_isolation(tenant_id: str) -> None:
    """Validate tenant directory structure and prevent corruption.

    Args:
        tenant_id: Tenant ID to validate

    Raises:
        ValueError: If tenant marker exists but doesn't match tenant_id
    """
    if not MULTITENANCY_ENABLED:
        return

    tenant_dir = Path(f".devsync/tenants/{tenant_id}")
    marker_file = tenant_dir / ".tenant_id"

    if marker_file.exists():
        stored_tenant = marker_file.read_text().strip()
        if stored_tenant != tenant_id:
            raise ValueError(
                f"Tenant mismatch: Expected '{tenant_id}', "
                f"but directory contains '{stored_tenant}'. "
                f"This indicates directory corruption or misconfiguration."
            )


@dataclass
class ActivityEntry:
    developer_id: str
    file_path: str
    intent: str
    region: Optional[str]  # e.g., "MyClass.method_name" or "lines 10-25"
    timestamp: float
    # Multitenancy support
    tenant_id: str = "default"
    # Enhanced fields (optional)
    agent_metadata: Optional[Dict[str, Any]] = None
    intent_category: Optional[str] = None
    intent_scope: Optional[str] = None
    blocking_others: bool = False
    estimated_completion: Optional[int] = None

    def to_dict(self):
        return asdict(self)


def ensure_log_exists(tenant_id: Optional[str] = None) -> Path:
    """Ensure log directory and file exist (tenant-aware).

    Args:
        tenant_id: Tenant ID. If None, uses DEFAULT_TENANT_ID or legacy path.

    Returns:
        Path to the activity log file
    """
    log_file = get_tenant_log_path(tenant_id)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if not log_file.exists():
        log_file.write_text(json.dumps([]))
    return log_file


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
    tenant_id: Optional[str] = None,
) -> ActivityEntry:
    """Log a developer's or agent's intent to work on a file (tenant-isolated).

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
        tenant_id: Tenant ID (company). Defaults to CLAUDE_TENANT_ID env var.
    """
    resolved_tenant = tenant_id or DEFAULT_TENANT_ID
    ensure_tenant_isolation(resolved_tenant)
    log_file = ensure_log_exists(resolved_tenant)

    entry = ActivityEntry(
        developer_id=developer_id,
        file_path=file_path,
        intent=intent,
        region=region,
        timestamp=time.time(),
        tenant_id=resolved_tenant,
        agent_metadata=agent_metadata,
        intent_category=intent_category,
        intent_scope=intent_scope,
        blocking_others=blocking_others,
        estimated_completion=estimated_completion,
    )

    entries = json.loads(log_file.read_text())
    entries.append(entry.to_dict())

    log_file.write_text(json.dumps(entries, indent=2))
    return entry


def read_log(tenant_id: Optional[str] = None) -> List[dict]:
    """Read all entries from the activity log (tenant-isolated).

    Args:
        tenant_id: Tenant ID. If None, uses DEFAULT_TENANT_ID or legacy path.

    Returns:
        List of activity entries for the tenant
    """
    log_file = ensure_log_exists(tenant_id)
    return json.loads(log_file.read_text())


def get_active_entries(
    file_path: Optional[str] = None,
    expiry_minutes: int = 30,
    developer_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
) -> List[dict]:
    """Get non-expired entries, optionally filtered by file, developer, or tenant (tenant-isolated).

    Args:
        file_path: Optional file to filter by. If None, returns all active entries.
        expiry_minutes: How old entries can be before expiring
        developer_id: Optional developer to filter by
        tenant_id: Tenant ID (company). Defaults to CLAUDE_TENANT_ID env var.
                  If multitenancy disabled, filters are ignored and all entries returned.
    """
    if not MULTITENANCY_ENABLED:
        tenant_id = None  # Use legacy path

    entries = read_log(tenant_id)
    now = time.time()
    expiry_seconds = expiry_minutes * 60

    active = []
    for entry in entries:
        age_seconds = now - entry["timestamp"]
        if age_seconds >= expiry_seconds:
            continue

        # Filter by tenant if multitenancy enabled
        if MULTITENANCY_ENABLED:
            resolved_tenant = tenant_id or DEFAULT_TENANT_ID
            if entry.get("tenant_id", "default") != resolved_tenant:
                continue

        if file_path and entry["file_path"] != file_path:
            continue

        if developer_id and entry["developer_id"] != developer_id:
            continue

        active.append(entry)

    return active


def clear_log(tenant_id: Optional[str] = None) -> None:
    """Clear the activity log for a tenant (for testing).

    Args:
        tenant_id: Tenant ID. If None, uses DEFAULT_TENANT_ID or legacy path.
    """
    log_file = ensure_log_exists(tenant_id)
    log_file.write_text(json.dumps([]))

    # Clean up empty tenant directory if multitenancy enabled
    if MULTITENANCY_ENABLED and tenant_id:
        tenant_dir = Path(f".devsync/tenants/{tenant_id}")
        try:
            if tenant_dir.exists() and not any(tenant_dir.iterdir()):
                tenant_dir.rmdir()
        except OSError:
            pass  # Directory not empty or other OS error


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

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
import threading
import time
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

try:
    import fcntl  # POSIX only; cross-process locking is skipped elsewhere
except ImportError:  # pragma: no cover
    fcntl = None

# Multitenancy configuration
MULTITENANCY_ENABLED = os.getenv("NEO_MULTITENANCY", "false").lower() == "true"
DEFAULT_TENANT_ID = os.getenv("CLAUDE_TENANT_ID", "default")

# Activity log directory (supports parallel worktrees via environment variable)
# Use NEO_ACTIVITY_LOG_DIR env var to set custom location (useful for git worktrees)
# Defaults to .devsync/ in current directory for backward compatibility
ACTIVITY_LOG_DIR = Path(os.getenv("NEO_ACTIVITY_LOG_DIR", ".devsync"))
LOG_DIR = ACTIVITY_LOG_DIR
LOG_FILE = LOG_DIR / "activity-log.json"


def get_tenant_log_path(tenant_id: Optional[str] = None) -> Path:
    """Get isolated activity log for a specific tenant.

    Args:
        tenant_id: Tenant ID (company). If None, uses DEFAULT_TENANT_ID.
                  If multitenancy is disabled, uses legacy activity-log.json

    Returns:
        Path to tenant-specific activity-log.json
    """
    if not MULTITENANCY_ENABLED:
        return ACTIVITY_LOG_DIR / "activity-log.json"  # Legacy single-tenant

    resolved_tenant = tenant_id or DEFAULT_TENANT_ID
    tenant_dir = ACTIVITY_LOG_DIR / f"tenants/{resolved_tenant}"
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

    tenant_dir = ACTIVITY_LOG_DIR / f"tenants/{tenant_id}"
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
    # Explicit lock fields (NEW - optional for backward compatibility)
    lock_state: Optional[str] = None       # "ACQUIRED", "WAITING", "RELEASED"
    lock_holder: Optional[str] = None      # developer_id who holds the lock
    lock_acquired_at: Optional[float] = None
    lock_expires_at: Optional[float] = None  # Unix timestamp (lock expiration)
    lock_timeout_seconds: int = 1800       # default 30 minutes
    lock_reason: Optional[str] = None      # "MEDIUM_CONFLICT", "HIGH_CONFLICT"
    lock_scope: Optional[str] = None       # "file", "function", "region"
    queue_position: Optional[int] = None   # Position in queue if waiting (0=next)
    waiting_for: Optional[str] = None      # developer_id this one is waiting for

    def to_dict(self):
        return asdict(self)


def ensure_log_exists(tenant_id: Optional[str] = None) -> Path:
    """Ensure log directory and file exist (tenant-aware, JSONL format).

    Args:
        tenant_id: Tenant ID. If None, uses DEFAULT_TENANT_ID or legacy path.

    Returns:
        Path to the activity log file
    """
    log_file = get_tenant_log_path(tenant_id)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if not log_file.exists():
        log_file.write_text("")
    return log_file


class _GroupCommitWriter:
    """Coalesces concurrent appends to activity log files into batched writes.

    When several threads log at once, the first one to arrive becomes the
    leader: it takes every line queued so far, appends them to each file in a
    single locked write, and wakes the others. Every caller still returns only
    after its own line is on disk, so a write is visible to readers exactly as
    soon as it was before batching existed. Batches are ordered by arrival, so
    lines land in the file in the order they were submitted.
    """

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._pending: List[Tuple[int, Path, str]] = []
        self._next_seq = 0
        self._flushed_seq = -1  # highest seq durably written so far
        self._failed: Dict[int, BaseException] = {}
        self._flushing = False

    def append(self, log_file: Path, line: str) -> None:
        with self._cond:
            seq = self._next_seq
            self._next_seq += 1
            self._pending.append((seq, log_file, line))

            while self._flushed_seq < seq and seq not in self._failed:
                if self._flushing:
                    self._cond.wait()
                else:
                    self._flush_pending_locked()

            error = self._failed.pop(seq, None)
        if error is not None:
            raise error

    def _flush_pending_locked(self) -> None:
        # Caller holds self._cond. Release it during I/O so new writers can queue.
        batch, self._pending = self._pending, []
        self._flushing = True
        self._cond.release()
        error: Optional[BaseException] = None
        try:
            _write_batch(batch)
        except BaseException as exc:  # propagated to each caller in the batch
            error = exc
        finally:
            self._cond.acquire()
            self._flushing = False
            if error is None:
                self._flushed_seq = batch[-1][0]
            else:
                for seq, _, _ in batch:
                    self._failed[seq] = error
            self._cond.notify_all()


def _write_batch(batch: List[Tuple[int, Path, str]]) -> None:
    """Write queued lines, grouped per file, with one open/lock/write per file."""
    by_file: Dict[Path, List[str]] = {}
    for _, log_file, line in batch:
        by_file.setdefault(log_file, []).append(line)

    for log_file, lines in by_file.items():
        with open(log_file, "a") as f:
            if fcntl is not None:
                # Serialize against other processes (e.g. other developers' tools)
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                f.write("".join(lines))
                f.flush()
            finally:
                if fcntl is not None:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)


_writer = _GroupCommitWriter()


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
    # Explicit lock parameters (NEW)
    lock_state: Optional[str] = None,
    lock_holder: Optional[str] = None,
    lock_acquired_at: Optional[float] = None,
    lock_expires_at: Optional[float] = None,
    lock_timeout_seconds: int = 1800,
    lock_reason: Optional[str] = None,
    lock_scope: Optional[str] = None,
    queue_position: Optional[int] = None,
    waiting_for: Optional[str] = None,
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
        lock_state: Explicit lock state ("ACQUIRED", "WAITING", "RELEASED")
        lock_holder: Developer ID who holds the lock
        lock_acquired_at: When lock was acquired (Unix timestamp)
        lock_expires_at: When lock expires (Unix timestamp)
        lock_timeout_seconds: Lock timeout in seconds (default 30 min)
        lock_reason: Reason for lock ("MEDIUM_CONFLICT", "HIGH_CONFLICT")
        lock_scope: Lock scope ("file", "function", "region")
        queue_position: Position in waiting queue (0=next)
        waiting_for: Developer ID this one is waiting for
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
        lock_state=lock_state,
        lock_holder=lock_holder,
        lock_acquired_at=lock_acquired_at,
        lock_expires_at=lock_expires_at,
        lock_timeout_seconds=lock_timeout_seconds,
        lock_reason=lock_reason,
        lock_scope=lock_scope,
        queue_position=queue_position,
        waiting_for=waiting_for,
    )

    _writer.append(log_file, json.dumps(entry.to_dict()) + "\n")
    return entry


def read_log(tenant_id: Optional[str] = None) -> List[dict]:
    """Read all entries from the activity log in JSONL format (tenant-isolated).

    Args:
        tenant_id: Tenant ID. If None, uses DEFAULT_TENANT_ID or legacy path.

    Returns:
        List of activity entries for the tenant
    """
    log_file = ensure_log_exists(tenant_id)
    if not log_file.exists():
        return []

    entries = []
    try:
        with open(log_file, "r") as f:
            for line in f:
                if line.strip():
                    try:
                        entries.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        pass
    except Exception:
        pass
    return entries


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
    log_file.write_text("")

    # Clean up empty tenant directory if multitenancy enabled
    if MULTITENANCY_ENABLED and tenant_id:
        tenant_dir = ACTIVITY_LOG_DIR / f"tenants/{tenant_id}"
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

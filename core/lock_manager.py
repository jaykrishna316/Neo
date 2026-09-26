#!/usr/bin/env python3
"""Lock management for explicit lock tracking in Neo coordination.

Provides LockManager class for acquiring, releasing, and tracking locks
on files and regions. Operates on the activity log to store lock state.
"""

import time
from typing import Optional, Dict, List, Any
from pathlib import Path
from core.activity_log import (
    get_tenant_log_path,
    read_log,
    log_activity,
    ensure_tenant_isolation,
)


class LockManager:
    """Manages explicit locks for file regions across developers."""

    def __init__(self, tenant_id: Optional[str] = None):
        """Initialize LockManager with optional tenant context.

        Args:
            tenant_id: Tenant ID for isolated lock tracking
        """
        self.tenant_id = tenant_id

    def acquire_lock(
        self,
        file_path: str,
        region: Optional[str],
        developer_id: str,
        reason: str,
        scope: str = "file",
        duration_seconds: int = 1800,
    ) -> Dict[str, Any]:
        """Acquire a lock or queue developer if lock is held.

        Args:
            file_path: File path to lock
            region: Code region (e.g., "validate_password")
            developer_id: Developer requesting lock
            reason: Reason for lock ("MEDIUM_CONFLICT" or "HIGH_CONFLICT")
            scope: Lock scope ("file" or "region")
            duration_seconds: Lock timeout in seconds

        Returns:
            {
                "success": bool,
                "lock_holder": str or None,
                "queue_position": int or None,
                "waiting_for": str or None,
                "lock_acquired_at": float or None,
                "lock_expires_at": float or None,
            }
        """
        lock_key = self._make_lock_key(file_path, region, scope)
        current_lock = self._get_current_lock(lock_key)

        now = time.time()
        lock_expires_at = now + duration_seconds

        if current_lock is None:
            # Lock is free - acquire immediately
            log_activity(
                developer_id=developer_id,
                file_path=file_path,
                intent=f"Lock acquired on {scope}",
                region=region,
                lock_state="ACQUIRED",
                lock_holder=developer_id,
                lock_acquired_at=now,
                lock_expires_at=lock_expires_at,
                lock_timeout_seconds=duration_seconds,
                lock_reason=reason,
                lock_scope=scope,
                queue_position=None,
                waiting_for=None,
                tenant_id=self.tenant_id,
            )
            return {
                "success": True,
                "lock_holder": developer_id,
                "queue_position": None,
                "waiting_for": None,
                "lock_acquired_at": now,
                "lock_expires_at": lock_expires_at,
            }
        else:
            # Lock is held - queue developer
            queue_position = self._get_next_queue_position(lock_key)

            log_activity(
                developer_id=developer_id,
                file_path=file_path,
                intent=f"Waiting for lock held by {current_lock['lock_holder']}",
                region=region,
                lock_state="WAITING",
                lock_holder=current_lock["lock_holder"],
                lock_acquired_at=current_lock.get("lock_acquired_at"),
                lock_expires_at=current_lock.get("lock_expires_at"),
                lock_timeout_seconds=duration_seconds,
                lock_reason=reason,
                lock_scope=scope,
                queue_position=queue_position,
                waiting_for=current_lock["lock_holder"],
                tenant_id=self.tenant_id,
            )
            return {
                "success": False,
                "lock_holder": current_lock["lock_holder"],
                "queue_position": queue_position,
                "waiting_for": current_lock["lock_holder"],
                "lock_acquired_at": None,
                "lock_expires_at": None,
            }

    def release_lock(
        self, file_path: str, region: Optional[str], developer_id: str, scope: str = "file"
    ) -> Dict[str, Any]:
        """Release a lock and promote next waiting developer.

        Args:
            file_path: File path to unlock
            region: Code region
            developer_id: Developer releasing lock (must be current holder)
            scope: Lock scope

        Returns:
            {
                "success": bool,
                "message": str,
                "next_lock_holder": str or None,
            }
        """
        lock_key = self._make_lock_key(file_path, region, scope)
        current_lock = self._get_current_lock(lock_key)

        if current_lock is None:
            return {
                "success": False,
                "message": f"No lock held on {lock_key}",
                "next_lock_holder": None,
            }

        if current_lock["lock_holder"] != developer_id:
            return {
                "success": False,
                "message": f"Lock held by {current_lock['lock_holder']}, not {developer_id}",
                "next_lock_holder": current_lock["lock_holder"],
            }

        # Release current lock
        log_activity(
            developer_id=developer_id,
            file_path=file_path,
            intent=f"Lock released on {scope}",
            region=region,
            lock_state="RELEASED",
            lock_holder=developer_id,
            lock_acquired_at=current_lock.get("lock_acquired_at"),
            lock_expires_at=time.time(),  # Mark as expired
            lock_reason=current_lock.get("lock_reason"),
            lock_scope=scope,
            tenant_id=self.tenant_id,
        )

        # Find next waiting developer and promote
        next_developer = self._get_next_waiting(lock_key, developer_id)

        if next_developer:
            now = time.time()
            duration_seconds = current_lock.get("lock_timeout_seconds", 1800)
            lock_expires_at = now + duration_seconds

            log_activity(
                developer_id=next_developer,
                file_path=file_path,
                intent=f"Lock acquired (promoted from queue)",
                region=region,
                lock_state="ACQUIRED",
                lock_holder=next_developer,
                lock_acquired_at=now,
                lock_expires_at=lock_expires_at,
                lock_timeout_seconds=duration_seconds,
                lock_reason=current_lock.get("lock_reason"),
                lock_scope=scope,
                queue_position=None,
                waiting_for=None,
                tenant_id=self.tenant_id,
            )
            return {
                "success": True,
                "message": f"Lock released, {next_developer} promoted",
                "next_lock_holder": next_developer,
            }

        return {
            "success": True,
            "message": "Lock released, no one waiting",
            "next_lock_holder": None,
        }

    def get_lock_state(
        self, file_path: str, region: Optional[str], scope: str = "file"
    ) -> Dict[str, Any]:
        """Get current lock state for a file/region.

        Args:
            file_path: File path
            region: Code region
            scope: Lock scope

        Returns:
            {
                "locked": bool,
                "lock_holder": str or None,
                "lock_acquired_at": float or None,
                "lock_expires_at": float or None,
                "queue_size": int,
                "queue_list": [str, ...],
            }
        """
        lock_key = self._make_lock_key(file_path, region, scope)
        current_lock = self._get_current_lock(lock_key)
        queue_list = self._get_queue(lock_key)

        if current_lock is None:
            return {
                "locked": False,
                "lock_holder": None,
                "lock_acquired_at": None,
                "lock_expires_at": None,
                "queue_size": 0,
                "queue_list": [],
            }

        return {
            "locked": True,
            "lock_holder": current_lock["lock_holder"],
            "lock_acquired_at": current_lock.get("lock_acquired_at"),
            "lock_expires_at": current_lock.get("lock_expires_at"),
            "queue_size": len(queue_list),
            "queue_list": queue_list,
        }

    def check_expired(self, file_path: str, region: Optional[str], scope: str = "file") -> bool:
        """Check if lock has expired.

        Args:
            file_path: File path
            region: Code region
            scope: Lock scope

        Returns:
            True if lock has expired, False otherwise
        """
        lock_key = self._make_lock_key(file_path, region, scope)
        log = read_log(self.tenant_id)
        now = time.time()

        # Find most recent ACQUIRED entry (don't skip expired ones)
        for entry in reversed(log):
            if (
                self._matches_lock_key(entry, lock_key)
                and entry.get("lock_state") == "ACQUIRED"
            ):
                lock_expires_at = entry.get("lock_expires_at")
                if lock_expires_at:
                    return now >= lock_expires_at
                return False

        return False

    def cleanup_expired(self) -> int:
        """Release all expired locks and auto-promote.

        Returns:
            Number of locks cleaned up
        """
        log = read_log(self.tenant_id)
        cleanup_count = 0

        # Find all active locks
        now = time.time()
        for entry in log:
            if entry.get("lock_state") == "ACQUIRED":
                lock_expires_at = entry.get("lock_expires_at")
                if lock_expires_at and now >= lock_expires_at:
                    # Auto-release and promote
                    lock_key = self._make_lock_key(
                        entry["file_path"],
                        entry.get("region"),
                        entry.get("lock_scope", "file"),
                    )
                    next_developer = self._get_next_waiting(
                        lock_key, entry["developer_id"]
                    )

                    if next_developer:
                        self.release_lock(
                            entry["file_path"],
                            entry.get("region"),
                            entry["developer_id"],
                            entry.get("lock_scope", "file"),
                        )
                    cleanup_count += 1

        return cleanup_count

    # Private helper methods

    def _make_lock_key(
        self, file_path: str, region: Optional[str], scope: str = "file"
    ) -> str:
        """Create a unique lock key from file, region, and scope.

        Args:
            file_path: File path
            region: Code region (optional)
            scope: Lock scope

        Returns:
            Lock key string
        """
        if scope == "region" and region:
            return f"{file_path}::{region}"
        return file_path

    def _get_current_lock(self, lock_key: str) -> Optional[Dict[str, Any]]:
        """Get the current lock holder for a lock key.

        Args:
            lock_key: Lock key (file or file::region)

        Returns:
            Current lock entry or None
        """
        log = read_log(self.tenant_id)
        now = time.time()

        # Find most recent ACQUIRED or WAITING entry for this lock
        for entry in reversed(log):
            if self._matches_lock_key(entry, lock_key):
                if entry.get("lock_state") in ("ACQUIRED", "WAITING"):
                    # Check expiration
                    expires_at = entry.get("lock_expires_at")
                    if expires_at and now >= expires_at:
                        continue  # Expired, skip
                    return entry

        return None

    def _matches_lock_key(self, entry: Dict[str, Any], lock_key: str) -> bool:
        """Check if entry matches lock key.

        Args:
            entry: Activity log entry
            lock_key: Lock key to match

        Returns:
            True if entry matches lock key
        """
        file_path = entry["file_path"]
        region = entry.get("region")
        scope = entry.get("lock_scope", "file")

        expected_key = self._make_lock_key(file_path, region, scope)
        return expected_key == lock_key

    def _get_queue(self, lock_key: str) -> List[str]:
        """Get list of developers waiting in queue.

        Args:
            lock_key: Lock key

        Returns:
            List of developer IDs in queue order
        """
        log = read_log(self.tenant_id)
        queue = []
        promoted_devs = set()

        # First pass: find all developers who have been promoted (have ACQUIRED state)
        for entry in log:
            if (
                self._matches_lock_key(entry, lock_key)
                and entry.get("lock_state") == "ACQUIRED"
            ):
                promoted_devs.add(entry["developer_id"])

        # Second pass: collect WAITING entries that haven't been promoted
        for entry in log:
            if (
                self._matches_lock_key(entry, lock_key)
                and entry.get("lock_state") == "WAITING"
                and entry["developer_id"] not in promoted_devs
            ):
                queue_pos = entry.get("queue_position", 999)
                queue.append((queue_pos, entry["developer_id"]))

        # Sort by queue position
        queue.sort(key=lambda x: x[0])
        return [dev_id for _, dev_id in queue]

    def _get_next_queue_position(self, lock_key: str) -> int:
        """Get next position in queue.

        Args:
            lock_key: Lock key

        Returns:
            Next queue position (0 = next to acquire)
        """
        queue = self._get_queue(lock_key)
        return len(queue)

    def _get_next_waiting(self, lock_key: str, current_holder: str) -> Optional[str]:
        """Get next developer waiting for lock.

        Args:
            lock_key: Lock key
            current_holder: Current lock holder (to skip)

        Returns:
            Next developer ID or None
        """
        queue = self._get_queue(lock_key)
        if queue:
            return queue[0]
        return None

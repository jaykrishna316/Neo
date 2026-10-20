"""
Lock Management - File-level locking and coordination between developers
Tracks lock state, queue, wait times, and lock conflicts
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class LockState(Enum):
    ACQUIRED = "ACQUIRED"
    WAITING = "WAITING"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


@dataclass
class Lock:
    """Represents a file lock"""
    file_path: str
    holder: str  # developer_id holding the lock
    state: LockState
    acquired_at: float
    expires_at: float
    reason: str = "editing"  # editing, testing, building, integrating
    scope: str = "file"  # file, function, block
    auto_renew: bool = False
    renewal_count: int = 0

    def is_expired(self) -> bool:
        return time.time() > self.expires_at

    def time_held(self) -> float:
        return time.time() - self.acquired_at

    def time_until_expiry(self) -> float:
        return max(0, self.expires_at - time.time())

    def to_dict(self):
        data = asdict(self)
        data['state'] = self.state.value
        return data


@dataclass
class LockWaiter:
    """Developer waiting for a lock"""
    developer_id: str
    file_path: str
    requested_at: float
    priority: int = 0  # 0 = normal, higher = higher priority

    def wait_time(self) -> float:
        return time.time() - self.requested_at


class LockManager:
    """Manages file locks and lock queues"""

    def __init__(self, state_dir: str = ".neo_locks"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.locks: Dict[str, Lock] = {}
        self.lock_queue: Dict[str, List[LockWaiter]] = {}  # file_path -> waiters
        self.lock_history: List[Dict] = []

    def acquire_lock(
        self,
        developer_id: str,
        file_path: str,
        reason: str = "editing",
        scope: str = "file",
        ttl_seconds: int = 1800  # 30 minutes default
    ) -> Dict:
        """Acquire a lock on a file"""

        # Check if lock exists and is still valid
        if file_path in self.locks:
            existing = self.locks[file_path]
            if not existing.is_expired() and existing.holder != developer_id:
                # Lock exists and is held by someone else - add to queue
                return self._add_to_queue(developer_id, file_path)

            # Lock expired - release it
            if existing.is_expired():
                self._release_lock(file_path, existing.holder)

        # Acquire new lock
        now = time.time()
        lock = Lock(
            file_path=file_path,
            holder=developer_id,
            state=LockState.ACQUIRED,
            acquired_at=now,
            expires_at=now + ttl_seconds,
            reason=reason,
            scope=scope
        )

        self.locks[file_path] = lock
        self.lock_history.append({
            "action": "acquired",
            "file": file_path,
            "developer": developer_id,
            "timestamp": now
        })

        return {
            "status": "acquired",
            "file_path": file_path,
            "holder": developer_id,
            "expires_in": lock.time_until_expiry()
        }

    def _add_to_queue(self, developer_id: str, file_path: str) -> Dict:
        """Add developer to lock queue"""
        if file_path not in self.lock_queue:
            self.lock_queue[file_path] = []

        # Check if already in queue
        for waiter in self.lock_queue[file_path]:
            if waiter.developer_id == developer_id:
                return {
                    "status": "waiting",
                    "queue_position": self.lock_queue[file_path].index(waiter),
                    "queue_length": len(self.lock_queue[file_path]),
                    "wait_time": waiter.wait_time()
                }

        waiter = LockWaiter(developer_id, file_path, time.time())
        self.lock_queue[file_path].append(waiter)

        return {
            "status": "waiting",
            "queue_position": len(self.lock_queue[file_path]) - 1,
            "queue_length": len(self.lock_queue[file_path]),
            "message": f"Queued at position {len(self.lock_queue[file_path]) - 1}"
        }

    def renew_lock(self, developer_id: str, file_path: str, ttl_seconds: int = 1800) -> Dict:
        """Renew an existing lock"""
        if file_path not in self.locks:
            return {"status": "error", "message": "Lock not found"}

        lock = self.locks[file_path]
        if lock.holder != developer_id:
            return {"status": "error", "message": "Not lock holder"}

        lock.expires_at = time.time() + ttl_seconds
        lock.renewal_count += 1

        return {
            "status": "renewed",
            "renewal_count": lock.renewal_count,
            "expires_in": lock.time_until_expiry()
        }

    def _release_lock(self, file_path: str, holder: str) -> None:
        """Release a lock and process queue"""
        if file_path in self.locks:
            lock = self.locks[file_path]
            lock.state = LockState.RELEASED

            self.lock_history.append({
                "action": "released",
                "file": file_path,
                "developer": holder,
                "timestamp": time.time(),
                "held_for": lock.time_held()
            })

            del self.locks[file_path]

        # Process queue - grant to next waiter
        if file_path in self.lock_queue and self.lock_queue[file_path]:
            next_waiter = self.lock_queue[file_path].pop(0)
            self.acquire_lock(next_waiter.developer_id, file_path)

    def release_lock(self, developer_id: str, file_path: str) -> Dict:
        """Release a lock held by developer"""
        if file_path not in self.locks:
            return {"status": "error", "message": "Lock not found"}

        lock = self.locks[file_path]
        if lock.holder != developer_id:
            return {"status": "error", "message": "Not lock holder"}

        self._release_lock(file_path, developer_id)

        return {"status": "released", "file_path": file_path}

    def get_lock_status(self, file_path: str) -> Dict:
        """Get status of a lock"""
        if file_path not in self.locks:
            return {
                "status": "available",
                "file_path": file_path,
                "queue_length": len(self.lock_queue.get(file_path, []))
            }

        lock = self.locks[file_path]
        queue = self.lock_queue.get(file_path, [])

        return {
            "status": "locked",
            "file_path": file_path,
            "holder": lock.holder,
            "state": lock.state.value,
            "time_held": lock.time_held(),
            "expires_in": lock.time_until_expiry(),
            "reason": lock.reason,
            "scope": lock.scope,
            "queue_length": len(queue),
            "queue_positions": [w.developer_id for w in queue]
        }

    def get_queue_position(self, developer_id: str, file_path: str) -> int:
        """Get position in queue for a file"""
        queue = self.lock_queue.get(file_path, [])
        for i, waiter in enumerate(queue):
            if waiter.developer_id == developer_id:
                return i
        return -1

    def get_all_locks(self) -> Dict:
        """Get all active locks"""
        return {
            path: lock.to_dict()
            for path, lock in self.locks.items()
            if not lock.is_expired()
        }

    def cleanup_expired_locks(self) -> int:
        """Remove expired locks"""
        expired = [
            path for path, lock in self.locks.items()
            if lock.is_expired()
        ]
        for path in expired:
            holder = self.locks[path].holder
            self._release_lock(path, holder)
        return len(expired)

    def get_blocking_info(self, developer_id: str) -> Dict:
        """What locks is this developer blocked by"""
        blocked_by = {}
        for file_path, queue in self.lock_queue.items():
            for waiter in queue:
                if waiter.developer_id == developer_id:
                    if file_path in self.locks:
                        holder = self.locks[file_path].holder
                        blocked_by[file_path] = {
                            "blocked_by": holder,
                            "queue_position": queue.index(waiter),
                            "wait_time": waiter.wait_time()
                        }
        return blocked_by

    def get_lock_metrics(self) -> Dict:
        """Get lock management metrics"""
        all_locks = self.get_all_locks()
        all_queues = self.lock_queue

        total_wait_time = 0
        total_waiters = 0
        for queue in all_queues.values():
            for waiter in queue:
                total_wait_time += waiter.wait_time()
                total_waiters += 1

        avg_wait_time = (total_wait_time / total_waiters) if total_waiters > 0 else 0

        return {
            "active_locks": len(all_locks),
            "total_waiters": total_waiters,
            "queued_files": len([q for q in all_queues.values() if q]),
            "average_wait_time": avg_wait_time,
            "max_queue_length": max([len(q) for q in all_queues.values()], default=0),
            "lock_history_count": len(self.lock_history)
        }


# Global lock manager instance
_lock_manager = None


def get_lock_manager():
    global _lock_manager
    if not _lock_manager:
        _lock_manager = LockManager()
    return _lock_manager


def acquire_lock(developer_id: str, file_path: str, reason: str = "editing"):
    return get_lock_manager().acquire_lock(developer_id, file_path, reason)


def release_lock(developer_id: str, file_path: str):
    return get_lock_manager().release_lock(developer_id, file_path)


def get_lock_status(file_path: str):
    return get_lock_manager().get_lock_status(file_path)


def get_all_locks():
    return get_lock_manager().get_all_locks()

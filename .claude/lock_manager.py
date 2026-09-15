"""
Lock Manager - Prevents concurrent edits on HIGH conflict functions
Implements hard locking for HIGH conflicts, soft warning for MEDIUM
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict


class LockManager:
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
        self.locks_dir = self.repo_path / ".activity_log" / "locks"
        self.locks_dir.mkdir(exist_ok=True)

    def acquire_lock(self, file_path: str, function_name: str, developer: str,
                     severity: str = "high", timeout_minutes: int = 30) -> Dict:
        """
        Attempt to lock a function for editing
        severity: "low" (no lock), "medium" (warning only), "high" (hard lock)

        Returns: {"locked": bool, "message": str, "lock_holder": str, "time_remaining": int}
        """

        lock_file = self._get_lock_file_path(file_path, function_name)

        if severity == "low":
            return {"locked": False, "message": "No lock needed (LOW conflict)", "lock_holder": None}

        if lock_file.exists():
            lock_data = json.loads(lock_file.read_text())
            elapsed = (datetime.now() - datetime.fromisoformat(lock_data["timestamp"])).total_seconds() / 60
            remaining = timeout_minutes - elapsed

            if remaining > 0:
                if severity == "medium":
                    return {
                        "locked": False,
                        "message": f"⚠️ WARNING: {lock_data['developer']} editing (soft lock). Continue? [Yes/No]",
                        "lock_holder": lock_data["developer"],
                        "time_remaining": int(remaining),
                        "auto_pull_suggested": True
                    }
                else:  # HIGH
                    return {
                        "locked": True,
                        "message": f"🔴 LOCKED: {lock_data['developer']} editing {function_name}",
                        "lock_holder": lock_data["developer"],
                        "time_remaining": int(remaining)
                    }
            else:
                # Timeout reached, release lock and reacquire
                lock_file.unlink()

        # Acquire new lock
        lock_data = {
            "file": file_path,
            "function": function_name,
            "developer": developer,
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "timeout_minutes": timeout_minutes
        }

        lock_file.write_text(json.dumps(lock_data, indent=2))

        return {
            "locked": False,
            "message": f"✅ Lock acquired by {developer}",
            "lock_holder": developer,
            "time_remaining": timeout_minutes
        }

    def release_lock(self, file_path: str, function_name: str) -> Dict:
        """Release lock on a function"""
        lock_file = self._get_lock_file_path(file_path, function_name)

        if lock_file.exists():
            lock_data = json.loads(lock_file.read_text())
            lock_file.unlink()
            return {
                "released": True,
                "message": f"🔓 Lock released by {lock_data['developer']}",
                "held_by": lock_data["developer"]
            }

        return {"released": False, "message": "No lock found"}

    def get_lock_status(self, file_path: str, function_name: str) -> Optional[Dict]:
        """Get current lock status"""
        lock_file = self._get_lock_file_path(file_path, function_name)

        if lock_file.exists():
            return json.loads(lock_file.read_text())

        return None

    def list_all_locks(self) -> list:
        """List all active locks"""
        locks = []
        for lock_file in self.locks_dir.glob("*.json"):
            locks.append(json.loads(lock_file.read_text()))
        return locks

    def _get_lock_file_path(self, file_path: str, function_name: str) -> Path:
        """Generate lock file path"""
        safe_name = f"{file_path.replace('/', '_')}_{function_name}.lock.json"
        return self.locks_dir / safe_name

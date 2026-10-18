"""
Error & Exception Tracking - Monitor errors, test failures, and exception handling
"""

import json
import time
from pathlib import Path
from typing import Dict, List
from collections import defaultdict


class ErrorTracker:
    """Track errors and exceptions during development"""

    def __init__(self, state_dir: str = ".neo_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.errors_file = self.state_dir / "error_tracking.json"
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        if self.errors_file.exists():
            return json.loads(self.errors_file.read_text())
        return {
            "errors": [],
            "test_failures": [],
            "exceptions": [],
            "recovery_times": []
        }

    def _save_data(self) -> None:
        self.errors_file.write_text(json.dumps(self.data, indent=2))

    def log_error(self, file_path: str, error_type: str, severity: str, description: str) -> Dict:
        """Log an error in code"""
        error = {
            "file": file_path,
            "type": error_type,  # syntax, type, logic, runtime
            "severity": severity,  # critical, high, medium, low
            "description": description,
            "timestamp": time.time(),
            "resolved": False,
            "resolution_time": None
        }

        self.data["errors"].append(error)
        self._save_data()

        return {"status": "logged", "error": error}

    def log_test_failure(self, test_name: str, file_path: str, failure_reason: str) -> Dict:
        """Log a test failure"""
        failure = {
            "test": test_name,
            "file": file_path,
            "reason": failure_reason,
            "timestamp": time.time(),
            "resolved": False
        }

        self.data["test_failures"].append(failure)
        self._save_data()

        return {"status": "logged", "test_failure": failure}

    def resolve_error(self, file_path: str, error_type: str) -> Dict:
        """Mark an error as resolved"""
        now = time.time()

        for error in self.data["errors"]:
            if error["file"] == file_path and error["type"] == error_type and not error["resolved"]:
                error["resolved"] = True
                error["resolution_time"] = now - error["timestamp"]
                self.data["recovery_times"].append(error["resolution_time"])
                break

        self._save_data()

        avg_recovery = (
            sum(self.data["recovery_times"]) / len(self.data["recovery_times"])
            if self.data["recovery_times"]
            else 0
        )

        return {
            "status": "resolved",
            "average_recovery_time": avg_recovery
        }

    def log_exception(self, exception_type: str, message: str, traceback: str) -> Dict:
        """Log an unhandled exception"""
        exception = {
            "type": exception_type,
            "message": message,
            "traceback": traceback,
            "timestamp": time.time()
        }

        self.data["exceptions"].append(exception)
        self._save_data()

        return {"status": "logged", "exception": exception}

    def get_error_count(self) -> int:
        """Total errors logged"""
        return len(self.data["errors"])

    def get_error_types(self) -> Dict[str, int]:
        """Count errors by type"""
        type_counts = defaultdict(int)
        for error in self.data["errors"]:
            type_counts[error["type"]] += 1
        return dict(type_counts)

    def get_test_failure_count(self) -> int:
        """Total test failures"""
        return len(self.data["test_failures"])

    def get_test_failure_rate(self) -> float:
        """Percentage of tests failing"""
        if not self.data["test_failures"]:
            return 0.0

        total_tests = 100  # Placeholder
        failures = len([f for f in self.data["test_failures"] if not f["resolved"]])

        return (failures / total_tests * 100) if total_tests > 0 else 0.0

    def get_flaky_test_count(self) -> int:
        """Count of flaky/intermittent tests"""
        # Tests that failed multiple times
        test_counts = defaultdict(int)
        for failure in self.data["test_failures"]:
            test_counts[failure["test"]] += 1

        return len([t for t in test_counts.values() if t > 1])

    def get_unhandled_exceptions(self) -> int:
        """Count of unhandled exceptions"""
        return len(self.data["exceptions"])

    def get_exception_coverage(self) -> float:
        """Percentage of code with try/catch (estimated)"""
        return 75.0  # Placeholder

    def get_average_recovery_time(self) -> float:
        """Average time to fix errors"""
        if not self.data["recovery_times"]:
            return 0.0
        return sum(self.data["recovery_times"]) / len(self.data["recovery_times"])

    def get_error_metrics(self) -> Dict:
        """Get all error tracking metrics"""
        return {
            "error_count": self.get_error_count(),
            "error_types": self.get_error_types(),
            "test_failures": self.get_test_failure_count(),
            "test_failure_rate": self.get_test_failure_rate(),
            "flaky_tests": self.get_flaky_test_count(),
            "unhandled_exceptions": self.get_unhandled_exceptions(),
            "exception_coverage": self.get_exception_coverage(),
            "average_recovery_time": self.get_average_recovery_time()
        }


# Global instance
_error_tracker = None


def get_error_tracker():
    global _error_tracker
    if not _error_tracker:
        _error_tracker = ErrorTracker()
    return _error_tracker


def log_error(file_path: str, error_type: str, severity: str, description: str):
    return get_error_tracker().log_error(file_path, error_type, severity, description)


def log_test_failure(test_name: str, file_path: str, failure_reason: str):
    return get_error_tracker().log_test_failure(test_name, file_path, failure_reason)


def get_error_metrics():
    return get_error_tracker().get_error_metrics()

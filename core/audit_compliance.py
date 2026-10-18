"""
Audit & Compliance Metrics - Code review, security scanning, and compliance tracking
"""

import json
import time
from pathlib import Path
from typing import Dict, List
from enum import Enum


class ReviewStatus(Enum):
    APPROVED = "APPROVED"
    PENDING = "PENDING"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"


class ComplianceTracker:
    """Track audit, compliance, and code review metrics"""

    def __init__(self, state_dir: str = ".neo_state"):
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.compliance_file = self.state_dir / "audit_compliance.json"
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        if self.compliance_file.exists():
            return json.loads(self.compliance_file.read_text())
        return {
            "reviews": [],
            "security_scans": [],
            "compliance_checks": [],
            "violations": []
        }

    def _save_data(self) -> None:
        self.compliance_file.write_text(json.dumps(self.data, indent=2))

    def log_code_review(self, pr_number: int, reviewer: str, status: str, comments: int = 0) -> Dict:
        """Log a code review"""
        review = {
            "pr": pr_number,
            "reviewer": reviewer,
            "status": status,  # approved, pending, rejected, changes-requested
            "comment_count": comments,
            "timestamp": time.time()
        }

        self.data["reviews"].append(review)
        self._save_data()

        return {"status": "logged", "review": review}

    def log_security_scan(self, file_path: str, scan_type: str, vulnerabilities: int) -> Dict:
        """Log security scan results"""
        scan = {
            "file": file_path,
            "scan_type": scan_type,
            "vulnerability_count": vulnerabilities,
            "severity": self._classify_vulnerability_severity(vulnerabilities),
            "timestamp": time.time()
        }

        self.data["security_scans"].append(scan)
        self._save_data()

        return {"status": "scanned", "scan": scan}

    def _classify_vulnerability_severity(self, count: int) -> str:
        """Classify severity based on vulnerability count"""
        if count == 0:
            return "none"
        elif count <= 3:
            return "low"
        elif count <= 10:
            return "medium"
        else:
            return "high"

    def log_compliance_check(self, check_name: str, passed: bool, details: str = "") -> Dict:
        """Log a compliance check"""
        check = {
            "name": check_name,
            "passed": passed,
            "details": details,
            "timestamp": time.time()
        }

        self.data["compliance_checks"].append(check)
        self._save_data()

        return {"status": "logged", "check": check}

    def log_violation(self, violation_type: str, file_path: str, rule: str) -> Dict:
        """Log a policy violation"""
        violation = {
            "type": violation_type,
            "file": file_path,
            "rule": rule,
            "timestamp": time.time(),
            "resolved": False
        }

        self.data["violations"].append(violation)
        self._save_data()

        return {"status": "logged", "violation": violation}

    def get_review_status(self, pr_number: int) -> str:
        """Get current review status of a PR"""
        for review in reversed(self.data["reviews"]):
            if review["pr"] == pr_number:
                return review["status"]
        return "unknown"

    def get_review_comment_count(self, pr_number: int) -> int:
        """Get total review comments on PR"""
        total = 0
        for review in self.data["reviews"]:
            if review["pr"] == pr_number:
                total += review["comment_count"]
        return total

    def get_security_scan_results(self) -> Dict:
        """Get latest security scan results"""
        if not self.data["security_scans"]:
            return {"scan_result": "none", "vulnerabilities": 0}

        latest_scan = self.data["security_scans"][-1]

        return {
            "scan_result": latest_scan["severity"],
            "vulnerability_count": latest_scan["vulnerability_count"],
            "file": latest_scan["file"]
        }

    def get_compliance_status(self) -> bool:
        """Check if all compliance checks passed"""
        if not self.data["compliance_checks"]:
            return True

        return all(check["passed"] for check in self.data["compliance_checks"][-10:])

    def get_accessibility_score(self) -> float:
        """Estimate accessibility compliance (0-100)"""
        return 85.0  # Placeholder

    def get_license_compliance(self) -> bool:
        """Check if dependencies are license-compliant"""
        return True  # Placeholder

    def get_open_violations(self) -> int:
        """Count of unresolved policy violations"""
        return len([v for v in self.data["violations"] if not v["resolved"]])

    def get_audit_metrics(self) -> Dict:
        """Get all audit and compliance metrics"""
        return {
            "review_count": len(self.data["reviews"]),
            "review_status": self.get_review_status(0) if self.data["reviews"] else "none",
            "review_comments": sum(r["comment_count"] for r in self.data["reviews"]),
            "security_scan_count": len(self.data["security_scans"]),
            "security_results": self.get_security_scan_results(),
            "compliance_checks": len(self.data["compliance_checks"]),
            "compliance_passed": self.get_compliance_status(),
            "violations": self.get_open_violations(),
            "accessibility_score": self.get_accessibility_score(),
            "license_compliance": self.get_license_compliance()
        }


# Global instance
_compliance_tracker = None


def get_compliance_tracker():
    global _compliance_tracker
    if not _compliance_tracker:
        _compliance_tracker = ComplianceTracker()
    return _compliance_tracker


def log_code_review(pr_number: int, reviewer: str, status: str, comments: int = 0):
    return get_compliance_tracker().log_code_review(pr_number, reviewer, status, comments)


def log_security_scan(file_path: str, scan_type: str, vulnerabilities: int):
    return get_compliance_tracker().log_security_scan(file_path, scan_type, vulnerabilities)


def log_compliance_check(check_name: str, passed: bool, details: str = ""):
    return get_compliance_tracker().log_compliance_check(check_name, passed, details)


def get_audit_metrics():
    return get_compliance_tracker().get_audit_metrics()

#!/usr/bin/env python3
"""
Breaking Change Tracking & Management

Tracks API/function signature changes that break downstream services.
Supports both manual registration and automatic detection.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import re


@dataclass
class BreakingChange:
    """A single breaking change in a service."""
    repo: str
    file_path: str
    symbol: str  # function/class name
    change_type: str  # "signature", "return_type", "removed", "deprecated"
    old_value: str
    new_value: str
    severity: str  # "LOW", "MEDIUM", "HIGH"
    affected_services: List[str]
    status: str  # "UNRESOLVED", "IN_PROGRESS", "RESOLVED"
    timestamp: str
    recorded_by: str
    description: str
    resolution_notes: Optional[str] = None


class BreakingChangeTracker:
    """Track and manage breaking changes across repos."""

    def __init__(self, log_dir: str = ".devsync/breaking-changes"):
        """Initialize breaking change tracker."""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / "breaking_changes.log"

    def record_breaking_change(
        self,
        repo: str,
        file_path: str,
        symbol: str,
        change_type: str,
        old_value: str,
        new_value: str,
        severity: str,
        affected_services: List[str],
        recorded_by: str,
        description: str,
    ) -> BreakingChange:
        """
        Manually record a breaking change.

        Args:
            repo: Service/repo name (e.g., "auth-service")
            file_path: File where change occurred
            symbol: Function/class name
            change_type: "signature", "return_type", "removed", "deprecated"
            old_value: Previous signature/value
            new_value: New signature/value
            severity: "LOW", "MEDIUM", "HIGH"
            affected_services: List of services that depend on this
            recorded_by: Developer ID recording the change
            description: Human-readable description
        """
        change = BreakingChange(
            repo=repo,
            file_path=file_path,
            symbol=symbol,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
            severity=severity,
            affected_services=affected_services,
            status="UNRESOLVED",
            timestamp=datetime.utcnow().isoformat(),
            recorded_by=recorded_by,
            description=description,
        )

        # Append to log
        with open(self.log_file, "a") as f:
            f.write(json.dumps(asdict(change)) + "\n")

        return change

    def auto_detect_breaking_changes(
        self,
        repo: str,
        old_code: str,
        new_code: str,
        file_path: str,
        recorded_by: str,
    ) -> List[BreakingChange]:
        """
        Auto-detect breaking changes by analyzing diffs.

        Args:
            repo: Service name
            old_code: Previous code
            new_code: New code
            file_path: File path
            recorded_by: Developer ID

        Returns:
            List of detected breaking changes
        """
        changes = []

        # Detect function signature changes
        old_sigs = self._extract_function_signatures(old_code)
        new_sigs = self._extract_function_signatures(new_code)

        for func_name, old_sig in old_sigs.items():
            if func_name not in new_sigs:
                # Function removed
                change = BreakingChange(
                    repo=repo,
                    file_path=file_path,
                    symbol=func_name,
                    change_type="removed",
                    old_value=old_sig,
                    new_value="<removed>",
                    severity="HIGH",
                    affected_services=[],  # To be filled by dependency resolver
                    status="UNRESOLVED",
                    timestamp=datetime.utcnow().isoformat(),
                    recorded_by=recorded_by,
                    description=f"Function {func_name} was removed",
                )
                changes.append(change)
            elif new_sigs[func_name] != old_sig:
                # Signature changed
                change = BreakingChange(
                    repo=repo,
                    file_path=file_path,
                    symbol=func_name,
                    change_type="signature",
                    old_value=old_sig,
                    new_value=new_sigs[func_name],
                    severity="MEDIUM",
                    affected_services=[],
                    status="UNRESOLVED",
                    timestamp=datetime.utcnow().isoformat(),
                    recorded_by=recorded_by,
                    description=f"Function {func_name} signature changed",
                )
                changes.append(change)

        # Store detected changes
        for change in changes:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(asdict(change)) + "\n")

        return changes

    def get_unresolved_changes(self, repo: Optional[str] = None) -> List[BreakingChange]:
        """Get all unresolved breaking changes."""
        if not self.log_file.exists():
            return []

        changes = []
        with open(self.log_file) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("status") == "UNRESOLVED":
                        if repo is None or data.get("repo") == repo:
                            changes.append(BreakingChange(**data))
                except:
                    continue

        return changes

    def get_breaking_changes_for_service(self, service: str) -> List[BreakingChange]:
        """Get breaking changes that affect a specific service."""
        if not self.log_file.exists():
            return []

        changes = []
        with open(self.log_file) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    change = BreakingChange(**data)
                    if service in change.affected_services:
                        changes.append(change)
                except:
                    continue

        return changes

    def resolve_breaking_change(
        self,
        repo: str,
        symbol: str,
        resolution_notes: str,
    ) -> bool:
        """
        Mark a breaking change as resolved.

        Args:
            repo: Source repo
            symbol: Symbol that was changed
            resolution_notes: How it was resolved

        Returns:
            True if resolved, False if not found
        """
        if not self.log_file.exists():
            return False

        changes = []
        found = False

        with open(self.log_file) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("repo") == repo and data.get("symbol") == symbol:
                        if data.get("status") == "UNRESOLVED":
                            data["status"] = "RESOLVED"
                            data["resolution_notes"] = resolution_notes
                            found = True
                    changes.append(data)
                except:
                    continue

        # Rewrite log with updates
        if found:
            with open(self.log_file, "w") as f:
                for change in changes:
                    f.write(json.dumps(change) + "\n")

        return found

    def _extract_function_signatures(self, code: str) -> Dict[str, str]:
        """Extract function signatures from Python code."""
        signatures = {}

        # Python function pattern: def function_name(args) -> return_type:
        pattern = r"def\s+(\w+)\s*\((.*?)\)\s*(?:->\s*(.+?))?\s*:"
        matches = re.finditer(pattern, code)

        for match in matches:
            func_name = match.group(1)
            params = match.group(2).strip()
            return_type = match.group(3) or "None"
            signature = f"{func_name}({params}) -> {return_type}"
            signatures[func_name] = signature

        return signatures

    def format_breaking_changes(self, changes: List[BreakingChange]) -> str:
        """Format breaking changes for display."""
        lines = []
        lines.append("=" * 80)
        lines.append("BREAKING CHANGES")
        lines.append("=" * 80)
        lines.append("")

        if not changes:
            lines.append("No breaking changes recorded.")
            return "\n".join(lines)

        by_repo = {}
        for change in changes:
            if change.repo not in by_repo:
                by_repo[change.repo] = []
            by_repo[change.repo].append(change)

        for repo, repo_changes in by_repo.items():
            lines.append(f"📦 {repo}")
            for change in repo_changes:
                severity_icon = "🔴" if change.severity == "HIGH" else "🟡" if change.severity == "MEDIUM" else "🟢"
                lines.append(f"  {severity_icon} {change.symbol} ({change.change_type})")
                lines.append(f"     From: {change.old_value}")
                lines.append(f"     To:   {change.new_value}")
                lines.append(f"     Affects: {', '.join(change.affected_services)}")
                lines.append(f"     Status: {change.status}")
            lines.append("")

        lines.append("=" * 80)
        return "\n".join(lines)

#!/usr/bin/env python3
"""
Dependency Resolution & Cross-Repo Validation

Tracks service dependencies and validates that breaking changes are resolved
before dependent services proceed with work.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
import re
from .breaking_change_tracker import BreakingChangeTracker, BreakingChange


@dataclass
class ServiceDependency:
    """A dependency relationship between services."""
    service: str  # The service
    depends_on: List[str]  # Services it depends on
    repo_urls: Dict[str, str]  # Service -> repo URL mapping
    last_updated: str


@dataclass
class UnresolvedDependency:
    """An unresolved breaking change affecting a service."""
    service: str
    blocking_repo: str
    breaking_change: BreakingChange
    severity: str
    blocks_work: bool


class DependencyResolver:
    """Resolve and validate service dependencies."""

    def __init__(self, config_dir: str = ".devsync/dependencies", breaking_changes_dir: str = ".devsync/breaking-changes"):
        """Initialize dependency resolver."""
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "dependencies.json"
        self.breaking_change_tracker = BreakingChangeTracker(breaking_changes_dir)
        self.dependencies = self._load_dependencies()

    def _load_dependencies(self) -> Dict[str, ServiceDependency]:
        """Load dependency configuration."""
        if not self.config_file.exists():
            return {}

        try:
            with open(self.config_file) as f:
                data = json.load(f)
                return {
                    service: ServiceDependency(**dep_data)
                    for service, dep_data in data.items()
                }
        except:
            return {}

    def save_dependencies(self) -> None:
        """Save dependency configuration to disk."""
        data = {
            service: asdict(dep)
            for service, dep in self.dependencies.items()
        }
        with open(self.config_file, "w") as f:
            json.dump(data, f, indent=2)

    def register_dependency(
        self,
        service: str,
        depends_on: List[str],
        repo_urls: Dict[str, str],
    ) -> ServiceDependency:
        """
        Register a service's dependencies.

        Args:
            service: Service name
            depends_on: List of services it depends on
            repo_urls: Mapping of service -> repo URL
        """
        from datetime import datetime

        dep = ServiceDependency(
            service=service,
            depends_on=depends_on,
            repo_urls=repo_urls,
            last_updated=datetime.utcnow().isoformat(),
        )
        self.dependencies[service] = dep
        self.save_dependencies()
        return dep

    def auto_detect_dependencies(
        self,
        service: str,
        code_files: List[Tuple[str, str]],  # [(file_path, code), ...]
    ) -> List[str]:
        """
        Auto-detect dependencies by analyzing imports.

        Args:
            service: Service name
            code_files: List of (file_path, code) tuples

        Returns:
            List of detected dependencies
        """
        detected_deps = set()

        for file_path, code in code_files:
            # Python imports
            if file_path.endswith(".py"):
                # from X import Y
                pattern_from = r"^from\s+([\w\.]+)\s+import"
                # import X
                pattern_import = r"^import\s+([\w\.]+)"

                for line in code.split("\n"):
                    m_from = re.match(pattern_from, line)
                    m_import = re.match(pattern_import, line)

                    if m_from:
                        module = m_from.group(1).split(".")[0]
                        detected_deps.add(module)
                    elif m_import:
                        module = m_import.group(1).split(".")[0]
                        detected_deps.add(module)

            # JavaScript/TypeScript imports
            elif file_path.endswith((".js", ".ts", ".tsx")):
                # import X from 'package'
                pattern = r"import\s+.*?from\s+['\"]([^'\"]+)['\"]"
                matches = re.finditer(pattern, code)
                for match in matches:
                    pkg = match.group(1).split("/")[0]
                    detected_deps.add(pkg)

        return list(detected_deps)

    def check_unresolved_dependencies(
        self,
        service: str,
    ) -> List[UnresolvedDependency]:
        """
        Check if a service has unresolved upstream dependencies.

        Args:
            service: Service to check

        Returns:
            List of unresolved dependencies that block work
        """
        unresolved = []

        # Get this service's dependencies
        if service not in self.dependencies:
            return unresolved

        depends_on = self.dependencies[service].depends_on

        # For each dependency, check for unresolved breaking changes
        for blocking_service in depends_on:
            breaking_changes = (
                self.breaking_change_tracker.get_unresolved_changes(blocking_service)
            )

            for change in breaking_changes:
                if service in change.affected_services:
                    unresolved.append(
                        UnresolvedDependency(
                            service=service,
                            blocking_repo=blocking_service,
                            breaking_change=change,
                            severity=change.severity,
                            blocks_work=change.severity in ["HIGH", "MEDIUM"],
                        )
                    )

        return unresolved

    def get_dependency_chain(self, service: str, max_depth: int = 5) -> Dict[str, any]:
        """
        Get the full dependency chain for a service.

        Args:
            service: Service to analyze
            max_depth: Maximum recursion depth

        Returns:
            Dependency tree
        """
        if max_depth <= 0 or service not in self.dependencies:
            return {"service": service, "depends_on": []}

        deps = self.dependencies[service].depends_on

        return {
            "service": service,
            "depends_on": [
                self.get_dependency_chain(dep, max_depth - 1) for dep in deps
            ],
        }

    def format_unresolved_dependencies(
        self, unresolved: List[UnresolvedDependency]
    ) -> str:
        """Format unresolved dependencies for display."""
        lines = []
        lines.append("=" * 80)
        lines.append("UNRESOLVED DEPENDENCIES")
        lines.append("=" * 80)
        lines.append("")

        if not unresolved:
            lines.append("✅ No unresolved dependencies")
            return "\n".join(lines)

        lines.append(f"⚠️  {len(unresolved)} unresolved dependencies found:")
        lines.append("")

        for dep in unresolved:
            severity_icon = "🔴" if dep.severity == "HIGH" else "🟡"
            blocks = "🚫 BLOCKS WORK" if dep.blocks_work else "⚠️  WARNING"

            lines.append(f"{severity_icon} {blocks}")
            lines.append(f"   Service: {dep.service}")
            lines.append(f"   Blocking: {dep.blocking_repo}")
            lines.append(f"   Change: {dep.breaking_change.symbol} "
                        f"({dep.breaking_change.change_type})")
            lines.append(f"   Description: {dep.breaking_change.description}")
            lines.append("")

        lines.append("=" * 80)
        lines.append("Resolution required before proceeding with work")
        lines.append("=" * 80)

        return "\n".join(lines)

#!/usr/bin/env python3
"""
Shared Service for Multi-Developer Coordination
Manages context sharing, change summaries, and developer notifications
Implements fair notification where ALL associated developers are notified of ALL changes
"""

from typing import Dict, List, Set, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field, asdict
import json


@dataclass
class ContextVersion:
    """Represents a context snapshot at a point in time"""
    file: str
    function: str
    version: str  # e.g., "ctx-auth-v1", "ctx-auth-v2"
    created_by: str
    created_at: str
    git_hash: str
    coverage_percent: float
    key_assumptions: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    staleness_age_ms: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChangeSummary:
    """Summary of changes sent to developers"""
    id: str
    from_developer: str
    to_developers: List[str]
    file: str
    function: str
    created_at: str
    intent: str
    lines_added: int
    lines_removed: int
    test_coverage_delta: int
    conflict_risk: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SharedChangeLogEntry:
    """Entry in the shared change log - tracks all developer activities"""
    sequence: int
    timestamp: str
    developer: str
    file: str
    function: str
    intent: str
    lines_added: int
    lines_removed: int
    context_version_used: str
    context_version_created: str
    change_summary_sent_to: List[str]  # All developers notified
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SharedService:
    """
    Central service for multi-developer coordination
    Manages context sharing, change summaries, and notifications
    """

    def __init__(self):
        # Per-file tracking
        self.developers_on_file: Dict[str, Set[str]] = {}  # file -> set of developers
        self.context_versions: Dict[str, List[ContextVersion]] = {}  # file -> list of context versions
        self.current_context: Dict[str, Optional[ContextVersion]] = {}  # file -> current context

        # Change tracking
        self.change_summaries: List[ChangeSummary] = []
        self.shared_change_log: List[SharedChangeLogEntry] = []

        # Pending notifications per developer
        self.pending_summaries: Dict[str, List[ChangeSummary]] = {}  # developer -> summaries waiting

        # Sequence counter
        self.sequence_counter = 0

    def declare_intent(self, developer: str, file: str, function: str) -> None:
        """Developer declares intent on a file"""
        if file not in self.developers_on_file:
            self.developers_on_file[file] = set()
        self.developers_on_file[file].add(developer)

    def share_context(self, file: str, function: str, developer: str,
                     git_hash: str, coverage: float, assumptions: List[str],
                     dependencies: List[str]) -> ContextVersion:
        """
        Share context when developer declares intent
        Context shared BEFORE lock applies (Phase 2 requirement)
        """
        if file not in self.context_versions:
            self.context_versions[file] = []

        # Generate version identifier
        version_count = len(self.context_versions[file]) + 1
        version_id = f"ctx-{file.replace('.py', '')}-v{version_count}"

        context = ContextVersion(
            file=file,
            function=function,
            version=version_id,
            created_by=developer,
            created_at=datetime.now().isoformat(),
            git_hash=git_hash,
            coverage_percent=coverage,
            key_assumptions=assumptions,
            dependencies=dependencies
        )

        self.context_versions[file].append(context)
        self.current_context[file] = context

        return context

    def publish_change_summary(self, from_developer: str, file: str, function: str,
                              intent: str, lines_added: int, lines_removed: int,
                              test_coverage_delta: int, conflict_risk: str) -> ChangeSummary:
        """
        Publish change summary to ALL developers associated with this file
        (Phase 3 requirement: fair notification)
        """
        # Get all developers who declared intent on this file
        associated_developers = self.developers_on_file.get(file, set())
        to_developers = [d for d in associated_developers if d != from_developer]

        # Create summary
        summary_id = f"cs-{len(self.change_summaries):03d}"
        summary = ChangeSummary(
            id=summary_id,
            from_developer=from_developer,
            to_developers=to_developers,
            file=file,
            function=function,
            created_at=datetime.now().isoformat(),
            intent=intent,
            lines_added=lines_added,
            lines_removed=lines_removed,
            test_coverage_delta=test_coverage_delta,
            conflict_risk=conflict_risk
        )

        self.change_summaries.append(summary)

        # Queue summaries for all recipients
        for to_dev in to_developers:
            if to_dev not in self.pending_summaries:
                self.pending_summaries[to_dev] = []
            self.pending_summaries[to_dev].append(summary)

        return summary

    def record_change(self, developer: str, file: str, function: str,
                     intent: str, lines_added: int, lines_removed: int,
                     context_used: str, context_created: str) -> SharedChangeLogEntry:
        """
        Record a developer's change in the shared log
        All associated developers can see this entry
        """
        self.sequence_counter += 1

        # Get all developers associated with this file (to notify)
        associated_developers = self.developers_on_file.get(file, set())
        to_notify = [d for d in associated_developers if d != developer]

        entry = SharedChangeLogEntry(
            sequence=self.sequence_counter,
            timestamp=datetime.now().isoformat(),
            developer=developer,
            file=file,
            function=function,
            intent=intent,
            lines_added=lines_added,
            lines_removed=lines_removed,
            context_version_used=context_used,
            context_version_created=context_created,
            change_summary_sent_to=to_notify
        )

        self.shared_change_log.append(entry)
        return entry

    def get_pending_summaries(self, developer: str) -> List[ChangeSummary]:
        """Get all pending change summaries for a developer"""
        return self.pending_summaries.get(developer, [])

    def acknowledge_summaries(self, developer: str) -> None:
        """Mark all pending summaries as acknowledged by developer"""
        self.pending_summaries[developer] = []

    def get_developers_on_file(self, file: str) -> Set[str]:
        """Get all developers who have worked on a file"""
        return self.developers_on_file.get(file, set())

    def get_current_context(self, file: str) -> Optional[ContextVersion]:
        """Get current context version for a file"""
        return self.current_context.get(file)

    def get_context_history(self, file: str) -> List[ContextVersion]:
        """Get all context versions for a file"""
        return self.context_versions.get(file, [])

    def get_file_summary(self, file: str) -> Dict[str, Any]:
        """Get aggregated summary of all changes on a file"""
        developers = self.developers_on_file.get(file, set())
        entries = [e for e in self.shared_change_log if e.file == file]

        total_added = sum(e.lines_added for e in entries)
        total_removed = sum(e.lines_removed for e in entries)

        return {
            "file": file,
            "developers": list(developers),
            "total_changes": len(entries),
            "total_lines_added": total_added,
            "total_lines_removed": total_removed,
            "context_versions": len(self.context_versions.get(file, [])),
            "change_summaries": len([s for s in self.change_summaries if s.file == file]),
            "intents": [e.intent for e in entries],
            "current_context": self.current_context.get(file).version if file in self.current_context else None
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize shared service state"""
        return {
            "developers_on_file": {k: list(v) for k, v in self.developers_on_file.items()},
            "context_versions": {k: [c.to_dict() for c in v] for k, v in self.context_versions.items()},
            "change_summaries": [s.to_dict() for s in self.change_summaries],
            "shared_change_log": [e.to_dict() for e in self.shared_change_log],
            "pending_summaries": {k: [s.to_dict() for s in v] for k, v in self.pending_summaries.items()}
        }

    def save(self, filepath: str) -> None:
        """Save shared service state to file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "SharedService":
        """Load shared service state from file"""
        service = cls()
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Restore developers_on_file
        for file, devs in data.get("developers_on_file", {}).items():
            service.developers_on_file[file] = set(devs)

        # Restore context versions
        for file, versions in data.get("context_versions", {}).items():
            service.context_versions[file] = [ContextVersion(**v) for v in versions]
            if versions:
                service.current_context[file] = service.context_versions[file][-1]

        # Restore change summaries
        service.change_summaries = [ChangeSummary(**s) for s in data.get("change_summaries", [])]

        # Restore shared change log
        service.shared_change_log = [SharedChangeLogEntry(**e) for e in data.get("shared_change_log", [])]

        # Restore pending summaries
        for dev, summaries in data.get("pending_summaries", {}).items():
            service.pending_summaries[dev] = [ChangeSummary(**s) for s in summaries]

        # Restore sequence counter
        if service.shared_change_log:
            service.sequence_counter = max(e.sequence for e in service.shared_change_log)

        return service

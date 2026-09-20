#!/usr/bin/env python3
"""
Neo 2.0 Phase 3: Dependency Graph

Tracks dependencies between symbols/functions to detect context invalidation.
"""

from typing import Dict, Set, List, Optional
import re


class DependencyGraph:
    """
    Tracks symbol dependencies for context invalidation detection.

    Supports:
    - Function-level symbols (file.py::func_name)
    - Class-level symbols (file.py::ClassName)
    - API relationships
    - Configuration dependencies
    """

    def __init__(self):
        # Direct dependencies: symbol -> set of symbols it depends on
        self.dependencies: Dict[str, Set[str]] = {}

        # Reverse dependencies: symbol -> set of symbols that depend on it
        self.dependents: Dict[str, Set[str]] = {}

        # Symbol metadata
        self.symbol_metadata: Dict[str, Dict] = {}

        # Changed symbols: track what's been modified
        self.changed_symbols: Set[str] = set()

    def add_symbol(self, symbol: str, metadata: Optional[Dict] = None):
        """Register a symbol in the graph."""
        if symbol not in self.dependencies:
            self.dependencies[symbol] = set()
        if symbol not in self.dependents:
            self.dependents[symbol] = set()

        if metadata:
            self.symbol_metadata[symbol] = metadata

    def add_dependency(self, source: str, target: str):
        """Add dependency: source depends on target."""
        self.add_symbol(source)
        self.add_symbol(target)

        self.dependencies[source].add(target)
        self.dependents[target].add(source)

    def get_all_dependencies(self, symbol: str, depth: int = -1) -> Set[str]:
        """
        Get all symbols that a symbol depends on (transitive closure).

        Args:
            symbol: Starting symbol
            depth: Maximum depth (-1 for unlimited)

        Returns:
            Set of all symbols this symbol depends on
        """
        visited = set()
        to_visit = [symbol]
        current_depth = 0

        while to_visit and (depth < 0 or current_depth < depth):
            next_visit = []
            for sym in to_visit:
                if sym in visited:
                    continue
                visited.add(sym)

                if sym in self.dependencies:
                    for dep in self.dependencies[sym]:
                        if dep not in visited:
                            next_visit.append(dep)

            to_visit = next_visit
            current_depth += 1

        # Remove the source symbol itself
        visited.discard(symbol)
        return visited

    def get_all_dependents(self, symbol: str, depth: int = -1) -> Set[str]:
        """
        Get all symbols that depend on this symbol (transitive closure).

        Args:
            symbol: Starting symbol
            depth: Maximum depth (-1 for unlimited)

        Returns:
            Set of all symbols that depend on this symbol
        """
        visited = set()
        to_visit = [symbol]
        current_depth = 0

        while to_visit and (depth < 0 or current_depth < depth):
            next_visit = []
            for sym in to_visit:
                if sym in visited:
                    continue
                visited.add(sym)

                if sym in self.dependents:
                    for dep in self.dependents[sym]:
                        if dep not in visited:
                            next_visit.append(dep)

            to_visit = next_visit
            current_depth += 1

        # Remove the source symbol itself
        visited.discard(symbol)
        return visited

    def mark_changed(self, symbol: str):
        """Mark a symbol as having changed."""
        self.changed_symbols.add(symbol)

    def get_affected_by_change(self, symbol: str) -> Set[str]:
        """
        Get all symbols affected by a change to this symbol.
        Returns symbols that directly or indirectly depend on it.
        """
        return self.get_all_dependents(symbol)

    def get_symbols_matching_pattern(self, pattern: str) -> Set[str]:
        """
        Get symbols matching a pattern (for symbol inference from code).

        Supports:
        - Exact match: "module.py::func"
        - File pattern: "module.py::*"
        - Wildcard: "*"
        """
        if pattern == "*":
            return set(self.dependencies.keys())

        if pattern.endswith("::*"):
            file_prefix = pattern[:-3]
            return {s for s in self.dependencies.keys() if s.startswith(file_prefix + "::")}

        # Exact match
        if pattern in self.dependencies:
            return {pattern}

        return set()

    def clear(self):
        """Clear the entire graph."""
        self.dependencies.clear()
        self.dependents.clear()
        self.symbol_metadata.clear()
        self.changed_symbols.clear()


class ContextSnapshot:
    """
    Represents the state of an actor's development context at a point in time.

    Enables detection of context invalidation when dependencies change.
    """

    def __init__(
        self,
        actor: str,
        actor_type: str,
        resource: str,  # file::function primary resource
        base_commit: str,
        task_id: Optional[str] = None,
    ):
        self.actor = actor
        self.actor_type = actor_type
        self.resource = resource
        self.base_commit = base_commit
        self.task_id = task_id

        # Context snapshot components
        self.timestamp: str = ""
        self.files_involved: Set[str] = set()
        self.symbols_involved: Set[str] = set()
        self.dependencies: Set[str] = set()
        self.assumptions: Dict[str, str] = {}  # key -> description
        self.api_signatures: Dict[str, str] = {}  # symbol -> signature
        self.configuration: Dict[str, str] = {}  # key -> value

        # Staleness tracking
        self.status = "CURRENT"  # CURRENT, STALE, SYNC_REQUIRED, REVALIDATING, REVALIDATED
        self.invalidation_reasons: List[str] = []
        self.changed_dependencies: Set[str] = set()

    def to_dict(self) -> Dict:
        """Serialize context snapshot."""
        return {
            "actor": self.actor,
            "actor_type": self.actor_type,
            "resource": self.resource,
            "base_commit": self.base_commit,
            "task_id": self.task_id,
            "timestamp": self.timestamp,
            "files_involved": list(self.files_involved),
            "symbols_involved": list(self.symbols_involved),
            "dependencies": list(self.dependencies),
            "assumptions": self.assumptions,
            "api_signatures": self.api_signatures,
            "configuration": self.configuration,
            "status": self.status,
            "invalidation_reasons": self.invalidation_reasons,
            "changed_dependencies": list(self.changed_dependencies),
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "ContextSnapshot":
        """Deserialize context snapshot."""
        snapshot = cls(
            actor=data["actor"],
            actor_type=data["actor_type"],
            resource=data["resource"],
            base_commit=data["base_commit"],
            task_id=data.get("task_id"),
        )
        snapshot.timestamp = data.get("timestamp", "")
        snapshot.files_involved = set(data.get("files_involved", []))
        snapshot.symbols_involved = set(data.get("symbols_involved", []))
        snapshot.dependencies = set(data.get("dependencies", []))
        snapshot.assumptions = data.get("assumptions", {})
        snapshot.api_signatures = data.get("api_signatures", {})
        snapshot.configuration = data.get("configuration", {})
        snapshot.status = data.get("status", "CURRENT")
        snapshot.invalidation_reasons = data.get("invalidation_reasons", [])
        snapshot.changed_dependencies = set(data.get("changed_dependencies", []))
        return snapshot

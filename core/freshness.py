#!/usr/bin/env python3
"""
C1/C2 Freshness mechanism: record reads and detect staleness.

Provides the public interface for:
- record_read: snapshot file state when agent reads it
- check_freshness: detect if file has stale symbols (CURRENT/STALE_SOURCE/UNVERIFIABLE)
- delta_since_base: get changed symbols as a payload string
"""

import os
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.symbol_hasher import snapshot_file, StalenessChecker
from core.delta_refresh import DeltaGenerator, ContextRefreshBuilder

# State directory for recording reads
NEO_STATE_DIR = Path(os.environ.get("NEO_STATE_DIR", ".neo_state"))


def _ensure_state_dir():
    """Ensure state directory exists."""
    NEO_STATE_DIR.mkdir(parents=True, exist_ok=True)


def _read_state_file(agent_id: str) -> Dict[str, Any]:
    """Load agent's state file (file path -> snapshot)."""
    _ensure_state_dir()
    state_file = NEO_STATE_DIR / f"{agent_id}.json"
    if not state_file.exists():
        return {}
    try:
        return json.loads(state_file.read_text())
    except Exception:
        return {}


def _write_state_file(agent_id: str, state: Dict[str, Any]) -> None:
    """Save agent's state file."""
    _ensure_state_dir()
    state_file = NEO_STATE_DIR / f"{agent_id}.json"
    state_file.write_text(json.dumps(state, indent=2, default=str))


def record_read(agent_id: str, path: str, symbols: Optional[List[str]] = None) -> None:
    """
    Record that agent read this file at this point in time.

    Stores symbol-level snapshot so we can later detect staleness.

    Args:
        agent_id: Agent identifier
        path: File path being read
        symbols: Optional list of specific symbols agent depends on (None = whole file)
    """
    try:
        file_path = Path(path)
        if not file_path.exists():
            return

        # Create snapshot of current state and capture file content
        current_time = time.time()
        file_content = file_path.read_text()
        snapshot = snapshot_file(file_path, agent_id, current_time)

        # Store in agent's state - include actual file content for later comparison
        state = _read_state_file(agent_id)
        state[path] = {
            "snapshot_time": snapshot.timestamp,
            "content_hash": snapshot.content_hash,
            "file_content": file_content,  # Store actual content to detect changes
            "symbols": {
                name: {
                    "hash": sym.body_hash,
                    "type": sym.type,
                    "lineno": sym.lineno
                }
                for name, sym in snapshot.symbols.items()
            },
            "dependency_symbols": symbols,  # which symbols agent depends on
            "parse_error": snapshot.parse_error
        }
        _write_state_file(agent_id, state)
    except Exception:
        pass


def check_freshness(agent_id: str, path: str) -> str:
    """
    Check if agent's cached context for this file is fresh.

    Returns:
        "CURRENT" - file unchanged for agent's dependencies
        "STALE_SOURCE" - file changed where agent depends
        "UNVERIFIABLE" - can't parse or verify (be conservative)
    """
    try:
        state = _read_state_file(agent_id)
        if path not in state:
            return "UNVERIFIABLE"  # no record of agent reading this file

        cached = state[path]
        file_path = Path(path)

        if not file_path.exists():
            return "UNVERIFIABLE"

        # Get the dependency symbols agent cares about
        dependency_symbols = cached.get("dependency_symbols")

        # Use stored file content to create base snapshot (not current file)
        # This way we detect actual changes from when agent read it
        if "file_content" not in cached:
            return "UNVERIFIABLE"

        from core.symbol_hasher import FileSnapshot, SymbolExtractor, compute_hash, normalize_source
        import ast

        try:
            # Parse the stored (base) file content
            base_content = cached["file_content"]
            base_normalized = normalize_source(base_content)
            base_hash = compute_hash(base_normalized)

            # Extract symbols from base content
            base_tree = ast.parse(base_content)
            base_lines = base_content.splitlines()
            base_extractor = SymbolExtractor(base_content, base_lines)
            base_extractor.visit(base_tree)

            # Recreate base snapshot
            cached_snapshot = FileSnapshot(
                file_path=str(file_path),
                content_hash=base_hash,
                symbols=base_extractor.symbols,
                timestamp=cached["snapshot_time"],
                agent_id=agent_id
            )
        except Exception:
            return "UNVERIFIABLE"

        # Check freshness at symbol level
        freshness_state, _ = StalenessChecker.check_file_staleness(
            cached_snapshot,
            str(file_path),
            dependency_symbols=dependency_symbols
        )

        return freshness_state
    except Exception as e:
        return "UNVERIFIABLE"


def delta_since_base(agent_id: str, path: str) -> str:
    """
    Get changed symbols as a payload string (C2 delta refresh).

    Returns only the changed symbols, not the whole file.
    Coalesces multiple intermediate edits into one net delta.

    Args:
        agent_id: Agent identifier
        path: File path to get delta for

    Returns:
        Human-readable payload with changed symbols
    """
    try:
        state = _read_state_file(agent_id)
        if path not in state:
            # No base snapshot - return full file
            file_path = Path(path)
            if file_path.exists():
                return file_path.read_text()
            return ""

        cached = state[path]
        file_path = Path(path)

        if not file_path.exists():
            return ""

        # Use stored file content to create base snapshot
        if "file_content" not in cached:
            return file_path.read_text()

        from core.symbol_hasher import FileSnapshot, SymbolExtractor, compute_hash, normalize_source
        import ast

        try:
            # Parse the stored (base) file content
            base_content = cached["file_content"]
            base_normalized = normalize_source(base_content)
            base_hash = compute_hash(base_normalized)

            # Extract symbols from base content
            base_tree = ast.parse(base_content)
            base_lines = base_content.splitlines()
            base_extractor = SymbolExtractor(base_content, base_lines)
            base_extractor.visit(base_tree)

            # Recreate base snapshot
            base_snapshot = FileSnapshot(
                file_path=str(file_path),
                content_hash=base_hash,
                symbols=base_extractor.symbols,
                timestamp=cached["snapshot_time"],
                agent_id=agent_id
            )
        except Exception:
            # Can't parse base - return current full file
            return file_path.read_text()

        # Generate delta from base to current
        dependency_symbols = cached.get("dependency_symbols")
        delta = DeltaGenerator.generate(
            base_snapshot,
            str(file_path),
            dependency_symbols=dependency_symbols
        )

        # Build human-readable message
        message = ContextRefreshBuilder.build_message(
            [delta],
            agent_id,
            str(file_path)
        )

        return message
    except Exception:
        # Fallback to full file on error
        try:
            return Path(path).read_text()
        except Exception:
            return ""

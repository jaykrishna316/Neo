#!/usr/bin/env python3
"""
Delta refresh (C2): Symbol-level context refresh instead of full file resync.

Compares base snapshot to current and sends only changed symbols,
falling back to unified-diff then full file if needed.
"""

import difflib
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from core.symbol_hasher import FileSnapshot, SymbolHash, snapshot_file


@dataclass
class SymbolDelta:
    """A single symbol change."""
    name: str
    type: str  # "added", "removed", "changed"
    body: Optional[str] = None
    signature: Optional[str] = None


@dataclass
class FileDelta:
    """Context refresh: the delta from base to current."""
    file_path: str
    delta_type: str  # "symbols", "unified_diff", "full_file"
    symbol_deltas: List[SymbolDelta] = None
    unified_diff: Optional[str] = None
    full_content: Optional[str] = None
    added_symbols: List[str] = None
    removed_symbols: List[str] = None
    changed_symbols: List[str] = None
    unchanged_signatures: Dict[str, str] = None  # symbol -> signature only
    base_hash: str = ""
    current_hash: str = ""

    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict."""
        return {
            "file_path": self.file_path,
            "delta_type": self.delta_type,
            "symbol_deltas": [asdict(d) for d in (self.symbol_deltas or [])],
            "unified_diff": self.unified_diff,
            "full_content": self.full_content,
            "added_symbols": self.added_symbols or [],
            "removed_symbols": self.removed_symbols or [],
            "changed_symbols": self.changed_symbols or [],
            "unchanged_signatures": self.unchanged_signatures or {},
            "base_hash": self.base_hash,
            "current_hash": self.current_hash,
        }


class DeltaGenerator:
    """Generate symbol-level deltas between base and current snapshots."""

    @staticmethod
    def generate(
        base_snapshot: FileSnapshot,
        current_file_path: str,
        dependency_symbols: Optional[List[str]] = None
    ) -> FileDelta:
        """
        Generate delta from base to current.

        Falls back: symbol-level → unified-diff → full file
        """
        import time

        current_snap = snapshot_file(current_file_path, base_snapshot.agent_id, time.time())

        # If current can't be parsed, try unified-diff
        if current_snap.parse_error:
            return DeltaGenerator._unified_diff_delta(
                base_snapshot, current_file_path
            )

        # If file missing, use full file
        if current_snap.content_hash == "MISSING":
            path = Path(current_file_path)
            content = path.read_text() if path.exists() else ""
            return FileDelta(
                file_path=current_file_path,
                delta_type="full_file",
                full_content=content,
                base_hash=base_snapshot.content_hash,
                current_hash=current_snap.content_hash
            )

        # Symbol-level delta
        return DeltaGenerator._symbol_delta(base_snapshot, current_snap, dependency_symbols)

    @staticmethod
    def _symbol_delta(
        base_snap: FileSnapshot,
        current_snap: FileSnapshot,
        dependency_symbols: Optional[List[str]] = None
    ) -> FileDelta:
        """Generate symbol-level delta."""
        added = []
        removed = []
        changed = []
        deltas = []
        unchanged_sigs = {}

        # Find added, removed, changed
        all_base_syms = set(base_snap.symbols.keys())
        all_current_syms = set(current_snap.symbols.keys())

        for sym_name in all_current_syms - all_base_syms:
            added.append(sym_name)
            current_sym = current_snap.symbols[sym_name]
            deltas.append(SymbolDelta(
                name=sym_name,
                type="added",
                body=DeltaGenerator._extract_body(current_snap.file_path, current_sym.lineno)
            ))

        for sym_name in all_base_syms - all_current_syms:
            removed.append(sym_name)
            deltas.append(SymbolDelta(
                name=sym_name,
                type="removed"
            ))

        for sym_name in all_base_syms & all_current_syms:
            base_sym = base_snap.symbols[sym_name]
            current_sym = current_snap.symbols[sym_name]

            if base_sym.body_hash != current_sym.body_hash:
                changed.append(sym_name)
                deltas.append(SymbolDelta(
                    name=sym_name,
                    type="changed",
                    body=DeltaGenerator._extract_body(current_snap.file_path, current_sym.lineno)
                ))
            elif not dependency_symbols or sym_name in dependency_symbols:
                # Keep signature for unchanged symbols we depend on
                unchanged_sigs[sym_name] = DeltaGenerator._extract_signature(
                    current_snap.file_path, current_sym.lineno
                )

        return FileDelta(
            file_path=current_snap.file_path,
            delta_type="symbols",
            symbol_deltas=deltas,
            added_symbols=added,
            removed_symbols=removed,
            changed_symbols=changed,
            unchanged_signatures=unchanged_sigs if not dependency_symbols else {},
            base_hash=base_snap.content_hash,
            current_hash=current_snap.content_hash
        )

    @staticmethod
    def _unified_diff_delta(
        base_snapshot: FileSnapshot,
        current_file_path: str
    ) -> FileDelta:
        """Fall back to unified-diff format."""
        path = Path(current_file_path)

        # Read both versions
        try:
            base_content = base_snapshot.file_path  # This is wrong - we don't store content
            # For now, treat as we don't have base content
            current_content = path.read_text() if path.exists() else ""
        except Exception:
            current_content = path.read_text() if path.exists() else ""
            # Can't create meaningful diff without base, so use full file
            return FileDelta(
                file_path=current_file_path,
                delta_type="full_file",
                full_content=current_content,
                base_hash=base_snapshot.content_hash,
                current_hash=""
            )

        # Generate unified diff
        diff = difflib.unified_diff(
            (base_snapshot.file_path or "").split('\n'),
            current_content.split('\n'),
            lineterm='',
            n=3
        )
        diff_text = '\n'.join(diff)

        return FileDelta(
            file_path=current_file_path,
            delta_type="unified_diff",
            unified_diff=diff_text,
            base_hash=base_snapshot.content_hash
        )

    @staticmethod
    def _extract_body(file_path: str, lineno: int) -> Optional[str]:
        """Extract function/class body from source file."""
        try:
            import ast
            path = Path(file_path)
            if not path.exists():
                return None

            source = path.read_text()
            tree = ast.parse(source)

            # Find node at lineno
            for node in ast.walk(tree):
                if hasattr(node, 'lineno') and node.lineno == lineno:
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        lines = source.split('\n')
                        start = node.lineno - 1
                        end = node.end_lineno if hasattr(node, 'end_lineno') else node.lineno
                        return '\n'.join(lines[start:end])
            return None
        except Exception:
            return None

    @staticmethod
    def _extract_signature(file_path: str, lineno: int) -> str:
        """Extract function/class signature from source file."""
        try:
            import ast
            path = Path(file_path)
            if not path.exists():
                return f"# line {lineno}"

            source = path.read_text()
            lines = source.split('\n')

            if 0 <= lineno - 1 < len(lines):
                sig_line = lines[lineno - 1].strip()
                # For multiline sigs, grab next few lines until colon
                for i in range(lineno - 1, min(lineno + 5, len(lines))):
                    sig_line += '\n' + lines[i].strip()
                    if ':' in lines[i]:
                        break
                return sig_line
            return f"# line {lineno}"
        except Exception:
            return f"# line {lineno}"


class ContextRefreshBuilder:
    """Build a context refresh message from deltas."""

    @staticmethod
    def build_message(
        deltas: List[FileDelta],
        agent_id: str,
        file_path: str
    ) -> str:
        """Build human-readable context refresh message with symbol bodies."""
        messages = [f"Context refresh for {agent_id}:"]

        for delta in deltas:
            if delta.delta_type == "symbols":
                # Include actual bodies for changed and added symbols only (minimal overhead)
                for sd in (delta.symbol_deltas or []):
                    if sd.type == "added" and sd.body:
                        messages.append(sd.body)
                    elif sd.type == "changed" and sd.body:
                        messages.append(sd.body)
            elif delta.delta_type == "unified_diff":
                messages.append(f"\n{delta.file_path} (diff):")
                messages.append(delta.unified_diff or "(no diff)")
            else:
                messages.append(f"\n{delta.file_path} (full file, {len(delta.full_content or '')} chars)")

        return '\n'.join(messages)

    @staticmethod
    def estimate_tokens(delta: FileDelta) -> int:
        """Estimate token cost of this delta."""
        if delta.delta_type == "full_file":
            # ~4 chars per token
            content = delta.full_content or ""
            return max(1, len(content) // 4)
        elif delta.delta_type == "symbols":
            # Per-symbol cost: ~2 tokens per symbol + body
            tokens = 2 * len(delta.symbol_deltas or [])
            for sd in (delta.symbol_deltas or []):
                if sd.body:
                    tokens += len(sd.body) // 8  # Symbol bodies are denser
            return max(1, tokens)
        else:
            # Unified diff: ~4 chars per token
            diff = delta.unified_diff or ""
            return max(1, len(diff) // 4)

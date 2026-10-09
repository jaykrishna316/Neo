#!/usr/bin/env python3
"""
Symbol-level content hashing for staleness detection (C1).

Records and checks content at AST-normalized level to detect real changes
without false positives from formatting or temporary touches.
"""

import ast
import hashlib
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SymbolHash:
    """Hash of a single symbol (function, class, etc.)."""
    name: str
    type: str  # "function", "class", "async_function"
    body_hash: str
    lineno: int
    qual_name: str = ""  # qualified name for nested classes


@dataclass
class FileSnapshot:
    """Snapshot of a file's content at symbol level."""
    file_path: str
    content_hash: str  # hash of entire file
    symbols: Dict[str, SymbolHash]  # name -> SymbolHash
    timestamp: float
    agent_id: str
    parse_error: Optional[str] = None  # if file couldn't be parsed


def normalize_source(source: str) -> str:
    """Normalize source code: remove comments and excess whitespace."""
    # Remove comments
    source = re.sub(r'#.*$', '', source, flags=re.MULTILINE)
    # Remove docstrings (very basic: just triple quotes on their own line)
    source = re.sub(r'^\s*"""[\s\S]*?"""', '', source, flags=re.MULTILINE)
    source = re.sub(r"^\s*'''[\s\S]*?'''", '', source, flags=re.MULTILINE)
    # Normalize whitespace: collapse multiple spaces/newlines
    source = re.sub(r'[ \t]+', ' ', source)
    source = re.sub(r'\n\s*\n', '\n', source)
    return source.strip()


def compute_hash(text: str) -> str:
    """Compute SHA256 hash of text."""
    return hashlib.sha256(text.encode()).hexdigest()[:16]


class SymbolExtractor(ast.NodeVisitor):
    """Extract symbols and their normalized bodies from AST."""

    def __init__(self, source: str, source_lines: List[str]):
        self.source = source
        self.source_lines = source_lines
        self.symbols: Dict[str, SymbolHash] = {}
        self.current_class: Optional[str] = None

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Extract function and its normalized body."""
        self._extract_symbol(node, "function")
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Extract async function."""
        self._extract_symbol(node, "async_function")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Extract class and its methods."""
        old_class = self.current_class
        self.current_class = node.name if not self.current_class else f"{self.current_class}.{node.name}"

        self._extract_symbol(node, "class")
        self.generic_visit(node)

        self.current_class = old_class

    def _extract_symbol(self, node: ast.AST, sym_type: str) -> None:
        """Extract a symbol's body and normalize it."""
        if not hasattr(node, 'lineno') or not hasattr(node, 'end_lineno'):
            return

        # Extract source lines for this symbol
        start_line = node.lineno - 1
        end_line = node.end_lineno if node.end_lineno else node.lineno

        if start_line < 0 or end_line > len(self.source_lines):
            return

        body_lines = self.source_lines[start_line:end_line]
        body_source = '\n'.join(body_lines)

        # Normalize and hash
        normalized = normalize_source(body_source)
        body_hash = compute_hash(normalized)

        # Determine qualified name
        name = node.name
        qual_name = f"{self.current_class}.{name}" if self.current_class else name

        symbol = SymbolHash(
            name=name,
            type=sym_type,
            body_hash=body_hash,
            lineno=node.lineno,
            qual_name=qual_name
        )
        self.symbols[qual_name] = symbol


def parse_file_symbols(file_path: str) -> Optional[Tuple[Dict[str, SymbolHash], str]]:
    """
    Parse a Python file and extract symbols with hashes.

    Returns:
        Tuple of (symbols_dict, parse_error) or (None, error_message) on failure
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return None, f"File not found: {file_path}"

        if not path.suffix == '.py':
            return None, f"Not a Python file: {file_path}"

        source = path.read_text()
        source_lines = source.split('\n')

        tree = ast.parse(source)
        extractor = SymbolExtractor(source, source_lines)
        extractor.visit(tree)

        return extractor.symbols, None

    except SyntaxError as e:
        return None, f"Syntax error in {file_path}: {e}"
    except Exception as e:
        return None, f"Parse error in {file_path}: {e}"


def snapshot_file(file_path: str, agent_id: str, timestamp: float) -> FileSnapshot:
    """Create a snapshot of a file's content at symbol level."""
    path = Path(file_path)

    # Content hash
    if path.exists():
        content = path.read_text()
        content_hash = compute_hash(content)
    else:
        content_hash = "MISSING"

    # Symbol hashes
    symbols, parse_error = parse_file_symbols(file_path)

    if parse_error:
        return FileSnapshot(
            file_path=file_path,
            content_hash=content_hash,
            symbols={},
            timestamp=timestamp,
            agent_id=agent_id,
            parse_error=parse_error
        )

    return FileSnapshot(
        file_path=file_path,
        content_hash=content_hash,
        symbols=symbols or {},
        timestamp=timestamp,
        agent_id=agent_id,
        parse_error=None
    )


class StalenessChecker:
    """Check if a file/symbols are stale based on content hashes."""

    CONTEXT_STATES = ["CURRENT", "STALE_SOURCE", "UNVERIFIABLE"]

    @staticmethod
    def check_file_staleness(
        base_snapshot: FileSnapshot,
        current_file_path: str,
        dependency_symbols: Optional[List[str]] = None
    ) -> Tuple[str, Dict]:
        """
        Check if a file/symbols are stale.

        Args:
            base_snapshot: Base snapshot from when agent read the file
            current_file_path: Path to file to check
            dependency_symbols: Specific symbols to check (None = check file)

        Returns:
            Tuple of (state, report) where state is CURRENT/STALE_SOURCE/UNVERIFIABLE
        """
        # Get current snapshot
        import time
        current_snap = snapshot_file(current_file_path, base_snapshot.agent_id, time.time())

        # If current file can't be parsed, result is UNVERIFIABLE
        if current_snap.parse_error:
            return "UNVERIFIABLE", {
                "reason": "Can't parse current file",
                "error": current_snap.parse_error,
                "base_symbols": list(base_snapshot.symbols.keys()),
            }

        # If file doesn't exist, it's STALE
        if current_snap.content_hash == "MISSING":
            return "STALE_SOURCE", {
                "reason": "File removed",
                "missing_file": current_file_path
            }

        # If no dependency_symbols specified, check file-level hash
        if not dependency_symbols:
            if base_snapshot.content_hash == current_snap.content_hash:
                return "CURRENT", {"reason": "Content unchanged"}
            else:
                return "STALE_SOURCE", {"reason": "File content changed"}

        # Check specific symbols
        changed_symbols = []
        missing_symbols = []

        for sym_name in dependency_symbols:
            if sym_name not in base_snapshot.symbols:
                continue  # Skip symbols we didn't see

            base_sym = base_snapshot.symbols[sym_name]
            current_sym = current_snap.symbols.get(sym_name)

            if current_sym is None:
                missing_symbols.append(sym_name)
            elif base_sym.body_hash != current_sym.body_hash:
                changed_symbols.append(sym_name)

        if not changed_symbols and not missing_symbols:
            return "CURRENT", {
                "reason": "Dependency symbols unchanged",
                "checked_symbols": dependency_symbols
            }

        return "STALE_SOURCE", {
            "reason": "Dependencies changed",
            "changed_symbols": changed_symbols,
            "missing_symbols": missing_symbols,
            "checked_symbols": dependency_symbols
        }


def extract_dependencies(file_path: str) -> Dict[str, List[str]]:
    """
    Extract which symbols depend on which other symbols.

    Returns:
        Dict mapping symbol name to list of symbols it uses.
    """
    try:
        path = Path(file_path)
        if not path.exists() or not path.suffix == '.py':
            return {}

        source = path.read_text()
        tree = ast.parse(source)

        # Simple analysis: find Names used in each function/class
        dependencies = {}

        class DependencyVisitor(ast.NodeVisitor):
            def __init__(self):
                self.current_symbol = None
                self.used_names = set()

            def visit_FunctionDef(self, node):
                old_symbol = self.current_symbol
                self.current_symbol = node.name
                self.used_names = set()
                self.generic_visit(node)

                # Extract unique identifiers used
                class NameCollector(ast.NodeVisitor):
                    def __init__(self):
                        self.names = set()

                    def visit_Name(self, node):
                        self.names.add(node.id)
                        self.generic_visit(node)

                collector = NameCollector()
                for child in ast.iter_child_nodes(node):
                    collector.visit(child)

                dependencies[node.name] = list(collector.names)
                self.current_symbol = old_symbol

            def visit_ClassDef(self, node):
                dependencies[node.name] = []
                self.generic_visit(node)

        visitor = DependencyVisitor()
        visitor.visit(tree)
        return dependencies

    except Exception:
        return {}

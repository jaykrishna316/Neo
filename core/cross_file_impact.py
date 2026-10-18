"""
Cross-file blast radius tracking.

When a function or class changes, find the files that consume it and raise an
impact alert for each one, so their owners see the change before they build
on the old version.

Detection works at the symbol level: a symbol counts as changed only when its
AST body hash changes, so formatting and comment-only edits raise no alerts.
Consumers are found by scanning the repo's Python imports. A consumer whose
top-level directory differs from the source file's is flagged as crossing a
service boundary.
"""

import ast
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set

from core.symbol_hasher import SymbolExtractor
from core.impact_alerts import ImpactAlertManager
from core.activity_log import log_activity

# Directories that never hold consumer code. Hidden directories (.git, .venv,
# .devsync, ...) are skipped by the leading-dot rule in _iter_python_files.
SKIP_DIRS = {"node_modules", "__pycache__", "build", "dist", "venv", "env"}

# Upper bound on files scanned per call, so a huge monorepo cannot stall a check.
MAX_FILES_SCANNED = 5000


@dataclass
class ConsumerImpact:
    """A file that consumes one or more changed symbols."""
    file_path: str
    symbols: List[str]  # changed qualified names this file uses
    cross_service: bool


def detect_changed_symbols(old_source: str, new_source: str) -> List[str]:
    """Return qualified names of symbols whose body changed, were added, or removed.

    Raises:
        SyntaxError: If either version of the source does not parse.
    """
    old_hashes = _symbol_hashes(old_source)
    new_hashes = _symbol_hashes(new_source)

    changed = [
        name for name in old_hashes.keys() | new_hashes.keys()
        if old_hashes.get(name) != new_hashes.get(name)
    ]
    return sorted(changed)


def find_downstream_consumers(
    repo_path: str,
    source_file: str,
    changed_symbols: List[str],
) -> List[ConsumerImpact]:
    """Find repo files that import or reference any of the changed symbols.

    Args:
        repo_path: Repository root
        source_file: Changed file, relative to repo_path
        changed_symbols: Qualified names from detect_changed_symbols

    Returns:
        One ConsumerImpact per consuming file, sorted by path
    """
    repo = Path(repo_path)
    target_module = _module_name(source_file)
    # Match on the top-level name, so a changed method also matches its class
    changed_top = {name.split(".")[0] for name in changed_symbols}

    consumers = []
    for py_file in _iter_python_files(repo):
        rel_path = py_file.relative_to(repo).as_posix()
        if rel_path == source_file:
            continue

        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError, OSError):
            continue

        used_top = _names_used_from_module(tree, rel_path, target_module, changed_top)
        if not used_top:
            continue

        symbols = [
            name for name in changed_symbols
            if name.split(".")[0] in used_top
        ]
        consumers.append(ConsumerImpact(
            file_path=rel_path,
            symbols=symbols,
            cross_service=_service_of(rel_path) != _service_of(source_file),
        ))

    return sorted(consumers, key=lambda c: c.file_path)


def record_change_impacts(
    repo_path: str,
    source_file: str,
    changed_by: str,
    old_source: str,
    new_source: Optional[str] = None,
    pr_number: Optional[int] = None,
    log_intent: bool = True,
) -> Dict:
    """Detect changed symbols in a file, then alert every downstream consumer.

    Alerts are deduplicated: a consumer that already has an unresolved alert
    from the same source file is reported as skipped, not alerted twice.

    Args:
        repo_path: Repository root
        source_file: Changed file, relative to repo_path
        changed_by: Developer or agent who made the change
        old_source: Previous contents of source_file
        new_source: Current contents; read from disk when omitted
        pr_number: Optional PR the change belongs to
        log_intent: Also record the changed symbols in the activity log

    Returns:
        Summary dict with status, changed symbols, and created/skipped consumers
    """
    repo = Path(repo_path)

    if new_source is None:
        source_path = repo / source_file
        if not source_path.exists():
            return {"status": "source_missing", "source_file": source_file}
        new_source = source_path.read_text(encoding="utf-8")

    try:
        changed = detect_changed_symbols(old_source, new_source)
    except SyntaxError as e:
        return {"status": "unparseable", "source_file": source_file, "error": str(e)}

    if not changed:
        return {
            "status": "no_symbol_changes",
            "source_file": source_file,
            "changed_symbols": [],
            "alerts_created": [],
            "alerts_skipped": [],
        }

    consumers = find_downstream_consumers(str(repo), source_file, changed)
    manager = ImpactAlertManager(str(repo))
    change_summary = f"Changed: {', '.join(changed)}"

    created, skipped = [], []
    for consumer in consumers:
        result = manager.create_alert_if_new(
            source_file=source_file,
            target_file=consumer.file_path,
            changed_by=changed_by,
            change_summary=change_summary,
            impact_reason=_format_reason(source_file, consumer),
            pr_number=pr_number,
            changed_symbols=changed,
            consumed_symbols=consumer.symbols,
            cross_service=consumer.cross_service,
        )
        if result["status"] == "created":
            created.append(consumer.file_path)
        else:
            skipped.append(consumer.file_path)

    if log_intent:
        log_activity(
            developer_id=changed_by,
            file_path=source_file,
            intent="Changed functions (blast radius recorded)",
            changed_symbols=changed,
        )

    return {
        "status": "impacts_recorded" if consumers else "no_consumers",
        "source_file": source_file,
        "changed_symbols": changed,
        "consumers": [c.file_path for c in consumers],
        "alerts_created": created,
        "alerts_skipped": skipped,
    }


def _symbol_hashes(source: str) -> Dict[str, str]:
    """Map qualified symbol name to body hash for every function and class."""
    tree = ast.parse(source)
    extractor = SymbolExtractor(source, source.split("\n"))
    extractor.visit(tree)
    return {name: sym.body_hash for name, sym in extractor.symbols.items()}


def _module_name(file_path: str) -> str:
    """Dotted module name for a repo-relative path, e.g. core/x.py -> core.x."""
    parts = list(Path(file_path).with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _service_of(file_path: str) -> str:
    """Service is the top-level directory. Files at the repo root share service ''."""
    parts = Path(file_path).parts
    return parts[0] if len(parts) > 1 else ""


def _iter_python_files(repo: Path):
    """Yield .py files under repo, pruning hidden and vendored directories."""
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in SKIP_DIRS
        ]
        for name in filenames:
            if not name.endswith(".py"):
                continue
            yield Path(dirpath) / name
            scanned += 1
            if scanned >= MAX_FILES_SCANNED:
                return


def _resolve_import_from(node: ast.ImportFrom, consumer_rel_path: str) -> Optional[str]:
    """Absolute module name an ImportFrom refers to, resolving relative levels."""
    if node.level == 0:
        return node.module or ""

    package_parts = list(Path(consumer_rel_path).parent.parts)
    ups = node.level - 1
    if ups > len(package_parts):
        return None
    base = package_parts[: len(package_parts) - ups]
    if node.module:
        base = base + node.module.split(".")
    return ".".join(base)


def _dotted(node: ast.AST) -> Optional[str]:
    """Dotted string for a Name/Attribute chain, or None for anything else."""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        inner = _dotted(node.value)
        return f"{inner}.{node.attr}" if inner else None
    return None


def _names_used_from_module(
    tree: ast.AST,
    consumer_rel_path: str,
    target_module: str,
    changed_top: Set[str],
) -> Set[str]:
    """Top-level changed names this module imports or references from target_module."""
    used: Set[str] = set()
    # Dotted prefixes that refer to the target module in this file's namespace
    module_prefixes: Set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = _resolve_import_from(node, consumer_rel_path)
            if module != target_module:
                continue
            for alias in node.names:
                if alias.name == "*":
                    used |= changed_top  # wildcard: assume every changed name is used
                elif alias.name in changed_top:
                    used.add(alias.name)

        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == target_module:
                    # `import a.b as x` binds x; `import a.b` binds the path a.b
                    module_prefixes.add(alias.asname or alias.name)

    if module_prefixes:
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute):
                continue
            dotted = _dotted(node)
            if not dotted:
                continue
            for prefix in module_prefixes:
                if dotted.startswith(prefix + "."):
                    first = dotted[len(prefix) + 1:].split(".")[0]
                    if first in changed_top:
                        used.add(first)

    return used


def _format_reason(source_file: str, consumer: ConsumerImpact) -> str:
    reason = f"{consumer.file_path} uses {', '.join(consumer.symbols)} from {source_file}"
    if consumer.cross_service:
        reason += " (crosses a service boundary)"
    return reason

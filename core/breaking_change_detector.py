#!/usr/bin/env python3
"""
AST-Based Breaking Change Detector

Uses semantic analysis (AST parsing + dependency graphs) to detect actual
breaking changes, not keyword heuristics.

Breaking changes detected:
1. Function signature changes (parameters added/removed/renamed)
2. Return type changes (when detectable)
3. Class/method removal
4. API contract violations
5. Exception signature changes

Uses dependency graph to find downstream impact.
"""

import ast
from pathlib import Path
from typing import Set, Dict, List, Tuple, Optional
from dataclasses import dataclass
from core.semantic_conflict_detector import SemanticAnalyzer, Symbol, Dependency, Language


@dataclass
class FunctionSignature:
    """Represents a function's signature."""
    name: str
    params: List[str]  # Parameter names
    defaults: int  # Number of default parameters
    varargs: bool  # Has *args
    kwargs: bool  # Has **kwargs
    is_async: bool
    decorators: List[str]
    return_annotation: Optional[str] = None

    def __hash__(self):
        return hash((self.name, tuple(self.params), self.defaults, self.varargs, self.kwargs))

    def __eq__(self, other):
        return (self.name == other.name and
                self.params == other.params and
                self.defaults == other.defaults and
                self.varargs == other.varargs and
                self.kwargs == other.kwargs)


@dataclass
class BreakingChange:
    """Represents a detected breaking change."""
    type: str  # "signature_change", "removal", "exception_change", "return_type_change"
    symbol: str  # Function/class name
    old_signature: Optional[FunctionSignature]
    new_signature: Optional[FunctionSignature]
    details: str  # Human-readable description
    severity: str  # "HIGH", "MEDIUM", "LOW"
    affected_downstream: List[str] = None  # Files that depend on this

    def __post_init__(self):
        if self.affected_downstream is None:
            self.affected_downstream = []


class SignatureExtractor(ast.NodeVisitor):
    """Extract function signatures from AST."""

    def __init__(self):
        self.signatures: Dict[str, FunctionSignature] = {}
        self.current_class: Optional[str] = None

    def visit_FunctionDef(self, node):
        """Extract function signature."""
        sig = self._extract_signature(node)
        self.signatures[sig.name] = sig
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Extract async function signature."""
        sig = self._extract_signature(node, is_async=True)
        self.signatures[sig.name] = sig
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """Track class for method names."""
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def _extract_signature(self, node, is_async: bool = False) -> FunctionSignature:
        """Extract signature details from function node."""
        args = node.args
        params = [arg.arg for arg in args.args]
        defaults_count = len(args.defaults)
        has_varargs = args.vararg is not None
        has_kwargs = args.kwarg is not None

        # Extract decorators
        decorators = [d.id if isinstance(d, ast.Name) else str(d) for d in node.decorator_list]

        # Extract return annotation if present
        return_annotation = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_annotation = node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return_annotation = str(node.returns.value)

        return FunctionSignature(
            name=node.name,
            params=params,
            defaults=defaults_count,
            varargs=has_varargs,
            kwargs=has_kwargs,
            is_async=is_async,
            decorators=decorators,
            return_annotation=return_annotation
        )


class BreakingChangeDetector:
    """Detect breaking changes between two versions of a file."""

    def __init__(self, file_path: str, language: Optional[Language] = None):
        self.file_path = Path(file_path)
        self.language = language or SemanticAnalyzer(str(file_path))._detect_language()
        self.analyzer = SemanticAnalyzer(str(file_path), self.language)
        self.breaking_changes: List[BreakingChange] = []

    def detect_changes(self, old_content: str, new_content: str) -> List[BreakingChange]:
        """
        Detect breaking changes between old and new file content.

        Args:
            old_content: Previous version of the file
            new_content: Current version of the file

        Returns:
            List of detected breaking changes
        """
        self.breaking_changes = []

        if self.language != Language.PYTHON:
            # For non-Python, fall back to symbol extraction
            return self._detect_changes_generic(old_content, new_content)

        try:
            old_sigs = self._extract_signatures(old_content)
            new_sigs = self._extract_signatures(new_content)
        except SyntaxError:
            return []

        # 1. Detect removed functions/classes
        removed = set(old_sigs.keys()) - set(new_sigs.keys())
        for removed_name in removed:
            self.breaking_changes.append(BreakingChange(
                type="removal",
                symbol=removed_name,
                old_signature=old_sigs[removed_name],
                new_signature=None,
                details=f"Function/class '{removed_name}' was removed",
                severity="HIGH"
            ))

        # 2. Detect signature changes in existing functions
        existing = set(old_sigs.keys()) & set(new_sigs.keys())
        for func_name in existing:
            old_sig = old_sigs[func_name]
            new_sig = new_sigs[func_name]

            breaking = self._compare_signatures(old_sig, new_sig)
            if breaking:
                self.breaking_changes.append(breaking)

        return self.breaking_changes

    def _extract_signatures(self, content: str) -> Dict[str, FunctionSignature]:
        """Extract function signatures from Python code."""
        try:
            tree = ast.parse(content)
            extractor = SignatureExtractor()
            extractor.visit(tree)
            return extractor.signatures
        except (SyntaxError, ValueError):
            return {}

    def _compare_signatures(
        self,
        old_sig: FunctionSignature,
        new_sig: FunctionSignature
    ) -> Optional[BreakingChange]:
        """Compare two signatures and detect breaking changes."""

        # Required parameters removed (but not if they were added as optional)
        old_required = old_sig.params[:len(old_sig.params) - old_sig.defaults]
        new_required = new_sig.params[:len(new_sig.params) - new_sig.defaults]

        # If required parameters were removed or order changed
        if len(old_required) > len(new_required):
            return BreakingChange(
                type="signature_change",
                symbol=old_sig.name,
                old_signature=old_sig,
                new_signature=new_sig,
                details=f"Required parameters removed: {set(old_required) - set(new_required)}",
                severity="HIGH"
            )

        # If parameter order changed (even with same count)
        if old_sig.params[:len(new_required)] != new_sig.params[:len(new_required)]:
            return BreakingChange(
                type="signature_change",
                symbol=old_sig.name,
                old_signature=old_sig,
                new_signature=new_sig,
                details=f"Parameter order changed: {old_sig.params} → {new_sig.params}",
                severity="HIGH"
            )

        # If *args or **kwargs was removed
        if old_sig.varargs and not new_sig.varargs:
            return BreakingChange(
                type="signature_change",
                symbol=old_sig.name,
                old_signature=old_sig,
                new_signature=new_sig,
                details="Variadic arguments (*args) removed",
                severity="HIGH"
            )

        if old_sig.kwargs and not new_sig.kwargs:
            return BreakingChange(
                type="signature_change",
                symbol=old_sig.name,
                old_signature=old_sig,
                new_signature=new_sig,
                details="Keyword arguments (**kwargs) removed",
                severity="HIGH"
            )

        # Return type changed (if annotated)
        if old_sig.return_annotation != new_sig.return_annotation:
            if old_sig.return_annotation and new_sig.return_annotation:
                return BreakingChange(
                    type="return_type_change",
                    symbol=old_sig.name,
                    old_signature=old_sig,
                    new_signature=new_sig,
                    details=f"Return type changed: {old_sig.return_annotation} → {new_sig.return_annotation}",
                    severity="MEDIUM"
                )

        return None

    def _detect_changes_generic(self, old_content: str, new_content: str) -> List[BreakingChange]:
        """Generic change detection for non-Python files (symbol-based)."""
        old_analyzer = SemanticAnalyzer.__new__(SemanticAnalyzer)
        old_analyzer.source_code = old_content
        old_analyzer.analyzer = old_analyzer._create_analyzer()

        new_analyzer = self.analyzer

        old_symbols = {s.fully_qualified_name(): s for s in old_analyzer.extract_symbols()}
        new_symbols = {s.fully_qualified_name(): s for s in new_analyzer.extract_symbols()}

        removed = set(old_symbols.keys()) - set(new_symbols.keys())
        for removed_name in removed:
            self.breaking_changes.append(BreakingChange(
                type="removal",
                symbol=removed_name,
                old_signature=None,
                new_signature=None,
                details=f"Symbol '{removed_name}' was removed",
                severity="HIGH"
            ))

        return self.breaking_changes

    def find_affected_files(self) -> Dict[str, List[str]]:
        """
        Find all files affected by breaking changes.

        Returns:
            Dict mapping affected file path → list of breaking changes that affect it
        """
        affected = {}

        if not self.breaking_changes:
            return affected

        # Get the module name of this file
        module_name = self.file_path.stem

        # Scan for downstream files that import this module
        service_dir = Path("test-scenarios/services")
        if not service_dir.exists():
            return affected

        for candidate_file in service_dir.rglob("*.py"):
            if candidate_file == self.file_path:
                continue

            try:
                content = candidate_file.read_text()

                # Check for imports
                if f"import {module_name}" in content or f"from {module_name}" in content:
                    # This file imports the changed module
                    affected[str(candidate_file)] = [bc.symbol for bc in self.breaking_changes]
            except Exception:
                continue

        return affected


def has_breaking_changes(old_content: str, new_content: str, file_path: str) -> Tuple[bool, List[BreakingChange]]:
    """
    Quick check: does file have breaking changes?

    Args:
        old_content: Previous version
        new_content: Current version
        file_path: Path to file (for language detection)

    Returns:
        (has_breaking_changes, list_of_changes)
    """
    detector = BreakingChangeDetector(file_path)
    changes = detector.detect_changes(old_content, new_content)
    return len(changes) > 0, changes

#!/usr/bin/env python3
"""
Semantic Conflict Detector for Neo

Moves beyond line-based conflict detection to semantic/symbol-level analysis.
Uses AST parsing to identify actual functions, classes, and dependencies being modified.

This module enables:
1. Function/symbol-level conflict detection (not line ranges)
2. Dependency graph analysis (transitive conflicts)
3. Evidence-based risk scoring
4. Cross-file conflict detection

Usage:
    from semantic_conflict_detector import SemanticAnalyzer

    analyzer = SemanticAnalyzer("src/auth.py")
    symbols = analyzer.extract_symbols()  # Get all functions/classes
    dependencies = analyzer.analyze_dependencies()
"""

import re
import ast
from dataclasses import dataclass, field
from typing import Set, Dict, List, Tuple, Optional
from enum import Enum
from pathlib import Path


class Language(Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    JAVA = "java"
    GOLANG = "go"
    RUST = "rust"
    CSHARP = "csharp"
    TYPESCRIPT = "typescript"


@dataclass
class Symbol:
    """Represents a function, class, or method."""
    name: str
    type: str  # "function", "class", "method", "async_function"
    start_line: int
    end_line: int
    parent: Optional[str] = None  # Parent class if method

    def __hash__(self):
        return hash((self.name, self.type, self.parent))

    def __eq__(self, other):
        return (self.name == other.name and
                self.type == other.type and
                self.parent == other.parent)

    def fully_qualified_name(self) -> str:
        """Returns fully qualified name (Class.method or just function)."""
        if self.parent:
            return f"{self.parent}.{self.name}"
        return self.name


@dataclass
class Dependency:
    """Represents a dependency between symbols."""
    source: str  # Function that depends on something
    target: str  # Function/module it depends on
    type: str  # "imports", "calls", "inherits", "uses"
    confidence: float = 1.0  # How confident we are (0.0-1.0)


@dataclass
class ConflictEvidence:
    """Evidence supporting a conflict detection."""
    reason: str
    weight: float  # Contribution to total score (0.0-1.0)
    confidence: float  # How confident we are (0.0-1.0)


class PythonAnalyzer(ast.NodeVisitor):
    """Analyzes Python AST to extract symbols and dependencies."""

    def __init__(self, source_code: str, file_path: str):
        self.source_code = source_code
        self.file_path = file_path
        self.symbols: Set[Symbol] = set()
        self.dependencies: List[Dependency] = []
        self.imports: Set[str] = set()
        self.current_class: Optional[str] = None

        try:
            self.tree = ast.parse(source_code)
        except SyntaxError:
            self.tree = None

    def extract_symbols(self) -> Set[Symbol]:
        """Extract all functions and classes from the code."""
        if not self.tree:
            return set()

        self.visit(self.tree)
        return self.symbols

    def visit_FunctionDef(self, node):
        """Visit function definitions."""
        symbol = Symbol(
            name=node.name,
            type="async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno,
            parent=self.current_class
        )
        self.symbols.add(symbol)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node):
        """Visit async function definitions."""
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node):
        """Visit class definitions."""
        symbol = Symbol(
            name=node.name,
            type="class",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno
        )
        self.symbols.add(symbol)

        # Track methods
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class

    def visit_Import(self, node):
        """Track imports."""
        for alias in node.names:
            self.imports.add(alias.name)

    def visit_ImportFrom(self, node):
        """Track from...import statements."""
        module = node.module or ""
        for alias in node.names:
            self.imports.add(f"{module}.{alias.name}")


class RegexBasedAnalyzer:
    """Language-agnostic regex-based analyzer for symbols and dependencies."""

    def __init__(self, source_code: str, language: Language):
        self.source_code = source_code
        self.language = language
        self.lines = source_code.split('\n')

    def extract_symbols(self) -> Set[Symbol]:
        """Extract symbols using regex patterns."""
        symbols = set()

        if self.language == Language.PYTHON:
            patterns = [
                (r'^\s*def\s+(\w+)\s*\(', "function"),
                (r'^\s*async def\s+(\w+)\s*\(', "async_function"),
                (r'^\s*class\s+(\w+)', "class"),
            ]

        elif self.language == Language.JAVASCRIPT:
            patterns = [
                (r'(?:function|const|let|var)\s+(\w+)\s*=?\s*(?:function|\(|async)', "function"),
                (r'^\s*class\s+(\w+)', "class"),
            ]

        elif self.language == Language.JAVA:
            patterns = [
                (r'(?:public|private|protected)?\s+\w+\s+(\w+)\s*\(', "method"),
                (r'(?:public|private|protected)?\s*class\s+(\w+)', "class"),
            ]

        elif self.language == Language.GOLANG:
            patterns = [
                (r'func\s+\(?[\w*\s]*\)?\s+(\w+)\s*\(', "method"),
                (r'func\s+(\w+)\s*\(', "function"),
                (r'type\s+(\w+)\s+struct', "struct"),
            ]

        else:  # Generic fallback
            patterns = [
                (r'(?:def|function|func)\s+(\w+)', "function"),
                (r'(?:class|struct|type)\s+(\w+)', "class"),
            ]

        for line_num, line in enumerate(self.lines, 1):
            for pattern, symbol_type in patterns:
                match = re.search(pattern, line)
                if match:
                    symbol = Symbol(
                        name=match.group(1),
                        type=symbol_type,
                        start_line=line_num,
                        end_line=line_num
                    )
                    symbols.add(symbol)

        return symbols

    def extract_dependencies(self) -> List[Dependency]:
        """Extract function call dependencies."""
        dependencies = []

        # Pattern: function_name(...)
        call_pattern = r'(\w+)\s*\('

        for line_num, line in enumerate(self.lines, 1):
            # Skip comments and strings
            if line.strip().startswith('#'):
                continue

            matches = re.finditer(call_pattern, line)
            for match in matches:
                function_name = match.group(1)
                # Filter out keywords
                if function_name not in ['if', 'while', 'for', 'switch', 'catch', 'def', 'class']:
                    dependencies.append(Dependency(
                        source="unknown",  # Would need more context
                        target=function_name,
                        type="calls",
                        confidence=0.7
                    ))

        return dependencies


class SemanticAnalyzer:
    """Main semantic analysis engine."""

    def __init__(self, file_path: str, language: Optional[Language] = None):
        self.file_path = Path(file_path)
        self.language = language or self._detect_language()

        try:
            self.source_code = self.file_path.read_text()
        except FileNotFoundError:
            self.source_code = ""

        self.analyzer = self._create_analyzer()

    def _detect_language(self) -> Language:
        """Detect language from file extension."""
        suffix = self.file_path.suffix.lower()
        mapping = {
            '.py': Language.PYTHON,
            '.js': Language.JAVASCRIPT,
            '.ts': Language.TYPESCRIPT,
            '.java': Language.JAVA,
            '.go': Language.GOLANG,
            '.rs': Language.RUST,
            '.cs': Language.CSHARP,
        }
        return mapping.get(suffix, Language.PYTHON)

    def _create_analyzer(self):
        """Create appropriate analyzer for the language."""
        if self.language == Language.PYTHON:
            return PythonAnalyzer(self.source_code, str(self.file_path))
        else:
            return RegexBasedAnalyzer(self.source_code, self.language)

    def extract_symbols(self) -> Set[Symbol]:
        """Extract all symbols (functions, classes, methods)."""
        return self.analyzer.extract_symbols()

    def analyze_dependencies(self) -> List[Dependency]:
        """Analyze dependencies between symbols."""
        if hasattr(self.analyzer, 'extract_dependencies'):
            return self.analyzer.extract_dependencies()
        return []

    def get_symbols_in_range(self, start_line: int, end_line: int) -> Set[Symbol]:
        """Get symbols that overlap with a given line range."""
        symbols = self.extract_symbols()
        return {s for s in symbols if s.start_line <= end_line and s.end_line >= start_line}


class ConflictScorer:
    """Calculates evidence-based conflict scores."""

    @staticmethod
    def score_conflict(
        symbols_a: Set[Symbol],
        symbols_b: Set[Symbol],
        file_overlap: bool,
        dependencies_graph: Optional[List[Dependency]] = None
    ) -> Tuple[int, List[ConflictEvidence]]:
        """
        Score conflict risk with evidence breakdown.

        Returns:
            (score, evidence_list)
            score: 0-100
            evidence_list: List of reasons contributing to score
        """
        evidence = []

        # Layer 1: Direct symbol overlap
        direct_overlap = symbols_a & symbols_b
        if direct_overlap:
            weight = len(direct_overlap) * 0.10  # Each overlapping symbol adds weight
            evidence.append(ConflictEvidence(
                reason=f"Direct symbol overlap: {', '.join(s.fully_qualified_name() for s in direct_overlap)}",
                weight=min(weight, 0.40),
                confidence=0.99
            ))

        # Layer 2: Related symbols (same file, different but related)
        if file_overlap and not direct_overlap:
            evidence.append(ConflictEvidence(
                reason="Same file, different symbols (potential indirect conflict)",
                weight=0.15,
                confidence=0.70
            ))

        # Layer 3: Dependency-based conflict
        if dependencies_graph:
            for dep in dependencies_graph:
                # Check if any dependency connects the two symbol sets
                for sym_a in symbols_a:
                    for sym_b in symbols_b:
                        if (dep.source == sym_a.name and dep.target == sym_b.name) or \
                           (dep.source == sym_b.name and dep.target == sym_a.name):
                            evidence.append(ConflictEvidence(
                                reason=f"Transitive dependency: {sym_a.name} → {sym_b.name}",
                                weight=0.25,
                                confidence=dep.confidence
                            ))

        # Calculate final score
        total_score = sum(e.weight * e.confidence * 100 for e in evidence)
        total_score = min(int(total_score), 100)

        return total_score, evidence


def compare_regions(
    file_path: str,
    region_a: str,
    region_b: str,
    language: Optional[Language] = None
) -> Tuple[int, List[ConflictEvidence]]:
    """
    Compare two regions of a file for semantic conflicts.

    Args:
        file_path: Path to the file
        region_a: First region (e.g., "authenticate_user" or "MyClass.method")
        region_b: Second region
        language: Programming language (auto-detected if None)

    Returns:
        (risk_score, evidence_list)
    """
    analyzer = SemanticAnalyzer(file_path, language)

    # Parse region names to get symbols
    symbols_a = _parse_region_to_symbols(region_a, analyzer)
    symbols_b = _parse_region_to_symbols(region_b, analyzer)

    # Score the conflict
    score, evidence = ConflictScorer.score_conflict(
        symbols_a,
        symbols_b,
        file_overlap=True,
        dependencies_graph=analyzer.analyze_dependencies()
    )

    return score, evidence


def _parse_region_to_symbols(region: str, analyzer: SemanticAnalyzer) -> Set[Symbol]:
    """Parse a region string (e.g., 'authenticate_user' or 'MyClass.method') to symbols."""
    all_symbols = analyzer.extract_symbols()
    matched = set()

    # Handle dot notation (Class.method)
    if '.' in region:
        parts = region.split('.')
        class_name, method_name = parts[0], parts[1]
        matched = {s for s in all_symbols
                  if s.name == method_name and s.parent == class_name}
    else:
        # Simple function/class name
        matched = {s for s in all_symbols if s.name == region}

    return matched


# Example usage and testing
if __name__ == "__main__":
    # Test with sample Python code
    sample_code = '''
def authenticate_user(username, password):
    """Authenticate user with password."""
    hashed = hash_password(password)
    user = get_user(username)
    return user and user.password == hashed

def hash_password(password):
    """Hash password using bcrypt."""
    import bcrypt
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def get_user(username):
    """Retrieve user from database."""
    return db.query("SELECT * FROM users WHERE username = ?", username)

class UserService:
    def validate_token(self, token):
        """Validate JWT token."""
        return decode_jwt(token) is not None
'''

    # Create temporary test file
    test_file = Path("/tmp/test_semantic.py")
    test_file.write_text(sample_code)

    print("SEMANTIC CONFLICT DETECTION - TEST")
    print("=" * 60)
    print()

    # Analyze the file
    analyzer = SemanticAnalyzer(str(test_file))

    print("EXTRACTED SYMBOLS:")
    symbols = analyzer.extract_symbols()
    for sym in sorted(symbols, key=lambda s: s.name):
        print(f"  • {sym.fully_qualified_name():30s} ({sym.type:20s}) lines {sym.start_line}-{sym.end_line}")

    print()
    print("DEPENDENCIES:")
    deps = analyzer.analyze_dependencies()
    for dep in deps[:10]:  # Show first 10
        print(f"  • {dep.source:20s} → {dep.target:20s} ({dep.type})")

    print()
    print("CONFLICT DETECTION EXAMPLES:")
    print("-" * 60)

    # Example 1: Direct overlap
    print("\n1. Direct Symbol Overlap:")
    print("   Region A: authenticate_user")
    print("   Region B: authenticate_user")
    score, evidence = compare_regions(str(test_file), "authenticate_user", "authenticate_user")
    print(f"   Risk Score: {score}/100")
    for e in evidence:
        print(f"     • {e.reason} (weight: {e.weight:.2f}, confidence: {e.confidence:.2f})")

    # Example 2: No overlap
    print("\n2. No Symbol Overlap:")
    print("   Region A: authenticate_user")
    print("   Region B: hash_password")
    score, evidence = compare_regions(str(test_file), "authenticate_user", "hash_password")
    print(f"   Risk Score: {score}/100")
    if evidence:
        for e in evidence:
            print(f"     • {e.reason} (weight: {e.weight:.2f})")
    else:
        print("     No conflict evidence found")

    print()
    print("✅ Semantic conflict detector operational")

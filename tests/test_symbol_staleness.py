#!/usr/bin/env python3
"""
Test C1: Symbol-level staleness detection.

Tests hash-based staleness detection with symbol-level granularity.
"""

import pytest
import tempfile
import time
from pathlib import Path
from core.symbol_hasher import (
    SymbolHash, FileSnapshot, snapshot_file, StalenessChecker,
    normalize_source, compute_hash, parse_file_symbols, extract_dependencies
)


@pytest.fixture
def temp_py_file():
    """Create a temporary Python file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def hello(name):
    """Say hello."""
    print(f"Hello {name}")

class Greeter:
    def __init__(self, greeting):
        self.greeting = greeting

    def greet(self, name):
        return f"{self.greeting} {name}"
''')
        f.flush()
        yield f.name

    Path(f.name).unlink()


def test_normalize_source_removes_comments():
    """Comments should be stripped."""
    source = "x = 1  # comment\ny = 2"
    normalized = normalize_source(source)
    assert "comment" not in normalized
    assert "x = 1" in normalized


def test_normalize_source_removes_docstrings():
    """Docstrings should be stripped."""
    source = '"""This is a docstring."""\nx = 1'
    normalized = normalize_source(source)
    assert "docstring" not in normalized


def test_compute_hash_is_deterministic():
    """Same input should always give same hash."""
    text = "def foo(): pass"
    h1 = compute_hash(text)
    h2 = compute_hash(text)
    assert h1 == h2


def test_parse_file_symbols_finds_functions(temp_py_file):
    """Should extract functions from file."""
    symbols, error = parse_file_symbols(temp_py_file)
    assert error is None
    assert "hello" in symbols
    assert symbols["hello"].type == "function"


def test_parse_file_symbols_finds_classes(temp_py_file):
    """Should extract classes from file."""
    symbols, error = parse_file_symbols(temp_py_file)
    assert error is None
    assert "Greeter" in symbols
    assert symbols["Greeter"].type == "class"


def test_parse_file_symbols_handles_missing_file():
    """Should gracefully handle missing file."""
    symbols, error = parse_file_symbols("/nonexistent/file.py")
    assert error is not None
    assert "not found" in error.lower()


def test_parse_file_symbols_handles_syntax_error():
    """Should gracefully handle syntax errors."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def broken(:\n  pass")
        f.flush()

        symbols, error = parse_file_symbols(f.name)
        assert error is not None
        assert "syntax error" in error.lower()

        Path(f.name).unlink()


def test_snapshot_file_creates_snapshot(temp_py_file):
    """Should create file snapshot."""
    snap = snapshot_file(temp_py_file, "agent1", time.time())
    assert snap.file_path == temp_py_file
    assert snap.agent_id == "agent1"
    assert len(snap.symbols) > 0
    assert "hello" in snap.symbols


def test_snapshot_file_handles_missing_file():
    """Should mark missing file."""
    snap = snapshot_file("/nonexistent.py", "agent1", time.time())
    assert snap.content_hash == "MISSING"


def test_staleness_checker_detects_current():
    """Should detect unchanged file as CURRENT."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def foo(): pass")
        f.flush()

        snap = snapshot_file(f.name, "agent1", time.time())
        state, report = StalenessChecker.check_file_staleness(snap, f.name)

        assert state == "CURRENT"
        assert "unchanged" in report.get("reason", "").lower()

        Path(f.name).unlink()


def test_staleness_checker_detects_stale_on_change():
    """Should detect changed file as STALE_SOURCE."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def foo(): pass")
        f.flush()

        snap = snapshot_file(f.name, "agent1", time.time())

        # Modify file
        Path(f.name).write_text("def foo(): return 42")

        state, report = StalenessChecker.check_file_staleness(snap, f.name)
        assert state == "STALE_SOURCE"

        Path(f.name).unlink()


def test_staleness_checker_unverifiable_on_parse_error():
    """Should return UNVERIFIABLE if can't parse."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write("def foo(): pass")
        f.flush()

        snap = snapshot_file(f.name, "agent1", time.time())

        # Break the file
        Path(f.name).write_text("def broken(:\n  pass")

        state, report = StalenessChecker.check_file_staleness(snap, f.name)
        assert state == "UNVERIFIABLE"

        Path(f.name).unlink()


def test_staleness_checker_scopes_by_dependency():
    """Should only check specified dependency symbols."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def foo(): pass
def bar(): pass
def baz(): pass
''')
        f.flush()

        snap = snapshot_file(f.name, "agent1", time.time())

        # Change bar() but not foo()
        Path(f.name).write_text('''
def foo(): pass
def bar(): return 42
def baz(): pass
''')

        # Checking only foo() should be CURRENT
        state, _ = StalenessChecker.check_file_staleness(snap, f.name, ["foo"])
        assert state == "CURRENT"

        # Checking bar() should be STALE_SOURCE
        state, _ = StalenessChecker.check_file_staleness(snap, f.name, ["bar"])
        assert state == "STALE_SOURCE"

        Path(f.name).unlink()


def test_extract_dependencies_finds_names():
    """Should extract symbol dependencies."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def helper(): return 42
def main(): return helper()
''')
        f.flush()

        deps = extract_dependencies(f.name)
        assert "main" in deps
        assert "helper" in deps["main"]

        Path(f.name).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

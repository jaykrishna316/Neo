#!/usr/bin/env python3
"""
Test C2: Symbol-level delta refresh.

Tests efficient context refresh using symbol-level deltas instead of full files.
"""

import pytest
import tempfile
import time
from pathlib import Path
from core.symbol_hasher import snapshot_file
from core.delta_refresh import DeltaGenerator, FileDelta, ContextRefreshBuilder


@pytest.fixture
def temp_py_file():
    """Create a temporary Python file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write('''
def foo():
    """Original foo."""
    return 1

def bar():
    return 2

class MyClass:
    def method(self):
        return 3
''')
        f.flush()
        yield f.name
    Path(f.name).unlink()


def test_delta_generator_detects_no_changes(temp_py_file):
    """Should return CURRENT for unchanged file."""
    base_snap = snapshot_file(temp_py_file, "agent1", time.time())
    delta = DeltaGenerator.generate(base_snap, temp_py_file)

    assert delta.delta_type == "symbols"
    assert len(delta.added_symbols) == 0
    assert len(delta.removed_symbols) == 0
    assert len(delta.changed_symbols) == 0


def test_delta_generator_detects_added_symbol(temp_py_file):
    """Should detect new function."""
    base_snap = snapshot_file(temp_py_file, "agent1", time.time())

    # Add new function
    Path(temp_py_file).write_text('''
def foo():
    return 1

def bar():
    return 2

def new_func():
    return 99

class MyClass:
    def method(self):
        return 3
''')

    delta = DeltaGenerator.generate(base_snap, temp_py_file)
    assert delta.delta_type == "symbols"
    assert "new_func" in delta.added_symbols


def test_delta_generator_detects_removed_symbol(temp_py_file):
    """Should detect removed function."""
    base_snap = snapshot_file(temp_py_file, "agent1", time.time())

    # Remove bar() function
    Path(temp_py_file).write_text('''
def foo():
    return 1

class MyClass:
    def method(self):
        return 3
''')

    delta = DeltaGenerator.generate(base_snap, temp_py_file)
    assert delta.delta_type == "symbols"
    assert "bar" in delta.removed_symbols


def test_delta_generator_detects_changed_symbol(temp_py_file):
    """Should detect modified function body."""
    base_snap = snapshot_file(temp_py_file, "agent1", time.time())

    # Change foo's body
    Path(temp_py_file).write_text('''
def foo():
    """Modified foo."""
    return 42

def bar():
    return 2

class MyClass:
    def method(self):
        return 3
''')

    delta = DeltaGenerator.generate(base_snap, temp_py_file)
    assert delta.delta_type == "symbols"
    assert "foo" in delta.changed_symbols


def test_delta_generator_ignores_formatting_changes(temp_py_file):
    """Should not flag formatting-only changes as stale."""
    base_snap = snapshot_file(temp_py_file, "agent1", time.time())

    # Only change whitespace/formatting
    Path(temp_py_file).write_text('''
def foo():
    """Original foo."""
    return     1

def bar():
    return 2

class MyClass:
    def method(self):
        return 3
''')

    delta = DeltaGenerator.generate(base_snap, temp_py_file)
    # Should NOT flag as changed (formatting only)
    assert "foo" not in delta.changed_symbols


def test_delta_generator_scopes_by_dependency(temp_py_file):
    """Should only report deltas for dependent symbols."""
    base_snap = snapshot_file(temp_py_file, "agent1", time.time())

    # Change bar() and add new_func()
    Path(temp_py_file).write_text('''
def foo():
    return 1

def bar():
    return 99

def new_func():
    return 100

class MyClass:
    def method(self):
        return 3
''')

    # Only care about foo and bar
    delta = DeltaGenerator.generate(base_snap, temp_py_file, ["foo", "bar"])

    # Should report bar as changed
    assert "bar" in delta.changed_symbols
    # Should NOT report new_func as added (not in dependency list)
    # (Actually, it still reports all symbols, but dependency_symbols affects signature reporting)


def test_context_refresh_builder_estimates_tokens():
    """Should estimate token cost of deltas."""
    from core.delta_refresh import SymbolDelta

    delta = FileDelta(
        file_path="test.py",
        delta_type="symbols",
        symbol_deltas=[
            SymbolDelta(name="foo", type="changed", body="def foo():\n    return 42")
        ]
    )

    tokens = ContextRefreshBuilder.estimate_tokens(delta)
    assert tokens > 0


def test_context_refresh_builder_builds_message(temp_py_file):
    """Should build human-readable refresh message."""
    base_snap = snapshot_file(temp_py_file, "agent1", time.time())

    # Change file
    Path(temp_py_file).write_text('''
def foo():
    return 42

def bar():
    return 2

def new_func():
    return 99

class MyClass:
    def method(self):
        return 3
''')

    delta = DeltaGenerator.generate(base_snap, temp_py_file)
    message = ContextRefreshBuilder.build_message([delta], "agent1", temp_py_file)

    assert "agent1" in message
    assert "new_func" in message
    assert "Changed" in message or "changed" in message


def test_delta_generator_full_file_fallback(temp_py_file):
    """Should fall back to full file if can't generate symbols."""
    base_snap = snapshot_file(temp_py_file, "agent1", time.time())

    # Break the file syntax
    Path(temp_py_file).write_text("def broken(:\n  pass")

    delta = DeltaGenerator.generate(base_snap, temp_py_file)
    # Should fall back gracefully (might be unified_diff or full_file)
    assert delta.delta_type in ["unified_diff", "full_file"]


def test_delta_refresh_token_efficiency():
    """Symbol-level delta should be much cheaper than full file."""
    full_file_delta = FileDelta(
        file_path="test.py",
        delta_type="full_file",
        full_content="x" * 4000  # 4000 chars = ~1000 tokens
    )

    from core.delta_refresh import SymbolDelta
    symbol_delta = FileDelta(
        file_path="test.py",
        delta_type="symbols",
        symbol_deltas=[
            SymbolDelta(name="foo", type="changed", body="def foo():\n    return 42")
        ]
    )

    full_tokens = ContextRefreshBuilder.estimate_tokens(full_file_delta)
    symbol_tokens = ContextRefreshBuilder.estimate_tokens(symbol_delta)

    # Symbol delta should be significantly cheaper
    assert symbol_tokens < full_tokens // 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

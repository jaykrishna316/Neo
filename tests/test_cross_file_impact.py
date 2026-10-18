"""
Tests for cross-file blast radius tracking.
Verifies symbol-level change detection, downstream consumer discovery,
impact alert creation with dedup, and the blast radius scoring factor.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.activity_log as activity_log
from core.conflict_scorer import calculate_conflict_score
from core.cross_file_impact import (
    detect_changed_symbols,
    find_downstream_consumers,
    record_change_impacts,
)
from core.impact_alerts import ImpactAlertManager


GREET_OLD = '''def greet(name):
    return "hello " + name


def unused():
    return 0
'''

GREET_NEW = '''def greet(name, punctuation="!"):
    return "hello " + name + punctuation


def unused():
    return 0
'''


def _write(root: Path, rel_path: str, text: str) -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _make_repo(root: Path) -> None:
    _write(root, "core/__init__.py", "")
    _write(root, "core/greet.py", GREET_NEW)
    # Cross-service consumer: imports the changed function by name
    _write(root, "app/main.py", "from core.greet import greet\n\nprint(greet('x'))\n")
    # Consumer that only uses an unchanged symbol, so it must not be flagged
    _write(root, "app/unrelated.py", "from core.greet import unused\n")
    # Consumer that reaches the function through a module alias
    _write(root, "worker/job.py", "import core.greet as g\n\ng.greet('y')\n")
    # Same-service consumer using a relative import
    _write(root, "core/use.py", "from .greet import greet\n")


def test_detect_changed_symbols_flags_body_change_only():
    """A body change is reported; the untouched function is not"""
    print("\n✓ Test 1: Body change detected, untouched symbol ignored")

    assert detect_changed_symbols(GREET_OLD, GREET_NEW) == ["greet"]


def test_detect_changed_symbols_ignores_formatting_and_comments():
    """Whitespace and comment edits do not count as a symbol change"""
    print("\n✓ Test 2: Formatting and comment edits raise no change")

    reformatted = '''def greet(name):
    # say hello
    return "hello " + name


def unused():
    return 0
'''
    assert detect_changed_symbols(GREET_OLD, reformatted) == []


def test_detect_changed_symbols_reports_added_and_removed():
    """Added and removed functions both count as changes"""
    print("\n✓ Test 3: Added and removed symbols are reported")

    old = "def a():\n    return 1\n"
    new = "def b():\n    return 2\n"
    assert detect_changed_symbols(old, new) == ["a", "b"]


def test_find_consumers_matches_imports_and_aliases(tmp_path):
    """Named imports, module aliases, and relative imports all find consumers"""
    print("\n✓ Test 4: Consumers found via from-import, alias, and relative import")

    _make_repo(tmp_path)
    consumers = find_downstream_consumers(str(tmp_path), "core/greet.py", ["greet"])
    by_file = {c.file_path: c for c in consumers}

    assert set(by_file) == {"app/main.py", "worker/job.py", "core/use.py"}
    assert by_file["app/main.py"].symbols == ["greet"]
    assert by_file["worker/job.py"].symbols == ["greet"]
    assert by_file["core/use.py"].symbols == ["greet"]


def test_find_consumers_flags_cross_service(tmp_path):
    """A consumer in another top-level directory is cross-service; same-directory is not"""
    print("\n✓ Test 5: Cross-service flag follows top-level directory")

    _make_repo(tmp_path)
    consumers = find_downstream_consumers(str(tmp_path), "core/greet.py", ["greet"])
    by_file = {c.file_path: c for c in consumers}

    assert by_file["app/main.py"].cross_service is True
    assert by_file["worker/job.py"].cross_service is True
    assert by_file["core/use.py"].cross_service is False


def test_record_change_creates_alerts_and_dedups(tmp_path, monkeypatch):
    """Each consumer gets one alert; a repeat change does not stack a duplicate"""
    print("\n✓ Test 6: Alerts created per consumer, repeat change deduplicated")

    monkeypatch.setattr(activity_log, "ACTIVITY_LOG_DIR", tmp_path / "activity")
    _make_repo(tmp_path)

    first = record_change_impacts(
        repo_path=str(tmp_path),
        source_file="core/greet.py",
        changed_by="Developer A",
        old_source=GREET_OLD,
        log_intent=False,
    )
    assert first["status"] == "impacts_recorded"
    assert first["changed_symbols"] == ["greet"]
    assert sorted(first["alerts_created"]) == ["app/main.py", "core/use.py", "worker/job.py"]
    assert first["alerts_skipped"] == []

    manager = ImpactAlertManager(str(tmp_path))
    alerts = manager.get_alerts_for_file("app/main.py")
    assert len(alerts) == 1
    assert alerts[0]["consumed_symbols"] == ["greet"]
    assert alerts[0]["cross_service"] is True
    assert alerts[0]["changed_symbols"] == ["greet"]

    second = record_change_impacts(
        repo_path=str(tmp_path),
        source_file="core/greet.py",
        changed_by="Developer A",
        old_source=GREET_OLD,
        log_intent=False,
    )
    assert second["alerts_created"] == []
    assert sorted(second["alerts_skipped"]) == ["app/main.py", "core/use.py", "worker/job.py"]
    assert len(manager.get_alerts_for_file("app/main.py")) == 1
    print("  Second change skipped all existing alerts")


def test_record_change_without_symbol_change_creates_nothing(tmp_path):
    """Formatting-only edits create no alerts"""
    print("\n✓ Test 7: No symbol change means no alerts")

    _make_repo(tmp_path)
    result = record_change_impacts(
        repo_path=str(tmp_path),
        source_file="core/greet.py",
        changed_by="Developer A",
        old_source=GREET_NEW,
        new_source=GREET_NEW + "\n\n",
        log_intent=False,
    )
    assert result["status"] == "no_symbol_changes"
    assert ImpactAlertManager(str(tmp_path)).get_alerts_for_file("app/main.py") == []


def test_record_change_logs_changed_symbols(tmp_path, monkeypatch):
    """The activity log records changed symbols for the file"""
    print("\n✓ Test 8: Changed symbols reach the activity log")

    monkeypatch.setattr(activity_log, "ACTIVITY_LOG_DIR", tmp_path / "activity")
    _make_repo(tmp_path)

    record_change_impacts(
        repo_path=str(tmp_path),
        source_file="core/greet.py",
        changed_by="Developer A",
        old_source=GREET_OLD,
    )
    assert activity_log.get_changed_symbols("core/greet.py") == ["greet"]
    assert activity_log.get_changed_symbols("app/main.py") == []


def test_blast_radius_raises_score_only_when_consumers_present():
    """Default call is unchanged; consumers raise the score and add guidance"""
    print("\n✓ Test 9: Blast radius factor affects score only when consumers exist")

    base = calculate_conflict_score(num_conflicts=1, conflict_types=["overlap"])
    assert base.impact_factors["blast_radius"] == 0

    with_consumers = calculate_conflict_score(
        num_conflicts=1,
        conflict_types=["overlap"],
        downstream_consumers=2,
        cross_service_consumers=1,
    )
    assert with_consumers.impact_factors["blast_radius"] == 7  # 2*2 + 1*3
    assert with_consumers.total_score == base.total_score + 7
    assert any("service boundary" in w for w in with_consumers.warnings)
    assert any("downstream consumer" in r for r in with_consumers.recommendations)


def test_blast_radius_factor_is_capped():
    """Many consumers cannot push the factor past 10 or the total past 100"""
    print("\n✓ Test 10: Blast radius factor and total are capped")

    score = calculate_conflict_score(
        num_conflicts=5,
        conflict_types=["overlap", "signature_change", "dependency_conflict"],
        overlap_severity=1.0,
        is_git_detected=True,
        active_time_minutes=120,
        developer_patterns={f"dev{i}": {"median": 300} for i in range(5)},
        downstream_consumers=20,
        cross_service_consumers=20,
    )
    assert score.impact_factors["blast_radius"] == 10
    assert score.total_score <= 100

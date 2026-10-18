"""Tests for write coalescing in core/activity_log.py.

Covers: no lost or torn lines under concurrent writers, per-thread read-after-write,
arrival ordering within a file, error propagation to every caller in a failed batch,
and that the public log_activity() behaviour is unchanged.
"""
import json
import sys
import threading
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import activity_log  # noqa: E402


@pytest.fixture
def log_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(activity_log, "ACTIVITY_LOG_DIR", tmp_path)
    monkeypatch.setattr(activity_log, "MULTITENANCY_ENABLED", False)
    return tmp_path


def _run_threads(n, target):
    barrier = threading.Barrier(n)
    errors = []

    def wrapper(i):
        try:
            barrier.wait()
            target(i)
        except BaseException as exc:  # surface to the main thread
            errors.append(exc)

    threads = [threading.Thread(target=wrapper, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return errors


def test_concurrent_writes_are_all_persisted_intact(log_dir):
    writers, per_writer = 16, 50

    def work(i):
        for j in range(per_writer):
            activity_log.log_activity(f"dev-{i}", f"file_{i}.py", f"intent {j}")

    assert _run_threads(writers, work) == []

    lines = (log_dir / "activity-log.json").read_text().splitlines()
    assert len(lines) == writers * per_writer
    parsed = [json.loads(line) for line in lines]  # every line is valid JSON
    seen = {(e["developer_id"], e["intent"]) for e in parsed}
    assert len(seen) == writers * per_writer


def test_each_caller_can_read_its_own_write_immediately(log_dir):
    def work(i):
        for j in range(20):
            entry = activity_log.log_activity(f"dev-{i}", "shared.py", f"step {j}")
            visible = activity_log.read_log()
            assert any(
                e["developer_id"] == entry.developer_id and e["intent"] == entry.intent
                for e in visible
            ), "write was not visible when log_activity returned"

    assert _run_threads(8, work) == []


def test_single_thread_order_is_preserved(log_dir):
    for j in range(100):
        activity_log.log_activity("solo", "a.py", f"intent {j}")

    intents = [e["intent"] for e in activity_log.read_log()]
    assert intents == [f"intent {j}" for j in range(100)]


def test_batch_groups_lines_per_file(log_dir):
    """Lines queued together for one file should hit disk in a single write call."""
    file_a = log_dir / "a.json"
    file_b = log_dir / "b.json"
    batch = [(0, file_a, "a0\n"), (1, file_b, "b0\n"), (2, file_a, "a1\n")]

    real_open = open
    opened = []

    def spy_open(path, *args, **kwargs):
        opened.append(Path(path))
        return real_open(path, *args, **kwargs)

    with mock.patch.object(activity_log, "open", spy_open, create=True):
        activity_log._write_batch(batch)

    assert opened == [file_a, file_b]  # one open per file, not per line
    assert file_a.read_text() == "a0\na1\n"
    assert file_b.read_text() == "b0\n"


def test_failed_batch_raises_for_every_caller(log_dir, monkeypatch):
    class Boom(RuntimeError):
        pass

    def broken(batch):
        raise Boom("disk full")

    real_write_batch = activity_log._write_batch
    failing = {"on": True}

    def maybe_broken(batch):
        if failing["on"]:
            raise Boom("disk full")
        return real_write_batch(batch)

    monkeypatch.setattr(activity_log, "_write_batch", maybe_broken)
    writer = activity_log._GroupCommitWriter()
    target = log_dir / "x.json"

    errors = []

    def work(i):
        try:
            writer.append(target, f"line {i}\n")
        except Boom as exc:
            errors.append(exc)

    assert _run_threads(4, work) == []
    assert len(errors) == 4
    assert not target.exists() or target.read_text() == ""

    # The writer recovers: once the fault is gone, later appends succeed.
    failing["on"] = False
    writer.append(target, "ok\n")
    assert target.read_text() == "ok\n"


def test_log_activity_return_value_unchanged(log_dir):
    entry = activity_log.log_activity(
        "dev-1", "f.py", "fix bug", region="foo", intent_category="bugfix"
    )
    assert entry.developer_id == "dev-1"
    assert entry.file_path == "f.py"
    assert entry.intent_category == "bugfix"
    assert entry.tenant_id == "default"
    stored = activity_log.read_log()
    assert stored == [entry.to_dict()]

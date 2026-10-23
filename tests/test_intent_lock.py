"""The first edit attempt on a file takes its lock. The lock is released when the task ends."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "scripts" / "neo_hook.py"


def _hook(mode, developer, workdir, file_path=None):
    env = {k: v for k, v in os.environ.items() if k not in ("NEO_DEVELOPER", "NEO_INTENT")}
    env.update({
        "PYTHONPATH": str(REPO),
        "NEO_STATE_DIR": str(Path(workdir) / ".neo_state"),
        "NEO_ACTIVITY_LOG_DIR": str(Path(workdir) / ".devsync"),
    })
    if developer:
        env["NEO_DEVELOPER"] = developer
    payload = {"tool_name": "Edit", "tool_input": {"file_path": file_path}} if file_path else {}
    return subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps(payload), text=True,
                          capture_output=True, cwd=workdir, env=env, timeout=120)


def _file(workdir):
    path = Path(workdir) / "auth.py"
    path.write_text("def authenticate(user):\n    return False\n")
    return str(path)


def _lock_entries(workdir):
    log = Path(workdir) / ".devsync" / "activity-log.json"
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line.strip()]


def test_first_edit_attempt_takes_the_lock():
    with tempfile.TemporaryDirectory() as workdir:
        file_path = _file(workdir)
        assert _hook("pre", "alice", workdir, file_path).returncode == 0
        acquired = [e for e in _lock_entries(workdir)
                    if e.get("lock_state") == "ACQUIRED" and e.get("lock_holder") == "alice"]
        assert acquired, "alice's first edit attempt should record her lock"


def test_second_developer_waits_when_first_started_first():
    with tempfile.TemporaryDirectory() as workdir:
        file_path = _file(workdir)
        assert _hook("pre", "alice", workdir, file_path).returncode == 0
        bob = _hook("pre", "bob", workdir, file_path)
        assert bob.returncode == 2 and "locked by alice" in bob.stderr


def test_first_developer_to_attempt_an_edit_wins_in_either_order():
    with tempfile.TemporaryDirectory() as workdir:
        file_path = _file(workdir)
        # bob starts first this time
        assert _hook("pre", "bob", workdir, file_path).returncode == 0
        alice = _hook("pre", "alice", workdir, file_path)
        assert alice.returncode == 2 and "locked by bob" in alice.stderr


def test_stop_releases_every_lock_and_promotes_the_next():
    with tempfile.TemporaryDirectory() as workdir:
        file_path = _file(workdir)
        assert _hook("pre", "alice", workdir, file_path).returncode == 0
        assert _hook("pre", "bob", workdir, file_path).returncode == 2
        stop = _hook("stop", "alice", workdir)
        assert stop.returncode == 0 and "bob is next" in stop.stderr
        assert _hook("pre", "bob", workdir, file_path).returncode == 0


def test_stop_with_nothing_locked_does_nothing():
    with tempfile.TemporaryDirectory() as workdir:
        result = _hook("stop", "alice", workdir)
        assert result.returncode == 0 and result.stderr.strip() == ""


def test_stop_without_developer_name_does_nothing():
    with tempfile.TemporaryDirectory() as workdir:
        result = _hook("stop", None, workdir)
        assert result.returncode == 0 and result.stdout.strip() == ""

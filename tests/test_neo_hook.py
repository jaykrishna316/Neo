"""Two Claude Code sessions (alice, bob) on one laptop, driven through the Neo hook.

Each hook call runs as a separate process, the way Claude Code runs hooks.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "scripts" / "neo_hook.py"
FILE = str(REPO / "src" / "auth.py")


def _run(mode, developer, workdir, file_path=FILE):
    env = {k: v for k, v in os.environ.items() if k != "NEO_DEVELOPER"}
    if developer:
        env["NEO_DEVELOPER"] = developer
    env["PYTHONPATH"] = str(REPO)
    payload = json.dumps({"tool_name": "Edit", "tool_input": {"file_path": file_path}})
    return subprocess.run(
        [sys.executable, str(HOOK), mode], input=payload, text=True,
        capture_output=True, cwd=workdir, env=env, timeout=120,
    )


def test_two_sessions_queue_and_hand_off():
    with tempfile.TemporaryDirectory() as workdir:
        # alice's first edit attempt takes the lock
        assert _run("pre", "alice", workdir).returncode == 0

        # bob is queued and his edit is blocked
        blocked = _run("pre", "bob", workdir)
        assert blocked.returncode == 2, blocked.stderr
        assert "locked by alice" in blocked.stderr

        # alice's edit does not release the lock: the task is still running
        assert _run("post", "alice", workdir).returncode == 0
        assert _run("pre", "bob", workdir).returncode == 2

        # alice's task ends: her lock is released and bob is promoted
        done = _run("stop", "alice", workdir)
        assert done.returncode == 0, done.stderr
        assert "bob is next" in done.stdout

        # bob can now edit
        assert _run("pre", "bob", workdir).returncode == 0


def test_without_developer_name_the_hook_does_nothing():
    with tempfile.TemporaryDirectory() as workdir:
        assert _run("pre", None, workdir).returncode == 0
        assert _run("post", None, workdir).returncode == 0

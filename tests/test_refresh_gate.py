"""An edit needs a fresh context: a file that changed since the last read blocks the edit."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "scripts" / "neo_hook.py"


def _hook(mode, developer, workdir, file_path):
    env = {k: v for k, v in os.environ.items() if k != "NEO_DEVELOPER"}
    env.update({
        "NEO_DEVELOPER": developer,
        "PYTHONPATH": str(REPO),
        "NEO_STATE_DIR": str(Path(workdir) / ".neo_state"),
        "NEO_ACTIVITY_LOG_DIR": str(Path(workdir) / ".devsync"),
    })
    payload = json.dumps({"tool_name": "X", "tool_input": {"file_path": file_path}})
    return subprocess.run([sys.executable, str(HOOK), mode], input=payload, text=True,
                          capture_output=True, cwd=workdir, env=env, timeout=120)


def test_stale_context_blocks_until_reread():
    with tempfile.TemporaryDirectory() as workdir:
        file_path = str(Path(workdir) / "auth.py")
        Path(file_path).write_text("def authenticate(user):\n    return False\n")

        # bob reads the file, then someone else changes it
        assert _hook("read", "bob", workdir, file_path).returncode == 0
        Path(file_path).write_text("def authenticate(user, password):\n    return True\n")

        blocked = _hook("pre", "bob", workdir, file_path)
        assert blocked.returncode == 2, blocked.stderr
        assert "changed after you last read it" in blocked.stderr

        # bob reads again, which refreshes his context, and the edit is allowed
        assert _hook("read", "bob", workdir, file_path).returncode == 0
        assert _hook("pre", "bob", workdir, file_path).returncode == 0


def test_own_edit_does_not_make_context_stale():
    with tempfile.TemporaryDirectory() as workdir:
        file_path = str(Path(workdir) / "auth.py")
        Path(file_path).write_text("def authenticate(user):\n    return False\n")
        assert _hook("read", "bob", workdir, file_path).returncode == 0
        assert _hook("pre", "bob", workdir, file_path).returncode == 0
        Path(file_path).write_text("def authenticate(user):\n    return True\n")
        assert _hook("post", "bob", workdir, file_path).returncode == 0
        # bob's own change is the new baseline, so his next edit is not blocked
        assert _hook("pre", "bob", workdir, file_path).returncode == 0

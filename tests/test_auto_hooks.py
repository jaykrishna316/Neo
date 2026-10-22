"""Hooks that run without explicit calls: intent from the prompt, change analysis, shell edits."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "scripts" / "neo_hook.py"


def _env(developer, workdir):
    env = {k: v for k, v in os.environ.items() if k not in ("NEO_DEVELOPER", "NEO_INTENT")}
    env.update({
        "PYTHONPATH": str(REPO),
        "NEO_STATE_DIR": str(Path(workdir) / ".neo_state"),
        "NEO_ACTIVITY_LOG_DIR": str(Path(workdir) / ".devsync"),
    })
    if developer:
        env["NEO_DEVELOPER"] = developer
    return env


def _hook(mode, developer, workdir, payload=None):
    return subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps(payload or {}),
                          text=True, capture_output=True, cwd=workdir,
                          env=_env(developer, workdir), timeout=120)


def _edit_payload(file_path):
    return {"tool_name": "Edit", "tool_input": {"file_path": file_path}}


def _log(workdir):
    path = Path(workdir) / ".devsync" / "activity-log.json"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _project(workdir):
    """A small project: src/auth.py, and a downstream service that imports it."""
    (Path(workdir) / "src").mkdir()
    auth = Path(workdir) / "src" / "auth.py"
    auth.write_text("def authenticate(user):\n    return False\n")
    (Path(workdir) / "payment.py").write_text("from auth import authenticate\n\n"
                                              "def pay(user):\n    return authenticate(user)\n")
    return auth


def test_prompt_becomes_the_intent():
    with tempfile.TemporaryDirectory() as workdir:
        assert _hook("prompt", "alice", workdir, {"prompt": "Add OAuth2 login to authenticate"}).returncode == 0
        file_path = str(_project(workdir))
        assert _hook("pre", "alice", workdir, _edit_payload(file_path)).returncode == 0
        intents = [e["intent"] for e in _log(workdir) if e["developer_id"] == "alice"]
        assert "Add OAuth2 login to authenticate" in intents, intents


def test_edit_that_breaks_a_downstream_caller_is_reported():
    with tempfile.TemporaryDirectory() as workdir:
        auth = _project(workdir)
        file_path = str(auth)
        assert _hook("read", "bob", workdir, {"tool_input": {"file_path": file_path}}).returncode == 0
        assert _hook("pre", "bob", workdir, _edit_payload(file_path)).returncode == 0
        auth.write_text("def authenticate(user, password):\n    return True\n")
        post = _hook("post", "bob", workdir, _edit_payload(file_path))
        assert post.returncode == 0, post.stderr
        context = json.loads(post.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "Breaking change" in context, context
        assert "payment.py" in context, context
        assert any(e["intent"].startswith("Breaking change") for e in _log(workdir))


def test_shell_edit_is_analysed_and_logged():
    with tempfile.TemporaryDirectory() as workdir:
        auth = _project(workdir)
        git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t"]
        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run([*git, "add", "."], cwd=workdir, check=True)
        subprocess.run([*git, "commit", "-q", "-m", "base"], cwd=workdir, check=True)

        assert _hook("read", "bob", workdir, {"tool_input": {"file_path": str(auth)}}).returncode == 0
        auth.write_text("def authenticate(user, password):\n    return True\n")  # changed by a shell command
        result = _hook("bash", "bob", workdir, {"tool_name": "Bash"})
        assert result.returncode == 0, result.stderr
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "Breaking change" in context, context
        assert any(e["intent"] == "Edit via shell: src/auth.py" for e in _log(workdir))

        # a second run with no new change does nothing
        again = _hook("bash", "bob", workdir, {"tool_name": "Bash"})
        assert again.stdout.strip() == "", again.stdout


def test_shell_edit_of_a_locked_file_is_flagged():
    with tempfile.TemporaryDirectory() as workdir:
        auth = _project(workdir)
        git = ["git", "-c", "user.email=t@example.com", "-c", "user.name=t"]
        subprocess.run(["git", "init", "-q"], cwd=workdir, check=True)
        subprocess.run([*git, "add", "."], cwd=workdir, check=True)
        subprocess.run([*git, "commit", "-q", "-m", "base"], cwd=workdir, check=True)

        lock = subprocess.run(
            [sys.executable, "-c",
             "from core.lock_manager import LockManager; "
             "LockManager().acquire_lock('src/auth.py', None, 'alice', 'MEDIUM_CONFLICT')"],
            cwd=workdir, env=_env(None, workdir), capture_output=True, text=True, timeout=120)
        assert lock.returncode == 0, lock.stderr

        assert _hook("read", "bob", workdir, {"tool_input": {"file_path": str(auth)}}).returncode == 0
        auth.write_text("def authenticate(user):\n    return True\n")
        result = _hook("bash", "bob", workdir, {"tool_name": "Bash"})
        context = json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
        assert "locked by alice" in context, context


def test_without_developer_every_mode_is_a_no_op():
    with tempfile.TemporaryDirectory() as workdir:
        auth = _project(workdir)
        for mode in ("prompt", "pre", "post", "read", "bash"):
            result = _hook(mode, None, workdir, {"prompt": "x", "tool_input": {"file_path": str(auth)}})
            assert result.returncode == 0 and result.stdout.strip() == "", (mode, result.stdout)

"""scripts/install_neo.sh copies the hook into a repo and wires it up, safely and repeatably."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
INSTALL = REPO / "scripts" / "install_neo.sh"


def _git_repo(path):
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)


def _install(target):
    return subprocess.run(["bash", str(INSTALL), str(target)], capture_output=True, text=True, timeout=120)


def _hook_commands(settings):
    return [h["command"] for groups in settings["hooks"].values()
            for g in groups for h in g["hooks"] if h["command"].startswith("python3 .neo/scripts/")]


def test_install_copies_hook_and_wires_all_six_modes():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "braxis"
        _git_repo(target)
        result = _install(target)
        assert result.returncode == 0, result.stderr

        assert (target / ".neo" / "scripts" / "neo_hook.py").is_file()
        assert (target / ".neo" / "core" / "lock_manager.py").is_file()
        assert (target / ".neo" / "VERSION").is_file()

        settings = json.loads((target / ".claude" / "settings.json").read_text())
        commands = _hook_commands(settings)
        assert len(commands) == 7, commands
        for mode in ("pre", "post", "read", "bash", "prompt", "stop"):
            assert any(c.endswith(f"neo_hook.py {mode}") for c in commands), mode
        assert any(c.endswith("neo_update_check.py") for c in commands)
        assert (target / ".neo" / "scripts" / "neo_update_check.py").is_file()
        assert (target / ".neo" / "scripts" / "braxis_demo.sh").is_file()

        ignored = (target / ".gitignore").read_text().splitlines()
        assert ignored.count(".neo_state/") == 1 and ignored.count(".devsync/") == 1


def test_rerun_refreshes_without_duplicating():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "braxis"
        _git_repo(target)
        _install(target)
        _install(target)
        settings = json.loads((target / ".claude" / "settings.json").read_text())
        assert len(_hook_commands(settings)) == 7
        assert (target / ".gitignore").read_text().count(".neo_state/") == 1


def test_existing_hooks_and_settings_are_kept():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "braxis"
        _git_repo(target)
        (target / ".claude").mkdir()
        (target / ".claude" / "settings.json").write_text(json.dumps({
            "permissions": {"allow": ["Bash"]},
            "hooks": {"PreToolUse": [{"matcher": "Edit", "hooks": [
                {"type": "command", "command": "./lint-check.sh", "timeout": 5}]}]},
        }))
        (target / ".gitignore").write_text("node_modules/")
        _install(target)

        settings = json.loads((target / ".claude" / "settings.json").read_text())
        assert settings["permissions"] == {"allow": ["Bash"]}
        pre_commands = [h["command"] for g in settings["hooks"]["PreToolUse"] for h in g["hooks"]]
        assert "./lint-check.sh" in pre_commands
        assert any("neo_hook.py pre" in c for c in pre_commands)
        assert (target / ".gitignore").read_text().splitlines()[0] == "node_modules/"


def test_installed_hook_runs_from_the_target_repo_alone():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "braxis"
        _git_repo(target)
        _install(target)
        (target / "src").mkdir()
        auth = target / "src" / "auth.py"
        auth.write_text("def authenticate(user):\n    return False\n")

        env = {k: v for k, v in os.environ.items() if k not in ("NEO_DEVELOPER", "PYTHONPATH")}
        payload = json.dumps({"tool_input": {"file_path": str(auth)}})

        silent = subprocess.run(["python3", ".neo/scripts/neo_hook.py", "pre"], input=payload,
                                text=True, capture_output=True, cwd=target, env=env)
        assert silent.returncode == 0 and silent.stdout.strip() == "", silent.stderr

        env["NEO_DEVELOPER"] = "alice"
        active = subprocess.run(["python3", ".neo/scripts/neo_hook.py", "pre"], input=payload,
                                text=True, capture_output=True, cwd=target, env=env)
        assert active.returncode == 0, active.stderr
        assert "taken by alice" in json.loads(active.stdout)["systemMessage"]
        assert (target / ".devsync" / "activity-log.json").exists()


def test_non_git_target_is_refused():
    with tempfile.TemporaryDirectory() as tmp:
        result = _install(Path(tmp))
        assert result.returncode == 1 and "not a git repo" in result.stderr


def _bare_remote_with_main(tmp, commit_message):
    """A bare repo whose main branch has one commit. Returns (path, commit sha)."""
    seed = Path(tmp) / "seed"
    seed.mkdir()
    remote = Path(tmp) / "neo-remote.git"
    subprocess.run(["git", "init", "-q", "-b", "main", str(seed)], check=True)
    (seed / "README.md").write_text(commit_message)
    subprocess.run(["git", "-C", str(seed), "add", "."], check=True)
    subprocess.run(["git", "-C", str(seed), "-c", "user.email=t@example.com", "-c", "user.name=t",
                    "commit", "-q", "-m", commit_message], check=True)
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "-C", str(seed), "push", "-q", str(remote), "main"], check=True,
                   capture_output=True)
    sha = subprocess.run(["git", "-C", str(seed), "rev-parse", "HEAD"],
                         capture_output=True, text=True, check=True).stdout.strip()
    return remote, sha


def _run_update_check(target, url, version=None):
    if version is not None:
        (target / ".neo" / "VERSION").write_text(version + "\n")
    env = {**os.environ, "NEO_REPO_URL": str(url)}
    env.pop("NEO_DEVELOPER", None)
    return subprocess.run(["python3", ".neo/scripts/neo_update_check.py"], text=True,
                          capture_output=True, cwd=target, env=env, timeout=60)


def test_update_check_reports_a_newer_main():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "braxis"
        _git_repo(target)
        _install(target)
        remote, main_sha = _bare_remote_with_main(tmp, "first")
        result = _run_update_check(target, remote, version="0" * 40)
        assert result.returncode == 0, result.stderr
        message = json.loads(result.stdout)["systemMessage"]
        assert "update available on main" in message and main_sha[:7] in message


def test_update_check_is_silent_when_up_to_date():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "braxis"
        _git_repo(target)
        _install(target)
        remote, main_sha = _bare_remote_with_main(tmp, "first")
        result = _run_update_check(target, remote, version=main_sha)
        assert result.returncode == 0 and result.stdout.strip() == ""


def test_update_check_is_silent_when_offline():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "braxis"
        _git_repo(target)
        _install(target)
        result = _run_update_check(target, Path(tmp) / "no-such-remote.git", version="0" * 40)
        assert result.returncode == 0 and result.stdout.strip() == ""


def test_update_check_writes_a_daily_cache_in_state_not_in_git():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "braxis"
        _git_repo(target)
        _install(target)
        remote, main_sha = _bare_remote_with_main(tmp, "first")
        _run_update_check(target, remote, version="0" * 40)
        cache = json.loads((target / ".neo_state" / "update_check.json").read_text())
        assert cache["latest"] == main_sha

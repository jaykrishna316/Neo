"""Stale-context detection compares against what the developer read, not against the present."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "scripts" / "neo_hook.py"


def _hook_read(developer, file_path, workdir):
    env = {k: v for k, v in os.environ.items() if k != "NEO_DEVELOPER"}
    env.update({"NEO_DEVELOPER": developer, "PYTHONPATH": str(REPO)})
    payload = json.dumps({"tool_name": "Read", "tool_input": {"file_path": file_path}})
    result = subprocess.run([sys.executable, str(HOOK), "read"], input=payload, text=True,
                            capture_output=True, cwd=workdir, env=env, timeout=120)
    assert result.returncode == 0, result.stderr


def test_staleness_uses_the_read_snapshot():
    with tempfile.TemporaryDirectory() as workdir:
        os.environ["NEO_STATE_DIR"] = str(Path(workdir) / ".neo_state")
        sys.path.insert(0, str(REPO))
        import core.freshness as freshness
        from core.pre_gen_check import check_source_staleness

        freshness._tracker = None
        file_path = str(Path(workdir) / "auth.py")
        Path(file_path).write_text("def authenticate(user):\n    return False\n")

        # bob reads the file, then alice changes it
        _hook_read("bob", file_path, workdir)
        Path(file_path).write_text("def authenticate(user, password):\n    return True\n")
        state, _report = check_source_staleness(file_path=file_path, agent_id="bob", read_time=0.0)
        assert state == "STALE_SOURCE", state

        # carol never read the file, so there is nothing to compare against
        state, report = check_source_staleness(file_path=file_path, agent_id="carol", read_time=0.0)
        assert state == "UNVERIFIABLE", state
        assert "No read recorded" in report["reason"]


def test_no_change_after_read_is_current():
    with tempfile.TemporaryDirectory() as workdir:
        os.environ["NEO_STATE_DIR"] = str(Path(workdir) / ".neo_state")
        sys.path.insert(0, str(REPO))
        import core.freshness as freshness
        from core.pre_gen_check import check_source_staleness

        freshness._tracker = None
        file_path = str(Path(workdir) / "auth.py")
        Path(file_path).write_text("def authenticate(user):\n    return False\n")
        _hook_read("bob", file_path, workdir)
        state, _report = check_source_staleness(file_path=file_path, agent_id="bob", read_time=0.0)
        assert state == "CURRENT", state

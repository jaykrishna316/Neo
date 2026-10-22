"""A developer with a stale context is still a conflict on the file, and must refresh."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SCRIPT = r'''
import json, sys
from core.freshness import record_read
from core.activity_log import log_activity
from core.pre_gen_check import check_for_conflicts
f = "src/auth.py"
record_read("alice", f)
log_activity(developer_id="alice", file_path=f, intent="Add OAuth2 login to authenticate", intent_category="feature")
open(f, "w").write("def authenticate(user, password):\n    return True\n")
risk, msg, _lock = check_for_conflicts(agent_id="bob", file_path=f, intent="Add JWT fallback to authenticate", region=None)
print(json.dumps({"risk": risk.value, "msg": msg}))
'''


def test_stale_developer_is_a_medium_conflict():
    import json

    with tempfile.TemporaryDirectory() as workdir:
        (Path(workdir) / "src").mkdir()
        (Path(workdir) / "src" / "auth.py").write_text("def authenticate(user):\n    return False\n")
        env = {k: v for k, v in os.environ.items() if k not in ("NEO_DEVELOPER",)}
        env.update({
            "PYTHONPATH": str(REPO),
            "NEO_STATE_DIR": str(Path(workdir) / ".neo_state"),
            "NEO_ACTIVITY_LOG_DIR": str(Path(workdir) / ".devsync"),
        })
        result = subprocess.run([sys.executable, "-c", SCRIPT], cwd=workdir, env=env,
                                capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        out = json.loads(result.stdout.strip().splitlines()[-1])
        assert out["risk"] == "MEDIUM", out
        assert "refresh required" in out["msg"], out

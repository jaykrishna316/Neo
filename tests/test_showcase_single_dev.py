"""The single-developer showcase: inherited breakage, fix, stale context, then a change."""

import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
def _sh(args, cwd):
    # Run the copy's script: the script cds to its own repo, so it must be the copy's.
    env = {**os.environ, "PYTHONPATH": str(REPO)}
    env.pop("NEO_DEVELOPER", None)
    return subprocess.run(["bash", str(cwd / "scripts" / "showcase_single_dev.sh"), *args],
                          cwd=cwd, env=env, text=True, capture_output=True, timeout=120)


def _hook(mode, developer, cwd, file_path):
    env = {**os.environ, "PYTHONPATH": str(REPO), "NEO_DEVELOPER": developer}
    payload = json.dumps({"tool_input": {"file_path": file_path}})
    return subprocess.run(["python3", str(REPO / "scripts" / "neo_hook.py"), mode], input=payload,
                          text=True, capture_output=True, cwd=cwd, env=env, timeout=120)


def _message(result):
    if result.returncode == 2:
        return result.stderr
    return json.loads(result.stdout)["systemMessage"] if result.stdout.strip() else ""


def test_single_developer_walks_through_every_check():
    with tempfile.TemporaryDirectory() as tmp:
        # The showcase edits files in the repo, so run it from a copy of the repo.
        work = Path(tmp) / "repo"
        subprocess.run(["cp", "-r", str(REPO), str(work)], check=True)
        auth, payment = "src/auth.py", "test-scenarios/services/payment.py"

        assert _sh(["setup"], work).returncode == 0

        # 1. Intent is set, and the inherited breakage blocks the edit before any lock.
        blocked = _hook("pre", "me", work, auth)
        assert blocked.returncode == 2
        assert "downstream breakage on src/auth.py" in blocked.stderr
        assert "payment.py line 4" in blocked.stderr
        assert "locked by" not in blocked.stderr

        # 2. Fixing the caller takes the lock on payment.py and clears the breakage.
        assert _hook("read", "me", work, payment).returncode == 0
        assert _hook("pre", "me", work, payment).returncode == 0
        (work / payment).write_text("from auth import authenticate\n\n"
                                    "def pay(user, password):\n    return authenticate(user, password)\n")
        fixed = _hook("post", "me", work, payment)
        assert "downstream breakage resolved" in _message(fixed)

        # 3. A teammate changes auth.py after this developer read it: the edit is stale.
        assert _hook("read", "me", work, auth).returncode == 0
        assert _sh(["teammate"], work).returncode == 0
        stale = _hook("pre", "me", work, auth)
        assert stale.returncode == 2 and "changed after you last read it" in stale.stderr

        # 4. Reading again makes the change allowed, and the lock is taken on auth.py.
        assert _hook("read", "me", work, auth).returncode == 0
        allowed = _hook("pre", "me", work, auth)
        assert allowed.returncode == 0
        assert "taken by me" in _message(allowed)

        # 5. The task ends: the lock is released.
        stop = subprocess.run(["python3", str(REPO / "scripts" / "neo_hook.py"), "stop"],
                              input="{}", text=True, capture_output=True, cwd=work,
                              env={**os.environ, "PYTHONPATH": str(REPO), "NEO_DEVELOPER": "me"})
        assert "released by me" in json.loads(stop.stdout)["systemMessage"]

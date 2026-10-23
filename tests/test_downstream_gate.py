"""A breaking signature change that leaves a caller broken blocks edits to the changed file.

Alice changes authenticate(user) to authenticate(user, password) and does not touch
payment.py. Bob may not edit src/auth.py until payment.py matches the new signature.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "scripts" / "neo_hook.py"
sys.path.insert(0, str(REPO))

from core.call_compat import broken_calls  # noqa: E402

OLD_AUTH = "def authenticate(user):\n    return False\n"
NEW_AUTH = "def authenticate(user, password):\n    return password == 'ok'\n"
OLD_PAYMENT = "from auth import authenticate\n\ndef pay(user):\n    return authenticate(user)\n"
FIXED_PAYMENT = ("from auth import authenticate\n\n"
                 "def pay(user, password):\n    return authenticate(user, password)\n")


def test_call_check_flags_missing_and_unknown_arguments():
    new = "def f(a, b, c=1):\n    pass\n"
    importer = "from m import f\nf(1)\nf(1, 2, 3, 4)\nf(1, b=2, d=4)\nf(1, 2, c=3)\n"
    problems = broken_calls(importer, "m", new, {"f"})
    found = {(line, problem) for line, _call, problem in problems}
    assert (2, "is missing 'b'") in found
    assert any(line == 3 and problem.startswith("passes 4 positional") for line, problem in found)
    assert any(line == 4 and problem == "has no parameter 'd'" for line, problem in found)
    assert not any(line == 5 for line, _problem in found)


def test_call_check_accepts_matching_calls():
    new = "def authenticate(user, password):\n    return True\n"
    importer = "import auth\nfrom auth import authenticate\nauthenticate('u', 'p')\nauth.authenticate(user='u', password='p')\n"
    assert broken_calls(importer, "auth", new, {"authenticate"}) == []


def _run(mode, developer, workdir, file_path=None):
    env = {k: v for k, v in os.environ.items() if k not in ("NEO_DEVELOPER", "NEO_INTENT")}
    env.update({"PYTHONPATH": str(REPO), "NEO_DEVELOPER": developer,
                "NEO_STATE_DIR": str(Path(workdir) / ".neo_state"),
                "NEO_ACTIVITY_LOG_DIR": str(Path(workdir) / ".devsync")})
    payload = {"tool_input": {"file_path": str(file_path)}} if file_path else {}
    return subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps(payload),
                          text=True, capture_output=True, cwd=workdir, env=env, timeout=120)


def test_bob_must_fix_the_caller_before_editing_the_changed_file():
    with tempfile.TemporaryDirectory() as workdir:
        auth = Path(workdir) / "src" / "auth.py"
        payment = Path(workdir) / "test-scenarios" / "services" / "payment.py"
        auth.parent.mkdir()
        payment.parent.mkdir(parents=True)
        auth.write_text(OLD_AUTH)
        payment.write_text(OLD_PAYMENT)

        # alice changes the signature and leaves payment.py as it is
        assert _run("read", "alice", workdir, auth).returncode == 0
        assert _run("pre", "alice", workdir, auth).returncode == 0
        auth.write_text(NEW_AUTH)
        post = _run("post", "alice", workdir, auth)
        assert "downstream breakage" in json.loads(post.stdout)["systemMessage"]

        # bob reads both files, then tries to edit auth.py: blocked by the breakage, not the lock
        assert _run("read", "bob", workdir, auth).returncode == 0
        assert _run("read", "bob", workdir, payment).returncode == 0
        blocked = _run("pre", "bob", workdir, auth)
        assert blocked.returncode == 2
        assert "has a downstream breakage" in blocked.stderr
        assert "line 4" in blocked.stderr and "is missing 'password'" in blocked.stderr
        assert "locked by" not in blocked.stderr

        # bob fixes the caller: its edit is allowed and resolves the breakage
        assert _run("pre", "bob", workdir, payment).returncode == 0
        payment.write_text(FIXED_PAYMENT)
        fixed = _run("post", "bob", workdir, payment)
        assert "downstream breakage resolved" in json.loads(fixed.stdout)["systemMessage"]

        # the gate is cleared: bob now reaches the normal lock check on auth.py
        after = _run("pre", "bob", workdir, auth)
        assert after.returncode == 2 and "locked by alice" in after.stderr
        assert "downstream breakage" not in after.stderr

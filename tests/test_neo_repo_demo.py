"""The repo demo: intent, inherited breakage, lock, teammate change, stale context, cleanup.

Runs against a repo with Neo installed by scripts/install_neo.sh, the way a real repo does.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEMO = REPO / "scripts" / "neo_repo_demo.sh"
INSTALL = REPO / "scripts" / "install_neo.sh"


def _run(args, cwd=None, developer=None, stdin=None):
    env = {k: v for k, v in os.environ.items() if k not in ("NEO_DEVELOPER", "PYTHONPATH")}
    if developer:
        env["NEO_DEVELOPER"] = developer
    return subprocess.run(args, cwd=cwd, env=env, input=stdin, text=True, capture_output=True, timeout=120)


def _hook(target, developer, mode, file_path=None):
    payload = json.dumps({"tool_input": {"file_path": file_path}}) if file_path else "{}"
    return _run(["python3", ".neo/scripts/neo_hook.py", mode], cwd=target, developer=developer, stdin=payload)


def _message(result):
    if result.returncode == 2:
        return result.stderr
    return json.loads(result.stdout)["systemMessage"] if result.stdout.strip() else ""


def test_repo_demo_walks_through_every_check():
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "my-repo"
        target.mkdir()
        subprocess.run(["git", "init", "-q", str(target)], check=True)
        assert _run(["bash", str(INSTALL), str(target)]).returncode == 0
        demo = lambda mode: _run(["bash", str(DEMO), str(target), mode])
        pricing, checkout = "neo_demo/pricing.py", "neo_demo/checkout.py"

        setup = demo("setup")
        assert setup.returncode == 0, setup.stderr
        breaks = json.loads((target / ".neo_state" / "breakages.json").read_text())
        assert [b["importer"] for b in breaks] == [checkout]

        # 1. Intent is set, and the inherited breakage blocks the edit before any lock.
        assert _hook(target, "me", "read", pricing).returncode == 0
        blocked = _hook(target, "me", "pre", pricing)
        assert blocked.returncode == 2
        assert "downstream breakage on neo_demo/pricing.py" in blocked.stderr
        assert "checkout.py line 5" in blocked.stderr and "locked by" not in blocked.stderr

        # 2. Fixing the caller takes the lock on checkout.py and clears the breakage.
        assert _hook(target, "me", "read", checkout).returncode == 0
        assert _hook(target, "me", "pre", checkout).returncode == 0
        (target / checkout).write_text("from pricing import price\n\n\n"
                                       "def total(items, tax_rate):\n"
                                       "    return sum(price(item, tax_rate) for item in items)\n")
        fixed = _hook(target, "me", "post", checkout)
        assert "downstream breakage resolved" in _message(fixed)

        # 3. A teammate changes pricing.py after this developer read it: the next edit is stale.
        assert _run(["bash", str(DEMO), str(target), "teammate"]).returncode == 0
        stale = _hook(target, "me", "pre", pricing)
        assert stale.returncode == 2 and "changed after you last read it" in stale.stderr

        # 4. Reading again allows the edit, and the lock is taken on pricing.py.
        assert _hook(target, "me", "read", pricing).returncode == 0
        allowed = _hook(target, "me", "pre", pricing)
        assert allowed.returncode == 0 and "taken by me" in _message(allowed)

        # 5. The task ends: the lock is released.
        stop = _hook(target, "me", "stop")
        assert "released by me" in json.loads(stop.stdout)["systemMessage"]

        # Cleanup removes the demo files and its state.
        assert demo("cleanup").returncode == 0
        assert not (target / "neo_demo").exists()
        assert json.loads((target / ".neo_state" / "breakages.json").read_text()) == []

"""At session start, Neo finds callers that no longer match their function, however they got that way."""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "scripts" / "neo_hook.py"

PRICING_NEW = 'def price(item, tax_rate):\n    return item["cost"] * (1 + tax_rate)\n'
CHECKOUT_OLD = "from pricing import price\n\n\ndef total(items):\n    return sum(price(item) for item in items)\n"
CHECKOUT_FIXED = "from pricing import price\n\n\ndef total(items, tax_rate):\n    return sum(price(item, tax_rate) for item in items)\n"


def _hook(mode, developer, workdir, file_path=None):
    env = {k: v for k, v in os.environ.items() if k not in ("NEO_DEVELOPER", "PYTHONPATH")}
    env.update({"PYTHONPATH": str(REPO), "NEO_DEVELOPER": developer,
                "NEO_STATE_DIR": str(Path(workdir) / ".neo_state"),
                "NEO_ACTIVITY_LOG_DIR": str(Path(workdir) / ".devsync")})
    payload = json.dumps({"tool_input": {"file_path": file_path}} if file_path else {})
    return subprocess.run([sys.executable, str(HOOK), mode], input=payload, text=True,
                          capture_output=True, cwd=workdir, env=env, timeout=120)


def _repo_with_break(workdir):
    (Path(workdir) / "pricing.py").write_text(PRICING_NEW)   # changed by someone earlier
    (Path(workdir) / "checkout.py").write_text(CHECKOUT_OLD)  # never updated


def test_session_start_reports_a_broken_caller_and_blocks_the_changed_file():
    with tempfile.TemporaryDirectory() as workdir:
        _repo_with_break(workdir)
        start = _hook("start", "kevin", workdir)
        assert start.returncode == 0, start.stderr
        out = json.loads(start.stdout)
        assert "checkout.py line 5: price(item) is missing 'tax_rate'" in out["systemMessage"]
        assert "Fix these calls before starting the task" in out["hookSpecificOutput"]["additionalContext"]
        assert out["hookSpecificOutput"]["hookEventName"] == "SessionStart"

        records = json.loads((Path(workdir) / ".neo_state" / "breakages.json").read_text())
        assert [r["importer"] for r in records] == ["checkout.py"]
        assert records[0]["origin"] == "scan"

        blocked = _hook("pre", "kevin", workdir, str(Path(workdir) / "pricing.py"))
        assert blocked.returncode == 2 and "has a downstream breakage" in blocked.stderr and "checkout.py line 5" in blocked.stderr


def test_fixing_the_caller_clears_the_report_and_unblocks_the_file():
    with tempfile.TemporaryDirectory() as workdir:
        _repo_with_break(workdir)
        _hook("start", "kevin", workdir)
        (Path(workdir) / "checkout.py").write_text(CHECKOUT_FIXED)

        clean = _hook("start", "kevin", workdir)
        assert "no broken callers found" in json.loads(clean.stdout)["systemMessage"]
        assert json.loads((Path(workdir) / ".neo_state" / "breakages.json").read_text()) == []

        allowed = _hook("pre", "kevin", workdir, str(Path(workdir) / "pricing.py"))
        assert allowed.returncode == 0


def test_a_repo_with_no_break_reports_nothing_to_fix():
    with tempfile.TemporaryDirectory() as workdir:
        (Path(workdir) / "pricing.py").write_text('def price(item):\n    return item["cost"]\n')
        (Path(workdir) / "checkout.py").write_text(
            "from pricing import price\n\n\ndef total(items):\n    return sum(price(i) for i in items)\n")
        out = json.loads(_hook("start", "kevin", workdir).stdout)
        assert "no broken callers found" in out["systemMessage"]


def test_same_file_names_in_two_folders_do_not_cross_match():
    """code/checkout.py imports code/pricing.py, not neo_demo/pricing.py, so it is not reported."""
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        for folder in ("code", "neo_demo"):
            (root / folder).mkdir()
        (root / "code" / "pricing.py").write_text('def price(item):\n    return item["cost"] * 1.2\n')
        (root / "code" / "checkout.py").write_text(
            "from pricing import price\n\n\ndef total(items):\n    return sum(price(i) for i in items)\n")
        (root / "neo_demo" / "pricing.py").write_text(PRICING_NEW)  # changed, caller left behind
        (root / "neo_demo" / "checkout.py").write_text(CHECKOUT_OLD)

        out = json.loads(_hook("start", "pam", workdir).stdout)
        assert "neo_demo/checkout.py line 5" in out["systemMessage"], out["systemMessage"]
        assert "code/checkout.py" not in out["systemMessage"], out["systemMessage"]

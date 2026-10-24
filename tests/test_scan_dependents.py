"""The dependent scan skips excluded folders without walking into them."""

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))

import neo_hook  # noqa: E402


def test_scan_finds_importers_and_skips_excluded_folders():
    with tempfile.TemporaryDirectory() as workdir:
        root = Path(workdir)
        (root / "src").mkdir()
        (root / "src" / "auth.py").write_text("def authenticate(user):\n    return False\n")
        (root / "app.py").write_text("from auth import authenticate\n")
        (root / ".venv" / "lib").mkdir(parents=True)
        (root / ".venv" / "lib" / "vendored.py").write_text("from auth import authenticate\n")
        (root / "node_modules").mkdir()
        (root / "node_modules" / "x.py").write_text("from auth import authenticate\n")

        cwd = os.getcwd()
        os.chdir(workdir)
        try:
            found = neo_hook.scan_dependents("src/auth.py")
        finally:
            os.chdir(cwd)
        assert found == ["app.py"], found

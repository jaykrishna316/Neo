"""The quick showcase runs end to end and shows each capability."""

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def test_showcase_shows_lock_queue_stale_block_and_breaking_change():
    result = subprocess.run([sys.executable, str(REPO / "scripts" / "neo_demo.py")],
                            capture_output=True, text=True, timeout=300, cwd=REPO)
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert "alice edit attempt -> ALLOWED" in out, out
    assert "bob edit attempt -> BLOCKED: Neo:" in out and "locked by alice" in out, out
    assert "Breaking change in" in out and "payment.py" in out, out
    assert "bob is next in the queue" in out, out
    assert "changed after you last read it" in out, out
    assert "bob edit attempt -> ALLOWED" in out, out

"""A developer waiting for a lock keeps one place in the queue, however often they ask."""

import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

SCRIPT = r'''
import json
from core.lock_manager import LockManager
from core.activity_log import read_log
lm = LockManager()
key = lm._make_lock_key("src/auth.py", None, "file")
first = lm.acquire_lock("src/auth.py", None, "alice", "MEDIUM_CONFLICT")
bob1 = lm.acquire_lock("src/auth.py", None, "bob", "MEDIUM_CONFLICT")
bob2 = lm.acquire_lock("src/auth.py", None, "bob", "MEDIUM_CONFLICT")
bob3 = lm.acquire_lock("src/auth.py", None, "bob", "MEDIUM_CONFLICT")
again = lm.acquire_lock("src/auth.py", None, "alice", "MEDIUM_CONFLICT")
waiting_entries = [e for e in read_log() if e["developer_id"] == "bob" and e.get("lock_state") == "WAITING"]
queue_before = lm._get_queue(key)
released = lm.release_lock("src/auth.py", None, "alice")
print(json.dumps({
    "first": first["success"], "bob_positions": [bob1["queue_position"], bob2["queue_position"], bob3["queue_position"]],
    "alice_again": again["success"], "bob_waiting_entries": len(waiting_entries),
    "queue_before": queue_before, "next": released["next_lock_holder"],
}))
'''


def test_repeat_requests_keep_one_place_and_handoff_works():
    import json

    with tempfile.TemporaryDirectory() as workdir:
        env = {k: v for k, v in os.environ.items()}
        env.update({
            "PYTHONPATH": str(REPO),
            "NEO_ACTIVITY_LOG_DIR": str(Path(workdir) / ".devsync"),
        })
        result = subprocess.run([sys.executable, "-c", SCRIPT], cwd=workdir, env=env,
                                capture_output=True, text=True, timeout=120)
        assert result.returncode == 0, result.stderr
        out = json.loads(result.stdout.strip().splitlines()[-1])
        assert out["first"] is True, out
        assert out["bob_positions"] == [0, 0, 0], out
        assert out["alice_again"] is True, out
        assert out["bob_waiting_entries"] == 1, out
        assert out["queue_before"] == ["bob"], out
        assert out["next"] == "bob", out

"""End-to-end test of the two-developer hand-off workflow.

A declares, B declares (queued), A codes and completes with a summary,
B is notified and must refresh before continuing, B completes,
A is notified with B's summary.

Runs a real neo_server subprocess and two git clones of one bare remote.
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from cli.neo_client import NeoClient, git_diff  # noqa: E402

FILE = "src/auth.py"


def _git(cwd, *args):
    subprocess.run(
        ["git", "-c", "user.email=test@example.com", "-c", "user.name=test", *args],
        cwd=cwd, check=True, capture_output=True, text=True,
    )


def _free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def setup(tmp_path):
    # Bare remote with one file, then two clones: dev-A and dev-B
    remote = tmp_path / "remote.git"
    seed = tmp_path / "seed"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    subprocess.run(["git", "init", "-q", str(seed)], check=True)
    (seed / "src").mkdir()
    (seed / FILE).write_text("def authenticate(user):\n    return False\n")
    _git(seed, "add", ".")
    _git(seed, "commit", "-q", "-m", "initial")
    _git(seed, "branch", "-M", "main")
    _git(seed, "remote", "add", "origin", str(remote))
    _git(seed, "push", "-q", "-u", "origin", "main")
    subprocess.run(["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=remote, check=True)

    dev_a = tmp_path / "dev-a"
    dev_b = tmp_path / "dev-b"
    subprocess.run(["git", "clone", "-q", str(remote), str(dev_a)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(dev_b)], check=True)

    # Server runs from its own directory so .devsync/ is isolated per test
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    port = _free_port()
    env = {**os.environ, "PYTHONPATH": os.pathsep.join(filter(None, [str(REPO_ROOT), os.environ.get("PYTHONPATH")]))}
    env.pop("NEO_API_TOKEN", None)
    proc = subprocess.Popen(
        [sys.executable, "-m", "cli.neo_server", "--port", str(port), "--clear"],
        cwd=server_dir, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            requests.get(f"{url}/api/status", timeout=0.5)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.1)
    else:
        proc.kill()
        pytest.fail("neo_server did not start")

    yield {"url": url, "dev_a": dev_a, "dev_b": dev_b}

    proc.terminate()
    proc.wait(timeout=5)


def test_two_developer_handoff(setup):
    client = NeoClient(setup["url"])
    dev_a, dev_b = setup["dev_a"], setup["dev_b"]

    # 1. Dev-A declares intent and takes the lock
    result = client.declare_intent("alice", FILE, "Add OAuth2 login")
    assert result.get("success"), result

    # 2. Dev-B declares intent and is queued behind A
    result = client.declare_intent("bob", FILE, "Add JWT tokens")
    assert result.get("success"), result

    # 3-4. A codes; B tries to change the file and is blocked by the lock queue
    (dev_a / FILE).write_text(
        "def authenticate(user, password):\n    return check_oauth(user, password)\n"
    )
    _git(dev_a, "commit", "-qam", "Add OAuth2 authenticate")
    _git(dev_a, "push", "-q", "origin", "main")

    lock = client.check_conflicts("bob", FILE, "Add JWT tokens")
    assert lock.get("risk_level") in ("MEDIUM", "HIGH"), lock

    # 5. A completes coding with a summary
    done_a = client.complete_work(
        "alice", FILE, 1, 1, summary="Added OAuth2 login check",
        diff=git_diff(FILE, repo_dir=str(dev_a)),
    )
    assert done_a.get("lock_released") is True
    assert done_a.get("next_developer") == "bob"

    # 6. B is notified that A is done; B's declare is refused until refresh
    inbox_b = client.get_inbox("bob").get("events", [])
    grants = [e for e in inbox_b if e["type"] == "lock_granted"]
    assert len(grants) == 1
    assert grants[0]["from"] == "alice"
    assert grants[0]["refresh_required"] is True
    assert grants[0]["summary"] == "Added OAuth2 login check"

    blocked = client.declare_intent("bob", FILE, "Add JWT tokens")
    assert "Refresh required" in blocked.get("error", ""), blocked

    # B refreshes: pulls A's code and acknowledges the hand-off
    refreshed = client.refresh_context("bob", FILE, repo_dir=str(dev_b))
    assert refreshed.get("refreshed") is True, refreshed
    assert refreshed["summary"] == "Added OAuth2 login check"
    assert "check_oauth" in (dev_b / FILE).read_text()
    assert "check_oauth" in (refreshed.get("diff") or "")

    # With refresh done, B can declare on the file again
    assert client.declare_intent("bob", FILE, "Add JWT tokens").get("success")

    # 7. B codes and completes with a summary
    (dev_b / FILE).write_text(
        "def authenticate(user, password):\n"
        "    return check_oauth(user, password) or check_jwt(user)\n"
    )
    _git(dev_b, "commit", "-qam", "Add JWT fallback")
    _git(dev_b, "push", "-q", "origin", "main")
    done_b = client.complete_work(
        "bob", FILE, 1, 0, summary="Added JWT fallback to authenticate",
        diff=git_diff(FILE, repo_dir=str(dev_b)),
    )
    assert done_b.get("lock_released") is True

    # 8. A is notified that B is done, with B's summary
    inbox_a = client.get_inbox("alice").get("events", [])
    finished = [e for e in inbox_a if e["type"] == "work_completed" and e["from"] == "bob"]
    assert len(finished) == 1
    assert finished[0]["summary"] == "Added JWT fallback to authenticate"
    assert "check_jwt" in (finished[0]["diff"] or "")

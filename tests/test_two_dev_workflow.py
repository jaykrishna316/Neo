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

from cli.neo_client import NeoClient, build_changes_report, git_diff, repo_snapshot  # noqa: E402

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
    dev_a, dev_b = str(setup["dev_a"]), str(setup["dev_b"])

    # 1. A declares intent and takes the lock
    result = client.declare_intent("alice", FILE, "Add OAuth2 login",
                                   snapshot=repo_snapshot(FILE, dev_a))
    assert result.get("success"), result

    # 2. B declares intent, is queued behind A, and builds his context on the original file
    result = client.declare_intent("bob", FILE, "Add JWT tokens",
                                   snapshot=repo_snapshot(FILE, dev_b))
    assert result.get("success"), result

    # 3. A codes, commits, pushes; B's check shows the file is taken
    (setup["dev_a"] / FILE).write_text(
        "def authenticate(user, password):\n    return check_oauth(user, password)\n"
    )
    _git(dev_a, "commit", "-qam", "Add OAuth2 authenticate")
    _git(dev_a, "push", "-q", "origin", "main")
    check = client.check_conflicts("bob", FILE, "Add JWT tokens")
    assert check.get("risk_level") in ("MEDIUM", "HIGH"), check

    # 4. A completes coding, with summary, diff and a snapshot of the final file
    snap_a = repo_snapshot(FILE, dev_a)
    done_a = client.complete_work(
        "alice", FILE, 1, 1, summary="Added OAuth2 login check",
        diff=git_diff(FILE, repo_dir=dev_a), commit=snap_a["commit"], file_hash=snap_a["file_hash"],
    )
    assert done_a.get("lock_released") is True
    assert done_a.get("next_developer") == "bob"

    # 5. B is notified A is done; B's context is validated (expired: file changed since B declared)
    grants = [e for e in client.get_inbox("bob")["events"] if e["type"] == "lock_granted"]
    assert len(grants) == 1
    assert grants[0]["from"] == "alice"
    assert grants[0]["refresh_required"] is True
    assert grants[0]["context_expired"] is True
    assert grants[0]["summary"] == "Added OAuth2 login check"

    # B cannot declare or complete on the file until the context is refreshed
    blocked = client.declare_intent("bob", FILE, "Add JWT tokens", snapshot=repo_snapshot(FILE, dev_b))
    assert "Refresh required" in blocked.get("error", ""), blocked

    # 6. B refreshes: pulls A's version and the server confirms the file matches the reset context
    refreshed = client.refresh_context("bob", FILE, repo_dir=dev_b)
    assert refreshed.get("refreshed") is True, refreshed
    assert refreshed["context_expired"] is True
    assert "check_oauth" in (setup["dev_b"] / FILE).read_text()

    # With the context reset, B can declare again
    result = client.declare_intent("bob", FILE, "Add JWT tokens", snapshot=repo_snapshot(FILE, dev_b))
    assert result.get("success"), result

    # 7. B codes on top of A's version, commits, pushes, and completes with a summary
    (setup["dev_b"] / FILE).write_text(
        "def authenticate(user, password):\n"
        "    return check_oauth(user, password) or check_jwt(user)\n"
    )
    _git(dev_b, "commit", "-qam", "Add JWT fallback")
    _git(dev_b, "push", "-q", "origin", "main")
    snap_b = repo_snapshot(FILE, dev_b)
    done_b = client.complete_work(
        "bob", FILE, 1, 0, summary="Added JWT fallback to authenticate",
        diff=git_diff(FILE, repo_dir=dev_b), commit=snap_b["commit"], file_hash=snap_b["file_hash"],
    )
    assert done_b.get("lock_released") is True

    # 8. A is notified B submitted updates on top of A's, with B's summary and diff
    finished = [e for e in client.get_inbox("alice")["events"]
                if e["type"] == "work_completed" and e["from"] == "bob"]
    assert len(finished) == 1
    assert "on top of your changes" in finished[0]["message"]
    assert finished[0]["summary"] == "Added JWT fallback to authenticate"
    assert "check_jwt" in (finished[0]["diff"] or "")

    # 9. Collective changes: overall diff from the base, with each developer attributed
    session = client.get_file_session(FILE)["session"]
    assert [c["developer"] for c in session["contributions"]] == ["alice", "bob"]
    report = build_changes_report(session, FILE, repo_dir=dev_a)
    assert "1. alice: Added OAuth2 login check" in report
    assert "2. bob: Added JWT fallback to authenticate" in report
    assert "+    return check_oauth(user, password) or check_jwt(user)" in report  # overall result
    assert "+    return check_oauth(user, password)\n" in report                   # alice's step

#!/usr/bin/env python3
"""Quick showcase of Neo with two developers, run against a scratch project.

It sends the same hook events a Claude Code session sends (prompt, read, edit, stop),
so it shows what Neo does. It does not show what a model decides to do.

  python3 scripts/neo_demo.py
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK = REPO / "scripts" / "neo_hook.py"


class Session:
    def __init__(self, name, workdir):
        self.name = name
        self.workdir = workdir
        self.env = {k: v for k, v in os.environ.items() if k not in ("NEO_DEVELOPER", "NEO_INTENT")}
        self.env.update({
            "PYTHONPATH": str(REPO),
            "NEO_DEVELOPER": name,
            "NEO_STATE_DIR": str(Path(workdir) / ".neo_state"),
            "NEO_ACTIVITY_LOG_DIR": str(Path(workdir) / ".devsync"),
        })

    def send(self, mode, payload=None):
        return subprocess.run([sys.executable, str(HOOK), mode], input=json.dumps(payload or {}),
                              text=True, capture_output=True, cwd=self.workdir, env=self.env, timeout=120)


def say(text):
    print(text, flush=True)


def outcome(result):
    if result.returncode == 2:
        return "BLOCKED: " + result.stderr.strip()
    shown = system_message(result)
    if shown:
        return "ALLOWED: " + shown
    return "ALLOWED"


def system_message(result):
    """The steps Neo showed in the terminal for this hook call."""
    if not result.stdout.strip():
        return ""
    data = json.loads(result.stdout)
    return data.get("systemMessage", "").replace("\n", " | ")


def edit_payload(path):
    return {"tool_name": "Edit", "tool_input": {"file_path": str(path)}}


def main():
    started = time.time()
    with tempfile.TemporaryDirectory() as workdir:
        auth = Path(workdir) / "src" / "auth.py"
        auth.parent.mkdir()
        auth.write_text("def authenticate(user):\n    return False\n")
        payment = Path(workdir) / "payment.py"
        payment.write_text(
            "from auth import authenticate\n\ndef pay(user):\n    return authenticate(user)\n")
        alice, bob = Session("alice", workdir), Session("bob", workdir)

        say("\n1. alice: 'Change authenticate() to require a password argument'")
        alice.send("prompt", {"prompt": "Change authenticate() to require a password argument"})
        alice.send("read", {"tool_input": {"file_path": str(auth)}})
        say(f"   alice edit attempt -> {outcome(alice.send('pre', edit_payload(auth)))}")

        say("\n2. bob: 'Add a JWT fallback to authenticate()'")
        bob.send("prompt", {"prompt": "Add a JWT fallback to authenticate()"})
        bob.send("read", {"tool_input": {"file_path": str(auth)}})
        say(f"   bob edit attempt -> {outcome(bob.send('pre', edit_payload(auth)))}")

        say("\n3. alice makes the breaking change")
        auth.write_text("def authenticate(user, password):\n    return True\n")
        say(f"   alice edit completed -> {outcome(alice.send('post', edit_payload(auth)))}")

        say("\n4. alice's task ends")
        stop = alice.send("stop")
        say(f"   released -> {system_message(stop) or 'nothing to release'}")

        say("\n5. bob retries without re-reading")
        say(f"   bob edit attempt -> {outcome(bob.send('pre', edit_payload(auth)))}")

        say("\n6. bob re-reads, then retries: blocked until payment.py matches the new signature")
        bob.send("read", {"tool_input": {"file_path": str(auth)}})
        say(f"   bob edit attempt -> {outcome(bob.send('pre', edit_payload(auth)))}")
        bob.send("read", {"tool_input": {"file_path": str(payment)}})
        say(f"   bob fixes payment.py -> {outcome(bob.send('pre', edit_payload(payment)))}")
        payment.write_text("from auth import authenticate\n\ndef pay(user, password):\n"
                           "    return authenticate(user, password)\n")
        say(f"   payment.py edit completed -> {outcome(bob.send('post', edit_payload(payment)))}")
        say(f"   bob edit attempt -> {outcome(bob.send('pre', edit_payload(auth)))}")
        auth.write_text("def authenticate(user, password):\n    return password == 'ok'\n")
        bob.send("post", edit_payload(auth))
        bob.send("stop")

        say(f"\nDone in {time.time() - started:.1f} seconds.")
        say("Activity log:")
        for line in (Path(workdir) / ".devsync" / "activity-log.json").read_text().splitlines():
            entry = json.loads(line)
            say(f"   {entry['developer_id']:6} {entry['intent'][:70]}")


if __name__ == "__main__":
    sys.exit(main())

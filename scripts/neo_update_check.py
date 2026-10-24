#!/usr/bin/env python3
"""Tell the session when a newer Neo is on main. Changes no files and never blocks.

Runs as a SessionStart hook in a repo that has Neo installed. It compares the
installed version (.neo/VERSION) with the latest commit on main, and checks at
most once a day. Network errors are ignored.
"""

import json
import os
import subprocess
import time
from pathlib import Path

DEFAULT_URL = "https://github.com/jaykrishna316/Neo"
CHECK_EVERY_SECONDS = 24 * 3600


def _state_path():
    return Path(os.environ.get("NEO_STATE_DIR", ".neo_state")) / "update_check.json"


def _installed():
    try:
        return (Path(__file__).resolve().parent.parent / "VERSION").read_text().strip()
    except OSError:
        return ""


def _latest_on_main(url):
    result = subprocess.run(["git", "ls-remote", url, "refs/heads/main"],
                            capture_output=True, text=True, timeout=5)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return result.stdout.split()[0]


def main():
    installed = _installed()
    if not installed or installed == "unknown":
        return 0

    url = os.environ.get("NEO_REPO_URL", DEFAULT_URL)
    state = _state_path()
    try:
        cached = json.loads(state.read_text())
    except (OSError, ValueError):
        cached = {}

    if cached.get("url") == url and time.time() - cached.get("checked_at", 0) < CHECK_EVERY_SECONDS:
        latest = cached.get("latest")
    else:
        try:
            latest = _latest_on_main(url)
        except (OSError, subprocess.SubprocessError):
            latest = None
        if latest:
            state.parent.mkdir(parents=True, exist_ok=True)
            state.write_text(json.dumps({"url": url, "checked_at": time.time(), "latest": latest}))

    if latest and latest != installed:
        print(json.dumps({"systemMessage": (
            f"Neo: update available on main ({installed[:7]} → {latest[:7]}). "
            "Re-run the Neo install prompt to update this repo.")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

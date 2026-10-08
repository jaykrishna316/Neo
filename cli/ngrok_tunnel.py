#!/usr/bin/env python3
"""Expose the local Neo server through an ngrok tunnel.

Lets remote developers reach the coordination server at a public https URL
without any changes on their side beyond setting the URL and token.

Requires the `ngrok` CLI on PATH (https://ngrok.com/download) and an
authtoken configured once with `ngrok config add-authtoken <token>`.
"""

import json
import shutil
import subprocess
import time
import urllib.request
from typing import Optional, Tuple

# ngrok's local inspection API; it reports the public URL of running tunnels
NGROK_API_URL = 'http://127.0.0.1:4040/api/tunnels'


class NgrokError(RuntimeError):
    """Raised when the ngrok tunnel cannot be started"""


def _public_https_url() -> Optional[str]:
    """Return the https public URL of the first tunnel, or None if not ready"""
    try:
        with urllib.request.urlopen(NGROK_API_URL, timeout=1) as resp:
            tunnels = json.loads(resp.read().decode('utf-8')).get('tunnels', [])
    except (OSError, ValueError):
        return None

    for tunnel in tunnels:
        url = tunnel.get('public_url', '')
        if url.startswith('https://'):
            return url
    return None


def start_ngrok_tunnel(port: int, timeout: float = 15.0) -> Tuple[subprocess.Popen, str]:
    """Start `ngrok http <port>` and wait for its public URL.

    Returns:
        (process, public_url). Caller must call stop_ngrok_tunnel(process).

    Raises:
        NgrokError: if the ngrok CLI is missing or no tunnel comes up in time.
    """
    if shutil.which('ngrok') is None:
        raise NgrokError(
            "ngrok not found on PATH. Install it from https://ngrok.com/download "
            "and run 'ngrok config add-authtoken <your-token>' once."
        )

    proc = subprocess.Popen(
        ['ngrok', 'http', str(port), '--log=stdout', '--log-format=json'],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise NgrokError(
                f"ngrok exited with code {proc.returncode}. "
                f"Check that your authtoken is configured and port {port} is free."
            )
        url = _public_https_url()
        if url:
            return proc, url
        time.sleep(0.3)

    stop_ngrok_tunnel(proc)
    raise NgrokError(f"ngrok did not report a public URL within {timeout:.0f}s")


def stop_ngrok_tunnel(proc: subprocess.Popen) -> None:
    """Terminate the ngrok process started by start_ngrok_tunnel"""
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()

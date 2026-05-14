"""Cross-platform Chromium browser launcher for CDP connections.

Auto-detects installed browsers, launches with --remote-debugging-port,
and waits for the CDP endpoint to become ready.

Usage:
    from .launcher import ensure_cdp, is_cdp_available

    if not is_cdp_available():
        ensure_cdp()          # auto-launch
    cdp = CDPManager()
    cdp.connect()

Env vars (optional):
    DOUBAO_CDP_PORT     — CDP port (default: 9222)
    DOUBAO_BROWSER_CMD  — custom browser command or full path
"""

import subprocess
import time
import json
import os
import sys
import shutil
from urllib.request import urlopen, Request
from urllib.error import URLError

from .config import CDP_PORT, BROWSER_CMD, ConnectionError


# ── Browser detection (per-platform) ─────────────────────────

def _browser_candidates():
    """Return ordered list of (name, executable) to try.

    Uses DOUBAO_BROWSER_CMD env var if set, otherwise auto-detects.
    """
    if BROWSER_CMD:
        return [("custom", BROWSER_CMD)]

    if sys.platform == "win32":
        return [
            ("edge",   r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
            ("edge",   r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
            ("chrome", r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            ("chrome", r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            ("chromium", r"C:\Program Files\Chromium\Application\chrome.exe"),
        ]
    elif sys.platform == "darwin":
        return [
            ("chrome",   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ("edge",     "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"),
            ("brave",    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"),
            ("chromium", "/Applications/Chromium.app/Contents/MacOS/Chromium"),
        ]
    else:  # linux
        candidates = []
        for name in ("google-chrome", "google-chrome-stable", "chromium",
                      "chromium-browser", "microsoft-edge", "microsoft-edge-stable",
                      "brave-browser", "brave"):
            if shutil.which(name):
                candidates.append((name.split("-")[-1], name))
        if not candidates:
            candidates.append(("chromium", "chromium-browser"))  # fallback for error msg
        return candidates


def find_browser():
    """Find the first available Chromium browser executable.

    Returns (name, path) or raises ConnectionError.
    """
    for name, exe in _browser_candidates():
        if os.path.exists(exe) or shutil.which(exe):
            return name, exe
    raise ConnectionError(
        "No Chromium browser found. Set DOUBAO_BROWSER_CMD env var "
        "to your browser path, or install Chrome/Edge/Chromium."
    )


# ── CDP health check ────────────────────────────────────────

def is_cdp_available(port=CDP_PORT, timeout=3):
    """Check if a Chromium browser with CDP is reachable on localhost:port."""
    try:
        req = Request(f"http://localhost:{port}/json/version")
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
            return "Browser" in data
    except Exception:
        return False


# ── Browser launch ──────────────────────────────────────────

def launch_browser(port=CDP_PORT, user_data_dir=None, headless=False):
    """Launch a Chromium browser with --remote-debugging-port.

    Finds the first available browser automatically.
    Returns True if CDP becomes ready within the timeout.
    """
    try:
        name, exe = find_browser()
    except ConnectionError:
        return False

    if user_data_dir is None:
        user_data_dir = os.path.join(
            os.path.expanduser("~"), ".doubaocli", "browser_profile"
        )
    os.makedirs(user_data_dir, exist_ok=True)

    args = [
        exe,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={user_data_dir}",
        "--no-first-run",
        "--no-default-browser-check",
    ]
    if headless:
        args.append("--headless=new")

    try:
        subprocess.Popen(
            args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        raise ConnectionError(
            f"Failed to launch {name} ({exe}): {e}"
        ) from e

    # Wait for CDP to become ready
    for i in range(30):
        time.sleep(1)
        if is_cdp_available(port, timeout=2):
            return True

    raise ConnectionError(
        f"Browser launched but CDP not ready on port {port} after 30s"
    )


def ensure_cdp(port=CDP_PORT, max_retries=2):
    """Ensure CDP is available; launch browser automatically if not.

    Returns True if CDP is ready (either was already running or launched ok).
    """
    if is_cdp_available(port):
        return True

    for attempt in range(max_retries + 1):
        try:
            launch_browser(port=port)
            if is_cdp_available(port):
                return True
        except ConnectionError as e:
            if attempt >= max_retries:
                raise
    return False

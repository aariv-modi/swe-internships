"""Hand postings to your regular Chrome, where an autofill extension such as Jobright Autofill runs.

Extensions can't run in the window `apply open` drives: Playwright launches a clean Chrome with
extensions disabled, and Chrome 137+ ignores --load-extension in branded builds. So for extension
autofill the posting opens in your everyday Chrome profile instead, and the tool only keeps the
queue and records the outcome.
"""
import shutil
import subprocess
import webbrowser
from pathlib import Path

from . import queue
from .fill import FORBIDS_TOOLS_RE

MODES = ("hybrid", "jobright", "builtin")
DEFAULT_CHROME = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
]


def route(url: str, mode: str) -> str:
    """'builtin' (our pre-fill window) or 'chrome' (your regular Chrome + extension)."""
    if mode == "builtin":
        return "builtin"
    if mode == "jobright":
        return "chrome"
    return "builtin" if queue.autofill_supported(url) else "chrome"   # hybrid


def forbids_tools(url: str):
    """True/False if the application page forbids tool- or AI-completed applications; None if it
    can't be checked (Workday and most other systems put the form behind a sign-in)."""
    if not queue.autofill_supported(url):
        return None
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(channel="chrome", headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            text = page.inner_text("body")
            browser.close()
    except Exception:
        return None
    return bool(FORBIDS_TOOLS_RE.search(text))


def open_in_chrome(url: str, settings: dict) -> str:
    """Open url in the user's everyday Chrome profile; returns how it was opened."""
    configured = settings.get("chrome_path")
    candidates = [Path(configured)] if configured else DEFAULT_CHROME
    exe = next((c for c in candidates if c.is_file()), None) or (shutil.which("chrome") and Path(shutil.which("chrome")))
    if exe:
        args = [str(exe)]
        if settings.get("chrome_profile"):
            args.append(f"--profile-directory={settings['chrome_profile']}")
        subprocess.Popen(args + [url])
        return f"Chrome ({settings.get('chrome_profile') or 'last used profile'})"
    webbrowser.open(url)
    return "your default browser"

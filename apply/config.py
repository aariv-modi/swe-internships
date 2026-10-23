"""Where personal data lives: outside the repo, so it can never be committed to the public list."""
import json
import os
import shutil
import tomllib
from pathlib import Path

# SWE_INTERNSHIPS_HOME lets tests use a throwaway folder (faking USERPROFILE breaks Chrome's launch).
HOME = Path(os.environ.get("SWE_INTERNSHIPS_HOME") or Path.home() / ".swe-internships")
PROFILE = HOME / "profile.toml"
STATE = HOME / "state.json"
COOKIES = HOME / "browser_state.json"   # cookies/local storage, so sign-ins survive between runs
TEMPLATE = Path(__file__).with_name("profile.example.toml")
LISTINGS_URL = "https://raw.githubusercontent.com/aariv-modi/swe-internships/main/data/listings.json"


def init() -> Path:
    HOME.mkdir(parents=True, exist_ok=True)
    if not PROFILE.exists():
        shutil.copy(TEMPLATE, PROFILE)
    return PROFILE


def load_profile() -> dict:
    if not PROFILE.exists():
        raise SystemExit(f"No profile yet. Run `python -m apply init`, then fill in {PROFILE}")
    return tomllib.loads(PROFILE.read_text(encoding="utf-8"))


def load_state() -> dict:
    return json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}


def save_state(state: dict) -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(state, indent=1), encoding="utf-8")

"""Rank open listings by fit with the profile."""
import json
import re
from datetime import date
from pathlib import Path

import requests

from scraper.render import _dedupe_key

from . import config

LOCAL_LISTINGS = Path(__file__).resolve().parent.parent / "data" / "listings.json"
AUTOFILL = ("greenhouse.io", "lever.co", "ashbyhq.com")


def load_listings(prefer_local: bool = False) -> dict:
    """The published list from GitHub (always current); the local copy as a fallback."""
    if not prefer_local:
        try:
            return requests.get(config.LISTINGS_URL, timeout=60).json()
        except (requests.RequestException, ValueError):
            pass
    return json.loads(LOCAL_LISTINGS.read_text(encoding="utf-8"))


def autofill_supported(url: str) -> bool:
    return any(h in url for h in AUTOFILL)


def _age_days(rec) -> int:
    d = rec.get("posted_at") or rec["first_seen"][:10]
    try:
        return max((date.today() - date.fromisoformat(d[:10])).days, 0)
    except ValueError:
        return 999


def score(rec, prefs) -> float | None:
    """Higher is better; None means filtered out."""
    title, company = rec["title"], rec["company"]
    if company.lower() in {c.lower() for c in prefs.get("exclude_companies", [])}:
        return None
    s = 0.0
    wanted = [t.lower() for t in prefs.get("terms", [])]
    if wanted:
        have = [t.lower() for t in rec.get("terms", [])]
        if have and not any(w in have for w in wanted):
            return None          # a stated term you didn't ask for
        s += 3 if have else 0    # unstated terms stay in, ranked below confirmed matches
    places = prefs.get("locations", [])
    if places:
        locs = " ".join(rec["locations"]).lower()
        if not any(re.search(rf"\b{re.escape(p.lower())}\b", locs) for p in places):
            return None
        s += 2
    s += sum(1 for w in prefs.get("interests", []) if w.lower() in title.lower())
    s += 1 if autofill_supported(rec["url"]) else 0
    s += max(0.0, 2 - _age_days(rec) / 7)   # fresh postings first; applying early matters
    return s


def build(profile, state, prefer_local=False, limit=25):
    prefs = profile.get("queue", {})
    out = []
    for lid, rec in load_listings(prefer_local).items():
        if not rec.get("active") or lid in state:
            continue
        s = score(rec, prefs)
        if s is not None:
            out.append((s, lid, rec))
    out.sort(key=lambda x: (-x[0], x[2]["company"]))
    # the same requisition can appear on several boards (see scraper.render.dedupe)
    seen, unique = set(), []
    for item in out:
        r = item[2]
        keys = {_dedupe_key(r), (r["company"].lower(), r["title"].lower(), tuple(sorted(r["locations"])))}
        if not keys & seen:
            seen |= keys
            unique.append(item)
    return unique[:limit]

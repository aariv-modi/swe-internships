"""Listing state: what's open, when it was first seen, when it closed."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

LISTINGS_PATH = Path(__file__).resolve().parent.parent / "data" / "listings.json"
KEEP_CLOSED_DAYS = 60


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load() -> dict:
    if LISTINGS_PATH.exists():
        return json.loads(LISTINGS_PATH.read_text(encoding="utf-8"))
    return {}


def save(listings: dict) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=KEEP_CLOSED_DAYS)).isoformat()
    kept = {k: v for k, v in listings.items() if v["active"] or (v.get("closed_at") or "") > cutoff}
    LISTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    LISTINGS_PATH.write_text(json.dumps(dict(sorted(kept.items())), indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8")


def apply_board(listings: dict, board_id: str, company: str, matches: list[dict], ts: str) -> int:
    """Record one successfully read board. Returns the number of new listings."""
    new = 0
    current = set()
    for job in matches:
        lid = f"{board_id}:{job['job_id']}"
        current.add(lid)
        rec = listings.get(lid)
        if rec is None:
            new += 1
            rec = listings[lid] = {"first_seen": ts}
        rec.update({
            "board": board_id,
            "company": company,
            "title": job["title"],
            "locations": job["locations"],
            "terms": job["terms"],
            "url": job["url"],
            "posted_at": job.get("posted_at") or rec.get("posted_at"),
            "last_seen": ts,
            "active": True,
            "closed_at": None,
        })
    for lid, rec in listings.items():
        if rec.get("board") == board_id and rec["active"] and lid not in current:
            rec["active"] = False
            rec["closed_at"] = ts
    return new

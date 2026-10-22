"""Measure recall against Simplify's list, and explain every miss.

Target set: Simplify listings that are active, in the Software category, and have a US location.
Each miss gets a reason, which tells us what to fix next:
  unsupported_ats   - the job is on an ATS we have no connector for yet
  board_unknown     - supported ATS, but the board isn't in our registry
  board_unreadable  - board is known but couldn't be fetched this run
  not_returned      - board was read but the connector didn't return this job (e.g. Workday search)
  filtered          - the job was fetched but our classifier rejected it (reason attached)
"""
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import requests

from . import classify, registry

SIMPLIFY_URL = registry.LISTING_SOURCES[0]
MISSES_PATH = Path(__file__).resolve().parent.parent / "data" / "scorecard_misses.json"
UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
GH_ID_RE = re.compile(r"(?:gh_jid=|greenhouse\.io/[\w-]+/jobs/)(\d+)")
WD_RE = re.compile(r"([\w-]+)\.wd\d+\.myworkdayjobs\.com/.*?/job/(.+)$", re.I)


def job_key(url: str):
    u = url.split("#")[0]
    if m := WD_RE.search(u.split("?")[0]):
        segs = [p for p in m[2].split("/") if p and p.lower() not in ("apply", "applymanually", "autofillwithresume")]
        return f"wd:{m[1].lower()}:{segs[-1].lower()}" if segs else None
    if m := GH_ID_RE.search(u):
        return f"gh:{m[1]}"
    if m := UUID_RE.search(u.lower()):
        return f"id:{m[0]}"
    # Other systems: (host, numeric or short id) taken from their canonical job paths.
    host = urlparse(u).netloc.lower()
    for pattern in (r"\.icims\.com/jobs/(\d+)", r"/hcmUI/CandidateExperience/.*/job/(\d+)",
                    r"smartrecruiters\.com/[\w-]+/(\d+)", r"/job/[^?]+/(\d+)/?(?:\?|$)",
                    r"lifeattiktok\.com/search/(\d+)"):
        if m := re.search(pattern, u, re.I):
            return f"{host}:{m[1]}"
    # JazzHR jobs are served on company domains too (career.example.com/apply/<code>)
    if m := re.search(r"/apply/([A-Za-z0-9]{10})(?:/|$)", u):
        return f"jazz:{m[1]}"
    return None


STALE_TEXT_RE = re.compile(r"no longer (available|accepting|open|posted)|position has been filled|"
                           r"job (is|has been) closed|this job is expired", re.I)


def is_stale(url: str) -> bool:
    """True if a listing Simplify still shows as open is gone from the company's job board."""
    board = registry.board_from_url(url)
    if board and board[0] == "workday":  # Workday pages are a JS shell; ask the API instead
        from .ats import workday
        return workday.is_open(board[2], url) is False
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    except requests.RequestException:
        return False
    return r.status_code in (404, 410) or bool(STALE_TEXT_RE.search(r.text[:200000]))


def compute(listings: dict, seen_jobs: dict, read_boards: set, reg: dict, simplify=None):
    """seen_jobs: job_key -> classifier verdict ('ok' or a rejection reason) for every job
    fetched this run."""
    if simplify is None:
        simplify = requests.get(SIMPLIFY_URL, timeout=120).json()
    ours = {job_key(r["url"]) for r in listings.values() if r["active"]}
    target = [x for x in simplify
              if x.get("active") and x.get("is_visible", True)
              and x.get("category") in ("Software", "Software Engineering")
              and classify.us_status(x.get("locations") or []) is True]
    reasons = Counter()
    misses = []
    supported_total = supported_hit = hit = 0
    for x in target:
        key = job_key(x["url"])
        board = registry.board_from_url(x["url"])
        supported = board is not None
        supported_total += supported
        if key and key in ours:
            hit += 1
            supported_hit += supported
            continue
        if not supported:
            reason = "unsupported_ats"
        else:
            rid = f"{board[0]}:{board[1]}"
            if rid not in reg:
                reason = "board_unknown"
            elif rid not in read_boards:
                reason = "board_unreadable"
            elif key not in seen_jobs:
                reason = "stale_on_simplify" if is_stale(x["url"]) else "not_returned"
            elif seen_jobs[key] == "ok":
                reason = "deduplicated_or_stale"
            else:
                reason = f"filtered:{seen_jobs[key]}"
        reasons[reason] += 1
        misses.append({"reason": reason, "company": x["company_name"], "title": x["title"],
                       "locations": x.get("locations"), "url": x["url"]})
    simplify_keys = {job_key(x["url"]) for x in simplify}
    only_ours = sum(1 for r in listings.values() if r["active"] and job_key(r["url"]) not in simplify_keys)
    MISSES_PATH.write_text(json.dumps(sorted(misses, key=lambda m: m["reason"]), indent=1,
                                      ensure_ascii=False) + "\n", encoding="utf-8")
    stats = {
        "target": len(target), "hit": hit, "supported_total": supported_total,
        "supported_hit": supported_hit, "only_ours": only_ours, "reasons": dict(reasons),
        "stale": reasons.get("stale_on_simplify", 0),
    }
    return stats


def markdown(stats) -> str:
    pct = lambda a, b: f"{100 * a / b:.0f}%" if b else "n/a"
    open_supported = stats["supported_total"] - stats.get("stale", 0)
    return (
        "<details><summary><b>Scorecard vs. SimplifyJobs</b> "
        f"(recall on still-open postings on supported job boards: "
        f"{pct(stats['supported_hit'], open_supported)})</summary>\n\n"
        f"- Simplify's open US software internships: **{stats['target']}**; also on this list: "
        f"**{stats['hit']}** ({pct(stats['hit'], stats['target'])})\n"
        f"- On job systems this scraper supports: "
        f"**{stats['supported_hit']} / {stats['supported_total']}** "
        f"({pct(stats['supported_hit'], stats['supported_total'])}); excluding "
        f"{stats.get('stale', 0)} Simplify listings already closed on the company's own board: "
        f"**{pct(stats['supported_hit'], open_supported)}**\n"
        f"- Open roles here that Simplify doesn't list: **{stats['only_ours']}**\n"
        f"- Misses by reason: {', '.join(f'{k} {v}' for k, v in sorted(stats['reasons'].items()))}\n"
        "\n</details>"
    )

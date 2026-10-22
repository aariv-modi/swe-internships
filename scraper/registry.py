"""Discover company job boards from community internship lists.

Only board identifiers (which ATS a company uses, and its board/tenant name) are taken from
these sources. Listings themselves are always re-fetched from the company's own ATS.
"""
import json
import re
from pathlib import Path
from urllib.parse import unquote, parse_qs, urlparse

import requests

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "data" / "companies.json"

# Structured listing files (JSON arrays with company_name + url).
LISTING_SOURCES = [
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/SimplifyJobs/New-Grad-Positions/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/vanshb03/Summer2027-Internships/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/vanshb03/New-Grad-2027/dev/.github/scripts/listings.json",
]
# Plain READMEs: every link in them is scanned for ATS boards.
README_SOURCES = [
    "https://raw.githubusercontent.com/speedyapply/2027-SWE-College-Jobs/main/README.md",
    "https://raw.githubusercontent.com/zapplyjobs/Internships-2027/main/README.md",
]

WORKDAY_RE = re.compile(
    r"https?://(?P<host>[\w-]+\.wd\d+\.myworkdayjobs\.com)/(?:[a-z]{2}-[a-z]{2}/)?(?P<site>[^/?#]+)",
    re.I)
GREENHOUSE_RE = re.compile(
    r"https?://(?:job-boards|boards)(?P<eu>\.eu)?\.greenhouse\.io/(?:embed/job_(?:app|board)\?for=)?(?P<board>[\w-]+)",
    re.I)
LEVER_RE = re.compile(r"https?://jobs\.(?P<eu>eu\.)?lever\.co/(?P<board>[^/?#]+)", re.I)
ASHBY_RE = re.compile(r"https?://jobs\.ashbyhq\.com/(?P<board>[^/?#]+)", re.I)
URL_RE = re.compile(r"https?://[^\s)\"'<>\]]+")

NOT_BOARDS = {"embed", "v1", "jobs", "api", "job_app", "job_board"}


def board_from_url(url: str):
    """Return (ats, key, params) for an ATS job URL, or None."""
    if m := WORKDAY_RE.match(url):
        host, site = m["host"].lower(), m["site"]
        if site.lower() in ("wday", "job"):
            return None
        tenant = host.split(".")[0]
        return "workday", f"{host}/{site}", {"host": host, "tenant": tenant, "site": site}
    if m := GREENHOUSE_RE.match(url):
        board = m["board"].lower()
        if board in NOT_BOARDS:
            q = parse_qs(urlparse(url).query).get("for")
            board = q[0].lower() if q else None
        if board and board not in NOT_BOARDS:
            if m["eu"]:
                return "greenhouse", f"eu/{board}", {"board": board, "eu": True}
            return "greenhouse", board, {"board": board}
        return None
    if m := LEVER_RE.match(url):
        board = m["board"].lower()
        return "lever", board, {"board": board, "eu": bool(m["eu"])}
    if m := ASHBY_RE.match(url):
        board = unquote(m["board"]).lower()
        if board not in NOT_BOARDS:
            return "ashby", board, {"board": board}
    return None


def _fetch(url: str):
    try:
        r = requests.get(url, timeout=60)
        return r.text if r.status_code == 200 else None
    except requests.RequestException:
        return None


def load() -> dict:
    if REGISTRY_PATH.exists():
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {}


def save(reg: dict) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    ordered = dict(sorted(reg.items()))
    REGISTRY_PATH.write_text(json.dumps(ordered, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def add(reg: dict, url: str, company: str | None, source: str) -> bool:
    found = board_from_url(url)
    if not found:
        return False
    ats, key, params = found
    rid = f"{ats}:{key}"
    entry = reg.get(rid)
    if entry is None:
        reg[rid] = {"ats": ats, "company": company or params.get("board") or params.get("tenant"),
                    "params": params, "sources": [source]}
        return True
    if company and entry["company"] in (params.get("board"), params.get("tenant")):
        entry["company"] = company  # upgrade a slug placeholder to a real name
    if source not in entry["sources"]:
        entry["sources"].append(source)
    return False


def discover(reg: dict | None = None) -> dict:
    reg = load() if reg is None else reg
    for src in LISTING_SOURCES:
        text = _fetch(src)
        if not text:
            print(f"  skip (unavailable): {src}")
            continue
        name = "/".join(src.split("/")[3:5])
        new = sum(add(reg, row.get("url", ""), row.get("company_name"), name)
                  for row in json.loads(text))
        print(f"  {name}: +{new} boards")
    for src in README_SOURCES:
        text = _fetch(src)
        if not text:
            print(f"  skip (unavailable): {src}")
            continue
        name = "/".join(src.split("/")[3:5])
        new = sum(add(reg, u, None, name) for u in URL_RE.findall(text))
        print(f"  {name}: +{new} boards")
    return reg

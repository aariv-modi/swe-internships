"""Render README.md from listing state."""
import re
from datetime import date, datetime
from pathlib import Path

README_PATH = Path(__file__).resolve().parent.parent / "README.md"
START, END = "<!-- LISTINGS:START -->", "<!-- LISTINGS:END -->"

HEADER = """# US Software Engineering Internships

Every US software-engineering internship (all seasons) that companies post on Workday, Greenhouse,
Lever, Ashby, iCIMS, Oracle Cloud, SmartRecruiters, SuccessFactors, JazzHR and TikTok's careers site,
read directly from the company's own job board and refreshed automatically.

- **Scope:** software / SWE / SDE / developer, full-stack, mobile, web, DevOps/SRE, platform and
  infrastructure, embedded software, ML/AI/data *engineering*. Not data science, research science,
  PM, design, IT support, hardware or quant trading.
- **Completeness is measured, not claimed:** see the scorecard below.
- Postings disappear from this list when the company removes them from its job board.
- Applying: [APPLY.md](APPLY.md) describes a local review queue that pre-fills Greenhouse, Lever and
  Ashby forms and stops before Submit.

"""


def _cell(s: str) -> str:
    return s.replace("|", "\\|").replace("\n", " ").strip()


def _age(rec, today: date) -> str:
    d = rec.get("posted_at") or rec["first_seen"][:10]
    try:
        days = (today - date.fromisoformat(d[:10])).days
    except ValueError:
        return ""
    return f"{max(days, 0)}d"


def _locations(locs):
    locs = [l.replace("\n", " ") for l in locs]
    if len(locs) <= 3:
        return "<br>".join(_cell(l) for l in locs) or "—"
    return f"<details><summary>{len(locs)} locations</summary>{'<br>'.join(_cell(l) for l in locs)}</details>"


WORKDAY_REQ_RE = re.compile(r"https?://([\w-]+)\.wd\d+\.myworkdayjobs\.com/.*_([A-Za-z0-9-]+)/?$")


def _dedupe_key(r):
    # A Workday tenant often lists one requisition on several sites (regional or case variants,
    # which the registry may also have filed under different company names).
    if m := WORKDAY_REQ_RE.match(r["url"].split("?")[0]):
        return ("workday", m[1].lower(), m[2].lower())
    return (r["company"].lower(), r["title"].lower().strip(), tuple(sorted(r["locations"])))


def dedupe(recs):
    """The same req is often posted on several boards or Workday sites of one company."""
    best = {}
    for r in recs:
        key = _dedupe_key(r)
        if key not in best or r["first_seen"] < best[key]["first_seen"]:
            best[key] = r
    return list(best.values())


def render(listings: dict, scorecard: str = "") -> str:
    today = date.today()
    active = dedupe([r for r in listings.values() if r["active"]])
    active.sort(key=lambda r: (r.get("posted_at") or r["first_seen"][:10], r["first_seen"]), reverse=True)
    lines = [
        f"**{len(active)} open roles** from {len({r['company'] for r in active})} companies · "
        f"updated {datetime.utcnow().strftime('%Y-%m-%d %H:%M')} UTC",
        "",
    ]
    if scorecard:
        lines += [scorecard, ""]
    lines += ["| Company | Role | Location | Term | Apply | Age |",
              "| --- | --- | --- | --- | --- | --- |"]
    for r in active:
        lines.append(
            f"| **{_cell(r['company'])}** | {_cell(r['title'])} | {_locations(r['locations'])} | "
            f"{_cell(', '.join(r['terms'])) or '—'} | [Apply]({r['url']}) | {_age(r, today)} |")
    body = "\n".join(lines)
    return f"{HEADER}{START}\n{body}\n{END}\n"


def write(listings: dict, scorecard: str = "") -> None:
    README_PATH.write_text(render(listings, scorecard), encoding="utf-8")

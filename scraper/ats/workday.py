"""Workday career sites (the cxs JSON API behind *.myworkdayjobs.com).

Measured behaviour that shapes this connector (2026-10-22):
- Search is not relevance-ranked at many tenants: Salesforce, Capital One, Northrop Grumman and J&J
  return date-ordered results for "intern", with zero internships on page one. Paging a search
  until it "runs out of interns" silently missed open roles.
- The same tenants tag internships in a facet (usually workerSubType: "Intern", "Co-Op (Fixed
  Term)", "Intern - Developmental"), holding only tens of jobs. Filtering on that facet is exact
  and cheap, so it is the primary strategy.
- An empty search returns newest first. A short newest-first sweep catches internships that a
  tenant didn't tag. Because the sweep only looks back a few days, listings that drop out of view
  are confirmed closed via their job page before being marked closed (see is_open).
"""
import re
from datetime import date, timedelta

from ..net import get_json, post_json

PAGE = 20
MAX_FACET_PAGES = 50
SEARCH_QUERIES = ["intern", "internship"]
INTERNISH = re.compile(r"\b(intern|interns|internship|co-?op)\b", re.I)
FACET_VALUE_RE = re.compile(r"\b(intern|interns|internship|co-?op)\b", re.I)
FACET_EXCLUDE_RE = re.compile(r"non-?intern|non-?student", re.I)
POSTED_RE = re.compile(r"Posted (Today|Yesterday|(\d+)\+? Days Ago)", re.I)


def _api(params):
    return f"https://{params['host']}/wday/cxs/{params['tenant']}/{params['site']}"


def _days_ago(text):
    m = POSTED_RE.search(text or "")
    if not m:
        return None
    if m[1].lower() == "today":
        return 0
    if m[1].lower() == "yesterday":
        return 1
    return int(m[2]) + (1 if "+" in m[0] else 0)


def _posted(text):
    days = _days_ago(text)
    if days is None or "+" in (text or ""):
        return None  # "30+ Days Ago" is not a date
    return (date.today() - timedelta(days=days)).isoformat()


def _job(params, p, typed_intern=False):
    path = p["externalPath"]
    return {
        "job_id": path.rsplit("/", 1)[-1],
        "title": p.get("title", ""),
        "locations": [p["locationsText"]] if p.get("locationsText") else [],
        "url": f"https://{params['host']}/{params['site']}{path}",
        "posted_at": _posted(p.get("postedOn")),
        "_path": path,
        "_intern_type": typed_intern,
    }


def _intern_facets(facets):
    """{facetParameter: [value ids]} for facet values that look like internships."""
    found = {}

    def walk(param, values):
        for v in values or []:
            if "values" in v:
                walk(v.get("facetParameter") or param, v["values"])
            elif FACET_VALUE_RE.search(v.get("descriptor", "")) and not FACET_EXCLUDE_RE.search(v.get("descriptor", "")):
                found.setdefault(param, []).append(v["id"])

    for f in facets or []:
        walk(f.get("facetParameter"), f.get("values"))
    return found


def fetch(params, lookback_days=3):
    api = f"{_api(params)}/jobs"
    seen = {}

    def page(body, offset):
        return post_json(api, {"appliedFacets": {}, "limit": PAGE, "offset": offset, "searchText": "", **body})

    def add(posts, typed_intern=False):
        for p in posts:
            path = p.get("externalPath")
            if not path:
                continue
            if path not in seen:
                seen[path] = _job(params, p, typed_intern)
            elif typed_intern:
                seen[path]["_intern_type"] = True

    first = page({}, 0)
    if first is None:
        return None
    add(first.get("jobPostings") or [])

    # 1. facet filter
    for param, ids in _intern_facets(first.get("facets")).items():
        total = None
        for n in range(MAX_FACET_PAGES):
            data = page({"appliedFacets": {param: ids}}, n * PAGE)
            if not data:
                break
            total = data.get("total") or 0 if total is None else total
            add(data.get("jobPostings") or [], typed_intern=True)
            if (n + 1) * PAGE >= total or not data.get("jobPostings"):
                break

    # 2. newest-first sweep of the last few days (first page already fetched)
    posts, offset = first.get("jobPostings") or [], 0
    while posts:
        ages = [a for a in (_days_ago(p.get("postedOn")) for p in posts) if a is not None]
        if not ages or min(ages) > lookback_days or offset >= 2000 - PAGE:
            break
        offset += PAGE
        data = page({}, offset)
        posts = (data or {}).get("jobPostings") or []
        add(posts)

    # 3. title search, for tenants where search is relevance-ranked
    for q in SEARCH_QUERIES:
        for n in range(10):
            data = page({"searchText": q}, n * PAGE)
            posts = (data or {}).get("jobPostings") or []
            add(posts)
            if not posts or not any(INTERNISH.search(p.get("title", "")) for p in posts):
                break
    return list(seen.values())


def _detail(params, path):
    return ((get_json(f"{_api(params)}{path}") or {}).get("jobPostingInfo")) or None


def enrich(params, job):
    """Fetch the job page for exact locations and posting date. Mutates and returns job."""
    info = _detail(params, job["_path"])
    if not info:
        return job
    locs = [info.get("location")] + list(info.get("additionalLocations") or [])
    country = (info.get("country") or {}).get("descriptor")
    locs = [l for l in locs if l]
    if country and not any(country in l for l in locs):
        locs = [f"{l}, {country}" for l in locs] or [country]
    if locs:
        job["locations"] = locs
    if info.get("startDate"):
        job["posted_at"] = info["startDate"][:10]
    job["_desc"] = re.sub(r"<[^>]+>", " ", info.get("jobDescription") or "")
    return job


def describe(params, job):
    if "_desc" not in job:
        enrich(params, job)
    return job.get("_desc", "")


def is_open(params, url):
    """True if the job page still exists and accepts applications; None if it couldn't be checked."""
    if "/job/" not in url:
        return None
    data = get_json(f"{_api(params)}/job/{url.split('/job/', 1)[1]}", tries=2)
    if data is None:
        return False
    info = data.get("jobPostingInfo") or {}
    return bool(info) and info.get("canApply", True) is not False

"""iCIMS portals on *.icims.com (HTML job cards; keyword search filters rather than ranks)."""
import html
import re

from ..jsonld import job_posting
from ..net import get_text

QUERIES = ["intern", "co-op"]
CARD_RE = re.compile(r'<li class="iCIMS_JobCardItem">(.*?)</li>', re.S)
LINK_RE = re.compile(r'<a href="(https://[^"]+/jobs/(\d+)/[^"?]*/job)[^"]*"[^>]*title="\d+ - ([^"]*)"')
LOC_RE = re.compile(r'field-label">Location</span>\s*<span[^>]*>\s*([^<]+?)\s*</span>', re.S)
CATEGORY_RE = re.compile(r'Category</dt>\s*<dd[^>]*><span[^>]*>\s*([^<]+?)\s*</span>', re.S)


def fetch(params):
    host = params["host"]
    seen, ok = {}, False
    for q in QUERIES:
        for page in range(20):
            text = get_text(f"https://{host}/jobs/search?ss=1&searchKeyword={q}&in_iframe=1&pr={page}")
            if text is None:
                break
            ok = True
            cards = CARD_RE.findall(text)
            for card in cards:
                m = LINK_RE.search(card)
                if not m:
                    continue
                loc = LOC_RE.search(card)
                cat = CATEGORY_RE.search(card)
                seen[m[2]] = {
                    "job_id": m[2],
                    "title": html.unescape(m[3]).strip(),
                    "locations": [html.unescape(loc[1])] if loc else [],
                    "url": m[1],
                    "posted_at": None,
                    "_intern_type": bool(cat and re.search(r"intern|co-?op", cat[1], re.I)),
                }
            if not cards or f"pr={page + 1}" not in text:
                break
    return list(seen.values()) if ok else None


def enrich(params, job):
    """Some portal templates omit location from the cards; the job page's JSON-LD has it."""
    info = job_posting(get_text(job["url"] + "?in_iframe=1"))
    if info:
        if info["locations"]:
            job["locations"] = info["locations"]
        job["posted_at"] = info["posted_at"] or job.get("posted_at")
        job["_desc"] = info["description"]
    return job


def describe(params, job):
    if "_desc" not in job:
        enrich(params, job)
    return job.get("_desc", "")

"""schema.org JobPosting extraction. Career sites embed it for Google's job search, so it is the
most portable source of location, date and description on otherwise custom pages."""
import html
import json
import re

LD_RE = re.compile(r'<script[^>]+type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)


def _postings(node):
    if isinstance(node, list):
        for n in node:
            yield from _postings(n)
    elif isinstance(node, dict):
        if node.get("@type") == "JobPosting":
            yield node
        for v in node.get("@graph", []) if isinstance(node.get("@graph"), list) else []:
            yield from _postings(v)


def _place(loc):
    a = (loc or {}).get("address") or {}
    if isinstance(a, str):
        return a
    parts = [a.get("addressLocality"), a.get("addressRegion"), a.get("addressCountry")]
    parts = [p if isinstance(p, str) else (p or {}).get("name") for p in parts]
    return ", ".join(p for p in parts if p and p != "UNAVAILABLE")


def job_posting(page: str):
    """Return {'title', 'locations', 'posted_at', 'description', 'remote'} or None."""
    for block in LD_RE.findall(page or ""):
        try:
            data = json.loads(block.strip())
        except ValueError:
            continue
        for p in _postings(data):
            locs = p.get("jobLocation") or []
            locs = locs if isinstance(locs, list) else [locs]
            places = [x for x in dict.fromkeys(_place(l) for l in locs) if x]
            remote = p.get("jobLocationType") == "TELECOMMUTE"
            if remote:
                req = p.get("applicantLocationRequirements") or {}
                req = req if isinstance(req, list) else [req]
                places.append("Remote, " + ", ".join(r.get("name", "") for r in req if isinstance(r, dict)))
            desc = re.sub(r"<[^>]+>", " ", html.unescape(p.get("description") or ""))
            return {"title": html.unescape(p.get("title") or ""), "locations": places,
                    "posted_at": (p.get("datePosted") or "")[:10] or None, "description": desc,
                    "remote": remote}
    return None

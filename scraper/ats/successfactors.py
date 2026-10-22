"""SAP SuccessFactors career sites (Career Site Builder, e.g. jobs.l3harris.com).

The sitemap lists every job with its title in the URL slug, so internship-looking slugs are picked
from it and only those job pages are fetched (they carry schema.org title/location/date).
"""
import html
import re
from datetime import datetime

from ..net import get_text

LOC_RE = re.compile(r"<loc>([^<]+)</loc>")
SLUG_RE = re.compile(r"\b(intern|interns|internship|co-?op|coop)\b", re.I)
TITLE_RE = re.compile(r'itemprop="title"[^>]*>([^<]+)<')
GEO_RE = re.compile(r'class="jobGeoLocation">\s*([^<]+?)\s*<')
DATE_RE = re.compile(r'itemprop="datePosted" content="([^"]+)"')
MAX_JOB_PAGES = 150


def _sitemap_urls(host):
    text = get_text(f"https://{host}/sitemap.xml")
    if text is None:
        return None
    urls = LOC_RE.findall(text)
    if "<sitemapindex" in text:  # large sites split the sitemap
        nested = []
        for sm in urls[:20]:
            nested += LOC_RE.findall(get_text(html.unescape(sm)) or "")
        urls = nested
    return [html.unescape(u) for u in urls if "/job/" in u]


def _date(s):
    try:
        return datetime.strptime(s, "%a %b %d %H:%M:%S UTC %Y").date().isoformat()
    except (TypeError, ValueError):
        return None


def fetch(params):
    host = params["host"]
    urls = _sitemap_urls(host)
    if urls is None:
        return None
    jobs = []
    for url in [u for u in urls if SLUG_RE.search(u.replace("-", " "))][:MAX_JOB_PAGES]:
        m = re.search(r"/job/[^/]+/(\d+)/?", url)
        page = get_text(url)
        if not m or not page:
            continue
        title = TITLE_RE.search(page)
        geo = GEO_RE.search(page)
        date = DATE_RE.search(page)
        jobs.append({
            "job_id": m[1],
            "title": html.unescape(title[1]).strip() if title else "",
            "locations": [html.unescape(geo[1])] if geo else [],
            "url": url,
            "posted_at": _date(date[1]) if date else None,
            "_desc": re.sub(r"<[^>]+>", " ", page),
        })
    return jobs

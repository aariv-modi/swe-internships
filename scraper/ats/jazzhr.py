"""JazzHR ({company}.applytojob.com), via its public XML job feed."""
import html
import re

from ..net import get_text

JOB_RE = re.compile(r"<job>(.*?)</job>", re.S)


def _field(block, name):
    m = re.search(rf"<{name}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{name}>", block, re.S)
    return html.unescape(m[1]).strip() if m else ""


def fetch(params):
    company = params["company"]
    text = get_text(f"https://app.jazz.co/feeds/export/jobs/{company}")
    if text is None:
        return None
    jobs = []
    for block in JOB_RE.findall(text):
        place = ", ".join(x for x in (_field(block, "city"), _field(block, "state"),
                                      _field(block, "country")) if x)
        url = _field(block, "url")
        code = re.search(r"/apply/([A-Za-z0-9]+)", url)
        if _field(block, "status").lower() not in ("", "open"):
            continue
        jobs.append({
            "job_id": code[1] if code else _field(block, "id"),
            "title": _field(block, "title"),
            "locations": [place] if place else [],
            "url": url,
            "posted_at": None,
            "_intern_type": "intern" in _field(block, "type").lower(),
            "_desc": re.sub(r"<[^>]+>", " ", _field(block, "description")),
        })
    return jobs

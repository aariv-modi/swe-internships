import html
import re
from datetime import datetime

from ..net import get_json


def _date(ts):
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return None


def fetch(params):
    host = "boards.eu.greenhouse.io" if params.get("eu") else "boards-api.greenhouse.io"
    data = get_json(f"https://{host}/v1/boards/{params['board']}/jobs")
    if data is None:
        return None
    jobs = []
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name", "")
        jobs.append({
            "job_id": str(j["id"]),
            "title": j.get("title", ""),
            "locations": [loc] if loc else [],
            "url": j.get("absolute_url", ""),
            "posted_at": _date(j.get("first_published") or j.get("updated_at")),
        })
    return jobs


def describe(params, job):
    host = "boards.eu.greenhouse.io" if params.get("eu") else "boards-api.greenhouse.io"
    data = get_json(f"https://{host}/v1/boards/{params['board']}/jobs/{job['job_id']}")
    content = html.unescape((data or {}).get("content") or "")
    return re.sub(r"<[^>]+>", " ", content)

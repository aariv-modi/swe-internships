import re
from datetime import datetime, timezone

from ..net import get_json


def fetch(params):
    host = "api.eu.lever.co" if params.get("eu") else "api.lever.co"
    data = get_json(f"https://{host}/v0/postings/{params['board']}?mode=json")
    if data is None:
        return None
    jobs = []
    for j in data:
        cats = j.get("categories") or {}
        locs = cats.get("allLocations") or ([cats["location"]] if cats.get("location") else [])
        created = j.get("createdAt")
        lists = " ".join(f"{l.get('text', '')} {l.get('content', '')}" for l in j.get("lists") or [])
        jobs.append({
            "job_id": j["id"],
            "title": j.get("text", ""),
            "locations": list(dict.fromkeys(locs)),
            "url": j.get("hostedUrl", ""),
            "posted_at": (datetime.fromtimestamp(created / 1000, timezone.utc).date().isoformat()
                          if created else None),
            "_intern_type": bool(re.search(r"intern|co-?op", cats.get("commitment") or "", re.I)),
            "_desc": f"{j.get('descriptionPlain', '')} {lists} {j.get('additionalPlain', '')}",
        })
    return jobs

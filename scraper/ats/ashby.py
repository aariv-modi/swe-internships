from urllib.parse import quote

from ..net import get_json


def fetch(params):
    data = get_json(f"https://api.ashbyhq.com/posting-api/job-board/{quote(params['board'])}")
    if data is None:
        return None
    jobs = []
    for j in data.get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location") or ""]
        locs += [s.get("location", "") for s in j.get("secondaryLocations") or []]
        country = ((j.get("address") or {}).get("postalAddress") or {}).get("addressCountry")
        if country and not any(country in l for l in locs):
            locs = [f"{l}, {country}" if l else country for l in locs]
        if j.get("isRemote") and not any("remote" in l.lower() for l in locs):
            locs.append("Remote")
        jobs.append({
            "job_id": j["id"],
            "title": j.get("title", "").strip(),
            "locations": [l for l in dict.fromkeys(locs) if l],
            "url": j.get("jobUrl", ""),
            "posted_at": (j.get("publishedAt") or "")[:10] or None,
            "_intern_type": j.get("employmentType") == "Intern",
            "_desc": j.get("descriptionPlain") or "",
        })
    return jobs

from ..net import get_json

QUERIES = ["intern", "co-op"]


def fetch(params):
    company = params["company"]
    seen, ok = {}, False
    for q in QUERIES:
        for offset in range(0, 1000, 100):
            data = get_json(f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
                            f"?limit=100&offset={offset}&q={q}")
            if data is None:
                break
            ok = True
            for p in data.get("content") or []:
                loc = p.get("location") or {}
                parts = [loc.get("city"), loc.get("region"), loc.get("country", "").upper()]
                place = ", ".join(x for x in parts if x)
                if loc.get("remote"):
                    place = f"{place} (Remote)" if place else "Remote"
                seen[p["id"]] = {
                    "job_id": p["id"],
                    "title": p.get("name", ""),
                    "locations": [place] if place else [],
                    "url": f"https://jobs.smartrecruiters.com/{company}/{p['id']}",
                    "posted_at": (p.get("releasedDate") or "")[:10] or None,
                    "_intern_type": "intern" in ((p.get("typeOfEmployment") or {}).get("label") or "").lower()
                                    or (p.get("experienceLevel") or {}).get("id") == "internship",
                }
            if offset + 100 >= (data.get("totalFound") or 0):
                break
    return list(seen.values()) if ok else None

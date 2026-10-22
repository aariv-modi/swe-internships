"""Oracle Recruiting Cloud (hcmUI/CandidateExperience sites).

The REST search ranks by relevance when sortBy=RELEVANCY (checked on Oracle's own site: internship
titles fill the first pages, unlike Workday at several tenants), so each query is paged until a
page holds no internship-looking titles.
"""
import re

from ..net import get_json

QUERIES = ["intern", "internship", "co-op"]
PAGE = 25
MAX_FULL_PAGES = 120  # 3,000 jobs
INTERNISH = re.compile(r"\b(intern|interns|internship|co-?op)\b", re.I)


def fetch(params):
    host, site = params["host"], params["site"]
    base = f"https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    seen, ok = {}, False

    def page(finder, offset):
        data = get_json(f"{base}?onlyData=true&expand=requisitionList.secondaryLocations"
                        f"&finder=findReqs;siteNumber={site},{finder}limit={PAGE},offset={offset}")
        items = (data or {}).get("items") or []
        return items[0] if items else None

    def add(reqs):
        for r in reqs:
            locs = [r.get("PrimaryLocation")] + [s.get("Name") for s in r.get("secondaryLocations") or []]
            seen[r["Id"]] = {
                "job_id": str(r["Id"]),
                "title": r.get("Title", ""),
                "locations": [l for l in dict.fromkeys(locs) if l],
                "url": f"https://{host}/hcmUI/CandidateExperience/en/sites/{site}/job/{r['Id']}",
                "posted_at": r.get("PostedDate"),
                "_desc": f"{r.get('ShortDescriptionStr') or ''} {r.get('ExternalResponsibilitiesStr') or ''} "
                         f"{r.get('ExternalQualificationsStr') or ''}",
            }

    keyword_hits = 0
    for q in QUERIES:
        for n in range(20):
            res = page(f"keyword=%22{q}%22,sortBy=RELEVANCY,", n * PAGE)
            if res is None:
                break
            ok = True
            reqs = res.get("requisitionList") or []
            keyword_hits += len(reqs)
            add(reqs)
            if len(reqs) < PAGE or not any(INTERNISH.search(r.get("Title", "")) for r in reqs):
                break
    if ok and keyword_hits == 0:
        # Some tenants' keyword index is broken (Citizens: "Software" matches 1 of 502 jobs,
        # "intern" matches 0), so read the whole listing instead.
        for n in range(MAX_FULL_PAGES):
            res = page("sortBy=POSTING_DATES_DESC,", n * PAGE)
            reqs = (res or {}).get("requisitionList") or []
            add(reqs)
            if len(reqs) < PAGE:
                break
    return list(seen.values()) if ok else None

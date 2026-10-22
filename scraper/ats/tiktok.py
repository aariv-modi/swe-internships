"""TikTok careers (lifeattiktok.com). The search API needs the `website-path: tiktok` header that
the site's own front end sends (captured from the page's request, 2026-10-22)."""
from ..net import _session

API = "https://api.lifeattiktok.com/api/v1/public/supplier/search/job/posts"
HEADERS = {"Content-Type": "application/json", "accept-language": "en-US",
           "origin": "https://lifeattiktok.com", "website-path": "tiktok"}
PAGE = 100


def _place(city):
    names = []
    while city:
        names.append(city.get("en_name") or city.get("i18n_name") or "")
        city = city.get("parent")
    return ", ".join(n for n in names if n)


def fetch(params):
    seen, ok = {}, False
    for offset in range(0, 5000, PAGE):
        body = {"recruitment_id_list": [], "job_category_id_list": [], "subject_id_list": [],
                "location_code_list": [], "keyword": "intern", "limit": PAGE, "offset": offset}
        try:
            r = _session().post(API, json=body, headers=HEADERS, timeout=30)
            data = r.json().get("data") or {}
        except Exception:
            break
        ok = True
        posts = data.get("job_post_list") or []
        for p in posts:
            seen[p["id"]] = {
                "job_id": p["id"],
                "title": p.get("title", ""),
                "locations": [_place(p.get("city_info"))] if p.get("city_info") else [],
                "url": f"https://lifeattiktok.com/search/{p['id']}",
                "posted_at": None,
                "_intern_type": ((p.get("recruit_type") or {}).get("en_name") or "").lower() == "intern",
                "_desc": f"{p.get('description') or ''} {p.get('requirement') or ''}",
            }
        if len(posts) < PAGE or offset + PAGE >= (data.get("count") or 0):
            break
    return list(seen.values()) if ok else None

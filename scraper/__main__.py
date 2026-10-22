"""Usage:
  python -m scraper discover            # refresh data/companies.json from community lists
  python -m scraper scrape [--ats X]    # fetch boards, update data/listings.json, README.md
  python -m scraper all                 # discover, then scrape
  python -m scraper crawl-discover      # promote Common Crawl boards that have a match (slow, monthly)
Options: --ats workday,greenhouse  --limit N (boards per ATS, for testing)  --no-scorecard
"""
import argparse
import concurrent.futures as cf
import sys
import time
from collections import Counter

from . import classify, discovery, registry, render, scorecard, store
from .ats import CONNECTORS, workday

BOARD_DEADLINE_S = 600  # a single board may not stall the whole run


def _verdict(ats, params, job):
    """Return 'ok' or the reason the job was rejected (recorded for the scorecard)."""
    title = job["title"]
    if not classify.is_internship(title, job.get("_intern_type", False)):
        return "not_internship"
    verdict = classify.swe_verdict(title)
    if verdict == "no":
        return "not_swe"
    us = classify.us_status(job["locations"])
    if us is False:
        return "not_us"
    connector = CONNECTORS[ats]
    # Workday list pages say "2 Locations" and give relative dates, so always fetch the job page;
    # other connectors only when the listing didn't say where the job is.
    if hasattr(connector, "enrich") and (ats == "workday" or us is None):
        connector.enrich(params, job)
        us = classify.us_status(job["locations"])
        if us is False:
            return "not_us"
    if verdict == "maybe":
        desc = job.get("_desc")
        if desc is None and hasattr(CONNECTORS[ats], "describe"):
            desc = CONNECTORS[ats].describe(params, job)
        if not classify.description_is_swe(desc or ""):
            return "not_swe_by_description"
    if us is not True:
        return "location_unknown"
    return "ok"


def classify_jobs(ats, params, jobs, seen_jobs):
    matches = []
    for job in jobs:
        reason = _verdict(ats, params, job)
        if key := scorecard.job_key(job["url"]):
            seen_jobs[key] = reason
        if reason == "ok":
            job["terms"] = classify.terms(job["title"])
            matches.append(job)
    return matches


def scrape(reg, only_ats=None, limit=None, with_scorecard=True):
    listings = store.load()
    ts = store.now_iso()
    boards = [(rid, b) for rid, b in reg.items() if not only_ats or b["ats"] in only_ats]
    if limit:
        per = Counter()
        boards = [x for x in boards if (per.update([x[1]["ats"]]) or per[x[1]["ats"]] <= limit)]
    print(f"scraping {len(boards)} boards")
    seen_jobs, read_boards, stats = {}, set(), Counter()
    active_by_board = {}
    for lid, rec in listings.items():
        if rec["active"]:
            active_by_board.setdefault(rec["board"], []).append((lid, rec))
    t0 = time.time()

    def work(item):
        rid, b = item
        jobs = CONNECTORS[b["ats"]].fetch(b["params"])
        if jobs is None:
            return rid, b, None
        matches = classify_jobs(b["ats"], b["params"], jobs, seen_jobs)
        if b["ats"] == "workday":
            # The Workday sweep only looks back a few days, so a listing missing from this fetch
            # isn't necessarily closed: confirm on its job page before letting it close.
            got = {f"{rid}:{m['job_id']}" for m in matches}
            for lid, rec in active_by_board.get(rid, []):
                if lid not in got and workday.is_open(b["params"], rec["url"]):
                    matches.append({"job_id": lid[len(rid) + 1:], "title": rec["title"],
                                    "locations": rec["locations"], "url": rec["url"],
                                    "posted_at": rec.get("posted_at"), "terms": rec["terms"]})
        return rid, b, matches

    with cf.ThreadPoolExecutor(32) as ex:
        futs = {ex.submit(work, item): item for item in boards}
        for i, fut in enumerate(cf.as_completed(futs), 1):
            try:
                rid, b, matches = fut.result(timeout=BOARD_DEADLINE_S)
            except Exception as e:  # one broken board must not kill the run
                rid, b = futs[fut]
                print(f"  error {rid}: {type(e).__name__}: {e}", file=sys.stderr)
                matches = None
            if matches is None:
                stats[f"{b['ats']}:unreadable"] += 1
                continue
            read_boards.add(rid)
            stats[f"{b['ats']}:read"] += 1
            stats["new"] += store.apply_board(listings, rid, b["company"], matches, ts)
            if i % 200 == 0:
                print(f"  {i}/{len(boards)} boards, {time.time() - t0:.0f}s")
    # Boards dropped or merged in the registry are never scraped again, so their listings would
    # otherwise stay open forever.
    for rec in listings.values():
        if rec["active"] and rec.get("board") not in reg:
            rec["active"], rec["closed_at"] = False, ts
            stats["closed_unregistered"] += 1
    store.save(listings)
    active = sum(r["active"] for r in listings.values())
    print(f"done in {time.time() - t0:.0f}s: {dict(stats)}; active listings {active}")
    card = ""
    if with_scorecard:
        try:
            s = scorecard.compute(listings, seen_jobs, read_boards, reg)
            print("scorecard:", s)
            card = scorecard.markdown(s)
        except Exception as e:
            print(f"scorecard failed: {e}", file=sys.stderr)
    render.write(listings, card)
    return listings


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("command", choices=["discover", "scrape", "all", "crawl-discover"])
    ap.add_argument("--ats", help="comma-separated subset of " + ",".join(CONNECTORS))
    ap.add_argument("--limit", type=int)
    ap.add_argument("--no-scorecard", action="store_true")
    a = ap.parse_args(argv)
    reg = registry.load()
    if a.command in ("discover", "all"):
        reg = registry.discover(reg)
        registry.save(reg)
        print(f"registry: {len(reg)} boards {dict(Counter(b['ats'] for b in reg.values()))}")
    if a.command == "crawl-discover":
        discovery.promote(reg, discovery.common_crawl_boards(), classify_jobs)
        registry.save(reg)
        print(f"registry: {len(reg)} boards")
    if a.command in ("scrape", "all"):
        scrape(reg, set(a.ats.split(",")) if a.ats else None, a.limit, not a.no_scorecard)


if __name__ == "__main__":
    main()

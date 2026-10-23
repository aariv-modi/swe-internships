"""Review queue for applying, with pre-filled forms. You always press Submit yourself.

  python -m apply init              create ~/.swe-internships/profile.toml to fill in
  python -m apply queue [-n 25]     open postings ranked by fit, minus ones you've handled
  python -m apply open N            open queue item N (or a URL), pre-fill it, wait for you
  python -m apply mark N applied    record an outcome without opening (applied | skipped)
"""
import argparse
import sys
from datetime import date

from . import config, draft, queue
from .fill import fill_page

APPLY_PATH = {"lever.co": "/apply", "ashbyhq.com": "/application"}


def _apply_url(url: str) -> str:
    for host, suffix in APPLY_PATH.items():
        if host in url and not url.rstrip("/").endswith(suffix):
            return url.rstrip("/") + suffix
    return url


def _print_queue(items):
    if not items:
        print("Nothing in the queue. Loosen [queue] in your profile, or check back after the next scrape.")
    for i, (s, _lid, r) in enumerate(items, 1):
        mode = "prefill" if queue.autofill_supported(r["url"]) else "manual "
        terms = ", ".join(r.get("terms", [])) or "term?"
        print(f"{i:3d}. [{mode}] {r['company'][:24]:24} {r['title'][:60]:60} {terms:12} {'; '.join(r['locations'])[:30]}")


def cmd_open(target, profile, state, items):
    if target.startswith("http"):
        lid, rec = target, {"url": target, "company": "", "title": ""}
    else:
        _s, lid, rec = items[int(target) - 1]
    url = _apply_url(rec["url"])
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Needs Playwright: pip install playwright")
    print(f"Opening {rec.get('company', '')} {rec.get('title', '')}\n  {url}")
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(str(config.BROWSER_DIR), channel="chrome", headless=False,
                                                   no_viewport=True)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=90000)
        if queue.autofill_supported(url):
            drafter = draft.claude_drafter if draft.available() else None
            rep = fill_page(page, profile, drafter, job_context=page.inner_text("body"))
            if rep.blocked:
                print("\n  This employer forbids tool- or AI-completed applications. Nothing was filled;"
                      " please complete it yourself.")
            else:
                print(f"\n  Filled {len(rep.filled)} fields:")
                for label, value in rep.filled:
                    print(f"    - {label[:70]}: {value}")
                if rep.drafted:
                    print("  Drafted (edit these before submitting):")
                    for label in rep.drafted:
                        print(f"    - {label[:90]}")
                left = rep.for_you + [l for l in rep.essays if l not in rep.drafted]
                if left:
                    print("  Yours to answer:")
                    for label in left:
                        print(f"    - {label[:90]}")
                if rep.essays and not draft.available():
                    print("  (Install Claude Code's CLI to get drafts for long answers.)")
        else:
            print("\n  Not a pre-fill system (e.g. Workday): sign in and complete it in this window.")
        print("\n  Review everything in the browser and submit there yourself.")
        outcome = input("  When you're done: applied / skipped / later? [a/s/L] ").strip().lower()
        ctx.close()
    if outcome in ("a", "applied", "s", "skipped"):
        state[lid] = {"status": "applied" if outcome.startswith("a") else "skipped",
                      "date": date.today().isoformat(), "company": rec.get("company"),
                      "title": rec.get("title"), "url": rec["url"]}
        config.save_state(state)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m apply")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init")
    q = sub.add_parser("queue")
    q.add_argument("-n", type=int, default=25)
    q.add_argument("--local", action="store_true", help="use data/listings.json instead of GitHub")
    o = sub.add_parser("open")
    o.add_argument("target", help="queue number or application URL")
    o.add_argument("--local", action="store_true")
    m = sub.add_parser("mark")
    m.add_argument("n", type=int)
    m.add_argument("status", choices=["applied", "skipped"])
    m.add_argument("--local", action="store_true")
    a = ap.parse_args(argv)

    if a.cmd == "init":
        print(f"Fill in your profile: {config.init()}")
        return
    profile, state = config.load_profile(), config.load_state()
    items = queue.build(profile, state, prefer_local=a.local, limit=getattr(a, "n", 200) or 200)
    if a.cmd == "queue":
        _print_queue(items)
    elif a.cmd == "open":
        cmd_open(a.target, profile, state, items)
    elif a.cmd == "mark":
        _s, lid, rec = items[a.n - 1]
        state[lid] = {"status": a.status, "date": date.today().isoformat(), "company": rec["company"],
                      "title": rec["title"], "url": rec["url"]}
        config.save_state(state)
        print(f"Marked {rec['company']} {rec['title']} as {a.status}.")


if __name__ == "__main__":
    main()

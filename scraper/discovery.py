"""Find job boards that no community list links to, via the Common Crawl URL index.

The index server (index.commoncrawl.org) rate-limits hard, so this reads the raw index files on
data.commoncrawl.org instead: cluster.idx is sorted by SURT key, so a binary search with HTTP range
requests finds the few dozen blocks covering ATS hosts (~15 MB) without downloading the 100 MB file.

Measured 2026-10-22 (crawl CC-MAIN-2026-43): 14,127 boards, 11,814 not in the registry. Scraping a
random 2,000 of them found ~6 real US SWE internships no list had (~35 extrapolated, roughly +2%),
concentrated in ~1% of boards. So boards are *promoted* into the hourly registry only when they
have a match, instead of scraping all of them every hour.
"""
import concurrent.futures as cf
import gzip
import json

import requests

from . import registry

DATA = "https://data.commoncrawl.org/cc-index/collections/{crawl}/indexes/"
DEFAULT_CRAWL = "CC-MAIN-2026-43"
PREFIXES = ["com,myworkdayjobs,", "io,greenhouse,", "co,lever,", "com,ashbyhq,",
            "com,smartrecruiters,", "com,icims,", "com,applytojob,"]


def latest_crawl() -> str:
    try:
        return requests.get("https://index.commoncrawl.org/collinfo.json", timeout=30).json()[0]["id"]
    except Exception:
        return DEFAULT_CRAWL


class _ClusterIndex:
    def __init__(self, crawl):
        self.url = DATA.format(crawl=crawl) + "cluster.idx"
        self.s = requests.Session()
        self.size = int(self.s.head(self.url, timeout=30).headers["Content-Length"])

    def chunk(self, off, n=65536):
        r = self.s.get(self.url, headers={"Range": f"bytes={off}-{off + n - 1}"}, timeout=60)
        return r.content.decode("utf-8", "replace")

    def _find(self, prefix):
        lo, hi = 0, self.size
        while hi - lo > 65536:
            mid = (lo + hi) // 2
            text = self.chunk(mid, 4096).split("\n", 1)[-1]
            if text.split(" ", 1)[0] < prefix:
                lo = mid
            else:
                hi = mid
        return lo

    def blocks(self, prefix):
        """Index lines for every block that may contain keys starting with prefix."""
        off, out, prev, buf, read = self._find(prefix), [], None, "", 0
        while read < 50_000_000:
            text = self.chunk(off + read, 1 << 20)
            read += 1 << 20
            if not text:
                break
            lines = (buf + text).split("\n")
            buf = lines.pop()
            if read == 1 << 20 and off > 0:
                lines = lines[1:]  # the first chunk starts mid-line
            for line in lines:
                key = line.split(" ", 1)[0]
                if key.startswith(prefix):
                    if not out and prev:
                        out.append(prev)  # the block before the first match can hold matches too
                    out.append(line)
                elif key > prefix:
                    return out or ([prev] if prev else [])
                prev = line
        return out


def common_crawl_boards(crawl=None) -> dict:
    """{registry id: (ats, key, params)} for every ATS board in the crawl's URL index."""
    crawl = crawl or latest_crawl()
    idx = _ClusterIndex(crawl)
    lines = {l for p in PREFIXES for l in idx.blocks(p) if l}
    base = DATA.format(crawl=crawl)

    def read(line):
        _, _, rest = line.partition(" ")
        _ts, f, off, length, _seq = rest.split("\t")
        r = idx.s.get(base + f, headers={"Range": f"bytes={off}-{int(off) + int(length) - 1}"}, timeout=120)
        return gzip.decompress(r.content).decode("utf-8", "replace").splitlines()

    boards = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for rows in ex.map(read, sorted(lines)):
            for row in rows:
                try:
                    url = json.loads(row.split(" ", 2)[2])["url"]
                except (IndexError, ValueError, KeyError):
                    continue
                if found := registry.board_from_url(url):
                    boards[f"{found[0]}:{found[1]}"] = found
    print(f"  common crawl {crawl}: {len(boards)} boards from {len(lines)} index blocks")
    return boards


def promote(reg: dict, candidates: dict, classify_jobs) -> int:
    """Scrape candidate boards not yet registered; add those with a US SWE internship."""
    from .ats import CONNECTORS
    todo = [(rid, b) for rid, b in candidates.items() if rid not in reg]
    print(f"  checking {len(todo)} unregistered boards")

    def check(item):
        rid, (ats, _key, params) = item
        jobs = CONNECTORS[ats].fetch(params)
        return item, bool(jobs) and bool(classify_jobs(ats, params, jobs, {}))

    added = 0
    with cf.ThreadPoolExecutor(32) as ex:
        for (rid, (ats, _key, params)), hit in ex.map(check, todo):
            if hit:
                reg[rid] = {"ats": ats, "company": registry._placeholder_name(ats, params),
                            "params": params, "sources": ["common-crawl"]}
                added += 1
    print(f"  promoted {added} boards")
    return added

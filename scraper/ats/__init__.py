"""ATS connectors. Each module exposes fetch(params) -> list[dict] | None.

None means the board could not be read (network error, removed board); an empty list means the
board was read and has no matching jobs. The distinction matters: jobs are only marked closed
when their board was read successfully.

Each job dict has: job_id, title, locations (list[str]), url, posted_at (ISO date or None).
"""
from . import (ashby, greenhouse, icims, jazzhr, lever, oracle, smartrecruiters, successfactors,
               tiktok, workday)

CONNECTORS = {
    "workday": workday,
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "icims": icims,
    "oracle": oracle,
    "smartrecruiters": smartrecruiters,
    "successfactors": successfactors,
    "jazzhr": jazzhr,
    "tiktok": tiktok,
}

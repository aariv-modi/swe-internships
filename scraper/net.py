"""Shared HTTP session with retries, backoff and per-host concurrency limits."""
import threading
import time
from collections import defaultdict
from urllib.parse import urlparse

import requests

USER_AGENT = "swe-internships-bot/0.1 (+https://github.com/; public job-board reader)"
RETRY_STATUSES = {429, 500, 502, 503, 504}

_local = threading.local()
_host_locks = defaultdict(lambda: threading.BoundedSemaphore(4))
_host_locks_guard = threading.Lock()


def _session() -> requests.Session:
    s = getattr(_local, "session", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        _local.session = s
    return s


def _host_slot(url: str, per_host: int):
    host = urlparse(url).netloc
    with _host_locks_guard:
        if host not in _host_locks:
            _host_locks[host] = threading.BoundedSemaphore(per_host)
        return _host_locks[host]


def request_json(method: str, url: str, *, json_body=None, tries: int = 4,
                 timeout: float = 30, per_host: int = 4):
    """Return parsed JSON, or None for 404/410 and after exhausting retries."""
    delay = 2.0
    for attempt in range(tries):
        try:
            with _host_slot(url, per_host):
                r = _session().request(method, url, json=json_body, timeout=timeout)
        except requests.RequestException:
            r = None
        if r is not None:
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    return None
            if r.status_code in (404, 410, 422):
                return None
            if r.status_code not in RETRY_STATUSES:
                return None
            retry_after = r.headers.get("Retry-After", "")
            if retry_after.isdigit():
                delay = max(delay, float(retry_after))
        if attempt < tries - 1:
            time.sleep(delay)
            delay *= 2
    return None


def get_text(url: str, *, tries: int = 3, timeout: float = 30, per_host: int = 4):
    """Return the body of a 200 response as text, or None."""
    delay = 2.0
    for attempt in range(tries):
        try:
            with _host_slot(url, per_host):
                r = _session().get(url, timeout=timeout, headers={"Accept": "text/html,application/xml,*/*"})
            if r.status_code == 200:
                return r.text
            if r.status_code not in RETRY_STATUSES:
                return None
        except requests.RequestException:
            pass
        if attempt < tries - 1:
            time.sleep(delay)
            delay *= 2
    return None


def get_json(url: str, **kw):
    return request_json("GET", url, **kw)


def post_json(url: str, body, **kw):
    return request_json("POST", url, json_body=body, **kw)

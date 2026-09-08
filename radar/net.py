"""Polite HTTP fetching on the standard library only."""

from __future__ import annotations

import gzip
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from concurrent.futures import ThreadPoolExecutor

from . import config

_host_lock = threading.Lock()
_last_hit: dict[str, float] = {}


def _throttle(url: str) -> None:
    """Keep at least HOST_DELAY seconds between requests to one host."""
    host = urllib.parse.urlsplit(url).netloc
    while True:
        with _host_lock:
            now = time.monotonic()
            prev = _last_hit.get(host, 0.0)
            wait = prev + config.HOST_DELAY - now
            if wait <= 0:
                _last_hit[host] = now
                return
        time.sleep(min(wait, 2.0))


def fetch(url: str, *, timeout: int | None = None, retries: int = 2) -> str | None:
    """GET a URL and return decoded text, or None if it could not be had.

    Never raises — a dead source must not take the poller down with it.
    """
    timeout = timeout or config.FETCH_TIMEOUT
    for attempt in range(retries + 1):
        _throttle(url)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": config.USER_AGENT,
                "Accept": "application/rss+xml, application/xml, text/xml, application/json, */*",
                "Accept-Language": "te-IN,te;q=0.9,en-IN;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                enc = (resp.headers.get("Content-Encoding") or "").lower()
                if "gzip" in enc:
                    raw = gzip.decompress(raw)
                elif "deflate" in enc:
                    raw = zlib.decompress(raw, -zlib.MAX_WBITS)
                charset = resp.headers.get_content_charset() or "utf-8"
                try:
                    return raw.decode(charset, errors="replace")
                except LookupError:
                    return raw.decode("utf-8", errors="replace")
        except (urllib.error.HTTPError, urllib.error.URLError, OSError, EOFError, zlib.error):
            if attempt == retries:
                return None
            time.sleep(1.5 * (attempt + 1))
        except Exception:
            return None
    return None


def fetch_all(urls: list[str]) -> dict[str, str | None]:
    """Fetch many URLs concurrently. Order-independent, failure-tolerant."""
    out: dict[str, str | None] = {}
    if not urls:
        return out
    workers = min(config.MAX_PARALLEL, len(urls))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fetch, u): u for u in urls}
        for fut, url in futures.items():
            try:
                out[url] = fut.result()
            except Exception:
                out[url] = None
    return out


def post_json(url: str, payload: dict, headers: dict | None = None, timeout: int = 40):
    """POST JSON and return the parsed response, or None."""
    import json

    body = json.dumps(payload).encode("utf-8")
    hdrs = {"Content-Type": "application/json", "User-Agent": config.USER_AGENT}
    hdrs.update(headers or {})
    req = urllib.request.Request(url, data=body, headers=hdrs, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None

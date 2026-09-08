"""Source collectors. Every one of these is free and needs no API key."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from . import config, feeds, lexicon, net, store


def _fingerprint(title: str, outlet: str) -> str:
    raw = f"{lexicon.normalise(title)}|{outlet.lower().strip()}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


def is_fresh(published, *, allow_undated: bool = False) -> bool:
    """Is this inside the freshness window we are willing to show?

    The gate lives at ingest so old material never reaches the database. Feeds
    carry a long tail — most publisher RSS runs a median of 4 to 20 hours deep,
    and one was three years deep — and without this the board fills with
    yesterday regardless of how the scoring is tuned.
    """
    if published is None:
        return allow_undated
    if not isinstance(published, datetime):
        return False
    age_h = (datetime.now(timezone.utc) - published).total_seconds() / 3600.0
    if age_h < -0.5:
        return False              # future stamp: unusable
    return age_h <= config.MAX_ITEM_AGE_HOURS


def ingest(items: list[dict]) -> tuple[int, int]:
    """Insert new items, skipping ones already seen.

    Returns (newly stored, refused as too old).
    """
    c = store.conn()
    now = store.now_iso()
    added = 0
    stale = 0
    for it in items:
        title = (it.get("title") or "").strip()
        if len(title) < 12:
            continue
        # Items sourced from a live trend carry no real timestamp of their own;
        # they are by definition current, so they are allowed through undated.
        if not is_fresh(it.get("published"), allow_undated=it.get("kind") == "trendnews"):
            stale += 1
            continue
        outlet = it.get("outlet") or it.get("source") or feeds.domain_of(it.get("url", ""))
        fp = _fingerprint(title, outlet or "")
        published = it.get("published")
        cur = c.execute(
            """INSERT OR IGNORE INTO items
               (fingerprint, title, url, domain, outlet, lang, kind,
                published_at, first_seen, entities)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                fp, title, it.get("url", ""), feeds.domain_of(it.get("url", "")),
                outlet or "", "te" if lexicon.is_telugu(title) else "en",
                it.get("kind", "news"),
                published.isoformat() if isinstance(published, datetime) else None,
                now,
                ",".join(sorted(lexicon.entities(title))),
            ),
        )
        if cur.rowcount:
            added += 1
    return added, stale


# --------------------------------------------------------------------------
# Google Trends — what Andhra Pradesh is typing into Google right now
# --------------------------------------------------------------------------

def collect_trends() -> list[dict]:
    """Refresh the trends table and return rows enriched with a rising rate.

    The RSS feed is a snapshot, not a time series, so we build the time series
    ourselves: how long we have been seeing a query, and how its estimated
    traffic has moved since the last poll. A query first seen twenty minutes ago
    with traffic climbing is what "about to break" looks like.
    """
    urls = {
        f"https://trends.google.com/trending/rss?geo={geo}": (geo, label, weight)
        for geo, label, weight in config.TREND_FEEDS
    }
    responses = net.fetch_all(list(urls))
    c = store.conn()
    now = store.now_iso()
    seen_now: list[dict] = []

    for url, body in responses.items():
        geo, label, weight = urls[url]
        if not body:
            continue
        for entry in feeds.parse_trends(body):
            query = entry["query"]
            ents = ",".join(sorted(lexicon.entities(query)))
            row = c.execute(
                "SELECT traffic, first_seen FROM trends WHERE query=? AND geo=?",
                (query, geo),
            ).fetchone()
            prev_traffic = row["traffic"] if row else 0
            if row:
                c.execute(
                    """UPDATE trends SET prev_traffic=traffic, traffic=?, last_seen=?,
                       picture=COALESCE(NULLIF(?,''), picture), entities=?
                       WHERE query=? AND geo=?""",
                    (entry["traffic"], now, entry["picture"], ents, query, geo),
                )
                first_seen = row["first_seen"]
            else:
                c.execute(
                    """INSERT INTO trends(query, geo, traffic, prev_traffic,
                       first_seen, last_seen, picture, entities)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (query, geo, entry["traffic"], 0, now, now, entry["picture"], ents),
                )
                first_seen = now

            seen_now.append({
                "query": query,
                "geo": geo,
                "geo_label": label,
                "geo_weight": weight,
                "traffic": entry["traffic"],
                "prev_traffic": prev_traffic,
                "first_seen": first_seen,
                "picture": entry["picture"],
                "news": entry["news"],
                "entities": set(ents.split(",")) if ents else set(),
            })

    for t in seen_now:
        t["rising"] = _rising_score(t)
    seen_now.sort(key=lambda t: t["rising"], reverse=True)
    return seen_now


def _rising_score(trend: dict) -> float:
    """0..1 — how much this looks like a query on the way up, not on the way down."""
    first = store.parse_iso(trend["first_seen"])
    age_min = 999.0
    if first:
        age_min = max(1.0, (datetime.now(timezone.utc) - first).total_seconds() / 60)

    # Novelty: brand new queries are the whole point of a radar.
    novelty = 1.0 if age_min <= 30 else max(0.0, 1.0 - (age_min - 30) / 480.0)

    # Growth in Google's own traffic estimate since the previous poll.
    growth = 0.0
    if trend["prev_traffic"] > 0 and trend["traffic"] > trend["prev_traffic"]:
        growth = min(1.0, (trend["traffic"] - trend["prev_traffic"]) / max(trend["prev_traffic"], 1))

    # Absolute size, log-flattened so a 2M query does not drown everything.
    size = min(1.0, (trend["traffic"] ** 0.35) / 40.0) if trend["traffic"] else 0.2

    raw = 0.45 * novelty + 0.30 * growth + 0.25 * size
    return round(min(1.0, raw * trend["geo_weight"]), 4)


def trend_news_items(trends: list[dict]) -> list[dict]:
    """The article links Google already attaches to each trending query."""
    out: list[dict] = []
    for t in trends:
        for news in t["news"]:
            out.append({
                "title": news["title"],
                "url": news["url"],
                "outlet": news["source"],
                "published": store.parse_iso(t["first_seen"]),
                "kind": "trendnews",
            })
    return out


# --------------------------------------------------------------------------
# Google News RSS
# --------------------------------------------------------------------------

def collect_google_news(queries: list[tuple[str, tuple[str, str], str]]) -> list[dict]:
    url_map = {
        feeds.google_news_url(q, hl, ceid, when): q
        for q, (hl, ceid), when in queries
    }
    responses = net.fetch_all(list(url_map))
    out: list[dict] = []
    for url, body in responses.items():
        if not body:
            continue
        for item in feeds.parse_items(body):
            headline, outlet = feeds.split_google_title(item["title"])
            if not headline:
                continue
            out.append({
                "title": headline,
                "url": item["link"],
                "outlet": outlet or item.get("source") or "",
                "published": item["published"],
                "kind": "news",
            })
    return out


def chase_trends(trends: list[dict]) -> list[dict]:
    """Search news for the queries that are actually rising.

    This is the loop that matters: Trends tells us what people want, this tells
    us what has been written about it — and, by its absence, what has not.
    """
    picks = [t for t in trends if t["rising"] > 0.25][: config.MAX_TREND_CHASES]
    queries = []
    for t in picks:
        hl_ceid = ("te-IN", "IN:te") if lexicon.is_telugu(t["query"]) else ("en-IN", "IN:en")
        queries.append((t["query"], hl_ceid, config.TREND_CHASE_WINDOW))
    return collect_google_news(queries) if queries else []


# --------------------------------------------------------------------------
# Publisher RSS and YouTube
# --------------------------------------------------------------------------

def collect_publishers() -> list[dict]:
    url_map = {url: (name, lang) for name, lang, url in config.PUBLISHER_FEEDS}
    responses = net.fetch_all(list(url_map))
    out: list[dict] = []
    for url, body in responses.items():
        name, _lang = url_map[url]
        if not body:
            continue
        for item in feeds.parse_items(body)[:40]:
            out.append({
                "title": item["title"],
                "url": item["link"],
                "outlet": name,
                "published": item["published"],
                "kind": "news",
            })
    return out


def collect_youtube() -> list[dict]:
    if not config.YOUTUBE_ENABLED:
        return []
    url_map = {
        f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}": name
        for name, cid in config.YOUTUBE_CHANNELS
    }
    responses = net.fetch_all(list(url_map))
    out: list[dict] = []
    for url, body in responses.items():
        if not body:
            continue
        for item in feeds.parse_items(body)[:15]:
            if not feeds.recent(item["published"], 12):
                continue
            out.append({
                "title": item["title"],
                "url": item["link"],
                "outlet": url_map[url],
                "published": item["published"],
                "kind": "video",
            })
    return out

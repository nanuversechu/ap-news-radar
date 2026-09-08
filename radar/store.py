"""SQLite storage. One file, WAL mode, safe for the poller + server threads."""

from __future__ import annotations

import sqlite3
import threading
from datetime import datetime, timedelta, timezone

from . import config

_local = threading.local()

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id           INTEGER PRIMARY KEY,
    fingerprint  TEXT UNIQUE,
    title        TEXT NOT NULL,
    url          TEXT,
    domain       TEXT,
    outlet       TEXT,
    lang         TEXT,
    kind         TEXT,              -- news | video | trendnews
    published_at TEXT,
    first_seen   TEXT NOT NULL,
    entities     TEXT,              -- comma separated lexicon keys
    cluster_id   INTEGER
);
CREATE INDEX IF NOT EXISTS idx_items_first_seen ON items(first_seen);
CREATE INDEX IF NOT EXISTS idx_items_cluster    ON items(cluster_id);

CREATE TABLE IF NOT EXISTS clusters (
    id          INTEGER PRIMARY KEY,
    title       TEXT NOT NULL,
    title_en    TEXT,
    summary     TEXT,
    signature   TEXT,
    first_seen  TEXT NOT NULL,
    last_seen   TEXT NOT NULL,
    score       REAL DEFAULT 0,
    peak_score  REAL DEFAULT 0,
    breakdown   TEXT,
    trend_query TEXT,
    picture     TEXT
);
CREATE INDEX IF NOT EXISTS idx_clusters_last_seen ON clusters(last_seen);

CREATE TABLE IF NOT EXISTS trends (
    id         INTEGER PRIMARY KEY,
    query      TEXT NOT NULL,
    geo        TEXT NOT NULL,
    traffic    INTEGER DEFAULT 0,
    prev_traffic INTEGER DEFAULT 0,
    first_seen TEXT NOT NULL,
    last_seen  TEXT NOT NULL,
    picture    TEXT,
    entities   TEXT,
    UNIQUE(query, geo)
);

CREATE TABLE IF NOT EXISTS cluster_history (
    cluster_id INTEGER NOT NULL,
    ts         TEXT NOT NULL,
    score      REAL,
    item_count INTEGER,
    outlets    INTEGER
);
CREATE INDEX IF NOT EXISTS idx_hist ON cluster_history(cluster_id, ts);

CREATE TABLE IF NOT EXISTS alerts (
    id         INTEGER PRIMARY KEY,
    cluster_id INTEGER NOT NULL,
    ts         TEXT NOT NULL,
    score      REAL,
    delivered  INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""


def conn() -> sqlite3.Connection:
    """Thread-local connection — sqlite objects are not shareable."""
    existing = getattr(_local, "conn", None)
    if existing is not None:
        return existing
    c = sqlite3.connect(config.DB_PATH, timeout=30, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA busy_timeout=30000")
    _local.conn = c
    return c


def init() -> None:
    conn().executescript(SCHEMA)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def get_meta(key: str, default: str = "") -> str:
    row = conn().execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(key: str, value: str) -> None:
    conn().execute(
        "INSERT INTO meta(key,value) VALUES(?,?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def housekeeping() -> None:
    """Drop rows past the retention window and clusters left with no items."""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=config.RETENTION_DAYS)).isoformat()
    c = conn()
    c.execute("DELETE FROM items WHERE first_seen < ?", (cutoff,))
    hist_cutoff = (datetime.now(timezone.utc)
                   - timedelta(days=config.HISTORY_RETENTION_DAYS)).isoformat()
    c.execute("DELETE FROM cluster_history WHERE ts < ?", (hist_cutoff,))
    c.execute("DELETE FROM alerts WHERE ts < ?", (cutoff,))
    c.execute(
        "DELETE FROM clusters WHERE last_seen < ? "
        "AND id NOT IN (SELECT DISTINCT cluster_id FROM items WHERE cluster_id IS NOT NULL)",
        (cutoff,),
    )
    c.execute("DELETE FROM trends WHERE last_seen < ?", (cutoff,))

"""One polling tick, and the loop that repeats it."""

from __future__ import annotations

import json
import threading
import time
import traceback
from datetime import datetime, timezone

from . import cluster, collect, config, lexicon, notify, score, store

_state_lock = threading.Lock()
_state: dict = {
    "last_tick": None,
    "last_error": None,
    "tick_count": 0,
    "window_hours": config.MAX_ITEM_AGE_HOURS,
    "trends": [],
    "board": [],
    "gaps": [],
    "stats": {},
}


def snapshot() -> dict:
    with _state_lock:
        return json.loads(json.dumps(_state, default=str))


def run_tick(tick: int = 0, *, verbose: bool = True) -> dict:
    """Collect, cluster, score, alert. Returns a summary dict."""
    started = time.time()
    store.init()
    slow = (tick % config.SLOW_EVERY_N_TICKS) == 0
    stats = {"trends": 0, "new_items": 0, "google_news": 0,
             "publishers": 0, "youtube": 0, "chased": 0}

    trends = collect.collect_trends()
    stats["trends"] = len(trends)

    items: list[dict] = collect.trend_news_items(trends)

    gn = collect.collect_google_news(config.STANDING_QUERIES)
    stats["google_news"] = len(gn)
    items += gn

    chased = collect.chase_trends(trends)
    stats["chased"] = len(chased)
    items += chased

    if slow:
        pub = collect.collect_publishers()
        stats["publishers"] = len(pub)
        items += pub
        yt = collect.collect_youtube()
        stats["youtube"] = len(yt)
        items += yt

    stats["new_items"], stats["too_old"] = collect.ingest(items)
    cluster.assign_clusters()
    board = score.score_all(trends)
    _add_english_gloss(board)
    gap_list = score.gaps(trends, board)

    # The very first run has no history to accelerate against, so every story
    # looks like a breakout. Fill the baseline quietly and start alerting from
    # the next tick.
    if store.get_meta("bootstrapped") == "1":
        alerts = score.due_alerts(board)
        if alerts:
            notify.send_alerts(alerts)
    else:
        store.set_meta("bootstrapped", "1")
        stats["bootstrap"] = True

    if slow:
        store.housekeeping()

    stats["seconds"] = round(time.time() - started, 1)
    stats["clusters"] = len(board)

    with _state_lock:
        _state["last_tick"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        _state["tick_count"] = tick + 1
        _state["trends"] = trends[:40]
        _state["board"] = board[:60]
        _state["gaps"] = gap_list
        _state["stats"] = stats
        _state["last_error"] = None

    store.set_meta("last_tick", _state["last_tick"])
    if verbose:
        print(f"[tick {tick}] {stats}", flush=True)
    return stats


def _add_english_gloss(board: list[dict]) -> None:
    """Put a one-line English reading under the Telugu headlines near the top.

    Skipped entirely without a Groq key, and only ever asked about the handful
    of clusters a sub-editor is actually looking at.
    """
    if not config.GROQ_API_KEY:
        return
    c = store.conn()
    wanted = [cl for cl in board[:20] if lexicon.is_telugu(cl["title"])]
    cached = {}
    for cl in wanted:
        row = c.execute("SELECT title_en FROM clusters WHERE id=?", (cl["id"],)).fetchone()
        if row and row["title_en"]:
            cached[cl["title"]] = row["title_en"]

    fresh = notify.gloss([cl["title"] for cl in wanted if cl["title"] not in cached])
    for cl in wanted:
        english = cached.get(cl["title"]) or fresh.get(cl["title"])
        if not english:
            continue
        cl["title_en"] = english
        if cl["title"] not in cached:
            c.execute("UPDATE clusters SET title_en=? WHERE id=?", (english, cl["id"]))


def loop(forever: bool = True) -> None:
    tick = 0
    while True:
        started = time.monotonic()
        try:
            run_tick(tick)
        except Exception:
            err = traceback.format_exc()
            with _state_lock:
                _state["last_error"] = err.splitlines()[-1]
            print("[tick error]\n" + err, flush=True)
        tick += 1
        if not forever:
            return
        # Sleep only the remainder of the interval. Sleeping the full amount
        # after a slow tick silently doubles the gap between polls.
        elapsed = time.monotonic() - started
        rest = config.TICK_SECONDS - elapsed
        if rest < 30:
            print(f"[tick {tick - 1}] took {elapsed:.0f}s, longer than the "
                  f"{config.TICK_SECONDS}s interval", flush=True)
        time.sleep(max(30.0, rest))


def start_background() -> threading.Thread:
    thread = threading.Thread(target=loop, name="radar-poller", daemon=True)
    thread.start()
    return thread

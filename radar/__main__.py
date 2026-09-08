"""Entry point.

    python -m radar          poll continuously and serve the dashboard
    python -m radar once     run a single tick and print the top stories
    python -m radar check    verify every configured source is alive
"""

from __future__ import annotations

import sys

from . import config, poll, server, store


def _run() -> None:
    store.init()
    print("AP news radar")
    print(f"  database   {config.DB_PATH}")
    print(f"  tick       every {config.TICK_SECONDS // 60} min")
    alerts = "telegram" if config.TELEGRAM_TOKEN else "console only"
    print(f"  alerts     {alerts} at score >= {config.ALERT_SCORE}")
    from . import watchdog
    print(f"  watchdog   {'systemd' if watchdog.enabled() else 'off (not under systemd)'}")
    poll.start_background()
    try:
        server.serve()
    except KeyboardInterrupt:
        print("\nstopped")


def _once() -> None:
    store.init()
    poll.run_tick(0)
    state = poll.snapshot()
    print("\nTop searches in AP right now")
    for t in state["trends"][:10]:
        print(f"  {t['rising']:.2f}  {t['query']}  ({t['traffic']}+, {t['geo_label']})")
    print("\nTop stories")
    for c in state["board"][:12]:
        flag = f"  ← searching “{c['trend_query']}”" if c["trend_query"] else ""
        print(f"  {c['score']:5.1f}  [{c['outlet_count']} outlets, {c['age_min']}m]  "
              f"{c['title'][:78]}{flag}")
    if state["gaps"]:
        print("\nRising with thin coverage")
        for g in state["gaps"][:8]:
            print(f"  {g['query']}  ({g['traffic']}+, {g['coverage']} outlets)")


def _check() -> None:
    from . import feeds, net

    def probe(label: str, url: str, parser=feeds.parse_items) -> int:
        res = net.fetch_result(url, retries=1)
        count = len(parser(res.body)) if res.body else 0
        mark = "ok  " if count else "DEAD"
        why = "" if count else f"  ({res.error or 'HTTP ' + str(res.status)})"
        print(f"  {mark} {count:>4}  {res.ms:>5}ms  {label}{why}")
        return count

    print("Google Trends")
    for geo, label, _ in config.TREND_FEEDS:
        probe(f"{label} ({geo})", f"https://trends.google.com/trending/rss?geo={geo}",
              feeds.parse_trends)
    print("Google News (sample of standing + district queries)")
    for q, (hl, ceid), when in config.STANDING_QUERIES[:3] + config.DISTRICT_QUERIES[:2]:
        probe(f"{q} when:{when}", feeds.google_news_url(q, hl, ceid, when))
    print("Google News geo sections")
    for name, url in config.GEO_FEEDS:
        probe(name, url)
    print("Publishers")
    for name, _lang, url in config.PUBLISHER_FEEDS:
        probe(name, url)
    print("Social")
    for name, url in config.SOCIAL_FEEDS:
        probe(name, url)
    state = "enabled" if config.YOUTUBE_ENABLED else "disabled — probing anyway"
    print(f"YouTube ({state})")
    alive = 0
    for name, cid in config.YOUTUBE_CHANNELS:
        alive += 1 if probe(name, f"https://www.youtube.com/feeds/videos.xml?channel_id={cid}") else 0
    if alive and not config.YOUTUBE_ENABLED:
        print("  -> the feed is answering again: set YOUTUBE_ENABLED = True in radar/config.py")
    print("Omarchy theme")
    from . import theme
    t = theme.current()
    print(f"  {t['source']:4}       {t['name']} ({t['mode']})")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    {"run": _run, "once": _once, "check": _check}.get(cmd, _run)()

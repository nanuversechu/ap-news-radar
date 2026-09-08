"""Tests for the pieces that make the board trustworthy.

    python3 tests/test_reliability.py

Theme contrast, freshness gating, beat labelling, direction arrows — the logic
that decides what a desk sees and whether it can be read.
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Point the store at a throwaway database before anything imports config.
_tmp = tempfile.mkdtemp()
os.environ["RADAR_DB"] = os.path.join(_tmp, "t.db")
os.environ["OMARCHY_STATE"] = os.path.join(_tmp, "no-such-omarchy")

from radar import collect, config, score, store, theme  # noqa: E402

failures = 0


def check(cond: bool, label: str) -> None:
    global failures
    if not cond:
        failures += 1
        print("FAIL", label)


# --- theme: every text role must read against the background ---------------
t = theme.current()
check(t["source"] == "fallback", "no omarchy dir -> fallback palette")
for role, colour in t["roles"].items():
    if role in theme.SURFACE_ROLES or role in ("line", "on_accent"):
        continue
    check(theme.contrast(colour, t["roles"]["bg"]) >= 4.5, f"role {role} {colour} contrast >= 4.5")
check(theme.contrast(t["roles"]["on_accent"], t["roles"]["accent"]) >= 3.0, "on_accent readable on accent")

# A muddy generated palette: dim olive on near-black must be lifted, not left.
lifted = theme.ensure_contrast("#67696f", "#010419")
check(theme.contrast(lifted, "#010419") >= 4.5, "ensure_contrast lifts a dim muted")
check(theme.ensure_contrast("#e0def4", "#191724") == "#e0def4", "ensure_contrast leaves a good colour alone")
# Light theme: must darken, not lighten.
dark = theme.ensure_contrast("#ea9d34", "#faf4ed")
check(theme.contrast(dark, "#faf4ed") >= 4.5, "ensure_contrast darkens on a light ground")

# --- freshness gate --------------------------------------------------------
now = datetime.now(timezone.utc)
check(collect.is_fresh(now - timedelta(minutes=30)), "30 min old is fresh")
check(not collect.is_fresh(now - timedelta(hours=config.MAX_ITEM_AGE_HOURS, minutes=1)),
      "just past the window is not fresh")
check(not collect.is_fresh(now + timedelta(hours=2)), "a future date is not fresh")
check(not collect.is_fresh(None), "undated is refused by default")
check(collect.is_fresh(None, allow_undated=True), "undated allowed only when asked")
check(not collect.is_fresh("2023-06-17"), "a string where a datetime should be is refused")

# item_age: a nonsense date must read as stale, never as fresh
row = {"published_at": (now - timedelta(days=1158)).isoformat(), "first_seen": now.isoformat()}
check(score.item_age(row) >= score.STALE, "three-year-old item is STALE, not 0 minutes")
row = {"published_at": "not a date", "first_seen": now.isoformat()}
check(score.item_age(row) >= score.STALE, "unparseable date is STALE")
row = {"published_at": None, "first_seen": now.isoformat()}
check(score.item_age(row) < 1, "genuinely undated falls back to discovery time")

# --- beats ------------------------------------------------------------------
check(score.beat_for({"pawan_kalyan", "flood"}) == "weather", "politician + flood is a weather story")
check(score.beat_for({"chandrababu_naidu"}) == "politics", "politician alone is politics")
check(score.beat_for({"tirumala", "arrest"}) == "crime", "arrest at Tirumala is crime first")
check(score.beat_for(set()) == "general", "no entities -> general")

# --- trend direction against ~30 minutes ago ---------------------------------
store.init()
c = store.conn()
then = (now - timedelta(minutes=40)).isoformat()
c.execute("INSERT INTO trend_history(query,geo,ts,traffic,rank) VALUES (?,?,?,?,?)",
          ("పవన్ కళ్యాణ్", "IN-AP", then, 200, 5))
base = {"query": "పవన్ కళ్యాణ్", "geo": "IN-AP", "first_seen": (now - timedelta(hours=1)).isoformat()}
check(collect._direction({**base, "traffic": 500, "rank": 3})[0] == "up", "traffic 200->500 is up")
check(collect._direction({**base, "traffic": 100, "rank": 3})[0] == "down", "traffic 200->100 is down")
check(collect._direction({**base, "traffic": 200, "rank": 2})[0] == "up", "same traffic, rank 5->2 is up")
check(collect._direction({**base, "traffic": 200, "rank": 9})[0] == "down", "same traffic, rank 5->9 is down")
check(collect._direction({**base, "traffic": 200, "rank": 5})[0] == "flat", "unchanged is flat")
check(collect._direction({**base, "first_seen": now.isoformat(), "traffic": 200, "rank": 5})[0] == "new",
      "first seen this tick is new")
check(collect._direction({"query": "x", "geo": "IN-AP", "first_seen": base["first_seen"],
                          "traffic": 1, "rank": 1})[0] == "flat", "no history -> flat, not an error")

# --- story direction from cluster history -----------------------------------
c.execute("INSERT INTO clusters(id,title,first_seen,last_seen) VALUES (77,'t',?,?)",
          (then, now.isoformat()))
c.execute("INSERT INTO cluster_history(cluster_id,ts,score,item_count,outlets) VALUES (77,?,40,3,2)", (then,))
check(score._direction(77, 50.0, 2, 60)[0] == "up", "score 40->50 is up")
check(score._direction(77, 30.0, 2, 60)[0] == "down", "score 40->30 is down")
check(score._direction(77, 42.0, 2, 60)[0] == "flat", "score 40->42 is flat")
check(score._direction(77, 42.0, 5, 60)[0] == "up", "+3 outlets is up even with a flat score")
check(score._direction(78, 42.0, 1, 2)[0] == "new", "no history and 2 minutes old is new")

# --- source health bookkeeping ------------------------------------------------
store.record_source("X", "http://x", "news", True, count=5, ms=100)
store.record_source("X", "http://x", "news", False, error="HTTP 500")
store.record_source("X", "http://x", "news", False, error="HTTP 500")
h = {r["name"]: r for r in store.source_health()}["X"]
check(h["failures"] == 2 and h["total_ok"] == 1 and h["total_fail"] == 2, "consecutive failures counted")
store.record_source("X", "http://x", "news", True, count=5, ms=100)
h = {r["name"]: r for r in store.source_health()}["X"]
check(h["failures"] == 0, "a success resets the consecutive count")

total = 36
print(f"{total - failures}/{total} passed")
sys.exit(1 if failures else 0)

"""Regression tests for the matching layer.

    python3 tests/test_matching.py

These are the judgement calls the radar gets wrong most expensively: merging
two unrelated stories about the same politician, or failing to merge a Telugu
headline with its English twin.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from radar import lexicon as L  # noqa: E402

MERGE_CASES = [
    # (headline a, headline b, should they be one story?)
    ("AP govt announces pension hike for farmers",
     "Andhra Pradesh government hikes farmer pension", True),
    ("Pawan Kalyan’s brother Naga Babu appointed chairman of AP Green Executive Committee",
     "Pawan Kalyan: గ్రీన్ ఎగ్జిక్యూటివ్ కమిటీ చైర్మన్‌గా నాగబాబు", True),
    ("Heavy rains lash Vizag, IMD issues warning",
     "Visakhapatnam records heavy rainfall as IMD warns", True),
    ("పవన్ కళ్యాణ్ విశాఖపట్నంలో పర్యటన",
     "Pawan Kalyan to visit Visakhapatnam today", True),
    # Same person, different story — must stay apart.
    ("Chandrababu Naidu reviews Polavaram works",
     "Pawan Kalyan tours Visakhapatnam", False),
    ("TTD announces extra darshan tokens for Tirumala",
     "Tirupati laddu row: TTD chief responds", False),
    ("JKM vs TKR, Caribbean Premier League",
     "Sri Lanka bowler worst record", False),
]

LOCALITY_CASES = [
    ("Bhogapuram airport opens in Vizianagaram", "AP"),
    # The cabinet and the opposition bench count, in either script.
    ("Botsa Satyanarayana hits back at TDP over ZP chairman", "AP"),
    ("మంత్రి అనిత సమీక్ష: గంజాయిపై ఉక్కుపాదం", "AP"),
    ("Payyavula Keshav presents supplementary budget", "AP"),
    ("AP cabinet clears local body poll reservations", "AP"),
    ("DSC results released: 16,347 posts filled", "AP"),
    # Telugu-sphere, not state news.
    ("Prabhas' next film gets a release date", "Telugu"),
    ("KTR slams Revanth over Musi project", "Telugu"),
    # National.
    ("Kohli century seals series for India", "wider"),
    ("Amit Shah reviews security in Delhi", "wider"),
    ("Chandrababu Naidu chairs cabinet meeting", "AP"),
    ("Revanth Reddy on Telangana funds", "Telugu"),
    # Topic words alone must not make something local news.
    ("JKM vs TKR Caribbean Premier League wicket", "wider"),
    ("Manchester United sign new striker", "wider"),
    # "Naidu" is a very common surname; on its own it is not AP politics.
    ("Who's Rohan Naidu, Indian astronomer behind black hole star discovery", "wider"),
]

TREND_CASES = [
    ("పవన్ కళ్యాణ్", "Pawan Kalyan to visit Visakhapatnam today", True),
    ("విశాఖపట్నం", "Air India shifts all Vizag flights to Bhogapuram airport", True),
    ("పవన్ కళ్యాణ్", "Chandrababu Naidu reviews Polavaram works", False),
    ("ananya raj indian film actress", "Film body pays tribute to actor Ananya Raj", True),
    # A generic topic word must not let a query claim an unrelated cluster.
    ("ananya raj indian film actress",
     "Pawan Kalyan directs officials to alert public over elephant movement", False),
    # 18 Aug 2026: a trending astronomer called Rohan Naidu was credited with
    # every Chandrababu story on the board, because both contain "Naidu".
    ("rohan naidu", "Who's Rohan Naidu, Indian astronomer behind black hole star discovery", True),
    ("rohan naidu", "Jagan slams Naidu over suspension of five teachers seeking TET exemption", False),
    ("rohan naidu", "CM Naidu Directs Officials To Step Up Search For Missing Fishermen", False),
]


def main() -> int:
    failures = 0

    for a, b, expected in MERGE_CASES:
        score = L.similarity(a, b)
        got = score >= L.MERGE_THRESHOLD
        if got != expected:
            failures += 1
            print(f"FAIL merge={got} want={expected} ({score:.3f})\n  {a}\n  {b}")

    for headline, expected in LOCALITY_CASES:
        _, label = L.locality(L.entities(headline))
        if label != expected:
            failures += 1
            print(f"FAIL locality={label} want={expected}\n  {headline}")

    for query, headline, expected in TREND_CASES:
        got = L.matches_trend(query, headline) >= 0.55
        if got != expected:
            failures += 1
            print(f"FAIL trend={got} want={expected}\n  {query} / {headline}")

    total = len(MERGE_CASES) + len(LOCALITY_CASES) + len(TREND_CASES)
    print(f"{total - failures}/{total} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

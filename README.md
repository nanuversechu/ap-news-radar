# Andhra Pradesh news radar

Tells you what Andhra Pradesh is searching Google for **right now**, which of
those searches the press has already covered, and which it has not.

Built for a desk, not a data scientist. No API keys, no accounts, no
`pip install` — Python's standard library and nothing else.

## Bookmark this

**<http://127.0.0.1:8787>**

It runs as a background service that starts on boot and restarts itself if it
ever crashes, so the link should simply always work. Nothing to launch.

The first tick after a reboot takes about a minute and stays quiet on purpose:
it has no history to compare against yet, so it fills the baseline instead of
alerting. After that it refreshes every 5 minutes.

### Installing it on another machine

Needs nothing but Python 3.11+ — no `pip install`, no keys.

```bash
git clone https://github.com/nanuversechu/ap-news-radar.git ~/ap-news-radar
```

```bash
cp ~/ap-news-radar/ap-radar.service ~/.config/systemd/user/
```

Edit `RADAR_CONTACT` in that file to your own address (it goes in the
User-Agent so a webmaster can reach a human), then:

```bash
systemctl --user daemon-reload && systemctl --user enable --now ap-radar
```

```bash
loginctl enable-linger $USER
```

The last line is what lets it run before you log in. The database rebuilds
itself from scratch within a couple of ticks, so nothing needs copying across.

### If the link is ever dead

```bash
systemctl --user status ap-radar
```

That tells you whether it is running and shows the last few log lines. To
restart, see logs, or stop it:

```bash
systemctl --user restart ap-radar
```

```bash
journalctl --user -u ap-radar -n 50
```

The service file is `~/.config/systemd/user/ap-radar.service`. Lingering is
enabled for your user, which is what lets it run before you log in.

`./run.sh` still works if you would rather run it by hand in a terminal — but
stop the service first, or the two will fight over the port.

---

## The look

Terminal, on purpose: monospace throughout, square corners everywhere, meters
drawn with block characters (`███·······`) rather than graphics, and a status
bar in the manner of tmux. The palette is Rose Pine — muted rose, gold, pine
and foam — which follows your system light/dark setting.

The accent values are darkened from the published Rose Pine set. Those are
tuned for large blocks of syntax-highlighted code; as small text they fall to
around 2:1, which made the score the least readable thing on screen. Every
text role now clears 4.78:1 in both themes.

## What it watches

### The freshness contract

**Nothing older than 2 hours, anywhere.** Enforced three times over: at ingest
(old items never enter the database), at scoring (a story whose freshest report
has aged out leaves the board), and in every query window sent to Google. The
status bar shows the window and how many items were refused last tick —
typically 200-plus against 30 kept.

To widen it, set `RADAR_MAX_AGE_HOURS` in the service file, or
`MAX_ITEM_AGE_HOURS` in `config.py`. Everything downstream — board window,
alert age limit, the acceleration comparison — keys off that one number.

### Sources

| Signal | Source | Cost | Refresh |
|---|---|---|---|
| What AP is searching | Google Trends RSS, `geo=IN-AP` | free, keyless | 5 min |
| Same for Telangana + India | Google Trends RSS, `IN-TG` / `IN` | free, keyless | 5 min |
| Breaking coverage | Google News RSS, 30 standing queries in Telugu and English, all `when:2h` | free, keyless | 5 min |
| Coverage of what's rising | Google News searched for each rising trend | free, keyless | 5 min |
| AP newspapers | 9 publisher RSS feeds (below) | free | 15 min |
| ~~Telugu TV~~ | ~~7 YouTube channel RSS feeds~~ | **dead since 18 Aug 2026** — see below | — |

The nine publisher feeds: **The Hindu (AP)**, **NTV Telugu**, **10TV**,
**Gulte**, **Telugu360**, **Hans India (AP)**, **Deccan Chronicle**, **Times of
India** (Vijayawada and Visakhapatnam). Government releases arrive through a
`site:pib.gov.in` search feed, since PIB's own RSS is broken.

Roughly 185 distinct outlets reach the board in a given tick, because the
Google News queries pull from far more mastheads than the nine we poll directly.

Everything is polled politely: one request per host per 1.2 s, six hosts in
parallel, a real User-Agent with a contact address.

### Deliberately left out

- **Andhra Jyothy** — its RSS is a frozen archive. All 1,000 items are dated
  June 2023, and it was the single worst source of stale material on the board:
  a sanity check meant to reject impossible dates was instead falling back to
  discovery time, so three-year-old articles were being served as zero minutes
  old. Both the feed and that fallback are gone.
- **Telugu TV via YouTube** — `youtube.com/feeds/videos.xml` served 15 entries
  per channel on 17 Aug 2026 and returned 404 for every channel the next
  morning, including the `playlist_id` and legacy `user=` variants, while the
  channel pages still load. The endpoint broke, not the IDs, which are still in
  `config.py`. `./run.sh check` probes it anyway and tells you if it returns;
  flip `YOUTUBE_ENABLED = True` then. The loss is small — the same newsrooms
  are covered through their websites.
- **GDELT** — unreachable from this network on every attempt. A source that
  times out is worse than no source, because it looks like it is working.
- **X/Twitter** — no usable free tier since February 2026.
- **pytrends** — archived April 2025. The RSS feed above does the same job and
  does not break.
- **LaBSE / IndicTrans2 embeddings** — a 2 GB model on a CPU-only laptop for a
  job the lexicon does in a millisecond. See below.

---

## How it decides what matters

Every item is grouped into a **story cluster**, then each cluster is scored:

```
score = 100 × locality × ( 0.34 trend        does a live Google search match this?
                         + 0.22 acceleration reports in the last hour vs the three before
                         + 0.20 corroboration how many independent outlets have it
                         + 0.14 velocity     raw reports per hour
                         + 0.10 freshness    decays with a 2½ hour half-life )
```

`locality` is `1.0` when the story names an AP place, politician or
institution, `0.55` for the wider Telugu sphere, `0.18` otherwise. This is what
keeps a Caribbean Premier League scorecard off an Andhra Pradesh board.

**Alerts** fire at score ≥ 62, but only when at least **two independent
outlets** have the story and it is under three hours old — the single best
filter against a bot spike or a coordinated film promotion. Same story will not
re-alert for 90 minutes.

### The bit that earns its keep

**Rising searches, thin coverage.** A query climbing in AP that no one has
written about, or that one outlet has to itself, is a commissioning list. It is
the second panel on the dashboard.

### Cross-language matching without a GPU

A Telugu headline and its English twin have to land in one cluster, or every
story gets counted twice and corroboration is meaningless.

The textbook answer is LaBSE. On a 16 GB CPU-only laptop that is a bad trade,
so this uses the fact that AP news revolves around a knowable cast — about
seventy people, places, parties and recurring topics, listed in both scripts in
`radar/config.py`. Match those and the headlines collapse onto one signature.

```
"Pawan Kalyan's brother Naga Babu appointed chairman of AP Green Executive Committee"
"Pawan Kalyan: గ్రీన్ ఎగ్జిక్యూటివ్ కమిటీ చైర్మన్‌గా నాగబాబు"
                                                    → similarity 1.00, one story
```

It also exploits something real about these outlets: their Telugu headlines
almost always carry a Latin kicker (`Visakhapatnam Airport | …`), which is a
genuine cross-script signal.

The limitation is honest: **a name not in the lexicon is a name it cannot match
across scripts.** Adding one is two lines, and it is the main upkeep this tool
needs.

```python
# radar/config.py
"naga_babu": ("person", ["naga babu", "nagababu", "నాగబాబు", "నాగ బాబు"]),
```

Run `python3 tests/test_matching.py` after editing — it checks that same-story
pairs merge and same-politician-different-story pairs do not.

**Aliases must be distinctive.** `naidu` was originally an alias for
Chandrababu; on 18 Aug 2026 a trending astronomer called Rohan Naidu was
credited with every Chandrababu story on the board, and read as AP news. A
surname that thousands of people share is not an identifier. The tests now
cover that case.

---

## Commands

```bash
./run.sh              # poll every 5 min + serve the dashboard
./run.sh once         # one tick, print the top stories, exit
./run.sh check        # is every configured feed still alive?
python3 tests/test_matching.py
```

`check` is the one to run if the board ever looks thin — publishers change
their RSS paths without warning.

## Optional extras

Neither is needed; both are free.

**Telegram alerts to a desk group.** Message `@BotFather` → `/newbot` → paste
the token below, add the bot to your group, and get the chat id from
`https://api.telegram.org/bot<TOKEN>/getUpdates`.

```bash
export RADAR_TELEGRAM_TOKEN="123456:ABC..."
export RADAR_TELEGRAM_CHAT="-1001234567890"
```

**English gloss for Telugu headlines** via the Groq free tier — the same key
the CUE Genius extension uses.

```bash
export GROQ_API_KEY="gsk_..."
```

## Tuning

Everything adjustable is in `radar/config.py`, nothing else needs editing:

| Want to | Change |
|---|---|
| Watch a new name, place or topic | `LEXICON` |
| Add a newspaper | `PUBLISHER_FEEDS` |
| Add a TV channel | `YOUTUBE_CHANNELS` (RSS is `?channel_id=UC…`) |
| Track a new beat | `STANDING_QUERIES` |
| Alert more or less often | `ALERT_SCORE` (62), `ALERT_COOLDOWN_MIN` |
| Value search demand over corroboration | `WEIGHTS` |
| Poll faster | `TICK_SECONDS` — but read the note below |

**On polling faster:** 5 minutes is already faster than Trends refreshes
(~10 min). Going below that adds load without adding signal, and risks a
temporary Google block that costs you the source for hours.

## Data

One SQLite file, `radar.db`, in this folder. Items, clusters, trends and a
score history are kept 14 days, then pruned automatically. Timestamps are
stored UTC and displayed in IST.

Story age comes from each report's **published** time, not from when the radar
happened to find it — otherwise an eight-hour-old wire story reads as a
breaking one.

## Scope

This is a monitoring tool, not a syndication tool. It stores headlines, links
and timestamps so a desk can decide what to chase; it does not copy article
text. Every source is either an official RSS feed or a public API, polled at a
rate below what any of them ask for.

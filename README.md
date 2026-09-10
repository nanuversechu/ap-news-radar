# Andhra Pradesh news radar

Tells you what Andhra Pradesh is searching for and reading **right now**,
which of it the press has already covered, and which it has not — so a desk can
write to demand instead of guessing at it.

Built for a desk, not a data scientist. No API keys, no accounts, no
`pip install` — Python's standard library and nothing else.

## See it without installing anything

**<https://nanuversechu.github.io/ap-news-radar/>** — a copy of the live
dashboard, exactly as the desk sees it. **It refreshes itself every 15
minutes**, so the link is current without anyone touching it; the time it was
taken is in the top bar. Nothing animates on the page, and every link opens the
real article.

Allowing for GitHub's ten-minute CDN cache, a visitor sees a board at most
about twenty-five minutes old.

The refresh is a systemd timer, `ap-radar-publish.timer`, running
[`publish.sh`](publish.sh). It only publishes when the radar answered and
produced a real page, so a stopped radar leaves the last good snapshot up
rather than replacing it with an error. The page is force-pushed to a
single-commit `gh-pages` branch, so the repository stays the size of one
snapshot however often it refreshes.

```bash
systemctl --user list-timers ap-radar-publish.timer
```

```bash
./publish.sh          # publish immediately, by hand
```

The Telangana twin is at <https://nanuversechu.github.io/tg-news-radar/>.

## Bookmark this

**<http://127.0.0.1:8787>** — the live one, on the desk machine.

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

It wears your Omarchy theme. The server reads
`~/.local/state/omarchy/current/theme/colors.toml` on every refresh, so
`omarchy theme set …` restyles the dashboard within thirty seconds, no restart.
Font is JetBrainsMono Nerd Font, the one your terminal uses. Square corners
everywhere, a waybar-style status bar, meters drawn in block characters.

Generated themes can be muddy — one names an olive "red" — and a dim colour
on a dark ground is unreadable at 13 px. So every text role is contrast-checked
against the theme background and nudged in lightness until it clears 4.5:1,
hue and saturation kept. The desktop keeps its palette; the text stays legible.
Without Omarchy it falls back to Rose Pine.

Direction is never colour alone: **▲ up · ▼ down · ● new · → flat** on
every trend and story, so it reads even on a palette where red and green agree.

### On the board

Four panels, in the order a desk needs them.

1. **Searching now** — every live Google search from Andhra Pradesh (then
   Telangana, then India, at lower weight), each with an arrow against thirty
   minutes ago, its traffic bucket, an `AP` mark when it names an AP place,
   person or institution, and — the important part — **its coverage right
   now**: `6 outlets`, `1 outlet`, or `uncovered`. Click a search and the board
   narrows to the stories that answer it. Hindi, Marathi, Tamil and Kannada
   queries from the India-wide feed are dropped; they are not this desk's
   readers.
2. **Trailing** — searches that were trending and have dropped off in the last
   90 minutes, with what they peaked at. A story that has stopped rising is as
   useful to know as one that has started.
3. **Top stories** — Google News' current ranking for **Andhra Pradesh,
   Vijayawada and Visakhapatnam**, English and Telugu interleaved in Google's
   own order, newest first, nothing older than two hours. Fetched with no
   account and no cookies, so it is what Google shows a stranger, not what it
   shows you. (Google's own city "sections" were tried and dropped: they ran
   12 to 60 hours stale.)
4. **Reading** — what people are reading, as opposed to searching: Telugu
   Wikipedia's most-viewed pages. The pageview data is daily, so the list is
   *yesterday* and says so. Each page is marked `✓ on board` when a story on
   the board matches it. (Times of India's most-read lists were tried and
   dropped: national, and never about AP.)
5. **Story board** — everything published in the last two hours, scored, with
   direction arrows (`▲ +15`), outlet counts (`+2` when more newsrooms picked it
   up), and `GN #3` when Google's own front page ranks it.

**Hover any score** for what it is made of: the six components with their
percentages, the direction against fifteen minutes ago, and what each bar
under the number means.

**Keyboard**: `/` filter · `j` `k` move · `o` open · `1`–`5` tabs · `s`
sources · `esc` clear (or drop the search filter).

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
| Google's front page | Google News top stories, Telugu and English, **rank kept** | free, keyless | 5 min |
| Every Google News section | Nation, World, Business, Technology, Entertainment, Sports, Science, Health (Telugu) + Nation, Business, Entertainment, Sports (English) | free, keyless | 15 min |
| Breaking coverage | Google News RSS, 30 standing queries in Telugu and English, all `when:2h` | free, keyless | 5 min |
| District sweeps | 18 more Google News queries, a third each tick | free, keyless | every district every 15 min |
| Coverage of what's rising | Google News searched for each rising trend | free, keyless | 5 min |
| Top stories by place | Google News search for Andhra Pradesh, Vijayawada, Visakhapatnam, both languages, `when:2h` | free, keyless | 5 min |
| AP newspapers | 17 publisher RSS feeds (below) | free | 15 min |
| What Telugu readers looked up | Telugu Wikipedia most-viewed pages (daily data) | free, keyless | hourly |
| Chatter | Reddit r/andhrapradesh (marked ◆ social) | free, keyless | 15 min |
| ~~Telugu TV~~ | ~~7 YouTube channel RSS feeds~~ | **dead since 18 Aug 2026** — see below | — |

The seventeen publisher feeds: **The Hindu** (AP, Vijayawada, Visakhapatnam),
**TV9 Telugu**, **NTV Telugu**, **10TV**, **Sakshi**, **GreatAndhra**,
**Gulte**, **Telugu360**, **Vaartha**, **Prabha News**, **Oneindia Telugu**,
**Hans India (AP)**, **Deccan Chronicle**, **Times of India** (Vijayawada and
Visakhapatnam). Government releases arrive through a `site:pib.gov.in` search
feed, since PIB's own RSS is broken.

Every source's outcome is recorded each poll — 42 of them. The status bar shows `src 44/44`;
click it (or press `s`) for the table — items, latency, last success, and the
error when there is one. A source is "ok" only when it answered *and* returned
something parseable; a 200 with an empty body counts as a failure, and a feed
that answers but has produced no item inside the freshness window for a day is
marked `quiet` — alive to a monitor, dead to a desk.

Roughly 185 distinct outlets reach the board in a given tick, because the
Google News queries pull from far more mastheads than the seventeen we poll directly.

Everything is polled politely: one request per host per 1.2 s, six hosts in
parallel, a real User-Agent with a contact address.

### Built to stay up

- **A hung poller gets restarted, not admired.** The service runs as
  `Type=notify` with `WatchdogSec=600`; the poll loop heartbeats to systemd
  every 30 seconds, including while sleeping between ticks. If the heartbeat
  stops — a socket that never returns, a deadlock — systemd kills and restarts
  it. `Restart=always` alone only helps when a process actually dies.
- **No single fetch can stall a tick.** Each request is bounded in time and a
  hung one is recorded as such and skipped.
- **Push-back is obeyed.** A 429 puts that host on a 30-minute cooldown
  (honouring `Retry-After` when sent); repeated 5xx, five minutes. The cooldown
  shows in the status bar. This is what stops a temporary limit becoming a ban.
- **Last good data survives a bad tick.** If Google Trends or Google News comes
  back empty, the previous board stays up and a notice says which sources were
  degraded — the page is told, not blanked.
- **A laptop lid closing does not stall it.** Linux's monotonic clock stops
  during suspend, so a sleep timer set before the lid closed is still "minutes
  away" hours later. The poll loop watches the wall clock too, and polls the
  moment the machine is back.
- **Staleness is loud.** If no tick has completed in three intervals the live
  dot becomes a red `▲ STALE 14m` segment. The bar also counts down to the next
  poll, so a healthy radar is visibly healthy.
- **The poller thread is checked for life** on every health request and revived
  if it has died. `/api/health` returns 503 if it cannot be.
- **The database migrates itself** forward when new columns are added, so an
  upgrade is a `git pull` and a restart.

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
score = 100 × locality × ( 0.32 trend        does a live Google search match this?
                         + 0.20 acceleration reports in the last 30 min vs the 90 before
                         + 0.18 corroboration how many independent outlets have it
                         + 0.12 prominence   rank on Google News' front page, if any
                         + 0.10 velocity     raw reports per hour
                         + 0.08 freshness    decays with a 40 minute half-life )
```

`locality` is `1.0` when the story names an AP place, politician or
institution, `0.55` for the wider Telugu sphere (Telangana politics, Telugu film
stars), `0.18` otherwise. It is derived from the lexicon, so adding a minister
there is enough. This is what
keeps a Caribbean Premier League scorecard off an Andhra Pradesh board.

**Alerts** fire at score ≥ 62, but only when at least **two independent
outlets** have the story and it is under 100 minutes old — the single best
filter against a bot spike or a coordinated film promotion. Same story will not
re-alert for 90 minutes.

One honest consequence of the two-hour window: single-outlet stories rank
higher than they used to, because there simply is not time for corroboration to
build. Alerts still require two outlets, so they will not fire on one report.

### The bit that earns its keep

**Rising searches, thin coverage.** A query climbing in AP that no one has
written about, or that one outlet has to itself, is a commissioning list. It is
the second panel on the dashboard.

### Cross-language matching without a GPU

A Telugu headline and its English twin have to land in one cluster, or every
story gets counted twice and corroboration is meaningless.

The textbook answer is LaBSE. On a 16 GB CPU-only laptop that is a bad trade,
so this uses the fact that AP news revolves around a knowable cast — about a
hundred and fifty people, places, parties and recurring topics, listed in both
scripts in `radar/config.py`: all 26 districts and their towns, the cabinet,
the opposition bench, the institutions, the film and cricket names AP searches
for constantly. Match those and the headlines collapse onto one signature.

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

`check` probes every configured source — trends, news queries, geo sections,
publishers, social, YouTube — with status and latency, and reports which
Omarchy theme it sees. Run it if the board ever looks thin.

```bash
python3 tests/test_reliability.py
```

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

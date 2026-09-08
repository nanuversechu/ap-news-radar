"""Sources, lexicon and tuning knobs for the AP news radar.

Everything a human might want to change lives here. No other file needs editing
to add a newspaper, a YouTube channel or a name to watch.
"""

from __future__ import annotations

import os

# --------------------------------------------------------------------------
# Identity / politeness
# --------------------------------------------------------------------------

# Sent in the User-Agent so a webmaster can reach a human. Set RADAR_CONTACT
# to your own address; the systemd unit does this. Kept out of the source so
# the repository carries no personal address.
CONTACT = os.environ.get("RADAR_CONTACT", "ap-news-radar@localhost")
USER_AGENT = (
    "APNewsRadar/1.0 (newsroom monitoring; +mailto:%s) "
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/128.0 Safari/537.36"
    % CONTACT
)

# Seconds to wait between two requests to the same host.
HOST_DELAY = 1.2
FETCH_TIMEOUT = 25
MAX_PARALLEL = 6
# How long to leave a host alone after it pushes back. A 429 obeyed now is a
# ban avoided later.
COOLDOWN_429 = 30 * 60
COOLDOWN_5XX = 5 * 60

# --------------------------------------------------------------------------
# Omarchy — the dashboard reads the live desktop theme from here.
# --------------------------------------------------------------------------

OMARCHY_STATE_DIR = os.environ.get(
    "OMARCHY_STATE", os.path.expanduser("~/.local/state/omarchy/current"))
OMARCHY_THEME_DIR = os.path.join(OMARCHY_STATE_DIR, "theme")

# --------------------------------------------------------------------------
# Poll cadence (seconds)
# --------------------------------------------------------------------------

TICK_SECONDS = int(os.environ.get("RADAR_TICK", "300"))  # 5 minutes
SLOW_EVERY_N_TICKS = 3  # publisher + youtube feeds run every 3rd tick (~15 min)

# The freshness contract. Anything published longer ago than this is refused at
# ingest and never reaches the board — this is a "what is breaking now" radar,
# not an archive. Raise it if the board ever looks too thin.
MAX_ITEM_AGE_HOURS = float(os.environ.get("RADAR_MAX_AGE_HOURS", "2"))

# How long a story stays on the live board. Kept equal to the ingest window so
# the board cannot outlive the material it is built from.
BOARD_WINDOW_HOURS = MAX_ITEM_AGE_HOURS
# Rows older than this are deleted on housekeeping (history for the baseline).
RETENTION_DAYS = 14
# The per-tick score history is only useful for recent trajectory, and it is by
# far the biggest table, so it is pruned much harder than everything else.
HISTORY_RETENTION_DAYS = 2
# Below this score a cluster's trajectory is not worth recording.
HISTORY_MIN_SCORE = 20.0

# --------------------------------------------------------------------------
# Google Trends — the "what is AP searching for right now" signal.
# Free, keyless RSS. IN-AP is the Andhra Pradesh sub-region.
# --------------------------------------------------------------------------

TREND_FEEDS = [
    # (geo code, human label, weight applied to the trend's score)
    ("IN-AP", "Andhra Pradesh", 1.0),
    ("IN-TG", "Telangana", 0.55),   # Telugu stories cross the border constantly
    ("IN", "India", 0.45),
]

# --------------------------------------------------------------------------
# Google News RSS — standing queries. `when:` forces freshness.
# Each entry: (query, hl, ceid, freshness window)
# --------------------------------------------------------------------------

_TE = ("te-IN", "IN:te")
_EN = ("en-IN", "IN:en")

STANDING_QUERIES: list[tuple[str, tuple[str, str], str]] = [
    # Broad state sweeps
    ("Andhra Pradesh", _EN, "2h"),
    ("ఆంధ్రప్రదేశ్", _TE, "2h"),
    ("ఆంధ్ర ప్రదేశ్ వార్తలు", _TE, "2h"),
    ("AP news", _EN, "2h"),
    ("Amaravati", _EN, "2h"),
    ("అమరావతి", _TE, "2h"),
    # Politics
    ("Chandrababu Naidu", _EN, "2h"),
    ("చంద్రబాబు", _TE, "2h"),
    ("Pawan Kalyan", _EN, "2h"),
    ("పవన్ కళ్యాణ్", _TE, "2h"),
    ("Jagan YSRCP", _EN, "2h"),
    ("జగన్", _TE, "2h"),
    ("Lokesh TDP", _EN, "2h"),
    # Faith / mass-interest
    ("Tirumala TTD", _EN, "2h"),
    ("తిరుమల", _TE, "2h"),
    # Weather / disaster — the classic AP virality engine
    ("Andhra Pradesh rains IMD warning", _EN, "2h"),
    ("వర్షాలు హెచ్చరిక", _TE, "2h"),
    ("Godavari Krishna flood", _EN, "2h"),
    ("cyclone Bay of Bengal Andhra", _EN, "2h"),
    # Infrastructure / money
    ("Polavaram project", _EN, "2h"),
    ("Visakhapatnam", _EN, "2h"),
    ("విశాఖపట్నం", _TE, "2h"),
    ("Vijayawada", _EN, "2h"),
    # Exams / jobs — huge search volume in AP
    ("AP results APPSC EAPCET", _EN, "2h"),
    ("ఏపీ ఫలితాలు", _TE, "2h"),
    # Entertainment
    ("Tollywood", _EN, "2h"),
    ("టాలీవుడ్", _TE, "2h"),
    # Crime / accidents
    ("Andhra Pradesh accident police", _EN, "2h"),
    # Official announcements (PIB serves no working RSS of its own)
    ("site:pib.gov.in Andhra Pradesh", _EN, "2h"),
    ("Andhra Pradesh government GO announcement", _EN, "2h"),
]

# District sweeps. Thirteen more requests to one host every tick would add load
# without adding much signal, so a third of this list runs each tick: every
# district is covered every 15 minutes at constant per-tick cost.
DISTRICT_QUERIES: list[tuple[str, tuple[str, str], str]] = [
    ("Guntur", _EN, "2h"), ("Nellore", _EN, "2h"), ("Kurnool", _EN, "2h"),
    ("Tirupati", _EN, "2h"), ("Kakinada", _EN, "2h"), ("Rajamahendravaram", _EN, "2h"),
    ("Anantapur", _EN, "2h"), ("Kadapa", _EN, "2h"), ("Srikakulam", _EN, "2h"),
    ("Vizianagaram", _EN, "2h"), ("Eluru", _EN, "2h"), ("Ongole", _EN, "2h"),
    ("గుంటూరు", _TE, "2h"), ("నెల్లూరు", _TE, "2h"), ("కర్నూలు", _TE, "2h"),
    ("తిరుపతి", _TE, "2h"), ("కాకినాడ", _TE, "2h"), ("రాజమహేంద్రవరం", _TE, "2h"),
]
DISTRICT_ROTATION = 3

# Google News "geo" sections. Only these three AP places return anything; the
# other twelve districts answer with an empty feed. They ignore `when:`, so the
# ingest gate does the freshness work.
GEO_FEEDS: list[tuple[str, str]] = [
    ("Google News · Visakhapatnam", "https://news.google.com/rss/headlines/section/geo/Visakhapatnam?hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News · Amaravati", "https://news.google.com/rss/headlines/section/geo/Amaravati?hl=en-IN&gl=IN&ceid=IN:en"),
    ("Google News · Vijayawada", "https://news.google.com/rss/headlines/section/geo/Vijayawada?hl=en-IN&gl=IN&ceid=IN:en"),
]

# Reddit's unauthenticated RSS is real but tight: three subreddit fetches in a
# row drew a 429. One feed, every 15 minutes, with the host cooled down on any
# push-back, stays well inside that. Kind "social" so the desk can tell chatter
# from reporting.
SOCIAL_FEEDS: list[tuple[str, str]] = [
    ("Reddit r/andhrapradesh", "https://www.reddit.com/r/andhrapradesh/new.rss"),
]

# Direction arrows compare a trend against this long ago, not the last poll.
TREND_LOOKBACK_MIN = 30
# Stories likewise, and a score has to move this much to earn an arrow.
STORY_LOOKBACK_MIN = 15
STORY_DELTA = 6.0
# A query that vanished from the feed within this window is shown as trailing.
TRAILING_WINDOW_MIN = 90

# When a Google Trends query is rising, we immediately search news for it.
# This is what turns "people are searching X" into "here is the coverage of X".
TREND_CHASE_WINDOW = "2h"
MAX_TREND_CHASES = 12  # per tick, highest-scoring rising trends first

# --------------------------------------------------------------------------
# Publisher RSS — all verified live.
# --------------------------------------------------------------------------

PUBLISHER_FEEDS: list[tuple[str, str, str]] = [
    # (outlet name, language, url)
    ("The Hindu AP", "en", "https://www.thehindu.com/news/national/andhra-pradesh/feeder/default.rss"),
    ("NTV Telugu", "te", "https://ntvtelugu.com/feed"),
    ("Telugu360", "en", "https://telugu360.com/feed/"),
    ("Hans India AP", "en", "https://www.thehansindia.com/rss/andhra-pradesh"),
    ("Gulte", "te", "https://telugu.gulte.com/feed"),
    ("10TV", "te", "https://10tv.in/latest/feed"),
    ("Deccan Chronicle", "en", "https://www.deccanchronicle.com/rss_feed/"),
    ("Times of India Vijayawada", "en", "https://timesofindia.indiatimes.com/rssfeeds/-2128816011.cms"),
    ("Times of India Visakhapatnam", "en", "https://timesofindia.indiatimes.com/rssfeeds/-2128839596.cms"),
    # Added 8 Sep 2026, each verified live and dated at the time.
    ("TV9 Telugu", "te", "https://tv9telugu.com/feed"),
    ("Sakshi", "te", "https://www.sakshi.com/rss.xml"),
    ("GreatAndhra", "en", "https://www.greatandhra.com/rss"),
    ("Prabha News", "te", "https://www.prabhanews.com/feed/"),
    ("Vaartha", "te", "https://www.vaartha.com/feed/"),
    ("Oneindia Telugu", "te", "https://telugu.oneindia.com/rss/telugu-news-fb.xml"),
    ("The Hindu Vijayawada", "en", "https://www.thehindu.com/news/cities/Vijayawada/feeder/default.rss"),
    ("The Hindu Visakhapatnam", "en", "https://www.thehindu.com/news/cities/Visakhapatnam/feeder/default.rss"),
    # PIB's ViewRss.aspx answers 200 with an empty body, so official releases
    # are covered by the site: query in STANDING_QUERIES instead.
    # Tried and dead on 8 Sep 2026: New Indian Express, Samayam, Zee Telugu,
    # News18 Telugu, Deccan Herald, Indian Express Vijayawada, AP7AM, TV5 web,
    # Andhra Prabha, HT Telugu, Eenadu, and every Sakshi sub-feed.
]

# --------------------------------------------------------------------------
# YouTube channel RSS.
#
# DISABLED 18 Aug 2026. youtube.com/feeds/videos.xml returned 200 with 15
# entries per channel on 17 Aug and 404 for every channel the next morning —
# including the playlist_id and legacy user= variants — while the channel
# pages themselves still load. The endpoint, not these IDs, is the problem.
#
# `./run.sh check` probes it anyway, so you will see it if it comes back.
# Flip this to True when it does.
# --------------------------------------------------------------------------

YOUTUBE_ENABLED = False

YOUTUBE_CHANNELS: list[tuple[str, str]] = [
    ("TV9 Telugu", "UCfaww9Q8C_-EaM0sXI8o-fA"),
    ("NTV Telugu", "UCtzYV2L-m8ew93mZb3qhf5w"),
    ("TV5 News", "UCxiv-IYyYR725C2apG_w6fQ"),
    ("10TV News", "UCcFQmmbb439JyfMjRokn_ww"),
    ("Prime9 News", "UC61kgbrqggBKUD2nBb8f3Aw"),
    ("Sakshi TV", "UCZ9m4KOh8Ei60428xeGYDCQ"),
    ("ETV Andhra Pradesh", "UCSs9H1cyB3OHdy8wkit8ZKg"),
]

# --------------------------------------------------------------------------
# Bilingual AP lexicon.
#
# This does the job LaBSE would do, without a 2 GB model on a CPU-only laptop:
# it collapses a Telugu headline and its English twin onto the same canonical
# entity, and it tells us whether a story is actually about Andhra Pradesh.
#
# key -> (kind, [surface forms in en and te])
#   kind: person | place | org | topic
# --------------------------------------------------------------------------

LEXICON: dict[str, tuple[str, list[str]]] = {
    # --- people ---
    # Deliberately no bare "naidu": it is one of the commonest surnames in the
    # state, and it made an astronomer called Rohan Naidu read as Andhra
    # Pradesh political news. Headlines that only ever say "Naidu" are the
    # price of that; they almost always name someone else identifiable too.
    "chandrababu_naidu": ("person", [
        "chandrababu", "chandra babu", "cbn", "cm naidu", "naidu government",
        "చంద్రబాబు", "చంద్రబాబు నాయుడు", "నారా చంద్రబాబు",
    ]),
    "jagan": ("person", [
        "jagan", "jagan mohan reddy", "ys jagan", "jagan mohan",
        "జగన్", "జగన్ మోహన్ రెడ్డి", "వైఎస్ జగన్",
    ]),
    "pawan_kalyan": ("person", [
        "pawan kalyan", "pawan", "deputy cm pawan",
        "పవన్ కళ్యాణ్", "పవన్",
    ]),
    "lokesh": ("person", ["nara lokesh", "lokesh", "లోకేష్", "నారా లోకేష్"]),
    "naga_babu": ("person", ["naga babu", "nagababu", "నాగబాబు", "నాగ బాబు"]),
    "sharmila": ("person", ["sharmila", "ys sharmila", "షర్మిల"]),
    "modi": ("person", ["narendra modi", "modi", "prime minister", "మోదీ", "ప్రధాని"]),
    "revanth": ("person", ["revanth reddy", "రేవంత్", "రేవంత్ రెడ్డి"]),
    "kcr": ("person", ["kcr", "chandrashekar rao", "కేసీఆర్"]),

    # --- places ---
    "amaravati": ("place", ["amaravati", "amaravathi", "అమరావతి"]),
    "visakhapatnam": ("place", ["visakhapatnam", "vizag", "vishakhapatnam", "విశాఖపట్నం", "విశాఖ", "వైజాగ్"]),
    "vijayawada": ("place", ["vijayawada", "bezawada", "విజయవాడ"]),
    "guntur": ("place", ["guntur", "గుంటూరు"]),
    "tirupati": ("place", ["tirupati", "తిరుపతి"]),
    "tirumala": ("place", ["tirumala", "తిరుమల"]),
    "nellore": ("place", ["nellore", "నెల్లూరు"]),
    "kurnool": ("place", ["kurnool", "కర్నూలు"]),
    "kadapa": ("place", ["kadapa", "cuddapah", "కడప"]),
    "anantapur": ("place", ["anantapur", "అనంతపురం"]),
    "rajahmundry": ("place", ["rajahmundry", "rajamahendravaram", "రాజమహేంద్రవరం", "రాజమండ్రి"]),
    "kakinada": ("place", ["kakinada", "కాకినాడ"]),
    "srikakulam": ("place", ["srikakulam", "శ్రీకాకుళం"]),
    "vizianagaram": ("place", ["vizianagaram", "విజయనగరం"]),
    "eluru": ("place", ["eluru", "ఏలూరు"]),
    "ongole": ("place", ["ongole", "ఒంగోలు", "prakasam", "ప్రకాశం"]),
    "chittoor": ("place", ["chittoor", "చిత్తూరు"]),
    "bhogapuram": ("place", ["bhogapuram", "భోగాపురం"]),
    "pithapuram": ("place", ["pithapuram", "పిఠాపురం"]),
    "andhra_pradesh": ("place", ["andhra pradesh", "andhra", "ap govt", "ఆంధ్రప్రదేశ్", "ఆంధ్ర", "ఏపీ"]),
    "godavari": ("place", ["godavari", "గోదావరి"]),
    "krishna_river": ("place", ["krishna river", "krishna district", "కృష్ణా"]),

    # --- orgs / parties ---
    "tdp": ("org", ["tdp", "telugu desam", "టీడీపీ", "తెలుగుదేశం"]),
    "ysrcp": ("org", ["ysrcp", "ysr congress", "వైసీపీ", "వైఎస్సార్సీపీ"]),
    "janasena": ("org", ["jana sena", "janasena", "జనసేన"]),
    "bjp": ("org", ["bjp", "బీజేపీ", "భాజపా"]),
    "congress": ("org", ["congress", "కాంగ్రెస్"]),
    "ttd": ("org", ["ttd", "tirumala tirupati devasthanams", "టీటీడీ"]),
    "apsrtc": ("org", ["apsrtc", "rtc", "ఆర్టీసీ"]),
    "imd": ("org", ["imd", "met department", "weather department", "వాతావరణ శాఖ"]),
    "appsc": ("org", ["appsc", "ఏపీపీఎస్సీ"]),

    # --- topics ---
    "polavaram": ("topic", ["polavaram", "పోలవరం"]),
    "flood": ("topic", ["flood", "floods", "inundation", "వరద", "వరదలు", "ముంపు"]),
    "rain": ("topic", ["rain", "rains", "rainfall", "downpour", "వర్షం", "వర్షాలు", "వాన"]),
    "cyclone": ("topic", ["cyclone", "depression", "low pressure", "తుఫాన్", "అల్పపీడనం"]),
    "heatwave": ("topic", ["heatwave", "heat wave", "వడగాలులు", "ఎండలు"]),
    "results": ("topic", ["result", "results", "merit list", "rank", "ఫలితాలు", "ర్యాంక్"]),
    "exam": ("topic", ["exam", "exams", "eapcet", "eamcet", "neet", "పరీక్ష", "పరీక్షలు"]),
    "jobs": ("topic", ["recruitment", "notification", "vacancy", "నోటిఫికేషన్", "ఉద్యోగాలు"]),
    "arrest": ("topic", ["arrest", "arrested", "remand", "custody", "అరెస్ట్", "రిమాండ్"]),
    "murder": ("topic", ["murder", "killed", "death", "హత్య", "మృతి", "మరణం"]),
    "accident": ("topic", ["accident", "crash", "collision", "ప్రమాదం", "రోడ్డు ప్రమాదం"]),
    "protest": ("topic", ["protest", "dharna", "strike", "bandh", "ధర్నా", "ఆందోళన", "బంద్"]),
    "liquor_scam": ("topic", ["liquor scam", "liquor case", "మద్యం కేసు", "లిక్కర్"]),
    "court": ("topic", ["high court", "supreme court", "verdict", "bail", "హైకోర్టు", "సుప్రీంకోర్టు", "బెయిల్"]),
    "cinema": ("topic", ["movie", "film", "box office", "teaser", "trailer", "ott", "సినిమా", "చిత్రం", "టీజర్"]),
    "cricket": ("topic", ["cricket", "ipl", "match", "క్రికెట్", "మ్యాచ్"]),
    "power_cut": ("topic", ["power cut", "electricity tariff", "కరెంట్", "విద్యుత్"]),
    "pension": ("topic", ["pension", "welfare scheme", "పింఛను", "పెన్షన్"]),
    "farmer": ("topic", ["farmer", "farmers", "crop", "paddy", "రైతు", "రైతులు", "పంట"]),
}

# --------------------------------------------------------------------------
# Beats — a one-word label per story so a desk can scan a board by colour.
# First match wins, so the order is the priority: a politician commenting on
# a flood is a weather story.
# --------------------------------------------------------------------------

BEATS: list[tuple[str, set[str]]] = [
    ("weather", {"rain", "flood", "cyclone", "heatwave", "imd", "godavari", "krishna_river"}),
    ("crime",   {"arrest", "murder", "accident", "liquor_scam", "court"}),
    ("faith",   {"tirumala", "ttd"}),
    ("exams",   {"results", "exam", "jobs", "appsc"}),
    ("infra",   {"polavaram", "power_cut", "bhogapuram", "apsrtc"}),
    ("civic",   {"protest", "pension", "farmer"}),
    ("cinema",  {"cinema"}),
    ("sport",   {"cricket"}),
    ("politics", {"chandrababu_naidu", "jagan", "pawan_kalyan", "lokesh", "sharmila",
                  "naga_babu", "modi", "revanth", "kcr", "tdp", "ysrcp", "janasena",
                  "bjp", "congress"}),
]

# Words too common to be worth clustering on.
STOPWORDS = set("""
a an the and or of in on at to for from with by is are was were be been being as
that this these those it its his her their our your my he she they we you i not
no yes new latest news update updates says said say after before over under into
ap andhra pradesh india indian live video watch photos photo full big top
కోసం మరియు అని ఒక ఈ ఆ లో కు తో పై నుంచి వరకు గా చేసిన చేసే అయిన ఉన్న
""".split())

# --------------------------------------------------------------------------
# Scoring weights. Tune here after a week of watching the board.
# --------------------------------------------------------------------------

WEIGHTS = {
    "trend": 0.34,          # matches a live Google search trend
    "acceleration": 0.22,   # coverage rate rising vs its own recent baseline
    "corroboration": 0.20,  # independent outlets carrying it
    "velocity": 0.14,       # raw items per hour
    "freshness": 0.10,      # decay
}

# Locality multiplier applied to the weighted sum. A clearly-AP story scores at
# full strength; everything else is marked down from there, so the top of the
# board cannot saturate at 100.
LOCALITY_STRONG = 1.00   # AP place, AP politician or AP institution named
LOCALITY_WEAK = 0.55     # Telugu-sphere but not clearly AP
LOCALITY_NONE = 0.18     # no AP signal at all

# Inside a two-hour window a 150-minute half-life barely separates anything.
FRESHNESS_HALFLIFE_MIN = 40.0

# Alert thresholds
ALERT_SCORE = int(os.environ.get("RADAR_ALERT_SCORE", "62"))
ALERT_MIN_OUTLETS = 2
ALERT_MAX_AGE_MIN = 100
ALERT_COOLDOWN_MIN = 90  # do not re-alert the same cluster within this window

# --------------------------------------------------------------------------
# Optional extras (all off unless you set the env var)
# --------------------------------------------------------------------------

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

TELEGRAM_TOKEN = os.environ.get("RADAR_TELEGRAM_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.environ.get("RADAR_TELEGRAM_CHAT", "").strip()

DB_PATH = os.environ.get(
    "RADAR_DB",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "radar.db"),
)

SERVER_HOST = os.environ.get("RADAR_HOST", "127.0.0.1")
SERVER_PORT = int(os.environ.get("RADAR_PORT", "8787"))

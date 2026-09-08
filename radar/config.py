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
SLOW_EVERY_N_TICKS = 3    # publishers, sections, most-read: every 3rd tick (~15 min)
HOURLY_EVERY_N_TICKS = 12  # Wikipedia top pages change once a day; once an hour is plenty

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

# Google News front page and sections, per language. Rank within the top
# stories feed is Google's own reading-behaviour signal and is kept.
# Verified 8 Sep 2026: every one of these answers with 22–70 items.
_GN = "https://news.google.com/rss"
GOOGLE_NEWS_TOP: list[tuple[str, str]] = [
    ("Google News · top stories (te)", f"{_GN}?hl=te-IN&gl=IN&ceid=IN:te"),
    ("Google News · top stories (en)", f"{_GN}?hl=en-IN&gl=IN&ceid=IN:en"),
]
GOOGLE_NEWS_TOPICS: list[tuple[str, str]] = [
    (f"Google News · {t.lower()} (te)", f"{_GN}/headlines/section/topic/{t}?hl=te-IN&gl=IN&ceid=IN:te")
    for t in ("NATION", "WORLD", "BUSINESS", "TECHNOLOGY", "ENTERTAINMENT", "SPORTS", "SCIENCE", "HEALTH")
] + [
    (f"Google News · {t.lower()} (en)", f"{_GN}/headlines/section/topic/{t}?hl=en-IN&gl=IN&ceid=IN:en")
    for t in ("NATION", "BUSINESS", "ENTERTAINMENT", "SPORTS")
]

# What people are *reading*, as opposed to searching. National, so each item
# is marked AP-local or not by the lexicon; still worth a desk's glance.
READING_FEEDS: list[tuple[str, str]] = [
    ("Times of India · most read", "https://timesofindia.indiatimes.com/rssfeedmostread.cms"),
    ("Times of India · most shared", "https://timesofindia.indiatimes.com/rssfeedmostshared.cms"),
]

# Wikipedia's most-viewed pages. The pageviews API is daily-only per article,
# so this is yesterday, and is labelled as such — it is still the clearest
# free read on what Telugu readers went looking for.
WIKI_PROJECTS: list[tuple[str, str]] = [
    ("te.wikipedia", "Telugu Wikipedia"),
]
WIKI_TOP_N = 15

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
    # ===================== people: government =====================
    # Deliberately no bare "naidu": it is one of the commonest surnames in the
    # state, and it made an astronomer called Rohan Naidu read as Andhra
    # Pradesh political news. Headlines that only ever say "Naidu" are the
    # price of that; they almost always name someone else identifiable too.
    "chandrababu_naidu": ("person", ["chandrababu", "chandra babu", "cbn", "cm naidu", "naidu government",
                                     "చంద్రబాబు", "చంద్రబాబు నాయుడు", "నారా చంద్రబాబు"]),
    "pawan_kalyan": ("person", ["pawan kalyan", "pawan", "deputy cm pawan", "పవన్ కళ్యాణ్", "పవన్", "పవన్ కల్యాణ్"]),
    "lokesh": ("person", ["nara lokesh", "lokesh", "లోకేష్", "నారా లోకేష్"]),
    "naga_babu": ("person", ["naga babu", "nagababu", "నాగబాబు", "నాగ బాబు"]),
    "atchannaidu": ("person", ["atchannaidu", "achchennaidu", "atchannaidu", "అచ్చెన్నాయుడు"]),
    "anagani": ("person", ["anagani satya prasad", "anagani", "అనగాని"]),
    "nadendla": ("person", ["nadendla manohar", "nadendla", "నాదెండ్ల"]),
    "kandula_durgesh": ("person", ["kandula durgesh", "durgesh", "కందుల దుర్గేష్", "దుర్గేష్"]),
    "gottipati": ("person", ["gottipati ravi", "gottipati", "గొట్టిపాటి"]),
    "p_narayana": ("person", ["minister narayana", "p narayana", "ponguru narayana", "మంత్రి నారాయణ", "పొంగూరు నారాయణ"]),
    "anitha": ("person", ["vangalapudi anitha", "home minister anitha", "anitha vangalapudi", "వంగలపూడి అనిత", "మంత్రి అనిత"]),
    "satya_kumar": ("person", ["satya kumar yadav", "satyakumar", "సత్యకుమార్"]),
    "nimmala": ("person", ["nimmala rama naidu", "nimmala", "నిమ్మల రామానాయుడు", "నిమ్మల"]),
    "payyavula": ("person", ["payyavula keshav", "payyavula", "పయ్యావుల కేశవ్", "పయ్యావుల"]),
    "kollu_ravindra": ("person", ["kollu ravindra", "కొల్లు రవీంద్ర"]),
    "tg_bharath": ("person", ["tg bharath", "t g bharath", "టీజీ భరత్"]),
    "savitha": ("person", ["minister savitha", "సవిత"]),
    "sandhya_rani": ("person", ["gummadi sandhya rani", "sandhya rani", "సంధ్యారాణి"]),
    "bc_janardhan": ("person", ["bc janardhan reddy", "janardhan reddy", "బీసీ జనార్దన్ రెడ్డి"]),
    "ram_prasad_reddy": ("person", ["kolusu parthasarathy", "parthasarathy", "పార్థసారథి"]),
    "governor_ap": ("person", ["governor abdul nazeer", "abdul nazeer", "గవర్నర్ నజీర్", "అబ్దుల్ నజీర్"]),
    # ===================== people: opposition & others =====================
    "jagan": ("person", ["jagan", "jagan mohan reddy", "ys jagan", "jagan mohan", "జగన్", "జగన్ మోహన్ రెడ్డి", "వైఎస్ జగన్"]),
    "sharmila": ("person", ["sharmila", "ys sharmila", "షర్మిల"]),
    "sajjala": ("person", ["sajjala", "sajjala ramakrishna reddy", "సజ్జల"]),
    "botsa": ("person", ["botsa", "botcha", "botsa satyanarayana", "బొత్స"]),
    "ambati": ("person", ["ambati rambabu", "ambati", "అంబటి రాంబాబు", "అంబటి"]),
    "perni_nani": ("person", ["perni nani", "perni venkataramaiah", "పేర్ని నాని"]),
    "roja": ("person", ["rk roja", "roja", "రోజా"]),
    "kodali_nani": ("person", ["kodali nani", "కొడాలి నాని"]),
    "anil_kumar_yadav": ("person", ["anil kumar yadav", "అనిల్ కుమార్ యాదవ్"]),
    "palla": ("person", ["palla srinivasa rao", "palla srinivas", "పల్లా శ్రీనివాసరావు", "పల్లా"]),
    "somireddy": ("person", ["somireddy", "somireddy chandramohan", "సోమిరెడ్డి"]),
    "bonda_uma": ("person", ["bonda uma", "బొండా ఉమా"]),
    "purandeswari": ("person", ["purandeswari", "purandeshwari", "పురందేశ్వరి"]),
    "pvn_madhav": ("person", ["pvn madhav", "పీవీఎన్ మాధవ్"]),
    "vijayasai": ("person", ["vijayasai reddy", "vijaya sai reddy", "విజయసాయి రెడ్డి"]),
    "modi": ("person", ["narendra modi", "modi", "prime minister", "మోదీ", "ప్రధాని"]),
    "amit_shah": ("person", ["amit shah", "అమిత్ షా"]),
    "revanth": ("person", ["revanth reddy", "రేవంత్", "రేవంత్ రెడ్డి"]),
    "kcr": ("person", ["kcr", "chandrashekar rao", "కేసీఆర్"]),
    "ktr": ("person", ["ktr", "kt rama rao", "కేటీఆర్"]),
    # ===================== people: film & sport (searched constantly) =====================
    "prabhas": ("person", ["prabhas", "ప్రభాస్"]),
    "mahesh_babu": ("person", ["mahesh babu", "మహేష్ బాబు", "మహేశ్ బాబు"]),
    "ntr_jr": ("person", ["jr ntr", "ntr", "tarak", "ఎన్టీఆర్", "తారక్"]),
    "ram_charan": ("person", ["ram charan", "రామ్ చరణ్"]),
    "allu_arjun": ("person", ["allu arjun", "bunny", "అల్లు అర్జున్"]),
    "chiranjeevi": ("person", ["chiranjeevi", "megastar", "చిరంజీవి", "మెగాస్టార్"]),
    "balakrishna": ("person", ["balakrishna", "balayya", "బాలకృష్ణ", "బాలయ్య"]),
    "nagarjuna": ("person", ["nagarjuna", "నాగార్జున"]),
    "vijay_deverakonda": ("person", ["vijay deverakonda", "విజయ్ దేవరకొండ"]),
    "rajamouli": ("person", ["rajamouli", "రాజమౌళి"]),
    "samantha": ("person", ["samantha", "సమంత"]),
    "rashmika": ("person", ["rashmika", "రష్మిక"]),
    "anushka": ("person", ["anushka shetty", "అనుష్క"]),
    "nayanthara": ("person", ["nayanthara", "నయనతార"]),
    "kohli": ("person", ["virat kohli", "kohli", "కోహ్లీ"]),
    "rohit": ("person", ["rohit sharma", "రోహిత్ శర్మ"]),
    "bumrah": ("person", ["bumrah", "బుమ్రా"]),
    # ===================== places: districts (all 26) =====================
    "andhra_pradesh": ("place", ["andhra pradesh", "andhra", "ap govt", "ఆంధ్రప్రదేశ్", "ఆంధ్ర", "ఏపీ"]),
    "amaravati": ("place", ["amaravati", "amaravathi", "అమరావతి"]),
    "srikakulam": ("place", ["srikakulam", "శ్రీకాకుళం"]),
    "vizianagaram": ("place", ["vizianagaram", "విజయనగరం"]),
    "parvathipuram": ("place", ["parvathipuram", "parvathipuram manyam", "పార్వతీపురం"]),
    "alluri": ("place", ["alluri sitharama raju district", "alluri district", "asr district", "అల్లూరి జిల్లా", "అల్లూరి సీతారామరాజు జిల్లా"]),
    "visakhapatnam": ("place", ["visakhapatnam", "vizag", "vishakhapatnam", "విశాఖపట్నం", "విశాఖ", "వైజాగ్"]),
    "anakapalli": ("place", ["anakapalli", "anakapalle", "అనకాపల్లి"]),
    "kakinada": ("place", ["kakinada", "కాకినాడ"]),
    "konaseema": ("place", ["konaseema", "amalapuram", "కోనసీమ", "అమలాపురం"]),
    "east_godavari": ("place", ["east godavari", "తూర్పు గోదావరి"]),
    "rajahmundry": ("place", ["rajahmundry", "rajamahendravaram", "రాజమహేంద్రవరం", "రాజమండ్రి"]),
    "west_godavari": ("place", ["west godavari", "bhimavaram", "పశ్చిమ గోదావరి", "భీమవరం"]),
    "eluru": ("place", ["eluru", "ఏలూరు"]),
    "krishna_district": ("place", ["krishna district", "machilipatnam", "gudivada", "కృష్ణా జిల్లా", "మచిలీపట్నం", "గుడివాడ"]),
    "ntr_district": ("place", ["ntr district", "ఎన్టీఆర్ జిల్లా"]),
    "vijayawada": ("place", ["vijayawada", "bezawada", "విజయవాడ"]),
    "guntur": ("place", ["guntur", "గుంటూరు"]),
    "mangalagiri": ("place", ["mangalagiri", "tadepalli", "మంగళగిరి", "తాడేపల్లి"]),
    "palnadu": ("place", ["palnadu", "narasaraopet", "పల్నాడు", "నరసరావుపేట"]),
    "bapatla": ("place", ["bapatla", "chirala", "బాపట్ల", "చీరాల"]),
    "ongole": ("place", ["ongole", "prakasam", "ఒంగోలు", "ప్రకాశం"]),
    "nellore": ("place", ["nellore", "kavali", "gudur", "నెల్లూరు", "కావలి", "గూడూరు"]),
    "tirupati": ("place", ["tirupati", "తిరుపతి"]),
    "tirumala": ("place", ["tirumala", "తిరుమల"]),
    "chittoor": ("place", ["chittoor", "చిత్తూరు"]),
    "annamayya": ("place", ["annamayya district", "rayachoti", "madanapalle", "అన్నమయ్య జిల్లా", "రాయచోటి", "మదనపల్లె"]),
    "kadapa": ("place", ["kadapa", "cuddapah", "proddatur", "కడప", "ప్రొద్దుటూరు"]),
    "kurnool": ("place", ["kurnool", "adoni", "కర్నూలు", "ఆదోని"]),
    "nandyal": ("place", ["nandyal", "నంద్యాల"]),
    "anantapur": ("place", ["anantapur", "anantapuram", "అనంతపురం"]),
    "sri_sathya_sai": ("place", ["sri sathya sai district", "puttaparthi", "hindupur", "dharmavaram",
                                 "శ్రీ సత్యసాయి జిల్లా", "పుట్టపర్తి", "హిందూపురం", "ధర్మవరం"]),
    # ===================== places: landmarks & projects =====================
    "bhogapuram": ("place", ["bhogapuram", "భోగాపురం"]),
    "pithapuram": ("place", ["pithapuram", "పిఠాపురం"]),
    "araku": ("place", ["araku", "అరకు"]),
    "simhachalam": ("place", ["simhachalam", "సింహాచలం"]),
    "srisailam": ("place", ["srisailam", "శ్రీశైలం"]),
    "rayalaseema": ("place", ["rayalaseema", "రాయలసీమ"]),
    "uttarandhra": ("place", ["uttarandhra", "north andhra", "ఉత్తరాంధ్ర"]),
    "godavari": ("place", ["godavari", "గోదావరి"]),
    "krishna_river": ("place", ["krishna river", "కృష్ణా నది", "కృష్ణానది"]),
    "polavaram": ("place", ["polavaram", "పోలవరం"]),
    "gangavaram": ("place", ["gangavaram port", "గంగవరం"]),
    # ===================== orgs =====================
    "tdp": ("org", ["tdp", "telugu desam", "టీడీపీ", "తెలుగుదేశం"]),
    "ysrcp": ("org", ["ysrcp", "ysr congress", "ycp", "వైసీపీ", "వైఎస్సార్సీపీ"]),
    "janasena": ("org", ["jana sena", "janasena", "జనసేన"]),
    "bjp": ("org", ["bjp", "బీజేపీ", "భాజపా"]),
    "congress": ("org", ["congress", "కాంగ్రెస్"]),
    "brs": ("org", ["brs", "బీఆర్ఎస్", "బీఆర్‌ఎస్"]),
    "ttd": ("org", ["ttd", "tirumala tirupati devasthanams", "టీటీడీ"]),
    "apsrtc": ("org", ["apsrtc", "rtc", "ఆర్టీసీ"]),
    "imd": ("org", ["imd", "met department", "weather department", "వాతావరణ శాఖ"]),
    "appsc": ("org", ["appsc", "ఏపీపీఎస్సీ"]),
    "ap_assembly": ("org", ["ap assembly", "andhra assembly", "assembly session", "ఏపీ అసెంబ్లీ", "అసెంబ్లీ", "శాసనసభ"]),
    "ap_cabinet": ("org", ["ap cabinet", "state cabinet", "cabinet meeting", "ఏపీ కేబినెట్", "క్యాబినెట్", "మంత్రివర్గం"]),
    "ap_high_court": ("org", ["ap high court", "andhra pradesh high court", "ఏపీ హైకోర్టు"]),
    "apspdcl": ("org", ["apspdcl", "apepdcl", "discom", "విద్యుత్ శాఖ"]),
    "andhra_university": ("org", ["andhra university", "ఆంధ్ర యూనివర్సిటీ", "ఏయూ"]),
    "svu": ("org", ["sri venkateswara university", "svu", "ఎస్వీ యూనివర్సిటీ"]),
    "cid_ap": ("org", ["ap cid", "cid", "సీఐడీ"]),
    "cbi": ("org", ["cbi", "సీబీఐ"]),
    "ed": ("org", ["enforcement directorate", "ఈడీ"]),
    "dsc": ("org", ["dsc", "mega dsc", "డీఎస్సీ"]),
    # ===================== topics =====================
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
    "gold_price": ("topic", ["gold rate", "gold price", "బంగారం ధర", "బంగారం ధరలు"]),
    "petrol": ("topic", ["petrol price", "diesel price", "పెట్రోల్ ధర"]),
    "local_body": ("topic", ["local body elections", "panchayat elections", "municipal elections", "స్థానిక ఎన్నికలు", "పంచాయతీ ఎన్నికలు"]),
    "capital": ("topic", ["capital city", "three capitals", "రాజధాని"]),
    "ganja": ("topic", ["ganja", "drugs", "narcotics", "గంజాయి", "డ్రగ్స్"]),
    "vinayaka_chavithi": ("topic", ["vinayaka chavithi", "ganesh chaturthi", "vinayaka", "వినాయక చవితి", "వినాయకుడు"]),
    "dasara": ("topic", ["dasara", "dussehra", "దసరా"]),
    "sankranti": ("topic", ["sankranti", "సంక్రాంతి"]),
}

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
    "trend": 0.32,          # matches a live Google search trend
    "acceleration": 0.20,   # coverage rate rising vs its own recent baseline
    "corroboration": 0.18,  # independent outlets carrying it
    "prominence": 0.12,     # how high Google News ranks it on its front page
    "velocity": 0.10,       # raw items per hour
    "freshness": 0.08,      # decay
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

"""The desk dashboard: stdlib HTTP server, one page, no build step."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, poll

PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ap-radar</title>
<style>
  /* Rose Pine — a terminal palette that stays legible for hours.
     Nothing here is fluorescent; severity is carried by hue, not by glare. */
  :root{
    --bg:#191724; --surface:#1f1d2e; --overlay:#26233a; --line:#302d41;
    /* Rose Pine's own --muted (#6e6a86) lands at 3.4 on this background, and
       it carries real information here — outlet counts, ages. Lifted. */
    --text:#e0def4; --subtle:#a9a4c2; --muted:#8b86a4;
    --love:#eb6f92; --gold:#f6c177; --rose:#ebbcba;
    --pine:#31748f; --foam:#9ccfd8; --iris:#c4a7e7;
    --sel:#2a273f;
  }
  /* Rose Pine Dawn, with the accents darkened. The published Dawn values are
     tuned for syntax highlighting on large blocks of code; used as small text
     on cream, foam and gold fall to about 2:1 and the score — the number that
     matters most — becomes the hardest thing on the page to read. */
  @media (prefers-color-scheme: light){
    :root{
      --bg:#faf4ed; --surface:#fffaf3; --overlay:#f2e9e1; --line:#ddd6ce;
      --text:#575279; --subtle:#6a6580; --muted:#6d6884;
      --love:#a03d5c; --gold:#8a5a10; --rose:#b4637a;
      --pine:#1f5a72; --foam:#256b7d; --iris:#7a5f9c;
      --sel:#f2e9e1;
    }
  }

  *{box-sizing:border-box; border-radius:0 !important}
  html{background:var(--bg)}
  body{
    margin:0; background:var(--bg); color:var(--text);
    font-family:ui-monospace,"JetBrains Mono","Cascadia Mono","SF Mono",
      Menlo,Consolas,"DejaVu Sans Mono",monospace,"Noto Sans Telugu";
    font-size:13.5px; line-height:1.65;
    font-variant-ligatures:none;
    -webkit-font-smoothing:antialiased;
  }
  a{color:inherit}

  /* ---- status bar, in the manner of tmux ---- */
  .status{
    display:flex; align-items:center; gap:0; flex-wrap:wrap;
    background:var(--overlay); border-bottom:1px solid var(--line);
    font-size:12.5px; position:sticky; top:0; z-index:10;
  }
  .seg{padding:5px 12px; white-space:nowrap}
  /* Pine is dark in both themes, so the label text is fixed cream rather than
     var(--bg), which would go dark-on-dark in the light theme. */
  .seg.name{background:var(--pine); color:#faf4ed; font-weight:700; letter-spacing:.06em}
  .seg.live{color:var(--foam)}
  .seg.dim{color:var(--muted)}
  .seg.right{margin-left:auto; color:var(--muted)}
  .blink{animation:bl 1.4s step-end infinite}
  @keyframes bl{50%{opacity:0}}

  .wrap{max-width:1000px; margin:0 auto; padding:20px 18px 70px}

  /* ---- section rules: "── LABEL ─────────────" ---- */
  .sec{display:flex; align-items:center; gap:10px; margin:26px 0 12px}
  .sec:first-of-type{margin-top:14px}
  .sec b{
    font-weight:700; font-size:12px; letter-spacing:.14em;
    text-transform:uppercase; color:var(--subtle); white-space:nowrap;
  }
  .sec .rule{flex:1; height:0; border-top:1px solid var(--line)}
  .sec .note{font-size:11.5px; color:var(--muted); letter-spacing:0;
    text-transform:none; font-weight:400; white-space:nowrap}

  /* ---- trend cells ---- */
  .grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(178px,1fr));
    gap:0; border-top:1px solid var(--line); border-left:1px solid var(--line)}
  .cell{
    border-right:1px solid var(--line); border-bottom:1px solid var(--line);
    padding:8px 11px; text-decoration:none; display:block; background:var(--bg);
  }
  .cell:hover{background:var(--sel)}
  .cell .q{color:var(--text); white-space:nowrap; overflow:hidden;
    text-overflow:ellipsis; font-size:13px}
  .cell .m{font-size:11.5px; color:var(--muted); margin-top:2px;
    display:flex; justify-content:space-between; gap:8px}
  .cell .m .meter{color:var(--pine); letter-spacing:-1px}
  .cell.up .q{color:var(--gold)}
  .cell.up .m .meter{color:var(--gold)}

  /* ---- gap rows ---- */
  .gap{
    display:flex; gap:14px; align-items:baseline; text-decoration:none;
    padding:6px 11px; border:1px solid var(--line); border-top:none;
    background:var(--bg);
  }
  .gap:first-child{border-top:1px solid var(--line)}
  .gap:hover{background:var(--sel)}
  .gap .flag{color:var(--gold); font-size:11.5px; letter-spacing:.08em;
    white-space:nowrap; width:11ch}
  .gap .q{color:var(--text); overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .gap .n{margin-left:auto; color:var(--muted); font-size:11.5px; white-space:nowrap}

  /* ---- filter tabs ---- */
  .tabs{display:flex; gap:0; margin:0 0 14px; border:1px solid var(--line); width:fit-content}
  .tabs button{
    font:inherit; font-size:12.5px; cursor:pointer; padding:4px 14px;
    background:var(--bg); color:var(--muted); border:none;
    border-right:1px solid var(--line);
  }
  .tabs button:last-child{border-right:none}
  .tabs button:hover{background:var(--sel); color:var(--text)}
  .tabs button.on{background:var(--pine); color:#faf4ed; font-weight:700}

  /* ---- story rows ---- */
  .row{
    display:grid; grid-template-columns:5ch 1fr; border:1px solid var(--line);
    border-top:none; background:var(--bg);
  }
  .row:first-of-type{border-top:1px solid var(--line)}
  .row:hover{background:var(--sel)}
  .gutter{
    border-right:1px solid var(--line); padding:9px 0 9px;
    text-align:center; display:flex; flex-direction:column; align-items:center; gap:2px;
  }
  .gutter .n{font-size:15px; font-weight:700; line-height:1.15;
    font-variant-numeric:tabular-nums}
  .gutter .sp{font-size:10px; letter-spacing:0; color:var(--muted); line-height:1}
  .body{padding:9px 12px; min-width:0}
  .ttl{margin:0; font-size:13.5px; font-weight:600; line-height:1.5}
  .gloss{color:var(--subtle); font-size:12.5px; margin-top:1px}
  .meta{color:var(--muted); font-size:12px; margin-top:3px}
  .meta .k{color:var(--subtle)}
  .why{color:var(--foam); font-size:12px; margin-top:4px}
  .bar{letter-spacing:-.5px}
  .t-hot{color:var(--love)} .t-warm{color:var(--gold)} .t-cool{color:var(--foam)}

  details{margin-top:5px}
  summary{cursor:pointer; list-style:none; color:var(--muted); font-size:12px}
  summary::-webkit-details-marker{display:none}
  summary:hover{color:var(--foam)}
  .links{margin-top:4px; border-top:1px solid var(--line)}
  .links a{
    display:flex; gap:10px; align-items:baseline; padding:3px 0;
    text-decoration:none; color:var(--subtle); font-size:12.5px;
  }
  .links a:hover{color:var(--text)}
  .links .t{overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .links .o{margin-left:auto; color:var(--muted); font-size:11.5px; white-space:nowrap}

  .empty{color:var(--muted); font-size:12.5px; padding:10px 11px;
    border:1px solid var(--line)}
  .err{color:var(--love); border:1px solid var(--love); padding:7px 11px;
    font-size:12.5px; margin-bottom:14px}
</style></head><body>

<div class="status">
  <span class="seg name">ap-radar</span>
  <span class="seg live">●&nbsp;live</span>
  <span class="seg dim" id="s-upd">connecting…</span>
  <span class="seg dim" id="s-cnt"></span>
  <span class="seg right" id="s-win">last 2h only</span>
</div>

<div class="wrap">
  <div id="err"></div>

  <div class="sec"><b>Searching now</b>
    <span class="note">what Andhra Pradesh is typing into Google</span>
    <span class="rule"></span></div>
  <div class="grid" id="trends"></div>

  <div class="sec"><b>Rising · thin coverage</b>
    <span class="note">nobody has written this yet</span>
    <span class="rule"></span></div>
  <div id="gaps"></div>

  <div class="sec"><b>Story board</b><span class="rule"></span></div>
  <div class="tabs">
    <button data-f="all" class="on">all</button>
    <button data-f="ap">ap only</button>
    <button data-f="fresh">&lt;2h</button>
    <button data-f="trend">search-backed</button>
  </div>
  <div id="board"></div>
</div>

<script>
let FILTER='all', DATA=null;

const esc = s => (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const ago = m => m<1?'now' : m<60?m+'m' : m<1440?Math.round(m/60)+'h' : Math.round(m/1440)+'d';
const tier = s => s>=70?'hot' : s>=48?'warm' : 'cool';

// Meters are text, not graphics — the whole point of a terminal.
const BLOCKS = '▁▂▃▄▅▆▇█';
const bar = (v, w) => {
  const on = Math.max(0, Math.min(w, Math.round(v*w)));
  return '█'.repeat(on) + '·'.repeat(w-on);
};
const spark = b => ['trend','acceleration','corroboration','velocity','freshness']
  .map(k => BLOCKS[Math.max(0, Math.min(7, Math.round((b[k]||0)*7)))]).join('');

function trendCell(t){
  const url='https://trends.google.com/trends/explore?q='+encodeURIComponent(t.query)
    +'&geo='+t.geo+'&date=now%201-d';
  const traffic = t.traffic ? t.traffic.toLocaleString()+'+' : '—';
  return `<a class="cell ${t.rising>0.45?'up':''}" href="${url}" target="_blank" rel="noopener"
    title="${esc(t.geo_label)} · rising ${Math.round(t.rising*100)}%">
    <div class="q">${t.rising>0.45?'↑ ':''}${esc(t.query)}</div>
    <div class="m"><span>${traffic}</span><span class="meter">${bar(t.rising,6)}</span></div></a>`;
}

function gapRow(g){
  const url='https://news.google.com/search?q='+encodeURIComponent(g.query)+'&hl=en-IN&gl=IN&ceid=IN:en';
  return `<a class="gap" href="${url}" target="_blank" rel="noopener">
    <span class="flag">${g.coverage===0?'UNCOVERED':'1 OUTLET'}</span>
    <span class="q">${esc(g.query)}</span>
    <span class="n">${g.traffic?g.traffic.toLocaleString()+'+':''} · ${ago(g.age_min)}</span></a>`;
}

function row(c){
  const t=tier(c.score);
  const langs=c.languages.map(l=>l==='te'?'తె':'en').join('+');
  const why=c.trend_query
    ? `<div class="why">└─ searching "${esc(c.trend_query)}" · ${esc(c.trend_geo)}</div>` : '';
  const gloss=c.title_en ? `<div class="gloss">${esc(c.title_en)}</div>` : '';
  const links=c.links.filter(l=>l.url).map(l=>
    `<a href="${esc(l.url)}" target="_blank" rel="noopener">
      <span class="t">${l.kind==='video'?'▶ ':''}${esc(l.title)}</span>
      <span class="o">${esc(l.outlet)} ${ago(l.age_min)}</span></a>`).join('');
  return `<article class="row">
    <div class="gutter">
      <span class="n t-${t}">${Math.round(c.score)}</span>
      <span class="sp" title="trend accel outlets velocity fresh">${spark(c.breakdown)}</span>
    </div>
    <div class="body">
      <h3 class="ttl">${esc(c.title)}</h3>
      ${gloss}
      <div class="meta"><span class="bar t-${t}">${bar(c.score/100,10)}</span>
        &nbsp; <span class="k">${c.outlet_count}</span> outlet${c.outlet_count===1?'':'s'}
        · ${ago(c.age_min)} · ${langs}${c.locality!=='AP'?' · '+esc(c.locality):''}</div>
      ${why}
      ${links?`<details><summary>+ ${c.item_count} reports</summary>
        <div class="links">${links}</div></details>`:''}
    </div></article>`;
}

const keep = c =>
  FILTER==='ap'    ? c.locality==='AP' :
  FILTER==='fresh' ? c.age_min<=120 :
  FILTER==='trend' ? !!c.trend_query : true;

function render(){
  if(!DATA) return;
  const s=DATA.stats||{};
  document.getElementById('s-upd').textContent = DATA.last_tick
    ? 'updated '+new Date(DATA.last_tick).toLocaleTimeString('en-IN',
        {hour:'2-digit',minute:'2-digit',hour12:false})+' IST'
    : 'waiting';
  document.getElementById('s-cnt').textContent =
    `${s.clusters||0} stories · ${s.trends||0} trends`
    + (s.too_old ? ` · ${s.too_old} too old, dropped` : '');
  if (DATA.window_hours)
    document.getElementById('s-win').textContent = `last ${DATA.window_hours}h only`;
  document.getElementById('err').innerHTML = DATA.last_error
    ? '<div class="err">'+esc(DATA.last_error)+'</div>' : '';

  const tr=(DATA.trends||[]).slice(0,24);
  document.getElementById('trends').innerHTML = tr.length
    ? tr.map(trendCell).join('') : '<div class="empty">no trend data yet</div>';

  const g=DATA.gaps||[];
  document.getElementById('gaps').innerHTML = g.length
    ? g.map(gapRow).join('')
    : '<div class="empty">nothing rising without coverage — you are on top of it</div>';

  const b=(DATA.board||[]).filter(keep);
  document.getElementById('board').innerHTML = b.length
    ? b.map(row).join('') : '<div class="empty">no stories match this filter</div>';
}

document.querySelectorAll('.tabs button').forEach(btn=>{
  btn.onclick=()=>{
    document.querySelectorAll('.tabs button').forEach(x=>x.classList.remove('on'));
    btn.classList.add('on'); FILTER=btn.dataset.f; render();
  };
});

async function tick(){
  try{
    const r=await fetch('/api/board',{cache:'no-store'});
    DATA=await r.json(); render();
  }catch(e){ /* keep the last good board on screen */ }
}
tick(); setInterval(tick, 30000);
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "APRadar/1.0"

    def log_message(self, fmt, *args):  # keep the console clean for tick output
        pass

    def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        if path == "/":
            self._send(PAGE.encode("utf-8"), "text/html; charset=utf-8")
        elif path == "/api/board":
            self._send(json.dumps(poll.snapshot(), default=str).encode("utf-8"),
                       "application/json; charset=utf-8")
        elif path == "/api/health":
            state = poll.snapshot()
            self._send(json.dumps({
                "ok": state["last_error"] is None,
                "last_tick": state["last_tick"],
                "ticks": state["tick_count"],
            }).encode("utf-8"), "application/json")
        else:
            self._send(b"not found", "text/plain", 404)


def serve() -> None:
    httpd = ThreadingHTTPServer((config.SERVER_HOST, config.SERVER_PORT), Handler)
    print(f"  dashboard  http://{config.SERVER_HOST}:{config.SERVER_PORT}", flush=True)
    httpd.serve_forever()

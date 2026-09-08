"""The desk dashboard: stdlib HTTP server, one page, no build step.

The page takes its colours from the live Omarchy theme (see theme.py) and
re-reads them every refresh, so `omarchy theme set` restyles it in seconds.
Everything is drawn boxy and monospace, like the rest of the desktop.
"""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config, poll, theme

PAGE = r"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ap-radar</title>
<style>
  :root{
__THEME_VARS__
  }
  *{box-sizing:border-box; border-radius:0 !important}
  html{background:var(--bg)}
  body{
    margin:0; background:var(--bg); color:var(--text);
    font-family:"JetBrainsMono Nerd Font","CaskaydiaMono Nerd Font",ui-monospace,
      "JetBrains Mono","Cascadia Mono",Menlo,Consolas,monospace,"Noto Sans Telugu";
    font-size:13.5px; line-height:1.6; font-variant-ligatures:none;
    -webkit-font-smoothing:antialiased;
  }
  a{color:inherit}
  button,input{font:inherit; color:inherit}

  /* ---- top bar, in the manner of waybar ---- */
  .bar{
    display:flex; align-items:stretch; flex-wrap:wrap; position:sticky; top:0; z-index:10;
    background:var(--panel); border-bottom:1px solid var(--line); font-size:12.5px;
  }
  .seg{padding:5px 12px; border-right:1px solid var(--line); white-space:nowrap;
    display:flex; align-items:center; gap:7px}
  .seg.name{background:var(--accent); color:var(--on_accent); font-weight:700; letter-spacing:.08em}
  .seg.right{margin-left:auto; border-right:none; border-left:1px solid var(--line); color:var(--muted)}
  .seg.dim{color:var(--muted)}
  .seg.btn{cursor:pointer; user-select:none}
  .seg.btn:hover{background:var(--sel); color:var(--text)}
  .dot{display:inline-block; width:7px; height:7px; background:var(--up)}
  .dot.bad{background:var(--down)}
  .dot.live{animation:pulse 2.2s ease-in-out infinite}
  @keyframes pulse{50%{opacity:.35}}
  .stale{background:var(--down); color:var(--bg); font-weight:700}

  .notice{padding:6px 14px; font-size:12.5px; border-bottom:1px solid var(--line);
    background:var(--panel); color:var(--warm)}
  .notice.bad{color:var(--down)}

  /* ---- source health panel ---- */
  #srcpanel{border-bottom:1px solid var(--line); background:var(--panel); font-size:12px}
  #srcpanel table{border-collapse:collapse; width:100%; max-width:1000px; margin:0 auto}
  #srcpanel td{padding:3px 12px; border-bottom:1px solid var(--line); white-space:nowrap}
  #srcpanel td.err{color:var(--down); white-space:normal}
  #srcpanel td.ok{color:var(--up)}
  #srcpanel td.num{text-align:right; color:var(--muted); font-variant-numeric:tabular-nums}

  .wrap{max-width:1000px; margin:0 auto; padding:18px 18px 80px}

  /* ---- section rules: "── LABEL ─────────────" ---- */
  .sec{display:flex; align-items:center; gap:10px; margin:24px 0 10px}
  .sec:first-of-type{margin-top:8px}
  .sec b{font-weight:700; font-size:11.5px; letter-spacing:.14em; text-transform:uppercase;
    color:var(--muted); white-space:nowrap}
  .sec .rule{flex:1; border-top:1px solid var(--line)}
  .sec .note{font-size:11.5px; color:var(--muted); white-space:nowrap}
  .sec .n{color:var(--muted); font-size:11.5px}

  /* ---- arrows ---- */
  .ar{display:inline-block; width:1.2ch; font-weight:700}
  .ar.up,.up-c{color:var(--up)} .ar.down,.down-c{color:var(--down)}
  .ar.new{color:var(--accent)} .ar.flat{color:var(--muted)}

  /* ---- trend cells ---- */
  .grid{display:grid; grid-template-columns:repeat(auto-fill,minmax(186px,1fr));
    border-top:1px solid var(--line); border-left:1px solid var(--line)}
  .cell{border-right:1px solid var(--line); border-bottom:1px solid var(--line);
    padding:7px 10px; text-decoration:none; display:block}
  .cell:hover{background:var(--sel)}
  .cell .q{white-space:nowrap; overflow:hidden; text-overflow:ellipsis; font-size:13px}
  .cell .m{font-size:11.5px; color:var(--muted); margin-top:1px; display:flex;
    justify-content:space-between; gap:8px}
  .cell .meter{letter-spacing:-1px; color:var(--accent)}
  .cell.up .meter{color:var(--up)} .cell.down .meter{color:var(--down)}
  .cell .geo{font-size:10.5px; letter-spacing:.06em}

  /* ---- trailing chips ---- */
  .chips{display:flex; flex-wrap:wrap; border-top:1px solid var(--line); border-left:1px solid var(--line)}
  .chip{padding:4px 10px; border-right:1px solid var(--line); border-bottom:1px solid var(--line);
    font-size:12px; color:var(--muted); text-decoration:none; white-space:nowrap}
  .chip:hover{background:var(--sel); color:var(--text)}
  .chip b{color:var(--text); font-weight:500}

  /* ---- gap rows ---- */
  .gap{display:flex; gap:14px; align-items:baseline; text-decoration:none; padding:5px 11px;
    border:1px solid var(--line); border-top:none}
  .gap:first-child{border-top:1px solid var(--line)}
  .gap:hover{background:var(--sel)}
  .gap .flag{color:var(--warm); font-size:11px; letter-spacing:.08em; width:11ch; white-space:nowrap}
  .gap .q{overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .gap .n{margin-left:auto; color:var(--muted); font-size:11.5px; white-space:nowrap}

  /* ---- toolbar ---- */
  .tools{display:flex; flex-wrap:wrap; gap:8px; margin:0 0 12px; align-items:stretch}
  .tabs{display:flex; border:1px solid var(--line)}
  .tabs button{font-size:12px; cursor:pointer; padding:3px 12px; background:transparent;
    border:none; border-right:1px solid var(--line); color:var(--muted)}
  .tabs button:last-child{border-right:none}
  .tabs button:hover{background:var(--sel); color:var(--text)}
  .tabs button.on{background:var(--accent); color:var(--on_accent); font-weight:700}
  .tabs.beats button.on{background:var(--sel); color:var(--text)}
  .tabs.beats button.on::before{content:"■ "}
  .search{border:1px solid var(--line); background:transparent; padding:3px 10px; font-size:12px;
    min-width:200px; outline:none}
  .search:focus{border-color:var(--accent)}
  .search::placeholder{color:var(--muted)}

  /* ---- story rows ---- */
  .row{display:grid; grid-template-columns:7ch 1fr; border:1px solid var(--line); border-top:none}
  .row:first-of-type{border-top:1px solid var(--line)}
  .row:hover,.row.cur{background:var(--sel)}
  .row.cur{outline:1px solid var(--accent); outline-offset:-1px}
  .gutter{border-right:1px solid var(--line); padding:8px 0; text-align:center;
    display:flex; flex-direction:column; align-items:center; gap:1px}
  .gutter .n{font-size:15px; font-weight:700; line-height:1.15; font-variant-numeric:tabular-nums}
  .gutter .d{font-size:11px; line-height:1.2}
  .gutter .sp{font-size:10px; color:var(--muted); line-height:1; margin-top:2px}
  .body{padding:8px 12px; min-width:0}
  .ttl{margin:0; font-size:13.5px; font-weight:600; line-height:1.5}
  .tag{font-size:10.5px; letter-spacing:.1em; text-transform:uppercase; font-weight:700;
    margin-right:8px; vertical-align:1px}
  .gloss{color:var(--muted); font-size:12.5px}
  .meta{color:var(--muted); font-size:12px; margin-top:2px}
  .meta .k{color:var(--text)}
  .why{color:var(--accent); font-size:12px; margin-top:3px}
  .bar-t{letter-spacing:-.5px}
  .t-hot{color:var(--hot)} .t-warm{color:var(--warm)} .t-cool{color:var(--cool)}
  .b-weather{color:var(--weather)} .b-crime{color:var(--crime)} .b-politics{color:var(--politics)}
  .b-cinema{color:var(--cinema)} .b-faith{color:var(--faith)} .b-exams{color:var(--exams)}
  .b-infra{color:var(--infra)} .b-civic{color:var(--civic)} .b-sport{color:var(--sport)}
  .b-general{color:var(--muted)}

  details{margin-top:4px}
  summary{cursor:pointer; list-style:none; color:var(--muted); font-size:12px}
  summary::-webkit-details-marker{display:none}
  summary:hover{color:var(--accent)}
  .links{margin-top:4px; border-top:1px solid var(--line)}
  .links a{display:flex; gap:10px; align-items:baseline; padding:3px 0; text-decoration:none;
    color:var(--muted); font-size:12.5px}
  .links a:hover{color:var(--text)}
  .links .t{overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .links .o{margin-left:auto; color:var(--muted); font-size:11.5px; white-space:nowrap}

  .empty{color:var(--muted); font-size:12.5px; padding:9px 11px; border:1px solid var(--line)}
  .keys{margin-top:26px; color:var(--muted); font-size:11.5px}
  .keys kbd{border:1px solid var(--line); padding:0 5px; margin-right:2px}
  @media (max-width:640px){ .seg.hide-sm{display:none} .row{grid-template-columns:6ch 1fr} }
</style></head><body>

<div class="bar">
  <span class="seg name">ap-radar</span>
  <span class="seg" id="s-live"><span class="dot live"></span>live</span>
  <span class="seg dim" id="s-upd">connecting…</span>
  <span class="seg dim hide-sm" id="s-next"></span>
  <span class="seg dim hide-sm" id="s-cnt"></span>
  <span class="seg btn" id="s-src" title="source health">src —</span>
  <span class="seg right" id="s-theme"></span>
</div>
<div id="notices"></div>
<div id="srcpanel" hidden></div>

<div class="wrap">
  <div class="sec"><b>Searching now</b><span class="note">what Andhra Pradesh is typing into Google</span>
    <span class="rule"></span><span class="n" id="n-tr"></span></div>
  <div class="grid" id="trends"></div>

  <div class="sec"><b>Trailing</b><span class="note">was trending, has dropped off</span>
    <span class="rule"></span><span class="n" id="n-trail"></span></div>
  <div class="chips" id="trailing"></div>

  <div class="sec"><b>Rising · thin coverage</b><span class="note">nobody has written this yet</span>
    <span class="rule"></span></div>
  <div id="gaps"></div>

  <div class="sec"><b>Story board</b><span class="rule"></span><span class="n" id="n-board"></span></div>
  <div class="tools">
    <div class="tabs" id="filters">
      <button data-f="all" class="on">all</button>
      <button data-f="ap">ap only</button>
      <button data-f="fresh">&lt;30m</button>
      <button data-f="trend">search-backed</button>
      <button data-f="moving">moving</button>
    </div>
    <div class="tabs beats" id="beats"></div>
    <input class="search" id="q" placeholder="/ filter…" autocomplete="off" spellcheck="false">
  </div>
  <div id="board"></div>
  <div class="keys"><kbd>/</kbd>filter <kbd>j</kbd><kbd>k</kbd>move <kbd>o</kbd>open <kbd>1</kbd>–<kbd>5</kbd>tabs <kbd>s</kbd>sources <kbd>esc</kbd>clear</div>
</div>

<script>
let FILTER='all', BEAT=null, Q='', DATA=null, CUR=-1;
const BEAT_LIST=['weather','crime','faith','exams','infra','civic','cinema','sport','politics','general'];

const esc = s => String(s??'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const ago = m => m<1?'now' : m<60?m+'m' : m<1440?Math.round(m/60)+'h' : Math.round(m/1440)+'d';
const tier = s => s>=70?'hot' : s>=48?'warm' : 'cool';
const fmtK = n => !n?'—' : n>=1e6?(n/1e6).toFixed(1)+'M+' : n>=1000?Math.round(n/1000)+'K+' : n+'+';
const BLOCKS='▁▂▃▄▅▆▇█';
const bar = (v,w) => { const on=Math.max(0,Math.min(w,Math.round(v*w))); return '█'.repeat(on)+'·'.repeat(w-on); };
const spark = b => ['trend','acceleration','corroboration','velocity','freshness']
  .map(k => BLOCKS[Math.max(0,Math.min(7,Math.round(((b||{})[k]||0)*7)))]).join('');
const ARROW = {up:'▲', down:'▼', new:'●', flat:'→'};
const arrow = d => `<span class="ar ${d}" title="${d}">${ARROW[d]||'→'}</span>`;

function applyTheme(t){
  if(!t||!t.roles) return;
  const r=document.documentElement.style;
  for(const [k,v] of Object.entries(t.roles)) r.setProperty('--'+k, v);
  document.getElementById('s-theme').textContent = (t.name||'theme') + (t.source==='fallback'?' (fallback)':'');
}

function trendCell(t){
  const url='https://trends.google.com/trends/explore?q='+encodeURIComponent(t.query)+'&geo='+t.geo+'&date=now%201-d';
  const d=t.direction||'flat';
  const title=`${t.geo_label} · rising ${Math.round((t.rising||0)*100)}%`+(t.delta?` · ${t.delta}`:'');
  const geo = t.geo==='IN-AP'?'AP' : t.geo==='IN-TG'?'TG' : 'IN';
  return `<a class="cell ${d}" href="${url}" target="_blank" rel="noopener" title="${esc(title)}">
    <div class="q">${arrow(d)} ${esc(t.query)}</div>
    <div class="m"><span>${fmtK(t.traffic)} <span class="geo">${geo}</span></span>
      <span class="meter">${bar(t.rising||0,6)}</span></div></a>`;
}

function trailChip(t){
  const url='https://trends.google.com/trends/explore?q='+encodeURIComponent(t.query)+'&geo='+t.geo+'&date=now%201-d';
  return `<a class="chip" href="${url}" target="_blank" rel="noopener"
    title="peaked ${fmtK(t.peak_traffic)} · lasted ${t.lasted_min}m">
    <span class="ar down">▼</span> <b>${esc(t.query)}</b> · ${fmtK(t.peak_traffic)} · gone ${ago(t.gone_min)}</a>`;
}

function gapRow(g){
  const url='https://news.google.com/search?q='+encodeURIComponent(g.query)+'&hl=en-IN&gl=IN&ceid=IN:en';
  return `<a class="gap" href="${url}" target="_blank" rel="noopener">
    <span class="flag">${g.coverage===0?'UNCOVERED':'1 OUTLET'}</span>
    <span class="q">${esc(g.query)}</span>
    <span class="n">${fmtK(g.traffic)} · ${ago(g.age_min)}</span></a>`;
}

function row(c,i){
  const t=tier(c.score), d=c.direction||'flat';
  const langs=(c.languages||[]).map(l=>l==='te'?'తె':'en').join('+');
  const delta = d==='up'||d==='down' ? `<span class="d ${d}-c">${c.score_delta>0?'+':''}${Math.round(c.score_delta)}</span>`
              : d==='new' ? `<span class="d ar new">new</span>` : `<span class="d">&nbsp;</span>`;
  const why=c.trend_query ? `<div class="why">└─ searching "${esc(c.trend_query)}" · ${esc(c.trend_geo||'')}</div>` : '';
  const gloss=c.title_en ? `<div class="gloss">${esc(c.title_en)}</div>` : '';
  const outl = c.outlet_delta>0 ? ` <span class="up-c">+${c.outlet_delta}</span>` : '';
  const links=(c.links||[]).filter(l=>l.url).map(l=>
    `<a href="${esc(l.url)}" target="_blank" rel="noopener">
      <span class="t">${l.kind==='social'?'◆ ':l.kind==='video'?'▶ ':''}${esc(l.title)}</span>
      <span class="o">${esc(l.outlet)} ${ago(l.age_min)}</span></a>`).join('');
  return `<article class="row ${i===CUR?'cur':''}" data-i="${i}">
    <div class="gutter">
      <span class="n t-${t}">${arrow(d)}${Math.round(c.score)}</span>
      ${delta}
      <span class="sp" title="trend accel outlets velocity fresh">${spark(c.breakdown)}</span>
    </div>
    <div class="body">
      <h3 class="ttl"><span class="tag b-${esc(c.beat||'general')}">${esc(c.beat||'general')}</span>${esc(c.title)}</h3>
      ${gloss}
      <div class="meta"><span class="bar-t t-${t}">${bar(c.score/100,10)}</span>
        &nbsp; <span class="k">${c.outlet_count}</span> outlet${c.outlet_count===1?'':'s'}${outl}
        · ${ago(c.age_min)} · ${langs}${c.locality!=='AP'?' · '+esc(c.locality):''}</div>
      ${why}
      ${links?`<details><summary>+ ${c.item_count} reports</summary><div class="links">${links}</div></details>`:''}
    </div></article>`;
}

const keep = c => {
  if(FILTER==='ap' && c.locality!=='AP') return false;
  if(FILTER==='fresh' && c.age_min>30) return false;
  if(FILTER==='trend' && !c.trend_query) return false;
  if(FILTER==='moving' && !['up','new'].includes(c.direction)) return false;
  if(BEAT && c.beat!==BEAT) return false;
  if(Q){ const h=(c.title+' '+(c.title_en||'')+' '+(c.trend_query||'')+' '+(c.outlets||[]).join(' ')).toLowerCase();
         if(!h.includes(Q)) return false; }
  return true;
};

let countdownTimer=null;
function renderBar(){
  const s=DATA.stats||{}; const now=Date.now();
  const last=DATA.last_tick?new Date(DATA.last_tick):null;
  const ageS=last?(now-last)/1000:0;
  const stale=last && ageS > (DATA.tick_seconds||300)*3;
  const live=document.getElementById('s-live');
  live.className='seg'+(stale?' stale':'');
  live.innerHTML= stale ? `▲ STALE ${ago(Math.round(ageS/60))}` : `<span class="dot live"></span>live`;
  document.getElementById('s-upd').textContent = last
    ? 'updated '+last.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',hour12:false})
    : 'first tick running…';
  const next=DATA.next_tick_at?new Date(DATA.next_tick_at):null;
  const nx=document.getElementById('s-next');
  clearInterval(countdownTimer);
  const tickDown=()=>{ if(!next){nx.textContent='';return;}
    const s=Math.max(0,Math.round((next-Date.now())/1000));
    nx.textContent = s>0 ? `next ${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}` : 'polling…'; };
  tickDown(); countdownTimer=setInterval(tickDown,1000);
  document.getElementById('s-cnt').textContent =
    `${s.clusters||0} stories · ${s.trends||0} trends` + (s.too_old?` · ${s.too_old} too old`:'');
  const ok=s.sources_ok??0, tot=s.sources_total??0;
  const src=document.getElementById('s-src');
  src.innerHTML=`<span class="dot ${ok<tot?'bad':''}"></span>src ${ok}/${tot}`;

  const notes=[];
  if(DATA.last_error) notes.push(['bad','last tick failed: '+esc(DATA.last_error)]);
  if((DATA.degraded||[]).length) notes.push(['warn','degraded this tick: '+DATA.degraded.join(', ')+' — showing last good data for those']);
  const cd=Object.entries(DATA.cooldowns||{});
  if(cd.length) notes.push(['warn','cooling down: '+cd.map(([h,s])=>`${h} (${Math.ceil(s/60)}m)`).join(', ')]);
  document.getElementById('notices').innerHTML =
    notes.map(([k,t])=>`<div class="notice ${k==='bad'?'bad':''}">${t}</div>`).join('');
}

function renderSources(){
  const rows=(DATA.sources||[]).map(s=>`<tr>
    <td class="${s.ok?'ok':'err'}">${s.ok?'ok':'FAIL'}</td>
    <td>${esc(s.name)}</td><td class="num">${s.count}</td><td class="num">${s.ms}ms</td>
    <td class="num">${s.last_ok?ago(Math.round((Date.now()-new Date(s.last_ok))/60000))+' ago':'never'}</td>
    <td class="${s.ok?'':'err'}">${s.ok?'':esc(s.last_error)+(s.failures>1?` ×${s.failures}`:'')}</td></tr>`).join('');
  document.getElementById('srcpanel').innerHTML = rows?`<table>${rows}</table>`:'';
}

function render(){
  if(!DATA) return;
  renderBar(); renderSources();
  const tr=(DATA.trends||[]).slice(0,24);
  document.getElementById('trends').innerHTML = tr.length ? tr.map(trendCell).join('') : '<div class="empty">no trend data yet</div>';
  document.getElementById('n-tr').textContent = tr.length ? `${tr.filter(t=>t.direction==='up'||t.direction==='new').length}▲ ${tr.filter(t=>t.direction==='down').length}▼` : '';
  const trl=DATA.trailing||[];
  document.getElementById('trailing').innerHTML = trl.length ? trl.map(trailChip).join('') : '<div class="empty" style="border:none">nothing has dropped off in the last 90 minutes</div>';
  document.getElementById('n-trail').textContent = trl.length? trl.length+'' : '';
  const g=DATA.gaps||[];
  document.getElementById('gaps').innerHTML = g.length ? g.map(gapRow).join('') : '<div class="empty">nothing rising without coverage — you are on top of it</div>';

  const all=DATA.board||[];
  const present=new Set(all.map(c=>c.beat||'general'));
  document.getElementById('beats').innerHTML = BEAT_LIST.filter(b=>present.has(b)).map(b=>
    `<button data-b="${b}" class="b-${b} ${BEAT===b?'on':''}">${b}</button>`).join('');
  document.querySelectorAll('#beats button').forEach(btn=>btn.onclick=()=>{BEAT=BEAT===btn.dataset.b?null:btn.dataset.b; render();});

  const b=all.filter(keep);
  if(CUR>=b.length) CUR=b.length-1;
  document.getElementById('board').innerHTML = b.length ? b.map(row).join('') : '<div class="empty">no stories match this filter</div>';
  document.getElementById('n-board').textContent = `${b.length}/${all.length}`;
  document.querySelectorAll('.row').forEach(el=>el.onclick=e=>{ if(e.target.closest('a,summary')) return; CUR=+el.dataset.i; markCur(); });
}
function markCur(){ document.querySelectorAll('.row').forEach(el=>el.classList.toggle('cur',+el.dataset.i===CUR));
  const el=document.querySelector('.row.cur'); if(el) el.scrollIntoView({block:'nearest'}); }

document.querySelectorAll('#filters button').forEach(btn=>btn.onclick=()=>setFilter(btn.dataset.f));
function setFilter(f){ FILTER=f; document.querySelectorAll('#filters button').forEach(x=>x.classList.toggle('on',x.dataset.f===f)); CUR=-1; render(); }
const qbox=document.getElementById('q');
qbox.oninput=()=>{ Q=qbox.value.trim().toLowerCase(); CUR=-1; render(); };
document.getElementById('s-src').onclick=()=>{ const p=document.getElementById('srcpanel'); p.hidden=!p.hidden; };

document.addEventListener('keydown',e=>{
  if(e.target===qbox){ if(e.key==='Escape'){ qbox.value=''; Q=''; qbox.blur(); render(); } return; }
  if(e.ctrlKey||e.metaKey||e.altKey) return;
  const rows=document.querySelectorAll('.row'); if(!rows.length && !'/s12345'.includes(e.key)) return;
  switch(e.key){
    case '/': e.preventDefault(); qbox.focus(); break;
    case 'j': CUR=Math.min(rows.length-1,CUR+1); markCur(); break;
    case 'k': CUR=Math.max(0,CUR-1); markCur(); break;
    case 'o': case 'Enter': { const el=document.querySelector('.row.cur .links a'); if(el) window.open(el.href,'_blank','noopener'); break; }
    case 'Escape': CUR=-1; BEAT=null; markCur(); render(); break;
    case 's': document.getElementById('s-src').click(); break;
    case '1': setFilter('all'); break; case '2': setFilter('ap'); break; case '3': setFilter('fresh'); break;
    case '4': setFilter('trend'); break; case '5': setFilter('moving'); break;
  }
});

async function tick(){
  try{
    const [b,t]=await Promise.all([fetch('/api/board',{cache:'no-store'}), fetch('/api/theme',{cache:'no-store'})]);
    DATA=await b.json(); applyTheme(await t.json()); render();
  }catch(e){ /* keep the last good board on screen */ }
}
tick(); setInterval(tick, 30000);
</script></body></html>
"""


class Handler(BaseHTTPRequestHandler):
    server_version = "APRadar/1.1"

    def log_message(self, fmt, *args):  # keep the console clean for tick output
        pass

    def _send(self, body: bytes, ctype: str, code: int = 200) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, code: int = 200) -> None:
        self._send(json.dumps(obj, default=str).encode("utf-8"),
                   "application/json; charset=utf-8", code)

    def do_GET(self) -> None:
        path = self.path.split("?")[0]
        try:
            if path == "/":
                page = PAGE.replace("__THEME_VARS__", theme.css_vars())
                self._send(page.encode("utf-8"), "text/html; charset=utf-8")
            elif path == "/api/board":
                self._json(poll.snapshot())
            elif path == "/api/theme":
                self._json(theme.current())
            elif path == "/api/health":
                state = poll.snapshot()
                alive = poll.ensure_poller()
                stale = poll.is_stale()
                self._json({
                    "ok": state["last_error"] is None and alive and not stale,
                    "poller_alive": alive,
                    "stale": stale,
                    "last_tick": state["last_tick"],
                    "ticks": state["tick_count"],
                    "sources_ok": (state.get("stats") or {}).get("sources_ok"),
                    "sources_total": (state.get("stats") or {}).get("sources_total"),
                    "degraded": state.get("degraded", []),
                }, 200 if alive else 503)
            else:
                self._send(b"not found", "text/plain", 404)
        except Exception as e:  # a rendering bug must not take the server down
            self._json({"error": type(e).__name__, "detail": str(e)[:200]}, 500)


def serve() -> None:
    httpd = ThreadingHTTPServer((config.SERVER_HOST, config.SERVER_PORT), Handler)
    httpd.daemon_threads = True
    print(f"  dashboard  http://{config.SERVER_HOST}:{config.SERVER_PORT}", flush=True)
    httpd.serve_forever()

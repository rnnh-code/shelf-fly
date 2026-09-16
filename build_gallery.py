"""Build the free gallery page: runs each example matchup through the fly once and bakes the
results into gallery/index.html, a single self-contained file that any static host can serve.

run:  .venv/bin/python build_gallery.py
"""
import html
from pathlib import Path

from markdown_it import MarkdownIt

import shelfly

HERE = Path(__file__).parent
EX = HERE / "examples"
REPO = "https://github.com/rnnh-code/shelf-fly"

PAIRS = [
    {"slug": "ridgeline", "title": "Ridgeline body wash", "change": "Same bottle in charcoal and in pale grey.",
     "a": ("ridgeline-a.jpg", "Charcoal bottle"), "b": ("ridgeline-b.jpg", "Pale bottle")},
    {"slug": "crunch", "title": "Crunch Hollow chips", "change": "Same bag with a big logo and a small logo.",
     "a": ("crunch-a.jpg", "Big logo"), "b": ("crunch-b.jpg", "Small logo")},
    {"slug": "voltra", "title": "Voltra energy drink", "change": "Same can with one big mark and with a busy all-over pattern.",
     "a": ("voltra-a.jpg", "One big mark"), "b": ("voltra-b.jpg", "Busy pattern")},
    {"slug": "hollow-pine", "title": "Hollow Pine cereal", "change": "Same box in bold dark colours and in soft pale colours.",
     "a": ("hollow-pine-bold.jpg", "Bold box"), "b": ("hollow-pine-soft.jpg", "Soft box")},
]

md = MarkdownIt()
hx, hy = shelfly.hex_coords()


def lane(side, colour, pct, label):
    return f"""
      <div class="lane">
        <h3>{html.escape(side['name'])}</h3>
        <div class="views">
          <figure><img src="data:image/jpeg;base64,{shelfly.b64_photo(side['photo'], 360)}" alt="{html.escape(side['name'])}, as a shopper sees it"><figcaption>What a shopper sees</figcaption></figure>
          <figure><img src="data:image/jpeg;base64,{shelfly.b64_fly_eye(side['eye'], hx, hy)}" alt="{html.escape(side['name'])}, as the fly sees it"><figcaption>What the fly sees</figcaption></figure>
        </div>
        <div class="meter"><span style="width:{pct}%;background:{colour}"></span></div>
        <div class="meter-label">{label}</div>
      </div>"""


sections, tabs = [], []
for i, p in enumerate(PAIRS):
    a, b = shelfly.analyse(EX / p["a"][0]), shelfly.analyse(EX / p["b"][0])
    a["name"], b["name"] = p["a"][1], p["b"][1]
    top = max(a["score"], b["score"])
    win_a = a["score"] > b["score"]
    ymax = top * 1.1
    print(p["slug"], "->", a["name"] if win_a else b["name"], f"{max(a['score'], b['score']) / min(a['score'], b['score']):.2f}x", flush=True)
    tabs.append(f'<button type="button" role="tab" id="tab-{p["slug"]}" aria-controls="m-{p["slug"]}" aria-selected="{str(i == 0).lower()}">{html.escape(p["title"])}</button>')
    sections.append(f"""
    <section class="matchup" id="m-{p['slug']}" role="tabpanel" aria-labelledby="tab-{p['slug']}"{'' if i == 0 else ' hidden'}>
      <p class="change"><strong>{html.escape(p['title'])}.</strong> {html.escape(p['change'])}</p>
      <div class="lanes">{lane(a, '#B23A2E', round(100 * a['score'] / top), 'Noticed more' if win_a else 'Noticed less')}{lane(b, '#2D5A9E', round(100 * b['score'] / top), 'Noticed more' if not win_a else 'Noticed less')}</div>
      <div class="result">
        <div class="verdict">{md.render(shelfly.plain_verdict(a, b))}</div>
        <figure class="chart">
          <svg viewBox="0 0 560 200" role="img" aria-label="How strongly the fly's brain reacted over time">
            <line x1="16" y1="170" x2="536" y2="170" stroke="#3A443E"></line>
            <line x1="81.8" y1="14" x2="81.8" y2="170" stroke="#6B776F" stroke-dasharray="3 4"></line>
            <text x="88" y="162" class="t">pack appears</text>
            <g transform="translate(16,14)">
              <path d="{shelfly.svg_path(a['trace'], ymax)}" fill="none" stroke="#E36A5E" stroke-width="2.5" stroke-linejoin="round"></path>
              <path d="{shelfly.svg_path(b['trace'], ymax)}" fill="none" stroke="#7FA6E8" stroke-width="2.5" stroke-linejoin="round"></path>
            </g>
            <text x="536" y="26" text-anchor="end" class="t" fill="{'#E36A5E' if win_a else '#7FA6E8'}">{html.escape((a if win_a else b)['name'])}</text>
            <text x="536" y="44" text-anchor="end" class="t" fill="{'#7FA6E8' if win_a else '#E36A5E'}">{html.escape((b if win_a else a)['name'])}</text>
            <text x="16" y="192" class="t">0 s</text>
            <text x="536" y="192" text-anchor="end" class="t">0.8 s</text>
          </svg>
          <figcaption>The fly's brain activity, from blank screen to 0.8 seconds after the pack appears.</figcaption>
        </figure>
      </div>
    </section>""")

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shelf Fly</title>
<meta name="description" content="Which package gets noticed first? Pack designs seen through a simulated fruit fly visual system.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root {{ color-scheme: light; --ground:#EEF1EC; --surface:#FBFCFA; --ink:#121714; --body:#3F4943; --muted:#5E6A63; --rule:#D5DBD5; --dark:#121714; }}
  * {{ box-sizing: border-box; }}
  [hidden] {{ display: none !important; }}
  body {{ margin:0; background:var(--ground); color:var(--ink); font:17px/1.55 'Bricolage Grotesque','Avenir Next',system-ui,sans-serif; }}
  .wrap {{ max-width:1120px; margin:0 auto; padding-inline:20px; padding-block:40px 64px; display:flex; flex-direction:column; gap:32px; }}
  .mono, figcaption, .t, .meter-label, .eyebrow {{ font-family:'IBM Plex Mono',Menlo,monospace; }}
  .eyebrow {{ font-size:12px; letter-spacing:.12em; text-transform:uppercase; color:var(--muted); }}
  header {{ display:flex; flex-direction:column; gap:12px; }}
  h1 {{ margin:0; font-size:clamp(34px,6vw,62px); line-height:1; letter-spacing:-.025em; text-wrap:balance; }}
  .lede {{ margin:0; font-size:clamp(18px,2.2vw,21px); color:var(--body); max-width:62ch; }}
  .tabs {{ display:flex; flex-wrap:wrap; gap:8px; }}
  .tabs button {{ font:inherit; font-size:16px; padding:9px 16px; border-radius:999px; border:1px solid var(--rule); background:var(--surface); color:var(--ink); cursor:pointer; }}
  .tabs button[aria-selected="true"] {{ background:var(--ink); color:#F1F4F0; border-color:var(--ink); }}
  .tabs button:focus-visible {{ outline:3px solid #2D5A9E; outline-offset:2px; }}
  .matchup {{ display:flex; flex-direction:column; gap:20px; }}
  .change {{ margin:0; font-size:19px; color:var(--body); }}
  .change strong {{ color:var(--ink); }}
  .lanes {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; }}
  .lane {{ background:var(--surface); border:1px solid var(--rule); border-radius:8px; padding:20px; display:flex; flex-direction:column; gap:14px; }}
  .lane h3 {{ margin:0; font-size:24px; letter-spacing:-.01em; }}
  .views {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
  figure {{ margin:0; }}
  .views img {{ width:100%; aspect-ratio:1; object-fit:contain; border-radius:4px; background:#fff; display:block; }}
  figcaption {{ font-size:11px; color:var(--muted); margin-top:6px; }}
  .meter {{ height:12px; background:#E3E8E3; border-radius:2px; overflow:hidden; }}
  .meter span {{ display:block; height:100%; }}
  .meter-label {{ font-size:13px; color:var(--body); }}
  .result {{ display:grid; grid-template-columns:1.1fr 1fr; gap:18px; align-items:start; }}
  .verdict {{ background:var(--surface); border:1px solid var(--rule); border-radius:8px; padding:24px; }}
  .verdict h2 {{ margin:0 0 10px; font-size:clamp(24px,3vw,30px); line-height:1.12; text-wrap:balance; }}
  .verdict p {{ margin:0 0 10px; color:var(--body); }}
  .verdict p:last-child {{ margin:0; }}
  .verdict strong {{ color:var(--ink); }}
  .chart {{ background:var(--dark); border-radius:8px; padding:18px; }}
  .chart svg {{ width:100%; height:auto; display:block; }}
  .chart .t {{ font-size:11px; fill:#9AA69F; }}
  .chart figcaption {{ color:#9AA69F; }}
  .about {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; border-top:1px solid var(--rule); padding-top:28px; }}
  .about h2 {{ margin:0 0 8px; font-size:22px; }}
  .about p {{ margin:0 0 10px; color:var(--body); max-width:60ch; }}
  a {{ color:#2D5A9E; }}
  footer {{ font-size:12px; color:var(--muted); line-height:1.6; }}
  @media (max-width: 760px) {{ .lanes, .result, .about {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="eyebrow">Shelf Fly</div>
    <h1>Which package gets noticed first?</h1>
    <p class="lede">Each matchup shows two versions of the same made-up product to a computer model of a fruit fly's eye and brain. The fly sees in blurry black and white, so it reacts to shapes and light-versus-dark, never to colour or words. Pick a matchup.</p>
  </header>

  <nav class="tabs" role="tablist" aria-label="Matchups">{''.join(tabs)}</nav>
  {''.join(sections)}

  <div class="about">
    <div>
      <h2>How it works</h2>
      <p>Each pack is turned grey and shown to a simulated fly eye made of 721 lenses: a blank screen, then the pack appears and stays. Five trained versions of the fly's visual system watch that clip, and we measure how much its brain activity changes once the pack is on screen.</p>
      <p>We also run a plain light-versus-dark measure with no brain in it, and check that both packs take up the same space, so you can see when a result is just about contrast or size.</p>
    </div>
    <div>
      <h2>What it doesn't tell you</h2>
      <p>Whether people would buy one pack over the other. A fly is not a shopper. This shows which pack is more likely to catch an eye first.</p>
      <p>Want to try your own photos? The <a href="{REPO}">code is on GitHub</a> and runs on a laptop.</p>
    </div>
  </div>

  <footer>All brands on this page are made up. Fly vision model: <a href="https://github.com/TuragaLab/flyvis">flyvis</a> (Lappalainen et al., Nature 2024), built on connectome data from Janelia Research Campus; results average 5 of its 50 trained versions.</footer>
</div>
<script>
  const tabs = [...document.querySelectorAll('[role="tab"]')];
  function show(tab) {{
    tabs.forEach(t => {{
      const on = t === tab;
      t.setAttribute('aria-selected', on);
      t.tabIndex = on ? 0 : -1;
      document.getElementById(t.getAttribute('aria-controls')).hidden = !on;
    }});
  }}
  tabs.forEach((t, i) => {{
    t.tabIndex = i === 0 ? 0 : -1;
    t.addEventListener('click', () => show(t));
    t.addEventListener('keydown', e => {{
      const d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
      if (d) {{ const n = tabs[(i + d + tabs.length) % tabs.length]; show(n); n.focus(); }}
    }});
  }});
</script>
</body>
</html>
"""
out = HERE / "gallery"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(page)
print(f"wrote {out / 'index.html'} ({len(page) // 1024} KB)")

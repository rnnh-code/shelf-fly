"""Shelf Fly: show two product photos to a simulated fruit fly visual system.

usage:  python shelfly.py photo-a.jpg photo-b.jpg [--names "Brand A" "Brand B"]

Writes results/<name>/result.html (open it in a browser) plus the raw numbers.
What it measures: which photo grabs an eye first. Not which one a shopper buys.
"""
import argparse
import base64
import logging
import io
import json
import subprocess
import sys
from pathlib import Path
from string import Template

import matplotlib.image as mpimg
import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image

logging.disable(logging.WARNING)  # the model chatters through top-level loggers on startup

import flyvis
from flyvis.datasets.rendering import BoxEye
from flyvis.utils import hex_utils

DT, N_FRAMES, POP, N_MODELS, SIDE = 1 / 100, 80, 10, 5, 256
LATE = slice(N_FRAMES - 20, N_FRAMES)
INK, MUTED, RULE, GROUND, SURFACE = "#121714", "#5E6A63", "#D5DBD5", "#EEF1EC", "#FBFCFA"
A_COLOUR, B_COLOUR = "#C8102E", "#1F4FA8"


def to_grey_square(path):
    """Load a photo, drop colour, pad to a square on its own background, shrink to 256px."""
    img = mpimg.imread(path)
    if img.dtype == np.uint8:
        img = img.astype(np.float32) / 255
    rgb = img[..., :3].astype(np.float32) if img.ndim == 3 else np.stack([img] * 3, -1).astype(np.float32)
    grey = rgb @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    bg = float(np.median(grey[:20, :20]))
    h, w = grey.shape
    s = max(h, w)
    canvas = np.full((s, s), bg, dtype=np.float32)
    canvas[(s - h) // 2 : (s - h) // 2 + h, (s - w) // 2 : (s - w) // 2 + w] = grey
    small = F.interpolate(torch.tensor(canvas)[None, None], size=(SIDE, SIDE), mode="area")[0, 0]
    return small.numpy(), bg


def frames(img, bg):
    """The clip the fly watches: grey, then the product appears and holds still.

    ponytail: walk-past mode (the product sliding across instead of popping in)
    drops in here as a second builder when we do version B.
    """
    f = np.full((N_FRAMES, SIDE, SIDE), bg, dtype=np.float32)
    f[POP:] = img
    return f


def b64_photo(path, width=420):
    im = Image.open(path).convert("RGB")
    im.thumbnail((width, width * 3))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=82)
    return base64.b64encode(buf.getvalue()).decode()


def b64_fly_eye(eye, hx, hy):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(3.2, 3.2), dpi=140)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.scatter(hx, hy, c=eye, cmap="gray", vmin=0, vmax=1, s=42, marker="h", linewidths=0)
    ax.set_aspect("equal")
    ax.axis("off")
    buf = io.BytesIO()
    fig.savefig(buf, format="jpeg", facecolor=SURFACE)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def svg_path(trace, ymax, w=520, h=150):
    pts = [f"{i * w / (len(trace) - 1):.1f},{h - v * h / ymax:.1f}" for i, v in enumerate(trace)]
    return "M" + " L".join(pts)


CARD = Template("""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shelf Fly · $name_a vs $name_b</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,400;12..96,600;12..96,700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root { color-scheme: light; }
  body { margin: 0; background: $ground; color: $ink;
         font-family: 'Bricolage Grotesque', 'Avenir Next', system-ui, sans-serif; }
  .wrap { max-width: 1180px; margin: 0 auto; padding-block: 44px; padding-left: 24px; padding-right: 24px;
          display: flex; flex-direction: column; gap: 26px; }
  .eyebrow { font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 12px; letter-spacing: .12em;
             text-transform: uppercase; color: $muted; }
  h1 { margin: 0; font-size: clamp(30px, 4.4vw, 50px); line-height: 1.04; letter-spacing: -.02em; text-wrap: balance; }
  .sub { margin: 0; font-size: 18px; line-height: 1.45; color: #3F4943; max-width: 660px; }
  .lanes { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 22px; }
  .lane { background: $surface; border: 1px solid $rule; border-radius: 6px; padding: 22px;
          display: flex; flex-direction: column; gap: 16px; }
  .lane h2 { margin: 0; font-size: 28px; letter-spacing: -.015em; }
  .pair { display: grid; grid-template-columns: minmax(0, 1fr) 150px; gap: 20px; align-items: start; }
  .pair img { width: 100%; border-radius: 4px; }
  .cap { font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 11px; color: $muted; margin-top: 6px; }
  .bar { height: 14px; background: #E3E8E3; border-radius: 2px; overflow: hidden; }
  .bar span { display: block; height: 100%; }
  .score { font-size: 26px; font-weight: 700; margin-top: 8px; }
  .verdict { background: $ink; color: #F1F4F0; border-radius: 6px; padding: 26px;
             display: flex; flex-direction: column; gap: 12px; }
  .verdict h3 { margin: 0; font-size: clamp(24px, 3vw, 34px); line-height: 1.1; text-wrap: balance; }
  .verdict p { margin: 0; font-size: 16px; line-height: 1.5; color: #C9D1CB; }
  .checks { background: $surface; border: 1px solid $rule; border-radius: 6px; padding: 26px; }
  .checks h3 { margin: 0 0 14px; font-size: 22px; }
  .row { display: flex; justify-content: space-between; gap: 16px; padding: 10px 0; border-bottom: 1px solid #E3E8E3; }
  .row span:last-child { font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 14px; white-space: nowrap; }
  .bottom { display: grid; grid-template-columns: 1.15fr 1fr; gap: 22px; }
  footer { font-family: 'IBM Plex Mono', Menlo, monospace; font-size: 11px; line-height: 1.6; color: $muted; }
  @media (max-width: 860px) { .lanes, .bottom { grid-template-columns: 1fr; } .pair { grid-template-columns: 1fr; } }
</style></head>
<body><div class="wrap">
  <div style="display:flex; flex-direction:column; gap:10px;">
    <div class="eyebrow">Shelf Fly · $name_a vs $name_b</div>
    <h1>$headline</h1>
    <p class="sub">Both photos were shown to a simulated fruit fly visual system: 45,669 cells, 721 grey hexagons instead of pixels. This measures what grabs an eye first.</p>
  </div>

  <div class="lanes">
    <div class="lane">
      <h2>$name_a</h2>
      <div class="pair">
        <div><img src="data:image/jpeg;base64,$photo_a" alt="$name_a"><div class="cap">What a shopper sees</div></div>
        <div><img src="data:image/jpeg;base64,$eye_a" alt="$name_a as the fly sees it"><div class="cap">What the fly sees</div></div>
      </div>
      <div>
        <div class="eyebrow">Eye-catch score</div>
        <div class="bar"><span style="width:$pct_a%; background:$a_colour;"></span></div>
        <div class="score">$score_a</div>
      </div>
    </div>
    <div class="lane">
      <h2>$name_b</h2>
      <div class="pair">
        <div><img src="data:image/jpeg;base64,$photo_b" alt="$name_b"><div class="cap">What a shopper sees</div></div>
        <div><img src="data:image/jpeg;base64,$eye_b" alt="$name_b as the fly sees it"><div class="cap">What the fly sees</div></div>
      </div>
      <div>
        <div class="eyebrow">Eye-catch score</div>
        <div class="bar"><span style="width:$pct_b%; background:$b_colour;"></span></div>
        <div class="score">$score_b</div>
      </div>
    </div>
  </div>

  <div class="bottom">
    <div class="verdict">
      <div class="eyebrow" style="color:#C9D1CB;">Verdict</div>
      <h3>$verdict</h3>
      <p>$verdict_note</p>
      <svg viewBox="0 0 560 196" width="100%" height="196" role="img" aria-label="Reaction over time">
        <line x1="16" y1="170" x2="536" y2="170" stroke="#3A443E" stroke-width="1"></line>
        <line x1="81.8" y1="14" x2="81.8" y2="170" stroke="#5E6A63" stroke-width="1" stroke-dasharray="3 4"></line>
        <text x="88" y="162" font-family="IBM Plex Mono, monospace" font-size="11" fill="#9AA69F">photo appears</text>
        <g transform="translate(16,14)">
          <path d="$path_a" fill="none" stroke="#E0443C" stroke-width="2.5" stroke-linejoin="round"></path>
          <path d="$path_b" fill="none" stroke="#6E9BF0" stroke-width="2.5" stroke-linejoin="round"></path>
        </g>
        <text x="536" y="26" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="12" fill="$top_colour">$top_name</text>
        <text x="536" y="44" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="12" fill="$bottom_colour">$bottom_name</text>
        <text x="16" y="190" font-family="IBM Plex Mono, monospace" font-size="11" fill="#9AA69F">0 ms</text>
        <text x="536" y="190" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="11" fill="#9AA69F">800 ms</text>
      </svg>
    </div>

    <div class="checks">
      <h3>Checks</h3>
      <div class="row"><span>Fly models that picked the winner</span><span>$agree of $n_models</span></div>
      <div class="row"><span>Simple stand-out measure, no brain</span><span>$baseline</span></div>
      <div class="row"><span>Size on screen (winner vs loser)</span><span>$size_note</span></div>
      <div class="row" style="border-bottom:none;"><span>Gap between the two</span><span>$ratio× </span></div>
      <p style="font-size:15px; line-height:1.5; color:#3F4943; margin:14px 0 0;">$caveat</p>
    </div>
  </div>

  <footer>Fly vision model: flyvis (Lappalainen et al., Nature 2024), built on an earlier Janelia map of the fly's visual system, averaged over $n_models of its 50 trained versions. The fly sees no colour. A high score means the photo grabs an eye, not that a shopper prefers it. Photo rights are the uploader's responsibility.</footer>
</div></body></html>""")


_MODELS = None


def models():
    """Load the 5 trained fly models once and keep them (about 20 seconds the first time)."""
    global _MODELS
    if not (flyvis.results_dir / "flow/0000/004").exists():
        print("First run: downloading the trained fly models from the flyvis project (a few MB)...", flush=True)
        subprocess.run([sys.executable, "-m", "flyvis_cli.download_pretrained_models"], check=True)
    if _MODELS is None:
        _MODELS = (
            BoxEye(),
            [flyvis.NetworkView(flyvis.results_dir / f"flow/0000/{i:03d}").init_network() for i in range(N_MODELS)],
        )
    return _MODELS


def hex_coords():
    return hex_utils.hex_to_pixel(*hex_utils.get_hex_coords(hex_utils.get_hextent(721)))


def analyse(path):
    """Show one photo to the fly. Returns its reaction over time plus what the eye saw."""
    receptors, nets = models()
    img, bg = to_grey_square(path)
    movie = receptors(torch.tensor(frames(img, bg), device=flyvis.device)[None])[0]
    per_model = []
    for net in nets:
        init = net.fade_in_state(1.0, DT, movie[[0]])
        r = net.simulate(movie[None], DT, initial_state=init).cpu().numpy()[0]
        per_model.append(np.abs(r - r[0]).mean(axis=1))
    per_model = np.array(per_model)
    eye = movie[-1, 0].cpu().numpy()
    return {
        "photo": str(path),
        "name": Path(path).stem.replace("-", " ").replace("_", " ").title(),
        "trace": per_model.mean(axis=0),
        "score": float(per_model.mean(axis=0)[LATE].mean()),
        "per_model": [float(m[LATE].mean()) for m in per_model],
        "stand_out": float(eye.std()),
        "coverage": float((np.abs(img - bg) > 0.08).mean()),  # share of the frame the product covers
        "eye": eye,
    }


def plain_verdict(a, b):
    """Turn the numbers into a few sentences anyone can read."""
    win, lose = (a, b) if a["score"] > b["score"] else (b, a)
    gap = win["score"] / lose["score"]
    agree = sum((x > y) == (a["score"] > b["score"]) for x, y in zip(a["per_model"], b["per_model"]))
    contrast_agrees = (win["stand_out"] > lose["stand_out"])
    size_gap = max(win["coverage"], lose["coverage"]) / max(min(win["coverage"], lose["coverage"]), 1e-6)

    if gap < 1.15:
        strength, how_much = "a close call", f"only about {round((gap - 1) * 100)}% more"
    elif gap < 1.5:
        strength, how_much = "a clear win", f"about {round((gap - 1) * 100)}% more"
    else:
        strength, how_much = "a big win", f"{gap:.1f} times more"

    if agree == N_MODELS:
        sure = f"We ran {N_MODELS} versions of the fly and **all of them agreed.**"
    elif agree >= N_MODELS - 1:
        sure = f"We ran {N_MODELS} versions of the fly and **{agree} agreed**, so this is fairly solid."
    else:
        sure = f"We ran {N_MODELS} versions of the fly and they **split {agree} to {N_MODELS - agree}.** Treat this as a toss-up."

    if contrast_agrees:
        why = f"**Why:** {win['name']} has more light-versus-dark contrast, and that's mostly what a fly's eye picks up."
    else:
        why = (f"**Why:** interesting one. {lose['name']} actually has more contrast, but the fly still reacted more to "
               f"{win['name']}, so its shape or pattern mattered more than plain contrast.")

    if size_gap > 1.25:
        bigger = win if win["coverage"] > lose["coverage"] else lose
        fair = (f"**Heads up:** {bigger['name']} takes up noticeably more of its photo, which gives it an unfair boost. "
                f"Use photos where both products are about the same size for a fairer test.")
    else:
        fair = "**Fair test:** both products take up about the same space in their photos, so size didn't decide this."

    return f"""## {win['name']} gets noticed first ({strength})
The fly's brain reacted {how_much} to **{win['name']}** than to {lose['name']}.

{sure}

{why}

{fair}

*What this means: {win['name']} is more likely to catch an eye first on a shelf. It doesn't tell you which one people would rather buy.*
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("photos", nargs=2, help="the two product photos to compare")
    ap.add_argument("--name", help="folder name for the result (default: the two filenames)")
    ap.add_argument("--names", nargs=2, metavar=("A", "B"), help="product names to print on the card")
    opts = ap.parse_args()
    args = opts.photos
    for photo in args:
        if not Path(photo).is_file():
            ap.error(f"no such photo: {photo}")
    labels = opts.names or [Path(a).stem for a in args]
    slug = "-vs-".join("".join(ch if ch.isalnum() else "-" for ch in n).strip("-").lower() for n in labels)
    out = Path(__file__).parent / "results" / (opts.name or slug)
    out.mkdir(parents=True, exist_ok=True)

    side = {key: analyse(path) for key, path in zip("AB", args)}
    hx, hy = hex_coords()

    if opts.names:
        side["A"]["name"], side["B"]["name"] = opts.names

    a, b = side["A"], side["B"]
    win, lose = (a, b) if a["score"] > b["score"] else (b, a)
    agree = sum((x > y) == (a["score"] > b["score"]) for x, y in zip(a["per_model"], b["per_model"]))
    ratio = win["score"] / lose["score"]
    baseline_winner = a["name"] if a["stand_out"] > b["stand_out"] else b["name"]
    ymax = max(a["trace"].max(), b["trace"].max()) * 1.1

    card = CARD.substitute(
        ground=GROUND, surface=SURFACE, ink=INK, muted=MUTED, rule=RULE,
        a_colour=A_COLOUR, b_colour=B_COLOUR, n_models=N_MODELS,
        name_a=a["name"], name_b=b["name"],
        headline=f"{win['name']} catches the fly's eye first.",
        photo_a=b64_photo(a["photo"]), photo_b=b64_photo(b["photo"]),
        eye_a=b64_fly_eye(a["eye"], hx, hy), eye_b=b64_fly_eye(b["eye"], hx, hy),
        pct_a=round(100 * a["score"] / max(a["score"], b["score"])),
        pct_b=round(100 * b["score"] / max(a["score"], b["score"])),
        score_a="Stronger" if a is win else "Weaker", score_b="Stronger" if b is win else "Weaker",
        verdict=f"The fly reacted {ratio:.1f}× more to {win['name']}.",
        verdict_note=f"All {N_MODELS} versions of the model watched the same clip: grey, then the photo appears and holds."
        if agree == N_MODELS else f"{agree} of {N_MODELS} versions of the model agreed.",
        path_a=svg_path(a["trace"], ymax), path_b=svg_path(b["trace"], ymax),
        top_name=win["name"], top_colour="#EF7A73" if win is a else "#8FB2F5",
        bottom_name=lose["name"], bottom_colour="#EF7A73" if lose is a else "#8FB2F5",
        agree=agree,
        baseline=("agrees" if baseline_winner == win["name"] else f"disagrees, picks {lose['name']}"),
        size_note=f"{win['coverage'] * 100:.0f}% vs {lose['coverage'] * 100:.0f}% of the frame",
        ratio=f"{ratio:.2f}",
        caveat="A bigger or darker product covers more of the eye, which lifts the score on its own. "
        "Shoot both products the same size against the same background before reading anything into a result.",
    )
    (out / "result.html").write_text(card)
    json.dump(
        {k: {kk: vv for kk, vv in v.items() if kk not in ("trace", "eye")} for k, v in side.items()}
        | {"winner": win["name"], "ratio": ratio, "models_agreeing": agree, "stand_out_picks": baseline_winner},
        open(out / "result.json", "w"), indent=2,
    )
    print(f"{win['name']} wins, {ratio:.2f}x, {agree}/{N_MODELS} models agree")
    print(f"open {out / 'result.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

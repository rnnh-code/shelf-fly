"""Shelf Fly, as a web page: drop in two product photos, see which one catches a fly's eye.

run:  .venv/bin/python app.py          then open the link it prints
"""
import base64
import io

from pathlib import Path

import gradio as gr
from PIL import Image

import shelfly

HERE = Path(__file__).parent

INTRO = """# Shelf Fly
**Which package gets noticed first?** Put in two product photos. A computer model of a fruit fly's eye and brain looks at both, and tells you which one it reacted to more.

The fly sees in blurry black and white, so it notices shapes and light-versus-dark, not colours or words.
"""


def fly_eye_image(eye):
    hx, hy = shelfly.hex_coords()
    return Image.open(io.BytesIO(base64.b64decode(shelfly.b64_fly_eye(eye, hx, hy))))


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
        strength, how_much = "a big win", f"{gap:.1f} times as much"

    if agree == shelfly.N_MODELS:
        sure = f"We ran {shelfly.N_MODELS} versions of the fly and **all of them agreed.**"
    elif agree >= shelfly.N_MODELS - 1:
        sure = f"We ran {shelfly.N_MODELS} versions of the fly and **{agree} agreed**, so this is fairly solid."
    else:
        sure = f"We ran {shelfly.N_MODELS} versions of the fly and they **split {agree} to {shelfly.N_MODELS - agree}.** Treat this as a toss-up."

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


def compare(photo_a, photo_b, name_a, name_b):
    if not photo_a or not photo_b:
        raise gr.Error("Two photos please, one in each box.")
    a, b = shelfly.analyse(photo_a), shelfly.analyse(photo_b)
    a["name"], b["name"] = (name_a or "Photo A").strip(), (name_b or "Photo B").strip()
    return fly_eye_image(a["eye"]), fly_eye_image(b["eye"]), plain_verdict(a, b)


with gr.Blocks(title="Shelf Fly") as demo:
    gr.Markdown(INTRO)
    with gr.Row():
        with gr.Column():
            photo_a = gr.Image(label="Photo A", type="filepath", height=300)
            name_a = gr.Textbox(label="Name it", placeholder="Photo A", scale=1)
        with gr.Column():
            photo_b = gr.Image(label="Photo B", type="filepath", height=300)
            name_b = gr.Textbox(label="Name it", placeholder="Photo B", scale=1)
    go = gr.Button("Show both to the fly (takes about a minute)", variant="primary")
    with gr.Row():
        eye_a = gr.Image(label="How the fly sees A", height=280)
        eye_b = gr.Image(label="How the fly sees B", height=280)
    verdict = gr.Markdown()
    example = gr.Button("Load an example: two versions of a made-up cereal box", variant="secondary")
    example.click(
        lambda: (str(HERE / "examples/hollow-pine-bold.jpg"), str(HERE / "examples/hollow-pine-soft.jpg"),
                 "Bold box", "Soft box"),
        outputs=[photo_a, photo_b, name_a, name_b],
    )
    gr.Markdown(
        "Fly vision model: flyvis (Lappalainen et al., Nature 2024), built on an earlier Janelia map of the fly's "
        "visual system, averaged over 5 of its 50 trained versions. Takes about a minute. Photos you upload are "
        "used for this comparison and nothing else."
    )
    go.click(compare, [photo_a, photo_b, name_a, name_b], [eye_a, eye_b, verdict])

if __name__ == "__main__":
    shelfly.models()  # load before the first click so nobody waits twice
    # no fixed port: if an older copy is still running, take the next free one instead of dying
    # address and port come from the environment on Hugging Face; locally this is 127.0.0.1
    demo.launch(theme=gr.themes.Soft(primary_hue="green"), inbrowser=True, share=False)

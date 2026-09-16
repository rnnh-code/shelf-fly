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


def compare(photo_a, photo_b, name_a, name_b):
    if not photo_a or not photo_b:
        raise gr.Error("Two photos please, one in each box.")
    a, b = shelfly.analyse(photo_a), shelfly.analyse(photo_b)
    a["name"], b["name"] = (name_a or "Photo A").strip(), (name_b or "Photo B").strip()
    return fly_eye_image(a["eye"]), fly_eye_image(b["eye"]), shelfly.plain_verdict(a, b)


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

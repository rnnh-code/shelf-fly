# Shelf Fly

**Which package gets noticed first?** Put in two product photos. A computer model of a fruit fly's eye and brain looks at both and tells you which one it reacted to more.

The fly sees in blurry black and white: 721 grey hexagons instead of pixels. It picks up shapes and light-versus-dark. Colour and words disappear.

A higher reaction means a package is more likely to catch an eye first. It says nothing about which product people would rather buy.

## Try it

```bash
git clone https://github.com/rnnh-code/shelf-fly.git
cd shelf-fly
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/flyvis download-pretrained      # fetches the trained fly models, about 100 MB
.venv/bin/python app.py                   # opens the page in your browser
```

Drop a photo in each box, name them, press the button. About a minute later you get both fly's-eye views and a plain-English verdict. There's a button that loads two versions of a made-up cereal box if you just want to see it work.

Prefer the command line?

```bash
.venv/bin/python shelfly.py examples/hollow-pine-bold.jpg examples/hollow-pine-soft.jpg --names "Bold box" "Soft box"
```

That writes a shareable result page to `results/`.

For a fair test, use photos where both products sit on a plain background at roughly the same size. A product that fills more of its photo gets a boost for that alone, and the page warns you when that happens.

## How it works

1. Each photo is turned grey, padded to a square and shrunk.
2. A simulated fly eye (721 hexagonal lenses) looks at a short clip: plain grey, then the product appears and stays.
3. Five trained versions of the fly's visual system run that clip. We measure how much the brain's activity changes once the product is on screen.
4. The page reports which product caused the bigger change, whether all five versions agreed, and whether a plain light-versus-dark measure (no brain at all) picked the same winner.

## What we found while building it

We tried hard to break our own results, because a demo like this can easily look smarter than it is.

- **On still photos, the fly mostly agrees with a simple contrast measure.** Whichever package has more light-versus-dark difference usually wins. The page tells you when that is the case.
- **Scrambling the fly's wiring did not change the winner** in the tests we ran, so the specific wiring diagram is not what decides still-photo results.
- **Movement is different.** When a package slides past instead of sitting still, the fly reacts far more strongly, and it prefers slow movement while a simple "amount of motion" measure prefers fast. That is where a fly model tells you something a formula cannot, and it is the next version of this project: a walk-past test.

## Credits

- Fly vision model: [flyvis](https://github.com/TuragaLab/flyvis) (MIT licence), from Lappalainen et al., "Connectome-constrained networks predict neural activity across the fly visual system", *Nature* (2024). It is built on connectome data from Janelia Research Campus.
- The example cereal boxes are made up for this project.

## Licence

MIT. Photos you run through the tool stay yours; make sure you have the right to use them.

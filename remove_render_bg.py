#!/usr/bin/env python3
"""Remove the background from KiCad 3D-viewer renders.

Every pixel that shows the render background becomes transparent, including
background seen through holes and gaps inside the board, not just the area
around it. Two kinds of input are handled:

* Opaque renders (KiCad GUI screenshots / "Export current view"): the
  background is KiCad's vertical gradient. It is fitted per colour channel as
  a linear function of the row, robustly, from the image border (the board may
  touch the border). A pixel's opacity follows its colour distance from the
  background of its row, and edge pixels are un-mixed from the background so
  no lavender halo is left.
* Renders that already have an alpha channel (kicad-cli --background
  transparent): background is already transparent, but soft shadows and glow
  are half-transparent. Alpha is clipped so they disappear.

Usage:
    python3 remove_render_bg.py IN.png [IN2.png ...]            # in place
    python3 remove_render_bg.py IN.png -o OUT.png
    python3 remove_render_bg.py IN.png -o OUT.png --fit 900x600 # trim, fit, centre

Output is always PNG with transparency. Needs numpy and Pillow.
"""
import argparse
import sys

import numpy as np
from PIL import Image

# Opaque mode: colour distance (0-255 RGB, Euclidean) from the fitted
# background.  Below LOW the pixel is background, above HIGH it is board,
# in between it is an anti-aliased edge.
LOW, HIGH = 10.0, 28.0
# Alpha mode: alpha below A_LOW is shadow/glow, above A_HIGH fully opaque.
A_LOW, A_HIGH = 0.55, 0.85


def fit_gradient(rgb):
    """Robustly fit bg(y) = a + b*y per channel from the image border."""
    h, w, _ = rgb.shape
    m = max(2, min(h, w) // 100)
    ys, cs = [], []
    for sl, yy in (((slice(0, m), slice(None)), np.repeat(np.arange(m), w)),
                   ((slice(h - m, h), slice(None)), np.repeat(np.arange(h - m, h), w)),
                   ((slice(None), slice(0, m)), np.repeat(np.arange(h), m)),
                   ((slice(None), slice(w - m, w)), np.repeat(np.arange(h), m))):
        ys.append(yy)
        cs.append(rgb[sl].reshape(-1, 3))
    y = np.concatenate(ys).astype(np.float64)
    c = np.concatenate(cs).astype(np.float64)
    # KiCad's background is a lavender grey: R == G and B a fixed ~26 above.
    # Start from samples with that signature so board edges, annotations or
    # extra panels that touch the border cannot skew the fit.
    sig = (np.abs(c[:, 0] - c[:, 1]) <= 4) & (c[:, 2] - c[:, 0] >= 12) & (c[:, 2] - c[:, 0] <= 45)
    keep = sig if sig.sum() >= 0.1 * len(y) else np.ones(len(y), bool)
    for _ in range(8):                       # iteratively drop non-background samples
        A = np.stack([np.ones(keep.sum()), y[keep]], 1)
        coef, *_ = np.linalg.lstsq(A, c[keep], rcond=None)
        pred = coef[0] + np.outer(y, coef[1])
        err = np.linalg.norm(c - pred, axis=1)
        thr = max(6.0, 2.5 * np.median(err[keep]))
        new = err < thr
        if new.sum() < 0.2 * len(y) or (new == keep).all():
            break
        keep = new
    if keep.mean() < 0.3:
        sys.exit("could not find a gradient background on the image border")
    return coef                               # shape (2, 3)


def remove_opaque(rgb):
    h, w, _ = rgb.shape
    coef = fit_gradient(rgb)
    bg = (coef[0] + np.outer(np.arange(h), coef[1]))[:, None, :]   # (h,1,3)
    f = rgb.astype(np.float64)
    d = np.linalg.norm(f - bg, axis=2)
    a = np.clip((d - LOW) / (HIGH - LOW), 0, 1)
    # un-mix the background from edge pixels: P = a*C + (1-a)*BG
    with np.errstate(divide="ignore", invalid="ignore"):
        col = np.where(a[..., None] > 0, (f - (1 - a[..., None]) * bg) / a[..., None], 0)
    return np.dstack([np.clip(col, 0, 255), a * 255]).astype(np.uint8)


def remove_alpha(rgba):
    a = rgba[..., 3].astype(np.float64) / 255
    a = np.clip((a - A_LOW) / (A_HIGH - A_LOW), 0, 1)
    out = rgba.copy()
    out[..., 3] = (a * 255).astype(np.uint8)
    out[out[..., 3] == 0, :3] = 0
    return out


def border_alpha(rgba):
    m = max(2, min(rgba.shape[:2]) // 100)
    a = rgba[..., 3]
    return np.concatenate([a[:m].ravel(), a[-m:].ravel(), a[:, :m].ravel(), a[:, -m:].ravel()])


def process(img):
    rgba = np.asarray(img.convert("RGBA"))
    # kicad-cli --background transparent: the border is see-through.
    if (border_alpha(rgba) < 128).mean() > 0.5:
        return Image.fromarray(remove_alpha(rgba), "RGBA")
    # KiCad GUI export: opaque gradient background, but the board itself is
    # saved semi-transparent (soldermask alpha ~219).  The input alpha is
    # ignored: the gradient decides what is background, everything else is
    # made fully opaque.
    return Image.fromarray(remove_opaque(rgba[..., :3]), "RGBA")


def fit(img, size):
    w, h = size
    box = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    if box:
        img = img.crop(box)
    pad = 0.94
    s = min(w * pad / img.width, h * pad / img.height)
    img = img.resize((max(1, round(img.width * s)), max(1, round(img.height * s))), Image.LANCZOS)
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2), img)
    return canvas


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+")
    ap.add_argument("-o", "--output", help="output file (only with one input; default: overwrite input as PNG)")
    ap.add_argument("--fit", metavar="WxH", help="trim to the board, fit and centre on a transparent WxH canvas")
    args = ap.parse_args()
    if args.output and len(args.inputs) != 1:
        ap.error("-o needs exactly one input")
    size = tuple(map(int, args.fit.lower().split("x"))) if args.fit else None
    for p in args.inputs:
        out = process(Image.open(p))
        if size:
            out = fit(out, size)
        dst = args.output or (p.rsplit(".", 1)[0] + ".png")
        out.save(dst, optimize=True)
        a = np.asarray(out.getchannel("A"))
        print(f"{p} -> {dst}: {100 * (a == 0).mean():.1f}% transparent, {100 * ((a > 0) & (a < 255)).mean():.1f}% edge")


if __name__ == "__main__":
    main()

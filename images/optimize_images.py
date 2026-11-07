#!/usr/bin/env python3
"""Re-encode every image in the repository as PNG and keep each under a size cap.

For every tracked or untracked (not ignored) image file in the repository:

* JPEG, BMP, TIFF, WebP and GIF files are converted to PNG. The original is
  removed and every Markdown link to it is rewritten to the new name.
  EXIF orientation is applied first, since PNG does not carry it.
* Any PNG (converted or already PNG) larger than the cap (default 2 MB) is
  downsampled, in steps, until it fits under the cap.

Transparency is kept. Run from anywhere inside the repository:

    python3 images/optimize_images.py              # do it
    python3 images/optimize_images.py --dry-run    # only report
    python3 images/optimize_images.py --max-mb 1.5

Needs Pillow and git.
"""
import argparse
import io
import os
import subprocess
import sys

from PIL import Image, ImageOps

EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp"}


def repo_root():
    return subprocess.check_output(["git", "rev-parse", "--show-toplevel"], text=True).strip()


def repo_files(root):
    out = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=root)
    return [f for f in out.decode().split("\0") if f and os.path.exists(os.path.join(root, f))]


def encode_png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def shrink(img, cap):
    """Return PNG bytes under `cap`, downsampling only as much as needed."""
    data = encode_png(img)
    w, h = img.size
    while len(data) > cap:
        # PNG size grows roughly with pixel count: aim a little under the cap.
        s = min(0.9, (cap / len(data)) ** 0.5 * 0.97)
        w, h = max(1, int(w * s)), max(1, int(h * s))
        data = encode_png(img.resize((w, h), Image.LANCZOS))
    return data, (w, h)


def load(path):
    img = Image.open(path)
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA" if "A" in img.getbands() or "transparency" in img.info else "RGB")
    return img


def rewrite_links(root, files, renames, dry):
    """Replace links to renamed images in every Markdown file."""
    changed = []
    for md in (f for f in files if f.lower().endswith(".md")):
        p = os.path.join(root, md)
        text = open(p, encoding="utf-8").read()
        new = text
        base = os.path.dirname(md)
        for old, dst in renames.items():
            rel_old = os.path.relpath(old, base or ".")
            rel_new = os.path.relpath(dst, base or ".")
            new = new.replace(rel_old, rel_new)
        if new != text:
            changed.append(md)
            if not dry:
                open(p, "w", encoding="utf-8").write(new)
    return changed


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--max-mb", type=float, default=2.0, help="size cap per image in MB (default 2)")
    ap.add_argument("--dry-run", action="store_true", help="report only, change nothing")
    args = ap.parse_args()
    cap = int(args.max_mb * 1024 * 1024)

    root = repo_root()
    files = repo_files(root)
    images = [f for f in files if os.path.splitext(f)[1].lower() in EXTS]
    renames = {}
    for f in sorted(images):
        src = os.path.join(root, f)
        stem, ext = os.path.splitext(f)
        dst_rel = stem + ".png"
        dst = os.path.join(root, dst_rel)
        convert = ext != ".png"            # also normalises ".PNG"
        if convert and os.path.exists(dst) and dst_rel != f:
            print(f"skip   {f}: {dst_rel} already exists", file=sys.stderr)
            continue
        size = os.path.getsize(src)
        if not convert and size <= cap:
            continue
        img = load(src)
        data, (w, h) = shrink(img, cap)
        resized = (w, h) != img.size
        what = ("convert" if convert else "shrink ") + (f" + downsample {img.size[0]}x{img.size[1]} -> {w}x{h}" if resized else "")
        print(f"{what:48s} {size / 1048576:6.2f} MB -> {len(data) / 1048576:5.2f} MB  {f}" + (f" -> {dst_rel}" if dst_rel != f else ""))
        if args.dry_run:
            if dst_rel != f:
                renames[f] = dst_rel
            continue
        with open(dst, "wb") as fh:
            fh.write(data)
        if dst_rel != f:
            os.remove(src)
            renames[f] = dst_rel
    for md in rewrite_links(root, files, renames, args.dry_run):
        print(f"links  {md}")


if __name__ == "__main__":
    main()

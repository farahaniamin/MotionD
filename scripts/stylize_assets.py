"""Harmonize generated / user images with the ACTIVE style so every asset looks like one art set.

    python3 tools/stylize_assets.py                 # all raw_img/*.png -> public/img/<id>.png
    python3 tools/stylize_assets.py --only brain eyes
    python3 tools/stylize_assets.py --input user_inputs/assets/match_theme/x.jpg --id x --kind cutout

Steps (driven by style.json -> assets.post):
  1. background removal: alpha from the API, or chroma-key (+ despill) when the model could not do transparency
  2. trim + pad to a square canvas (cut-outs) / cover-crop 1080x1920 (backgrounds)
  3. "ink_paper": remap tones to the style's exact ink & paper colors (kills model-to-model color drift)
     and RECOLOR the spot-color element to the project's current accent (palette presets / per-reel colors)
Writes raw_img/_assets_sheet.jpg — the agent must look at it before using the assets.
"""
import argparse
import colorsys
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def hex_rgb(h: str) -> np.ndarray:
    h = h.lstrip("#")
    return np.array([int(h[i : i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def chroma_key(rgb: np.ndarray, key_hex: str) -> np.ndarray:
    key = hex_rgb(key_hex)
    dist = np.linalg.norm(rgb - key, axis=-1)
    alpha = np.clip((dist - 0.28) / 0.22, 0, 1)
    # despill: pull the key channel down where it dominates
    ch = int(np.argmax(key))
    others = np.delete(rgb, ch, axis=-1).max(axis=-1)
    rgb[..., ch] = np.minimum(rgb[..., ch], others + 0.02)
    return alpha


def trim_square(img: Image.Image, margin: float = 0.06, max_dim: int = 1400) -> Image.Image:
    bbox = img.getchannel("A").point(lambda a: 255 if a > 12 else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
    side = int(max(img.size) * (1 + margin * 2))
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2), img)
    if side > max_dim:
        canvas = canvas.resize((max_dim, max_dim), Image.LANCZOS)
    return canvas


def cover(img: Image.Image, w: int = 1080, h: int = 1920) -> Image.Image:
    s = max(w / img.width, h / img.height)
    img = img.resize((int(img.width * s + 0.5), int(img.height * s + 0.5)), Image.LANCZOS)
    x, y = (img.width - w) // 2, (img.height - h) // 2
    return img.crop((x, y, x + w, y + h))


def ink_paper(rgba: np.ndarray, post: dict, accent_hex: str) -> np.ndarray:
    rgb = rgba[..., :3]
    ink, paper, acc = hex_rgb(post.get("ink", "#151413")), hex_rgb(post.get("paper", "#F4EFE4")), hex_rgb(accent_hex)
    lum = rgb @ np.array([0.299, 0.587, 0.114], np.float32)
    c = float(post.get("contrast", 1.1))
    lum_c = np.clip((lum - 0.5) * c + 0.5, 0, 1)
    mx, mn = rgb.max(-1), rgb.min(-1)
    sat = np.where(mx > 1e-4, (mx - mn) / np.maximum(mx, 1e-4), 0)
    is_acc = np.clip((sat - 0.28) / 0.2, 0, 1) * np.clip((mx - 0.18) / 0.15, 0, 1)
    mono = ink + (paper - ink) * lum_c[..., None]
    if post.get("recolorAccent", True):
        # shade the project accent by the original pixel's value so engraving detail survives
        v = np.clip(mx / max(1e-4, np.percentile(mx[is_acc > 0.5], 90) if (is_acc > 0.5).any() else 1.0), 0, 1.15)
        colored = np.clip(acc[None, None, :] * (0.35 + 0.65 * v[..., None]), 0, 1)
    else:
        colored = rgb
    out = mono * (1 - is_acc[..., None]) + colored * is_acc[..., None]
    rgba[..., :3] = out
    return rgba


def process(src: Path, out: Path, kind: str, meta: dict, style: dict):
    post = style.get("assets", {}).get("post", {"mode": "none"})
    im = Image.open(src).convert("RGBA")
    a = np.asarray(im).astype(np.float32) / 255.0
    chroma = meta.get("chroma")
    if kind in ("cutout", "portrait"):
        if chroma or a[..., 3].min() > 0.99:
            key = chroma or style.get("assets", {}).get("chroma", "#00FF00")
            corner = a[:8, :8, :3].reshape(-1, 3).mean(0)
            if np.linalg.norm(corner - hex_rgb(key)) > 0.35:  # background isn't the key color: treat near-white as bg
                key = "#FFFFFF" if corner.mean() > 0.85 else key
            a[..., 3] = chroma_key(a[..., :3], key)
    if post.get("mode") == "ink_paper":
        a = ink_paper(a, post, style["palette"]["accent"])
    img = Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8), "RGBA")
    if kind in ("cutout", "portrait"):
        img.putalpha(img.getchannel("A").filter(ImageFilter.GaussianBlur(0.6)))
        img = trim_square(img, max_dim=int(post.get("maxDim", 1400)))
    elif kind == "background":
        img = cover(img.convert("RGB")).convert("RGBA")
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, optimize=True)
    return img


def sheet(items: list[tuple[str, Image.Image]], path: Path):
    if not items:
        return
    cell = 300
    cols = min(5, len(items))
    rows = (len(items) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * cell, rows * (cell + 24)), (128, 128, 128))
    d = ImageDraw.Draw(canvas)
    for i, (name, im) in enumerate(items):
        t = im.copy()
        t.thumbnail((cell - 10, cell - 10))
        x, y = (i % cols) * cell, (i // cols) * (cell + 24)
        checker = Image.new("RGB", (cell, cell), (205, 205, 205))
        canvas.paste(checker, (x, y))
        canvas.paste(t, (x + (cell - t.width) // 2, y + (cell - t.height) // 2), t if t.mode == "RGBA" else None)
        d.text((x + 6, y + cell + 4), name, fill=(0, 0, 0))
    canvas.save(path, quality=88)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--input")
    ap.add_argument("--id")
    ap.add_argument("--kind", default="cutout")
    args = ap.parse_args()
    style = json.loads(Path("src/style.json").read_text(encoding="utf-8"))
    done: list[tuple[str, Image.Image]] = []
    if args.input:
        name = args.id or Path(args.input).stem
        done.append((name, process(Path(args.input), Path("public/img") / f"{name}.png", args.kind, {}, style)))
    else:
        plan_kinds = {}
        if Path("assets_plan.json").exists():
            plan_kinds = {a["id"]: a.get("kind", "cutout") for a in json.loads(Path("assets_plan.json").read_text(encoding="utf-8-sig")).get("assets", [])}
        for png in sorted(Path("raw_img").glob("*.png")):
            if png.name.startswith("_") or (args.only and png.stem not in args.only):
                continue
            mp = png.with_suffix(".json")
            meta = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
            kind = meta.get("kind") or plan_kinds.get(png.stem, "cutout")  # manual ChatGPT downloads have no meta
            done.append((png.stem, process(png, Path("public/img") / f"{png.stem}.png", kind, meta, style)))
            print(f"  [STYLE] {png.stem} ({kind}) -> public/img/{png.stem}.png")
    sheet(done, Path("raw_img/_assets_sheet.jpg"))
    print(f"[STYLE] {len(done)} asset(s) harmonized to '{style['name']}' (accent {style['palette']['accent']}). Review raw_img/_assets_sheet.jpg")


if __name__ == "__main__":
    main()

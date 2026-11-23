import argparse
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps
from rembg import remove, new_session

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

RAW_AI_DIR = Path("raw_img")
USER_MATCH_DIR = Path("user_inputs/assets/match_theme")
USER_CUTOUT_DIR = Path("user_inputs/assets/need_cutout")
USER_READY_DIR = Path("user_inputs/assets/ready")
OUT_AI_DIR = Path("public/img")
OUT_USER_DIR = Path("public/img/user")
TEMPLATE_IMGS = {"07_chrome_corner.png", "grain.png"}


def file_md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def verify_no_sibling_asset_copy(allow_shared: bool = False):
    """
    Blocks lazy cross-project copying of AI scene PNGs across sibling reel directories.
    """
    if allow_shared or not OUT_AI_DIR.exists():
        return
    cwd = Path.cwd().resolve()
    workspace_parent = cwd.parent
    sibling_hashes: dict[str, str] = {}
    for sib in workspace_parent.iterdir():
        if not sib.is_dir() or sib.resolve() == cwd or sib.name in ("skills", ".git") or sib.name.endswith("-output"):
            continue
        for sub_rel in ("public/img", "raw_img"):
            sub_dir = sib / sub_rel
            if not sub_dir.exists():
                continue
            for f in sub_dir.glob("*.png"):
                if f.name in TEMPLATE_IMGS:
                    continue
                sibling_hashes[file_md5(f)] = f"{sib.name}/{sub_rel}/{f.name}"

    dups = []
    for cur_dir in (RAW_AI_DIR, OUT_AI_DIR):
        if not cur_dir.exists():
            continue
        for f in cur_dir.glob("*.png"):
            if f.name in TEMPLATE_IMGS:
                continue
            h = file_md5(f)
            if h in sibling_hashes:
                dups.append(f"  - {cur_dir}/{f.name} == {sibling_hashes[h]} (MD5={h[:10]})")

    if dups:
        raise RuntimeError(
            "[DUPLICATE-ASSET BLOCKED] Cross-project copied scene objects detected!\n"
            + "\n".join(dups)
            + "\nEvery reel MUST generate fresh, topic-specific visual metaphors in raw_img/ via image-generator!"
        )


def load_brand() -> dict:
    sync_script = Path(__file__).resolve().parent / "sync_inputs.py"
    if sync_script.exists():
        sys.path.insert(0, str(sync_script.parent))
        from sync_inputs import sync_project_inputs

        sync_project_inputs()

    brand_path = Path("src/brand.json")
    if brand_path.exists():
        with open(brand_path, encoding="utf-8") as f:
            return json.load(f)
    return {"assetColorMode": "monochrome", "colors": {"ink": "#121212"}}


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def create_offline_safe_session():
    u2net_cache = Path.home() / ".u2net"
    if (u2net_cache / "u2net.onnx").exists():
        return new_session("u2net")
    if (u2net_cache / "isnet-general-use.onnx").exists():
        return new_session("isnet-general-use")
    return new_session("u2net")


def smart_remove_bg(img: Image.Image, session_holder: list) -> Image.Image:
    """
    Preserves crisp alpha if already transparent; uses clean chroma-distance matting
    for flat vector logos on uniform solid backgrounds; uses rembg u2net for 3D/photo subjects.
    """
    rgba = img.convert("RGBA")
    arr = np.asarray(rgba, dtype=np.float32)
    alpha = arr[:, :, 3]

    # 1. Already transparent background? Preserve original crisp alpha!
    corners_a = np.concatenate(
        [alpha[:8, :8].ravel(), alpha[:8, -8:].ravel(), alpha[-8:, :8].ravel(), alpha[-8:, -8:].ravel()]
    )
    if np.median(corners_a) < 20.0 and np.mean(alpha > 240.0) < 0.88:
        return rgba

    # 2. Check if flat graphic/logo on uniform solid background
    rgb = arr[:, :, :3]
    corners_rgb = np.concatenate(
        [
            rgb[:8, :8].reshape(-1, 3),
            rgb[:8, -8:].reshape(-1, 3),
            rgb[-8:, :8].reshape(-1, 3),
            rgb[-8:, -8:].reshape(-1, 3),
        ],
        axis=0,
    )
    corner_std = float(np.max(np.std(corners_rgb, axis=0)))
    small_arr = np.asarray(img.convert("RGB").resize((128, 128), Image.Resampling.NEAREST))
    unique_colors = int(len(np.unique(small_arr.reshape(-1, 3), axis=0)))

    if corner_std < 5.5 and unique_colors < 650:
        bg_color = np.median(corners_rgb, axis=0)
        dist = np.linalg.norm(rgb - bg_color[None, None, :], axis=2)
        new_alpha = np.clip((dist - 16.0) / (52.0 - 16.0), 0.0, 1.0) * 255.0
        out = arr.copy()
        out[:, :, 3] = np.minimum(alpha, new_alpha)
        return Image.fromarray(out.astype(np.uint8), mode="RGBA")

    # 3. Complex photo or 3D render -> offline rembg session + white-studio edge decontamination
    if not session_holder:
        session_holder.append(create_offline_safe_session())
    cut = remove(rgba, session=session_holder[0])
    c_arr = np.asarray(cut, dtype=np.float32).copy()
    c_rgb = c_arr[:, :, :3]
    c_a = c_arr[:, :, 3]
    c_lum = 0.299 * c_rgb[:, :, 0] + 0.587 * c_rgb[:, :, 1] + 0.114 * c_rgb[:, :, 2]
    c_sat = np.max(c_rgb, axis=2) - np.min(c_rgb, axis=2)
    # Remove faint white-background haze between semi-transparent fringes (great for dark scenes!)
    haze = (c_a > 0) & (c_a < 185.0) & (c_lum > 185.0) & (c_sat < 28.0)
    c_arr[haze, 3] = c_arr[haze, 3] * 0.22
    very_faint = c_arr[:, :, 3] < 24.0
    c_arr[very_faint, 3] = 0.0
    return Image.fromarray(c_arr.astype(np.uint8), mode="RGBA")


def apply_theme_grade(cut_rgba: Image.Image, brand: dict) -> Image.Image:
    """
    Transforms an asset's RGB channels to match the active reference theme in src/brand.json
    while preserving smooth alpha edges.
    """
    mode = brand.get("assetColorMode", "monochrome")
    arr = np.asarray(cut_rgba, dtype=np.float32).copy()
    rgb = arr[:, :, :3]
    alpha = arr[:, :, 3]
    fg_mask = alpha > 28.0

    if not np.any(fg_mask):
        return cut_rgba

    lum = 0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]

    if mode == "monochrome":
        # Full-range studio tonal curve [14..246] so frosted glass, white ceramic, brushed silver & charcoal stay distinct!
        fg_lum = lum[fg_mask]
        lo = float(np.percentile(fg_lum, 2))
        hi = float(np.percentile(fg_lum, 98))
        if hi - lo > 8.0:
            norm = np.clip((lum - lo) / (hi - lo), 0.0, 1.0)
        else:
            norm = np.clip(lum / 255.0, 0.0, 1.0)
        curved = 0.35 * norm + 0.65 * (0.5 - 0.5 * np.cos(np.pi * norm))
        graded = 14.0 + curved * 232.0
        arr[:, :, 0] = graded
        arr[:, :, 1] = graded
        arr[:, :, 2] = graded
        return Image.fromarray(arr.astype(np.uint8), mode="RGBA")

    if mode in ("duotone", "tint"):
        colors = brand.get("colors", {})
        ink_rgb = np.array(hex_to_rgb(colors.get("ink", "#121212")), dtype=np.float32)
        acc_hex = brand.get("themeAccentHex") or colors.get("slate", "#6B6B6B")
        acc_rgb = np.array(hex_to_rgb(acc_hex), dtype=np.float32)
        norm = np.clip(lum / 255.0, 0.0, 1.0)[:, :, None]
        toned = ink_rgb[None, None, :] * (1.0 - norm) + acc_rgb[None, None, :] * norm
        arr[:, :, :3] = np.clip(toned, 0.0, 255.0)
        return Image.fromarray(arr.astype(np.uint8), mode="RGBA")

    # mode == "color": keep rich RGB colors harmonized with clean contrast
    return cut_rgba


def crop_and_resize(proc_rgba: Image.Image, max_dim: int = 1100) -> Image.Image:
    a = proc_rgba.split()[3]
    alpha_mask = a.point(lambda p: 255 if p > 12 else 0)
    bbox = alpha_mask.getbbox()
    if bbox:
        pad = 16
        x0 = max(0, bbox[0] - pad)
        y0 = max(0, bbox[1] - pad)
        x1 = min(proc_rgba.width, bbox[2] + pad)
        y1 = min(proc_rgba.height, bbox[3] + pad)
        proc_rgba = proc_rgba.crop((x0, y0, x1, y1))

    if max(proc_rgba.width, proc_rgba.height) > max_dim:
        scale = max_dim / max(proc_rgba.width, proc_rgba.height)
        new_size = (int(proc_rgba.width * scale), int(proc_rgba.height * scale))
        proc_rgba = proc_rgba.resize(new_size, Image.Resampling.LANCZOS)
    return proc_rgba


def convert_svg_to_monochrome(svg_path: Path, out_path: Path):
    text = svg_path.read_text(encoding="utf-8", errors="ignore")

    def hex_repl(match: re.Match) -> str:
        r, g, b = hex_to_rgb(match.group(0))
        y = int(round(20 + (0.299 * r + 0.587 * g + 0.114 * b) * (202.0 / 255.0)))
        return f"#{y:02X}{y:02X}{y:02X}"

    def rgb_repl(match: re.Match) -> str:
        r, g, b = [int(x) for x in match.groups()]
        y = int(round(20 + (0.299 * r + 0.587 * g + 0.114 * b) * (202.0 / 255.0)))
        return f"rgb({y},{y},{y})"

    recolored = re.sub(r"#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})\b", hex_repl, text)
    recolored = re.sub(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", rgb_repl, recolored)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(recolored, encoding="utf-8")
    print(f"[USER:MATCH_THEME:SVG] {svg_path} -> {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Process AI renders and manual user assets (ready, need_cutout, match_theme).")
    parser.add_argument("--keep-color", action="store_true", help="Override monochrome grading and keep RGB color.")
    parser.add_argument("--allow-shared-assets", action="store_true", help="Bypass cross-project duplicate asset check.")
    args = parser.parse_args()

    verify_no_sibling_asset_copy(allow_shared=args.allow_shared_assets)

    OUT_AI_DIR.mkdir(parents=True, exist_ok=True)
    OUT_USER_DIR.mkdir(parents=True, exist_ok=True)
    brand = load_brand()
    if args.keep_color:
        brand = {**brand, "assetColorMode": "color"}

    img_exts = {".png", ".jpg", ".jpeg", ".webp"}
    session_holder: list = []
    processed_any = False

    # 1. user_assets/ready/ -> copy untouched (screenshots, ready PNGs, videos)
    if USER_READY_DIR.exists():
        for rf in sorted(USER_READY_DIR.iterdir()):
            if rf.is_file() and rf.name.lower() != "readme.md":
                dst = OUT_USER_DIR / rf.name
                shutil.copy2(rf, dst)
                print(f"[USER:READY] {rf} -> {dst}")
                processed_any = True

    # 2. user_assets/need_cutout/ -> remove background, KEEP original colors
    if USER_CUTOUT_DIR.exists():
        for uf in sorted(USER_CUTOUT_DIR.iterdir()):
            if uf.is_file() and uf.suffix.lower() in img_exts:
                cut = smart_remove_bg(Image.open(uf), session_holder)
                final_im = crop_and_resize(cut)
                dst = OUT_USER_DIR / f"{uf.stem}.png"
                final_im.save(dst, "PNG", optimize=True)
                print(f"[USER:CUTOUT_KEEP_COLOR] {uf} -> {dst} ({final_im.size[0]}x{final_im.size[1]})")
                processed_any = True

    # 3. user_assets/match_theme/ -> remove background AND recolor/grade to match reference theme!
    if USER_MATCH_DIR.exists():
        for mf in sorted(USER_MATCH_DIR.iterdir()):
            if not mf.is_file() or mf.name.lower() == "readme.md":
                continue
            if mf.suffix.lower() == ".svg":
                if brand.get("assetColorMode", "monochrome") == "monochrome":
                    convert_svg_to_monochrome(mf, OUT_USER_DIR / mf.name)
                else:
                    shutil.copy2(mf, OUT_USER_DIR / mf.name)
                    print(f"[USER:MATCH_THEME:SVG_COLOR] {mf} -> {OUT_USER_DIR / mf.name}")
                processed_any = True
            elif mf.suffix.lower() in img_exts:
                cut = smart_remove_bg(Image.open(mf), session_holder)
                themed = apply_theme_grade(cut, brand)
                final_im = crop_and_resize(themed)
                dst = OUT_USER_DIR / f"{mf.stem}.png"
                final_im.save(dst, "PNG", optimize=True)
                print(
                    f"[USER:MATCH_THEME:{brand.get('assetColorMode','monochrome').upper()}] "
                    f"{mf} -> {dst} ({final_im.size[0]}x{final_im.size[1]})"
                )
                processed_any = True

    # 4. raw_img/ (AI-generated scene metaphors) -> smart cutout + match active reference theme
    if RAW_AI_DIR.exists():
        for af in sorted(RAW_AI_DIR.iterdir()):
            if af.is_file() and af.suffix.lower() in img_exts:
                cut = smart_remove_bg(Image.open(af), session_holder)
                themed = apply_theme_grade(cut, brand)
                final_im = crop_and_resize(themed)
                dst = OUT_AI_DIR / f"{af.stem}.png"
                final_im.save(dst, "PNG", optimize=True)
                print(
                    f"[AI:ASSET:{brand.get('assetColorMode','monochrome').upper()}] "
                    f"{af} -> {dst} ({final_im.size[0]}x{final_im.size[1]})"
                )
                processed_any = True

    if not processed_any:
        print("[INFO] No assets found to process.")
    else:
        manifest = {
            "project_dir": str(Path.cwd().resolve()),
            "assets": {
                p.name: file_md5(p)
                for p in sorted(OUT_AI_DIR.glob("*.png"))
                if p.name not in TEMPLATE_IMGS
            },
        }
        (OUT_AI_DIR / "_asset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

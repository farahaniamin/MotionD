"""Quality gate. Runs automatically inside render_reel.py; can also be run by hand.

    python3 tools/qa_check.py            # static checks on src/scenes.tsx (before bundling)
    python3 tools/qa_check.py --stills   # pixel checks on out_stills/*.png (after --stills-only)

Static  : every logo id used in scenes exists in src/logos.json (real, fetched vectors only);
          no raster/hand-made logo files; no hardcoded colors or px font sizes in scenes (style independence);
          scene durations inside the pacing window; banned cliché props.
Stills  : blank/near-empty frames, MISSING-LOGO placeholders, builds a contact sheet for one-look review.
Exit code 1 on errors (render is blocked), warnings are printed only.
"""
import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BANNED_PROPS = ["hourglass", "balance", "scale", "infinity", "mobius", "puzzle", "rubik", "cogwheel", "gear", "dice", "turbine"]


def static_checks() -> tuple[list[str], list[str]]:
    errors, warns = [], []
    scenes = Path("src/scenes.tsx").read_text(encoding="utf-8")
    logos = json.loads(Path("src/logos.json").read_text(encoding="utf-8")) if Path("src/logos.json").exists() else {}

    used = set(re.findall(r"\bid=[\"']([\w-]+)[\"']", scenes))
    used |= set(re.findall(r"\b(?:logo|left|right)=[\"']([\w-]+)[\"']", scenes))
    used |= set(re.findall(r"\bcenter=\{\{\s*id:\s*[\"']([\w-]+)[\"']", scenes))
    for arr in re.findall(r"satellites=\{\[([^\]]*)\]\}", scenes):
        used |= set(re.findall(r"[\"']([\w-]+)[\"']", arr))
    for m in re.findall(r"logo:\s*[\"']([\w-]+)[\"']", scenes):
        used.add(m)
    for lid in sorted(used):
        if lid not in logos:
            errors.append(f"logo '{lid}' is used in scenes.tsx but not registered -> python3 tools/logo_fetch.py {lid}")
    for lid, meta in logos.items():
        if meta.get("provider") not in {"svgl", "simple-icons", "user"}:
            errors.append(f"logo '{lid}' has unknown provenance '{meta.get('provider')}'")

    for m in re.finditer(r"src=[\"'{`]+([^\"'`}]+)", scenes):
        src = m.group(1).lower()
        if "logo" in src and not src.startswith("logos/"):
            errors.append(f"raster/hand-placed logo file '{m.group(1)}' — logos must go through <BrandLogo id=...>")

    for i, line in enumerate(scenes.splitlines(), 1):
        if line.strip().startswith("//"):
            continue
        if re.search(r"#[0-9a-fA-F]{6}\b|rgba?\(", line):
            warns.append(f"scenes.tsx:{i} hardcoded color — use PAL.* so the style can be swapped")
        if re.search(r"fontSize:\s*\d", line):
            warns.append(f"scenes.tsx:{i} px fontSize — use roleStyle()/rem()")

    for prop in re.findall(r"src=[\"'{`]+img/([^\"'`}]+)", scenes):
        low = prop.lower()
        hit = [b for b in BANNED_PROPS if b in low]
        if hit:
            warns.append(f"prop '{prop}' looks like a banned cliché ({', '.join(hit)})")

    tl = json.loads(Path("src/timeline.json").read_text(encoding="utf-8"))
    for b in tl.get("beats", []):
        d = float(b.get("scene_end", b.get("e", 0))) - float(b.get("s", 0))
        if d < 1.6:
            warns.append(f"beat {b.get('id')} lasts {d:.2f}s (<1.6s) — too fast to read on mobile")
        if d > 6.5:
            warns.append(f"beat {b.get('id')} lasts {d:.2f}s (>6.5s) — split it or add an internal beat")
    return errors, warns


def stills_checks() -> tuple[list[str], list[str]]:
    import numpy as np
    from PIL import Image

    errors, warns = [], []
    files = sorted(Path("out_stills").glob("*.png"))
    if not files:
        return ["no stills in out_stills/ — run render_reel.py --stills-only first"], []
    thumbs = []
    for f in files:
        im = Image.open(f).convert("RGB")
        a = np.asarray(im).astype(np.int16)
        center = a[int(a.shape[0] * 0.15) : int(a.shape[0] * 0.8), int(a.shape[1] * 0.1) : int(a.shape[1] * 0.9)]
        if center.std() < 9:
            errors.append(f"{f.name}: frame is (nearly) empty — content missing or still mid-transition")
        red = (a[:, :, 0] > 240) & (a[:, :, 1] < 30) & (a[:, :, 2] < 70)
        if red.mean() > 0.0015:
            errors.append(f"{f.name}: MISSING-LOGO placeholder visible")
        t = im.copy()
        t.thumbnail((270, 480))
        thumbs.append((f.stem, t))
    cols = 6
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 270, rows * 500), "white")
    from PIL import ImageDraw

    d = ImageDraw.Draw(sheet)
    for i, (name, t) in enumerate(thumbs):
        x, y = (i % cols) * 270, (i // cols) * 500
        sheet.paste(t, (x, y))
        d.text((x + 6, y + 482), name, fill=(0, 0, 0))
    sheet.save("out_stills/_contact_sheet.jpg", quality=88)
    print("[QA] contact sheet -> out_stills/_contact_sheet.jpg (open it and review every frame)")
    return errors, warns


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stills", action="store_true")
    args = ap.parse_args()
    errors, warns = stills_checks() if args.stills else static_checks()
    for w in warns:
        print(f"[QA:WARN] {w}")
    for e in errors:
        print(f"[QA:ERROR] {e}")
    if errors:
        sys.exit(1)
    print(f"[QA] {'stills' if args.stills else 'static'} checks passed ({len(warns)} warning(s))")


if __name__ == "__main__":
    main()

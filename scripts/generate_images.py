"""Generate style-matched images with the OpenAI Images API from assets_plan.json.

    python3 tools/generate_images.py --dry-run          # print every final prompt (show these to the user)
    python3 tools/generate_images.py                    # generate missing/changed assets -> raw_img/<id>.png
    python3 tools/generate_images.py --only hero_brain --force
    python3 tools/generate_images.py --list-models

Then ALWAYS run:  python3 tools/stylize_assets.py   (cut-out + palette harmonization -> public/img/)

assets_plan.json
{
  "assets": [
    {"id": "brain", "kind": "cutout", "subject": "a human brain on a brass anatomical stand", "accent": "the brass stand", "scene": 2},
    {"id": "eyes",  "kind": "background", "subject": "extreme close-up of engraved eyes like a banknote portrait", "size": "1024x1536"},
    {"id": "phone", "kind": "cutout", "subject": "a vintage rotary phone", "from": "user_inputs/assets/ready/phone.jpg"}
  ]
}
kind: cutout | portrait | background | texture. "accent": the ONE element painted in the accent color (omit = pure B&W).
"from": an existing image to RE-STYLE (uses the edits endpoint) instead of generating from scratch.

Prompts are assembled from the ACTIVE style (src/style.json -> assets.*), so switching style/preset switches
the art direction of every generated image. Brand logos are NEVER generated here (use logo_fetch.py).
Needs OPENAI_API_KEY in the environment. Results are cached by prompt hash (no double billing).
"""
import argparse
import base64
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

API = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
COLOR_NAMES = [
    ("red", (211, 34, 27)), ("crimson", (160, 20, 30)), ("maroon", (126, 20, 22)), ("orange", (255, 90, 31)),
    ("mustard yellow", (217, 161, 43)), ("lemon yellow", (242, 226, 5)), ("neon green", (155, 242, 12)),
    ("green", (40, 150, 70)), ("cobalt blue", (31, 75, 255)), ("navy blue", (20, 40, 110)), ("purple", (110, 50, 200)),
    ("pink", (240, 90, 160)), ("teal", (0, 150, 150)),
]


def color_name(hexc: str) -> str:
    h = hexc.lstrip("#")
    rgb = tuple(int(h[i : i + 2], 16) for i in (0, 2, 4))
    return min(COLOR_NAMES, key=lambda c: sum((a - b) ** 2 for a, b in zip(c[1], rgb)))[0]


def load_json(p: str) -> dict:
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def build_prompt(item: dict, style: dict, transparent: bool) -> str:
    A = style.get("assets", {})
    accent = style["palette"]["accent"]
    aname = item.get("accentName") or color_name(accent)
    fill = lambda s: (
        s.replace("{ACCENT}", accent).replace("{ACCENT_NAME}", aname).replace("{CHROMA}", A.get("chroma", "#00FF00"))
    )
    style_block = fill(A.get("styleBlock", ""))
    accent_rule = fill(A.get("accentRule", "")).replace("{ACCENT_ELEMENT}", item["accent"]) if item.get("accent") else fill(A.get("noAccentRule", ""))
    bg = fill(A.get("transparentBg", "transparent background")) if transparent else fill(A.get("chromaBg", "on a flat solid white background"))
    tmpl = A.get("prompts", {}).get(item.get("kind", "cutout")) or A.get("prompts", {}).get("cutout", "{STYLE} {SUBJECT}")
    p = tmpl.replace("{STYLE}", style_block).replace("{SUBJECT}", item["subject"]).replace("{ACCENT_RULE}", accent_rule).replace("{BG}", bg)
    if item.get("extra"):
        p += " " + item["extra"]
    return re.sub(r"\s+", " ", p).strip()


def api(method: str, path: str, body: bytes | None = None, ctype: str = "application/json", timeout: float = 300) -> dict:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("[IMG] OPENAI_API_KEY is not set. Ask the user to export it (never paste keys into files).")
    req = urllib.request.Request(f"{API}{path}", data=body, method=method, headers={"Authorization": f"Bearer {key}", "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:600]}") from None


def pick_model(explicit: str | None) -> str:
    if explicit and explicit != "auto":
        return explicit
    try:
        ids = [m["id"] for m in api("GET", "/models").get("data", []) if m["id"].startswith("gpt-image")]
    except Exception as e:
        print(f"[IMG] model list unavailable ({e}); using gpt-image-1")
        return "gpt-image-1"
    full = [i for i in ids if "mini" not in i] or ids
    if not full:
        return "gpt-image-1"
    ver = lambda s: [int(x) for x in re.findall(r"\d+", s)] or [0]
    return sorted(full, key=ver)[-1]


def multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    b = uuid.uuid4().hex
    out = bytearray()
    for k, v in fields.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
    for k, (name, data, mime) in files.items():
        out += f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{name}"\r\nContent-Type: {mime}\r\n\r\n'.encode() + data + b"\r\n"
    out += f"--{b}--\r\n".encode()
    return bytes(out), f"multipart/form-data; boundary={b}"


def decode_result(res: dict) -> bytes:
    d = res["data"][0]
    if d.get("b64_json"):
        return base64.b64decode(d["b64_json"])
    with urllib.request.urlopen(d["url"], timeout=120) as r:
        return r.read()


def generate(item: dict, style: dict, model: str, quality: str) -> tuple[bytes, dict]:
    kind = item.get("kind", "cutout")
    size = item.get("size") or ("1024x1536" if kind == "background" else "1024x1024")
    want_alpha = kind in ("cutout", "portrait")
    for transparent in ([True, False] if want_alpha else [False]):
        prompt = build_prompt(item, style, transparent)
        if item.get("from"):
            src = Path(item["from"])
            prompt = "Re-draw this image, keeping its subject and composition, in the following style. " + prompt
            fields = {"model": model, "prompt": prompt, "size": size, "quality": quality}
            if transparent:
                fields["background"] = "transparent"
            body, ctype = multipart(fields, {"image[]": (src.name, src.read_bytes(), "image/png" if src.suffix.lower() == ".png" else "image/jpeg")})
            call = lambda: api("POST", "/images/edits", body, ctype)
        else:
            payload = {"model": model, "prompt": prompt, "size": size, "quality": quality, "n": 1}
            if transparent:
                payload["background"] = "transparent"
                payload["output_format"] = "png"
            call = lambda: api("POST", "/images/generations", json.dumps(payload).encode())
        try:
            res = call()
            return decode_result(res), {"prompt": prompt, "model": model, "size": size, "transparent": transparent, "chroma": None if transparent or not want_alpha else style["assets"].get("chroma", "#00FF00")}
        except RuntimeError as e:
            if transparent and ("background" in str(e) or "transparent" in str(e)):
                print("  [IMG] transparent background not supported by this model -> chroma-key fallback")
                continue
            raise
    raise RuntimeError("generation failed")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", default="assets_plan.json")
    ap.add_argument("--model", default=os.environ.get("OPENAI_IMAGE_MODEL", "auto"))
    ap.add_argument("--quality", default="high", help="low | medium | high")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--list-models", action="store_true")
    args = ap.parse_args()

    if args.list_models:
        print("\n".join(m["id"] for m in api("GET", "/models").get("data", []) if "image" in m["id"]))
        return
    style = load_json("src/style.json")
    plan = load_json(args.plan)
    items = [a for a in plan["assets"] if not args.only or a["id"] in args.only]
    raw = Path("raw_img")
    raw.mkdir(exist_ok=True)

    if args.dry_run:
        for it in items:
            alpha = it.get("kind", "cutout") in ("cutout", "portrait")
            print(f"\n## {it['id']}  ({it.get('kind', 'cutout')}{', re-style ' + it['from'] if it.get('from') else ''})\n{build_prompt(it, style, alpha)}")
        print(f"\n[DRY-RUN] {len(items)} image(s) would be generated with style '{style['name']}' / accent {style['palette']['accent']}")
        return

    model = pick_model(args.model)
    print(f"[IMG] model: {model} · quality: {args.quality} · {len(items)} asset(s)")
    for it in items:
        sig = hashlib.sha256(json.dumps([build_prompt(it, style, True), it.get("from"), model, args.quality], ensure_ascii=False).encode()).hexdigest()[:16]
        out_png, out_meta = raw / f"{it['id']}.png", raw / f"{it['id']}.json"
        if out_png.exists() and out_meta.exists() and not args.force and json.loads(out_meta.read_text()).get("sig") == sig:
            print(f"  [CACHE] {it['id']}")
            continue
        t0 = time.time()
        data, meta = generate(it, style, model, args.quality)
        out_png.write_bytes(data)
        out_meta.write_text(json.dumps({**meta, "sig": sig, "kind": it.get("kind", "cutout"), "id": it["id"]}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] {it['id']} ({time.time() - t0:.0f}s) -> {out_png}")
    print("[NEXT] python3 tools/stylize_assets.py  (then LOOK at raw_img/_assets_sheet.jpg)")


if __name__ == "__main__":
    main()

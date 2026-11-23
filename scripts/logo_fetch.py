"""Fetch REAL brand logos from verified vector sources and register them for <BrandLogo id=...>.

    python3 tools/logo_fetch.py claude chatgpt gemini "کلاد"
    python3 tools/logo_fetch.py --list            # show registered logos + provenance
    python3 tools/logo_fetch.py cursor --dark     # prefer the dark-background variant

Resolution order (first hit wins):
  1. user_inputs/logos/<slug>.svg  (official file supplied by the user — e.g. from the brand's press kit)
  2. svgl.app            (curated official SVGs, full brand colors, many AI tools, wordmarks)
  3. Simple Icons        (CC0 single-path icons + official brand hex)
  4. otherwise STOP and ask the user for the official file. Never draw, trace, or AI-generate a logo.

Output: public/logos/<slug>/{logo.svg, layer_N.svg, wordmark.svg} + src/logos.json manifest
(name, files, aspect, colors, provider, source URL, sha256) used by kit/brand.tsx.
The color layers let a style re-materialize the true vector (e.g. paper_cut stacks each color as a
separate paper sheet) without changing a single point of the official geometry.
"""
import argparse
import copy
import hashlib
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SVG_NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")
DRAWABLE = {"path", "rect", "circle", "ellipse", "polygon", "polyline", "line", "text", "use"}
NON_RENDER = {"defs", "clipPath", "mask", "pattern", "linearGradient", "radialGradient", "symbol", "marker", "filter", "title", "desc", "metadata", "style"}
UA = {"User-Agent": "motion-reel-logo-fetch/2.0"}


def http_get(url: str, timeout: float = 20.0) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def local(tag: str) -> str:
    return tag.split("}", 1)[-1]


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def load_registry() -> dict:
    for c in (Path("tools/brands_registry.json"), Path(__file__).resolve().parent.parent / "brands" / "registry.json"):
        if c.exists():
            return json.loads(c.read_text(encoding="utf-8"))
    return {}


def resolve_name(query: str, reg: dict) -> tuple[str, dict]:
    q = query.strip().lower()
    for slug, meta in reg.items():
        if slug.startswith("_"):
            continue
        names = [slug, meta.get("name", "")] + meta.get("aliases", [])
        if any(q == n.lower() for n in names):
            return slug, meta
    return slugify(query) or "logo", {"name": query}


# ---------- providers ----------
def from_user(slug: str) -> tuple[bytes, str] | None:
    for ext in (".svg",):
        p = Path("user_inputs/logos") / f"{slug}{ext}"
        if p.exists():
            return p.read_bytes(), f"user_inputs/logos/{p.name}"
    return None


def pick_route(route, dark: bool):
    if isinstance(route, dict):
        return route.get("dark" if dark else "light") or next(iter(route.values()))
    return route


def from_svgl(meta: dict, dark: bool) -> tuple[bytes, str, bytes | None, str | None] | None:
    term = meta.get("svgl") or meta.get("name")
    if not term:
        return None
    try:
        data = json.loads(http_get("https://api.svgl.app?search=" + urllib.parse.quote(term)))
    except Exception as e:
        print(f"  [svgl] lookup failed: {e}")
        return None
    if not isinstance(data, list) or not data:
        return None
    t = term.lower()
    best = next((d for d in data if d.get("title", "").lower() == t), None) or next(
        (d for d in data if d.get("title", "").lower().startswith(t)), None
    )
    if best is None:
        return None
    url = pick_route(best.get("route"), dark)
    svg = http_get(url)
    wm_url = pick_route(best.get("wordmark"), dark) if best.get("wordmark") else None
    wm = None
    if wm_url:
        try:
            wm = http_get(wm_url)
        except Exception:
            wm = None
    return svg, url, wm, wm_url


_SI_DATA: dict | None = None


def simple_icons_hex(slug: str) -> str | None:
    global _SI_DATA
    if _SI_DATA is None:
        _SI_DATA = {}
        for path in ("data/simple-icons.json", "_data/simple-icons.json"):
            try:
                raw = json.loads(http_get(f"https://cdn.jsdelivr.net/npm/simple-icons@latest/{path}"))
                items = raw.get("icons", raw) if isinstance(raw, dict) else raw
                for it in items:
                    key = it.get("slug") or slugify(it.get("title", "")).replace("-", "")
                    _SI_DATA[key] = it.get("hex")
                break
            except Exception:
                continue
    return _SI_DATA.get(slug)


def from_simple_icons(meta: dict, slug: str) -> tuple[bytes, str] | None:
    si = meta.get("simpleicons") or slug.replace("-", "")
    url = f"https://cdn.jsdelivr.net/npm/simple-icons@latest/icons/{si}.svg"
    try:
        svg = http_get(url)
    except Exception:
        return None
    if b"<svg" not in svg:
        return None
    hexc = meta.get("color") or simple_icons_hex(si) or "000000"
    svg = svg.replace(b"<svg ", f'<svg fill="#{hexc.lstrip("#")}" '.encode(), 1)
    return svg, url


# ---------- SVG processing ----------
def sanitize(svg_bytes: bytes) -> ET.Element:
    root = ET.fromstring(svg_bytes)
    if local(root.tag) != "svg":
        raise ValueError("not an <svg> document")
    for parent in root.iter():
        for ch in list(parent):
            if local(ch.tag) in {"script", "foreignObject"}:
                parent.remove(ch)
    vb = root.get("viewBox")
    if not vb:
        w = float(re.sub(r"[^\d.]", "", root.get("width", "100")) or 100)
        h = float(re.sub(r"[^\d.]", "", root.get("height", "100")) or 100)
        root.set("viewBox", f"0 0 {w} {h}")
    _, _, vw, vh = [float(x) for x in re.split(r"[\s,]+", root.get("viewBox").strip())]
    root.set("width", f"{vw:g}")
    root.set("height", f"{vh:g}")
    if any(local(e.tag) == "image" for e in root.iter()):
        print("  [WARN] SVG embeds a raster <image>; it is not a pure vector logo.")
    return root


def aspect_of(root: ET.Element) -> float:
    _, _, vw, vh = [float(x) for x in re.split(r"[\s,]+", root.get("viewBox").strip())]
    return round(vw / vh, 4) if vh else 1.0


def style_prop(el: ET.Element, prop: str) -> str | None:
    if el.get(prop):
        return el.get(prop)
    m = re.search(rf"(?:^|;)\s*{prop}\s*:\s*([^;]+)", el.get("style", ""))
    return m.group(1).strip() if m else None


def drawables(root: ET.Element) -> list[tuple[ET.Element, list[ET.Element]]]:
    out = []

    def walk(el, ancestors):
        for ch in el:
            name = local(ch.tag)
            if name in NON_RENDER:
                continue
            if name in DRAWABLE:
                out.append((ch, ancestors + [el]))
            walk(ch, ancestors + [el])

    walk(root, [])
    return out


def effective_paint(el: ET.Element, ancestors: list[ET.Element]) -> str:
    for node in [el] + ancestors[::-1]:
        f = style_prop(node, "fill")
        if f:
            if f.lower() == "none":
                s = style_prop(el, "stroke") or next((style_prop(a, "stroke") for a in ancestors[::-1] if style_prop(a, "stroke")), None)
                return f"stroke:{(s or 'none').lower()}"
            return f.lower()
    return "#000000"


def split_layers(root: ET.Element) -> tuple[list[ET.Element], list[str]]:
    complex_tags = {"style", "mask", "filter", "linearGradient", "radialGradient", "pattern"}
    if any(local(e.tag) in complex_tags for e in root.iter()):
        # CSS classes / gradients / masks / blurs: splitting would alter the look — keep one exact layer
        return [root], []
    items = drawables(root)
    keys: list[str] = []
    for el, anc in items:
        k = effective_paint(el, anc)
        if k not in keys:
            keys.append(k)
    if len(keys) < 2 or len(keys) > 6:
        return [root], keys
    layers = []
    for k in keys:
        cp = copy.deepcopy(root)
        for (el, anc) in drawables(cp):
            if effective_paint(el, anc) != k:
                el.set("display", "none")
        layers.append(cp)
    return layers, keys


def write_svg(el: ET.Element, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(el).write(path, encoding="utf-8", xml_declaration=False)


def register(query: str, reg: dict, dark: bool, force: bool) -> bool:
    slug, meta = resolve_name(query, reg)
    manifest_p = Path("src/logos.json")
    manifest = json.loads(manifest_p.read_text(encoding="utf-8")) if manifest_p.exists() else {}
    if slug in manifest and not force:
        print(f"[SKIP] {slug} already registered ({manifest[slug]['provider']}). Use --force to refetch.")
        return True

    print(f"[LOGO] {query} -> {slug}")
    svg = wm = None
    src_url = wm_url = None
    provider = None
    hit = from_user(slug)
    if hit:
        svg, src_url, provider = hit[0], hit[1], "user"
    if svg is None:
        hit2 = from_svgl(meta, dark)
        if hit2:
            svg, src_url, wm, wm_url = hit2
            provider = "svgl"
    if svg is None:
        hit3 = from_simple_icons(meta, slug)
        if hit3:
            svg, src_url, provider = hit3[0], hit3[1], "simple-icons"
    if svg is None:
        print(
            f"[STOP] No verified vector logo found for '{query}'.\n"
            f"       Ask the user for the OFFICIAL SVG (brand/press kit page{' ' + meta['site'] if meta.get('site') else ''})\n"
            f"       and save it as user_inputs/logos/{slug}.svg, then re-run. Do NOT draw or generate it."
        )
        return False

    root = sanitize(svg)
    out_dir = Path("public/logos") / slug
    if out_dir.exists():
        for f in out_dir.glob("*.svg"):
            f.unlink()
    write_svg(root, out_dir / "logo.svg")
    layers, keys = split_layers(root)
    layer_files = []
    for i, ly in enumerate(layers):
        fp = out_dir / f"layer_{i}.svg"
        write_svg(ly, fp)
        layer_files.append(f"logos/{slug}/{fp.name}")

    entry = {
        "name": meta.get("name", query),
        "src": f"logos/{slug}/logo.svg",
        "layers": layer_files,
        "aspect": aspect_of(root),
        "colors": [k for k in keys if k.startswith("#")],
        "provider": provider,
        "source": src_url,
        "sha256": hashlib.sha256(svg).hexdigest(),
        "fetched": date.today().isoformat(),
    }
    if wm:
        try:
            wroot = sanitize(wm)
            write_svg(wroot, out_dir / "wordmark.svg")
            entry["wordmark"] = f"logos/{slug}/wordmark.svg"
            entry["wordmarkAspect"] = aspect_of(wroot)
            entry["wordmarkSource"] = wm_url
        except Exception as e:
            print(f"  [WARN] wordmark skipped: {e}")

    manifest[slug] = entry
    manifest_p.parent.mkdir(parents=True, exist_ok=True)
    manifest_p.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"  [OK] {provider} · {len(layer_files)} layer(s) · aspect {entry['aspect']} · {src_url}")
    return True


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("names", nargs="*")
    ap.add_argument("--dark", action="store_true", help="prefer dark-background variants")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    if args.list:
        mp = Path("src/logos.json")
        data = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else {}
        for k, v in data.items():
            print(f"  {k:<14} {v['provider']:<13} layers={len(v['layers'])} {v['source']}")
        return
    reg = load_registry()
    ok = all([register(n, reg, args.dark, args.force) for n in args.names])
    sys.exit(0 if ok else 2)


if __name__ == "__main__":
    main()

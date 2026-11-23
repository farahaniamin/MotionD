"""Sync user_inputs/ -> engine (src/, public/) and apply the active style pack.

user_inputs/brand.json  -> src/brand.json   (identity: wordmark, tagline, font, voice, "style")
styles/<style>/style.json + brand.styleOverrides -> src/style.json  (all visual tokens)
styles/<style>/theme.tsx -> src/theme/active.tsx                      (all shape language)
"""
import json
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

FONT_EXTS = {".woff2", ".woff", ".ttf", ".otf"}
DEFAULT_FONT = "fonts/YekanBakhFaNum-VF.woff2"


def deep_merge(base: dict, over: dict) -> dict:
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def find_styles_dir(root: Path) -> Path:
    for c in (root / "styles", Path(__file__).resolve().parent.parent / "styles"):
        if c.is_dir():
            return c
    raise FileNotFoundError("styles/ directory not found (expected in project root or skill root)")


def find_font_library(root: Path) -> Path | None:
    for c in (root / "fonts_library", Path(__file__).resolve().parent.parent / "resources" / "fonts"):
        if (c / "catalog.json").exists():
            return c
    return None


def font_entry(lib: Path | None, group: str, key: str | None) -> dict | None:
    if not key or lib is None:
        return None
    cat = json.loads((lib / "catalog.json").read_text(encoding="utf-8"))[group]
    if key not in cat:
        raise SystemExit(f"[FONT] Unknown {group} font '{key}'. Available: {', '.join(cat)}")
    return cat[key]


def apply_fonts(root: Path, brand: dict):
    """brand.fontFa / brand.fontLatin -> copy from the font library and point the engine at them."""
    lib = find_font_library(root)
    pub = root / "public" / "fonts"
    fa = font_entry(lib, "fa", brand.get("fontFa"))
    brand.pop("digitFontFile", None)
    if fa:
        src = lib / fa["file"]
        shutil.copy2(src, pub / src.name)
        brand["fontFamily"], brand["fontFile"] = fa["family"], f"fonts/{src.name}"
        if not fa.get("digitsOk", True):
            dig = lib / font_entry(lib, "fa", "Vazirmatn")["file"]
            shutil.copy2(dig, pub / dig.name)
            brand["digitFontFile"] = f"fonts/{dig.name}"
        print(f"[FONT] Persian: {brand['fontFa']} ({fa['family']}){' + Vazirmatn digits' if not fa.get('digitsOk', True) else ''}")


def apply_style(root: Path, brand: dict) -> str:
    styles = find_styles_dir(root)
    name = brand.get("style") or "paper_cut"
    pack = styles / name
    if not (pack / "style.json").exists() or not (pack / "theme.tsx").exists():
        avail = sorted(p.name for p in styles.iterdir() if (p / "style.json").exists())
        raise SystemExit(f"[STYLE] Unknown style '{name}'. Available: {', '.join(avail)}")
    with open(pack / "style.json", encoding="utf-8-sig") as f:
        style = json.load(f)
    preset = brand.get("palettePreset")
    if preset:
        presets = style.get("palettePresets", {})
        if preset not in presets:
            raise SystemExit(f"[STYLE] Unknown palettePreset '{preset}' for {name}. Available: {', '.join(presets)}")
        style["palette"] = deep_merge(style["palette"], presets[preset])
    style = deep_merge(style, brand.get("styleOverrides") or {})
    la = font_entry(find_font_library(root), "latin", brand.get("fontLatin"))
    if la:
        src = find_font_library(root) / la["file"]
        dst = root / "public" / "fonts" / "style"
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst / src.name)
        style["typography"]["latinFamily"] = f"'{la['family']}', 'Helvetica Neue', Arial"
        style["typography"]["latinFile"] = f"fonts/style/{src.name}"
        print(f"[FONT] Latin: {brand['fontLatin']} ({la['family']})")
    (root / "src" / "theme").mkdir(parents=True, exist_ok=True)
    with open(root / "src" / "style.json", "w", encoding="utf-8") as f:
        json.dump(style, f, ensure_ascii=False, indent=2)
    shutil.copy2(pack / "theme.tsx", root / "src" / "theme" / "active.tsx")
    # style-owned textures -> public/style/textures/
    if (pack / "textures").is_dir():
        shutil.copytree(pack / "textures", root / "public" / "style" / "textures", dirs_exist_ok=True)
    # style-owned fonts (e.g. the Latin display face) -> public/fonts/style/
    if (pack / "fonts").is_dir():
        dst = root / "public" / "fonts" / "style"
        dst.mkdir(parents=True, exist_ok=True)
        for ff in (pack / "fonts").iterdir():
            if ff.suffix.lower() in FONT_EXTS:
                shutil.copy2(ff, dst / ff.name)
    return name


def sync_project_inputs(project_root: Path | None = None):
    root = (project_root or Path.cwd()).resolve()
    ui = root / "user_inputs"
    if not ui.exists():
        return

    ui_fonts = ui / "fonts"
    pub_fonts = root / "public" / "fonts"
    pub_fonts.mkdir(parents=True, exist_ok=True)
    custom_font: Path | None = None
    if ui_fonts.exists():
        for ff in sorted(p for p in ui_fonts.iterdir() if p.is_file() and p.suffix.lower() in FONT_EXTS):
            shutil.copy2(ff, pub_fonts / ff.name)
            if ff.name.lower() != Path(DEFAULT_FONT).name.lower() and custom_font is None:
                custom_font = ff

    with open(ui / "brand.json", encoding="utf-8-sig") as f:
        brand = json.load(f)

    font = brand.get("fontFile", DEFAULT_FONT)
    brand["fontFile"] = font if font.startswith("fonts/") else f"fonts/{Path(font).name}"
    if custom_font is not None and brand["fontFile"] == DEFAULT_FONT:
        brand["fontFile"] = f"fonts/{custom_font.name}"
        brand["fontFamily"] = custom_font.stem.replace("-VF", "").replace("_", "-")
        print(f"[INPUTS] Auto-activated custom font: {custom_font.name}")

    apply_fonts(root, brand)
    style_name = apply_style(root, brand)
    with open(root / "src" / "style.json", encoding="utf-8") as f:
        style = json.load(f)
    # Derived keys consumed by the Python audio/asset tools
    brand["assetColorMode"] = "monochrome" if style.get("assets", {}).get("cutoutGrade") == "monochrome" else "color"
    brand["musicMood"] = style.get("sfx", {}).get("musicMood", "editorial")

    with open(root / "src" / "brand.json", "w", encoding="utf-8") as out_f:
        json.dump(brand, out_f, ensure_ascii=False, indent=2)
    logos = root / "src" / "logos.json"
    if not logos.exists():
        logos.write_text("{}\n", encoding="utf-8")
    print(f"[SYNC] brand.json + fonts synced · active style: {style_name}")


if __name__ == "__main__":
    sync_project_inputs()

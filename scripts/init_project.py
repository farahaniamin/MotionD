"""Scaffold a new reel project.

    python3 <SKILL_DIR>/scripts/init_project.py --target ./my-reel [--style paper_cut]

Copies the Remotion template, all style packs, pipeline tools, brand registry, SFX library and the
user_inputs/ hub, then applies the chosen style.
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TOOLS = [
    "output_paths.py", "sync_inputs.py", "set_style.py", "analyze_references.py", "generate_voice.py",
    "export_srt.py", "apply_external_voice.py", "cutout_assets.py", "build_mix.py", "tighten_voice.py",
    "render_reel.py", "logo_fetch.py", "capture_site.py", "qa_check.py", "generate_images.py", "stylize_assets.py",
]
UI_SUBDIRS = ["fonts", "logos", "reference_videos/custom", "assets/match_theme", "assets/need_cutout", "assets/ready", "audio/voice", "audio/music"]


def copy_files_only(src: Path, dst: Path) -> int:
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    if src.exists():
        for item in src.iterdir():
            if item.is_file():
                shutil.copy2(item, dst / item.name)
                n += 1
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--target", required=True)
    ap.add_argument("--style", default=None, help="style pack name (default: brand.json 'style')")
    ap.add_argument("--inputs-dir", default=None, help="import an external user_inputs/ folder")
    args = ap.parse_args()

    skill = Path(__file__).resolve().parent.parent
    target = Path(args.target).resolve()
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(skill / "resources" / "template", target, dirs_exist_ok=True)
    shutil.copytree(skill / "styles", target / "styles", dirs_exist_ok=True)
    shutil.copytree(skill / "resources" / "fonts", target / "fonts_library", dirs_exist_ok=True)

    tools = target / "tools"
    tools.mkdir(exist_ok=True)
    for name in TOOLS:
        if (skill / "scripts" / name).exists():
            shutil.copy2(skill / "scripts" / name, tools / name)
    shutil.copy2(skill / "brands" / "registry.json", tools / "brands_registry.json")

    for d in ("public/fonts", "public/img/screens", "public/logos", "public/audio", "raw_img", "exports"):
        (target / d).mkdir(parents=True, exist_ok=True)
    shutil.copy2(skill / "resources" / "img" / "grain.png", target / "public" / "img" / "grain.png")

    ui_src = Path(args.inputs_dir).resolve() if args.inputs_dir else skill / "user_inputs"
    ui = target / "user_inputs"
    for sub in UI_SUBDIRS:
        copy_files_only(ui_src / sub, ui / sub)
    for doc in ("README.md", "brand.json"):
        src = ui_src / doc if (ui_src / doc).exists() else skill / "user_inputs" / doc
        shutil.copy2(src, ui / doc)
    if not any((ui / "fonts").iterdir()):
        copy_files_only(skill / "user_inputs" / "fonts", ui / "fonts")

    if args.style:
        bp = ui / "brand.json"
        brand = json.loads(bp.read_text(encoding="utf-8-sig"))
        brand["style"] = args.style
        bp.write_text(json.dumps(brand, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    sys.path.insert(0, str(tools))
    from output_paths import get_project_output_dir
    from sync_inputs import sync_project_inputs

    sync_project_inputs(target)
    shutil.copytree(skill / "resources" / "sfx", target / "public" / "sfx", dirs_exist_ok=True)

    print(f"[READY] {target}")
    print(f"        user-facing folder : {ui}")
    print(f"        outputs            : {get_project_output_dir(target)}")
    print("        next               : npm install && python3 tools/logo_fetch.py <tools...>")


if __name__ == "__main__":
    main()

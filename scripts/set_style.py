"""Switch the visual style of a project in one command.

    python3 tools/set_style.py paper_cut
    python3 tools/set_style.py studio_mono
    python3 tools/set_style.py --list

Writes "style" into user_inputs/brand.json and re-syncs. Scenes are untouched: every kit component
renders through the active theme, so the whole reel re-skins (backgrounds, cards, highlights, logo
treatment, transitions, motion stepping, SFX remap, outro).
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_inputs import find_styles_dir, sync_project_inputs  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("style", nargs="?")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args()
    root = Path.cwd()
    styles = find_styles_dir(root)
    if args.list or not args.style:
        for p in sorted(styles.iterdir()):
            sj = p / "style.json"
            if sj.exists():
                meta = json.loads(sj.read_text(encoding="utf-8"))
                print(f"  {p.name:<16} {meta.get('description', '')}")
        return
    bp = root / "user_inputs" / "brand.json"
    brand = json.loads(bp.read_text(encoding="utf-8-sig"))
    brand["style"] = args.style
    bp.write_text(json.dumps(brand, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sync_project_inputs(root)


if __name__ == "__main__":
    main()

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TEMPLATE_IMGS = {"grain.png"}
TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))


def run_cmd(cmd: list[str]):
    use_shell = os.name == "nt" and cmd[0] in ("npx", "npm")
    subprocess.run(cmd, check=True, shell=use_shell)


def verify_bespoke_project_assets(allow_shared: bool = False):
    """
    Guarantees every reel uses bespoke topic-specific scene objects rather than
    lazily copying public/img/*.png from a previous reel in the workspace.
    """
    if allow_shared:
        return
    out_img_dir = Path("public/img")
    if not out_img_dir.exists():
        return

    cwd = Path.cwd().resolve()
    workspace_parent = cwd.parent
    sibling_hashes: dict[str, str] = {}
    for sib in workspace_parent.iterdir():
        if not sib.is_dir() or sib.resolve() == cwd or sib.name == "skills" or sib.name.endswith("-output"):
            continue
        sib_img = sib / "public" / "img"
        if not sib_img.exists():
            continue
        for f in sib_img.glob("*.png"):
            if f.name in TEMPLATE_IMGS:
                continue
            h = hashlib.md5(f.read_bytes()).hexdigest()
            sibling_hashes[h] = f"{sib.name}/public/img/{f.name}"

    dups = []
    for f in sorted(out_img_dir.glob("*.png")):
        if f.name in TEMPLATE_IMGS:
            continue
        h = hashlib.md5(f.read_bytes()).hexdigest()
        if h in sibling_hashes:
            dups.append(f"  - public/img/{f.name} is an exact copy of {sibling_hashes[h]}")

    if dups:
        raise RuntimeError(
            "\n[DUPLICATE-ASSET BLOCKED] Reused AI scene objects copied from another reel project!\n"
            + "\n".join(dups)
            + "\nFix: Generate fresh, topic-specific objects in raw_img/ via image-generator and run 'python tools/cutout_assets.py' "
            "(or pass --allow-shared-assets ONLY if the user explicitly requested reusing old images)."
        )


def main():
    parser = argparse.ArgumentParser(description="Bundle, verify scene stills, and render final MP4 with 320k AAC original audio.")
    parser.add_argument("--stills-only", action="store_true", help="Only render verification stills per scene.")
    parser.add_argument("--skip-stills", action="store_true", help="Skip verification stills (when already inspected via --stills-only).")
    parser.add_argument(
        "--output",
        default=None,
        help="Final muxed MP4 path or filename (defaults to ../<project>-output/<project>.mp4).",
    )
    parser.add_argument("--concurrency", default="4", help="Remotion render concurrency.")
    parser.add_argument("--browser-executable", default=os.environ.get("REMOTION_BROWSER_EXECUTABLE"), help="Use a local Chrome/headless-shell instead of Remotion's download.")
    parser.add_argument("--allow-shared-assets", action="store_true", help="Allow shared PNGs across sibling projects.")
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from output_paths import resolve_mp4_output_path

    browser_flag = [f"--browser-executable={args.browser_executable}"] if args.browser_executable else []

    final_output_path = resolve_mp4_output_path(args.output)
    final_output_path.parent.mkdir(parents=True, exist_ok=True)

    verify_bespoke_project_assets(allow_shared=args.allow_shared_assets)

    with open("src/timeline.json", encoding="utf-8") as f:
        tl = json.load(f)

    sync_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sync_inputs.py")
    if os.path.exists(sync_script):
        subprocess.run([sys.executable, sync_script], check=True)

    fps = int(tl.get("fps", 30))
    voice_end = float(tl["voice_end"])
    total_dur = float(tl["total_dur"])

    qa = os.path.join(TOOLS_DIR, "qa_check.py")
    if os.path.exists(qa):
        print("[QA] static checks (logos, style independence, pacing) ...")
        subprocess.run([sys.executable, qa], check=True)

    if os.path.exists("tsconfig.json"):
        print("[0/3] Type-checking src/ with TypeScript ...")
        run_cmd(["npx", "tsc", "--noEmit"])

    print("[1/3] Bundling Remotion project -> remotion_bundle ...")
    run_cmd(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=remotion_bundle"])

    if not args.skip_stills:
        os.makedirs("out_stills", exist_ok=True)
        for b_idx, b in enumerate(tl["beats"]):
            bs = float(b["s"])
            be = float(b["e"])
            bdur = be - bs
            sample_points = [bs + 0.46 * bdur, bs + 0.88 * bdur] if bdur > 4.4 else [bs + 0.86 * bdur]
            for sp_idx, mid_t in enumerate(sample_points):
                frame = max(1, int(round(mid_t * fps)))
                suffix = f"_{chr(97 + sp_idx)}" if len(sample_points) > 1 else ""
                still_out = f"out_stills/scene_{b_idx + 1}{suffix}.png"
                if os.path.exists(still_out):
                    os.remove(still_out)
                run_cmd(
                    [
                        "npx",
                        "remotion",
                        "still",
                        "remotion_bundle",
                        "Reel",
                        still_out,
                        f"--frame={frame}",
                        "--scale=0.5",
                    ]
                    + browser_flag
                )
                print(f"  [STILL] {still_out} (frame {frame}, t={mid_t:.2f}s)")

        outro_frame = min(int(round(total_dur * fps)) - 5, int(round((voice_end + 1.15) * fps)))
        if outro_frame > 0:
            if os.path.exists("out_stills/scene_outro.png"):
                os.remove("out_stills/scene_outro.png")
            run_cmd(
                [
                    "npx",
                    "remotion",
                    "still",
                    "remotion_bundle",
                    "Reel",
                    "out_stills/scene_outro.png",
                    f"--frame={outro_frame}",
                    "--scale=0.5",
                ]
                + browser_flag
            )
            print(f"  [STILL] out_stills/scene_outro.png (frame {outro_frame})")

        if os.path.exists(qa):
            subprocess.run([sys.executable, qa, "--stills"], check=True)

        if args.stills_only:
            print("[DONE] Stills in out_stills/ + out_stills/_contact_sheet.jpg. Inspect them before full render.")
            return

    os.makedirs("audio_work", exist_ok=True)
    raw_video = "audio_work/video_raw.mp4"
    print("[2/3] Rendering muted lossless-grade Remotion video ...")
    run_cmd(
        [
            "npx",
            "remotion",
            "render",
            "remotion_bundle",
            "Reel",
            raw_video,
            "--muted",
            "--crf=14",
            "--x264-preset=slow",
            f"--concurrency={min(int(args.concurrency), os.cpu_count() or 1)}",
        ]
        + browser_flag
    )

    print(f"[3/3] Muxing final H.264 + 320k studio AAC original audio -> {final_output_path} ...")
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            raw_video,
            "-i",
            "public/audio/final_mix.wav",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-movflags",
            "+faststart",
            "-shortest",
            str(final_output_path),
        ],
        check=True,
    )
    print(f"[SUCCESS] Final Reel delivered at: {final_output_path}")

    out_dir = str(final_output_path.parent)
    base_stem = final_output_path.stem
    srt_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "export_srt.py")
    if os.path.exists(srt_script):
        subprocess.run(
            [sys.executable, srt_script, "--timeline", "src/timeline.json", "--out-dir", out_dir, "--name", base_stem],
            check=True,
        )


if __name__ == "__main__":
    main()

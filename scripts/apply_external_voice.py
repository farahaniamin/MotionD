import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SR = 48000
VOICE_EXTS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac", ".opus", ".mp4", ".mov", ".webm"}


def decode_stereo_f32(path: Path) -> np.ndarray:
    probe = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=channels", "-of", "csv=p=0", str(path)],
        capture_output=True,
        text=True,
    )
    ch_str = (probe.stdout or "1").strip().splitlines()[0].strip()
    in_ch = int(ch_str) if ch_str.isdigit() else 1
    if in_ch == 1:
        cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
        res = subprocess.run(cmd, capture_output=True, check=True)
        mono = np.frombuffer(res.stdout, dtype=np.float32).copy()
        return np.column_stack([mono, mono])
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    res = subprocess.run(cmd, capture_output=True, check=True)
    return np.frombuffer(res.stdout, dtype=np.float32).copy().reshape(-1, 2)


def write_wav_s24le(path: str | Path, stereo_f32: np.ndarray):
    clipped = np.clip(stereo_f32, -1.0, 1.0).astype(np.float32)
    cmd = [
        "ffmpeg",
        "-v",
        "error",
        "-y",
        "-f",
        "f32le",
        "-ar",
        str(SR),
        "-ac",
        "2",
        "-i",
        "-",
        "-c:a",
        "pcm_s24le",
        str(path),
    ]
    subprocess.run(cmd, input=clipped.tobytes(), check=True)


def find_voice_file(explicit_path: str | None) -> Path:
    if explicit_path:
        p = Path(explicit_path).resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"Specified voice file not found: {p}")

    voice_dir = Path("user_inputs/audio/voice")
    if voice_dir.exists():
        candidates = sorted(
            [p for p in voice_dir.iterdir() if p.is_file() and p.suffix.lower() in VOICE_EXTS],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if candidates:
            return candidates[0]
    raise FileNotFoundError(
        "No external voice file found! Put your recorded voice (.m4a/.wav) or AI voice (.mp3) in user_inputs/audio/voice/ or pass --voice <path>."
    )


def main():
    parser = argparse.ArgumentParser(
        description="100% Original-Voice Swap Utility (Zero Denoise / Zero EQ / Zero Compression)."
    )
    parser.add_argument(
        "--voice",
        default=None,
        help="Path to voice file (auto-checks user_inputs/audio/voice/).",
    )
    parser.add_argument(
        "--mode",
        choices=["direct", "rebuild-timeline"],
        default="direct",
        help=(
            "'direct' places the untouched 100%% original voice directly onto the existing video and remuxes at 320k AAC; "
            "'rebuild-timeline' re-aligns timeline.json & .srt via generate_voice.py."
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output MP4 path or filename (defaults to ../<project>-output/<project>_CustomVoice.mp4).",
    )
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from output_paths import resolve_mp4_output_path

    default_stem = f"{Path.cwd().resolve().name}_CustomVoice"
    final_output_path = resolve_mp4_output_path(args.output, default_stem=default_stem)

    ext_voice_path = find_voice_file(args.voice)
    print(f"[VOICE-SWAP] Loading 100% original voice (Zero-DSP): {ext_voice_path}")

    if args.mode == "rebuild-timeline":
        cmd = [sys.executable, "tools/generate_voice.py", "--voice-file", str(ext_voice_path)]
        subprocess.run(cmd, check=True)
        subprocess.run([sys.executable, "tools/build_mix.py"], check=True)
        print(
            "[SUCCESS] Rebuilt src/timeline.json, exports/*.srt, and public/audio/final_mix.wav with 100% original voice! "
            "Run 'python tools/render_reel.py' to render frames to the new voice duration."
        )
        return

    with open("src/timeline.json", encoding="utf-8") as f:
        tl = json.load(f)

    total_dur = float(tl["total_dur"])
    lead_s = float(tl["beats"][0]["s"]) if tl.get("beats") else 0.14
    lead_samples = int(round(lead_s * SR))
    total_samples = int(round(total_dur * SR))

    raw_stereo = decode_stereo_f32(ext_voice_path)
    assembled = np.zeros((total_samples, 2), dtype=np.float32)
    take = min(len(raw_stereo), max(0, total_samples - lead_samples))
    if take > 0:
        assembled[lead_samples : lead_samples + take] = raw_stereo[:take]

    os.makedirs("audio_work", exist_ok=True)
    proc_wav = "audio_work/voice_mastered.wav"
    write_wav_s24le(proc_wav, assembled)
    print(f"[VOICE-SWAP] Saved 100% untouched 24-bit voice -> {proc_wav}")

    subprocess.run([sys.executable, "tools/build_mix.py"], check=True)

    raw_video = Path("audio_work/video_raw.mp4")
    if raw_video.exists():
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-y",
                "-i",
                str(raw_video),
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
        print(f"[SUCCESS] Remuxed 100% original voice + SFX + Music (320k AAC) -> {final_output_path}")
        srt_script = Path(__file__).resolve().parent / "export_srt.py"
        if srt_script.exists():
            subprocess.run(
                [
                    sys.executable,
                    str(srt_script),
                    "--timeline",
                    "src/timeline.json",
                    "--out-dir",
                    str(final_output_path.parent),
                    "--name",
                    final_output_path.stem,
                ],
                check=True,
            )
    else:
        print("[INFO] Mix updated at public/audio/final_mix.wav. Run 'npm run render' to produce MP4.")


if __name__ == "__main__":
    main()

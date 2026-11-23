import argparse
import subprocess
import sys
from pathlib import Path
import numpy as np

SR = 48000

def tighten_audio_stream(
    in_path: Path,
    out_path: Path,
    thresh_db: float = -42.0,
    max_pause_s: float = 0.14,
    target_pause_s: float = 0.12,
    tempo: float = 1.00,
):
    # 1. Decode bit-transparent stereo float32
    cmd = ["ffmpeg", "-v", "error", "-i", str(in_path), "-vn", "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"]
    res = subprocess.run(cmd, capture_output=True, check=True)
    audio = np.frombuffer(res.stdout, dtype=np.float32).reshape(-1, 2)
    orig_dur = len(audio) / SR

    # 2. 10ms RMS window detection
    win_size = int(0.010 * SR)
    num_wins = len(audio) // win_size
    mono = np.mean(audio, axis=1)
    rms = np.array([np.sqrt(np.mean(mono[i*win_size:(i+1)*win_size]**2)) for i in range(num_wins)])
    rms_db = 20 * np.log10(np.maximum(rms, 1e-7))
    is_silent = rms_db < thresh_db

    # 3. Identify segments
    raw_segments = []
    cur_state = not is_silent[0]
    cur_start_win = 0
    for w_idx in range(1, num_wins):
        state = not is_silent[w_idx]
        if state != cur_state:
            raw_segments.append((cur_start_win * win_size, w_idx * win_size, cur_state))
            cur_state = state
            cur_start_win = w_idx
    raw_segments.append((cur_start_win * win_size, len(audio), cur_state))

    # Merge very brief dip silences (< 70ms) to avoid cutting intra-consonant stops
    merged = []
    for s, e, is_speech in raw_segments:
        dur = (e - s) / SR
        if not is_speech and dur < 0.070:
            if merged and merged[-1][2]:
                merged[-1] = (merged[-1][0], e, True)
            else:
                merged.append((s, e, True))
        else:
            if merged and merged[-1][2] == is_speech:
                merged[-1] = (merged[-1][0], e, is_speech)
            else:
                merged.append((s, e, is_speech))

    # 4. Trim silences > max_pause_s down to target_pause_s with cosine fades
    target_samples = int(target_pause_s * SR)
    fade_len = int(0.006 * SR) # 6ms crossfade
    fade_in = (0.5 * (1 - np.cos(np.linspace(0, np.pi, fade_len))))[:, None].astype(np.float32)
    fade_out = (0.5 * (1 + np.cos(np.linspace(0, np.pi, fade_len))))[:, None].astype(np.float32)

    chunks = []
    trimmed_seconds = 0.0

    for s, e, is_speech in merged:
        chunk = audio[s:e].copy()
        dur = len(chunk) / SR
        if is_speech:
            chunks.append(chunk)
        else:
            if dur > max_pause_s:
                trimmed_seconds += (dur - target_pause_s)
                # Keep target_samples of low room-tone / silence with smooth edges
                kept = chunk[:target_samples].copy()
                if len(kept) >= fade_len * 2:
                    kept[:fade_len] *= fade_in
                    kept[-fade_len:] *= fade_out
                chunks.append(kept)
            else:
                chunks.append(chunk)

    tightened = np.vstack(chunks)

    # 5. Optional subtle tempo adjustment (atempo) if requested
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp_wav = out_path.parent / "_temp_tightened.wav"

    # Write intermediate 24-bit PCM
    clipped = np.clip(tightened, -1.0, 1.0).astype(np.float32)
    cmd_write = [
        "ffmpeg", "-v", "error", "-y",
        "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", "-",
        "-c:a", "pcm_s24le", str(temp_wav)
    ]
    subprocess.run(cmd_write, input=clipped.tobytes(), check=True)

    if abs(tempo - 1.00) > 0.005:
        cmd_tempo = [
            "ffmpeg", "-v", "error", "-y",
            "-i", str(temp_wav),
            "-filter:a", f"atempo={tempo}",
            "-c:a", "pcm_s24le", str(out_path)
        ]
        subprocess.run(cmd_tempo, check=True)
        if temp_wav.exists():
            temp_wav.unlink()
    else:
        if out_path.exists():
            out_path.unlink()
        temp_wav.rename(out_path)

    final_dur = len(tightened) / SR if abs(tempo - 1.00) <= 0.005 else (len(tightened) / SR) / tempo
    print(f"[TIGHTEN] Original: {orig_dur:.2f}s -> Tightened: {final_dur:.2f}s (Saved {orig_dur - final_dur:.2f}s dead air!)")
    return orig_dur, final_dur

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-pause", type=float, default=0.14)
    parser.add_argument("--target-pause", type=float, default=0.11)
    parser.add_argument("--tempo", type=float, default=1.00)
    args = parser.parse_args()

    tighten_audio_stream(
        Path(args.input),
        Path(args.output),
        max_pause_s=args.max_pause,
        target_pause_s=args.target_pause,
        tempo=args.tempo
    )

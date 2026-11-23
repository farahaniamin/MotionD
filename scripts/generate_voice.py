import argparse
import asyncio
import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
import numpy as np
from scipy.io import wavfile

os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SR = 48000
LEAD_IN_S = 0.14
AUDIO_EXTS = {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".opus", ".mp4", ".mov", ".webm"}


def strip_kasreh(text: str) -> str:
    return text.replace("\u0650", "").strip()


def norm_fa(text: str) -> str:
    t = strip_kasreh(text)
    t = t.replace("\u200c", "").replace("ي", "ی").replace("ك", "ک").replace("ة", "ه").replace("ؤ", "و").replace("أ", "ا").replace("إ", "ا")
    return re.sub(r"[^\w\u0600-\u06FF]", "", t).lower()


def find_user_voice_input(explicit_path: str | None) -> Path | None:
    if explicit_path:
        p = Path(explicit_path).resolve()
        if p.exists():
            return p
        raise FileNotFoundError(f"Specified voice file not found: {p}")

    voice_dir = Path("user_inputs/audio/voice")
    if not voice_dir.exists():
        return None
    candidates = sorted(
        [p for p in voice_dir.iterdir() if p.is_file() and p.suffix.lower() in AUDIO_EXTS],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return candidates[0] if candidates else None


def decode_original_stereo_f32(path: Path) -> np.ndarray:
    """
    100% Bit-Transparent Decode:
    Preserves true stereo if >=2ch, or maps 1ch mono at 1.00x unity gain to [L, R]
    (avoiding FFmpeg's -3dB stereo pan-law drop on mono voice files!). Zero filters applied.
    """
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
    raw = np.frombuffer(res.stdout, dtype=np.float32).copy()
    return raw.reshape(-1, 2)


def write_wav_s24le(path: str | Path, stereo_f32: np.ndarray):
    """
    Writes studio-grade 24-bit PCM WAV (144 dB dynamic range, universal Remotion & FFmpeg support)
    directly from float32 memory without 16-bit truncation or DSP filters.
    """
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


def transcribe_words_with_whisper(
    audio_source_path: Path,
    prompt_text: str,
    model_name: str = "small",
    language: str | None = "fa",
) -> list[dict]:
    """
    Extracts millisecond-accurate word timestamps from a read-only 16kHz in-memory buffer.
    Never modifies the output audio file.
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("[ALIGN] faster-whisper not installed; falling back to acoustic VAD alignment.")
        return []

    lang_arg = None if (language in (None, "", "auto")) else language
    print(f"[ALIGN] Running faster-whisper ('{model_name}', lang={lang_arg or 'auto'} word-level alignment on untouched voice) ...")
    try:
        cmd_16k = ["ffmpeg", "-v", "error", "-i", str(audio_source_path), "-vn", "-f", "f32le", "-ac", "1", "-ar", "16000", "-"]
        res_16k = subprocess.run(cmd_16k, capture_output=True, check=True)
        audio_16k = np.frombuffer(res_16k.stdout, dtype=np.float32).copy()

        model = WhisperModel(model_name, device="cpu", compute_type="int8")
        segments, _ = model.transcribe(
            audio_16k,
            language=lang_arg,
            initial_prompt=strip_kasreh(prompt_text)[:600] if prompt_text else None,
            word_timestamps=True,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 180, "speech_pad_ms": 60},
            condition_on_previous_text=False,
        )
        out_words = []
        for seg in segments:
            for w in seg.words or []:
                txt = w.word.strip()
                if txt:
                    out_words.append({"t": txt, "s": float(w.start), "e": float(w.end)})
        print(f"[ALIGN] Extracted {len(out_words)} acoustic word timestamps.")
        return out_words
    except Exception as exc:
        print(f"[ALIGN] Whisper alignment warning ({exc}); falling back to acoustic VAD.")
        return []


def auto_build_beats_from_whisper(whisper_words: list[dict]) -> list[dict]:
    """
    Used when the user provides a spontaneous recorded voice file without a matching beats.json script.
    Groups spoken words into balanced 3.2s-5.0s editorial beats at natural pauses/punctuation.
    """
    beats = []
    cur_words = []
    b_id = 0
    for idx, w in enumerate(whisper_words):
        cur_words.append(w)
        is_last = idx == len(whisper_words) - 1
        dur = cur_words[-1]["e"] - cur_words[0]["s"]
        gap = (whisper_words[idx + 1]["s"] - w["e"]) if not is_last else 1.0
        ends_sent = w["t"].endswith((".", "؟", "?", "!", "؛"))

        if is_last or (dur >= 3.0 and (gap >= 0.32 or ends_sent)) or dur >= 5.2:
            txt = " ".join(x["t"] for x in cur_words).strip()
            beats.append(
                {
                    "id": b_id,
                    "tts": txt,
                    "display": strip_kasreh(txt),
                    "pause_after": 0.24 if not is_last else 0.35,
                }
            )
            b_id += 1
            cur_words = []
    return beats


def align_whisper_to_beats(beats: list[dict], whisper_words: list[dict], total_audio_dur: float) -> list[list[dict]]:
    """
    Maps Whisper's acoustic [s, e] timestamps onto the exact canonical tokens of `beats.json`
    using normalized Persian SequenceMatcher + strict monotonic interpolation.
    """
    flat_tokens = []
    for b_idx, b in enumerate(beats):
        raw_tokens = b["tts"].strip().split()
        for t_idx, tok in enumerate(raw_tokens):
            flat_tokens.append({"b": b_idx, "i": t_idx, "tok": tok, "norm": norm_fa(tok)})

    if not flat_tokens:
        return [[] for _ in beats]

    w_norms = [norm_fa(w["t"]) for w in whisper_words]
    t_norms = [ft["norm"] for ft in flat_tokens]

    matcher = difflib.SequenceMatcher(None, t_norms, w_norms, autojunk=False)
    anchors: dict[int, tuple[float, float]] = {}

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for offset in range(i2 - i1):
                w = whisper_words[j1 + offset]
                anchors[i1 + offset] = (w["s"], w["e"])
        elif tag == "replace" and (i2 - i1) > 0 and (j2 - j1) > 0:
            span_s = whisper_words[j1]["s"]
            span_e = whisper_words[j2 - 1]["e"]
            n_span = i2 - i1
            step = max(0.06, (span_e - span_s) / n_span)
            for k in range(n_span):
                anchors[i1 + k] = (span_s + k * step, min(span_e, span_s + (k + 1) * step))

    n_tok = len(flat_tokens)
    first_speech_s = whisper_words[0]["s"] if whisper_words else 0.04
    last_speech_e = whisper_words[-1]["e"] if whisper_words else max(0.5, total_audio_dur - 0.04)

    resolved: list[tuple[float, float]] = [(0.0, 0.0)] * n_tok
    idx = 0
    while idx < n_tok:
        if idx in anchors:
            resolved[idx] = anchors[idx]
            idx += 1
            continue
        end_un = idx
        while end_un < n_tok and end_un not in anchors:
            end_un += 1
        left_s = resolved[idx - 1][1] if idx > 0 else first_speech_s
        right_e = anchors[end_un][0] if end_un < n_tok else last_speech_e
        if right_e <= left_s:
            right_e = left_s + 0.12 * (end_un - idx)
        weights = [max(1.0, len(flat_tokens[m]["norm"]) + 1.0) for m in range(idx, end_un)]
        w_sum = sum(weights)
        cur = left_s
        for m_off, w_val in enumerate(weights):
            nxt = cur + (right_e - left_s) * (w_val / w_sum)
            resolved[idx + m_off] = (cur, max(cur + 0.06, nxt))
            cur = nxt
        idx = end_un

    for k in range(1, n_tok):
        prev_s = resolved[k - 1][0]
        cur_s, cur_e = resolved[k]
        if cur_s < prev_s + 0.04:
            cur_s = prev_s + 0.04
        resolved[k] = (cur_s, max(cur_s + 0.06, cur_e))

    per_beat: list[list[dict]] = [[] for _ in beats]
    for ft, (s_val, e_val) in zip(flat_tokens, resolved):
        per_beat[ft["b"]].append({"t": ft["tok"], "s": s_val, "e": max(s_val + 0.06, e_val)})
    return per_beat


def fallback_vad_align_beats(mono_audio: np.ndarray, beats: list[dict]) -> list[list[dict]]:
    hop = int(0.010 * SR)
    n_frames = max(1, len(mono_audio) // hop)
    rms = np.array([np.sqrt(np.mean(mono_audio[i * hop : (i + 1) * hop] ** 2)) + 1e-9 for i in range(n_frames)])
    db = 20.0 * np.log10(rms)
    thresh_db = max(-45.0, min(-28.0, float(np.percentile(db, 10)) + 10.0))

    active = np.where(db > thresh_db)[0]
    s0 = (active[0] * hop / SR) if len(active) else 0.0
    e0 = ((active[-1] + 1) * hop / SR) if len(active) else (len(mono_audio) / SR)

    silent = db <= thresh_db
    runs = []
    i = 0
    while i < n_frames:
        if silent[i]:
            j = i
            while j < n_frames and silent[j]:
                j += 1
            if i > 12 and j < n_frames - 12 and (j - i) >= 12:
                runs.append((j - i, ((i + j) * 0.5 * hop) / SR))
            i = j
        else:
            i += 1

    n_beats = len(beats)
    if len(runs) >= n_beats - 1 and n_beats > 1:
        splits = sorted([r[1] for r in sorted(runs, key=lambda x: x[0], reverse=True)[: n_beats - 1]])
        bounds = [s0] + splits + [e0]
    else:
        char_weights = [max(4, len(strip_kasreh(b["tts"]))) for b in beats]
        tot_w = sum(char_weights)
        bounds = [s0]
        acc = s0
        for cw in char_weights:
            acc += (e0 - s0) * (cw / tot_w)
            bounds.append(acc)

    per_beat = []
    for b_idx, b in enumerate(beats):
        bs = bounds[b_idx]
        be = bounds[b_idx + 1]
        tokens = b["tts"].strip().split()
        if not tokens:
            per_beat.append([])
            continue
        w_weights = [max(1.5, len(norm_fa(t)) + 1.0) for t in tokens]
        w_sum = sum(w_weights)
        cur = bs
        b_words = []
        for tok, ww in zip(tokens, w_weights):
            dur = max(0.06, (be - bs) * (ww / w_sum))
            b_words.append({"t": tok, "s": cur, "e": cur + dur})
            cur += dur
        per_beat.append(b_words)
    return per_beat


def build_original_voice_timeline_and_wav(
    stereo_audio: np.ndarray,
    beats: list[dict],
    aligned_per_beat: list[list[dict]],
) -> tuple[np.ndarray, list[dict], float]:
    """
    Preserves 100.00% of the user's continuous original audio waveform untouched!
    No slicing, no crossfading, no pause-chopping, and zero DSP filters.
    Adds only a tiny 0.14s pure digital lead-in before sample 0 so frame 0 transitions cleanly,
    and shifts all acoustic word timestamps by +LEAD_IN_S.
    """
    lead_samples = int(round(LEAD_IN_S * SR))
    tail_samples = int(round(0.20 * SR))
    out_stereo = np.vstack(
        [
            np.zeros((lead_samples, 2), dtype=np.float32),
            stereo_audio,
            np.zeros((tail_samples, 2), dtype=np.float32),
        ]
    )

    raw_dur = len(stereo_audio) / SR
    timeline_beats = []
    n_beats = len(beats)

    shifted_beats = []
    for b_words in aligned_per_beat:
        shifted_beats.append(
            [{"t": w["t"], "s": round(w["s"] + LEAD_IN_S, 3), "e": round(w["e"] + LEAD_IN_S, 3)} for w in b_words]
        )

    for b_idx, (b, s_words) in enumerate(zip(beats, shifted_beats)):
        if s_words:
            first_s = s_words[0]["s"]
            last_e = s_words[-1]["e"]
        else:
            first_s = LEAD_IN_S + (b_idx / max(1, n_beats)) * raw_dur
            last_e = LEAD_IN_S + ((b_idx + 1) / max(1, n_beats)) * raw_dur

        b_start = LEAD_IN_S if b_idx == 0 else timeline_beats[-1]["scene_end"]
        if b_idx + 1 < n_beats and shifted_beats[b_idx + 1]:
            next_first_s = shifted_beats[b_idx + 1][0]["s"]
            scene_end = round(0.5 * (last_e + next_first_s), 3)
            scene_end = max(b_start + 0.4, scene_end)
        else:
            scene_end = round(max(last_e + 0.25, LEAD_IN_S + raw_dur), 3)

        timeline_beats.append(
            {
                "id": b.get("id", b_idx),
                "s": round(b_start, 3),
                "e": round(max(b_start + 0.25, last_e), 3),
                "scene_end": round(scene_end, 3),
                "display": b.get("display") or strip_kasreh(b["tts"]),
                "tts": b["tts"],
                "words": s_words,
            }
        )

    voice_end = round(timeline_beats[-1]["scene_end"] if timeline_beats else (LEAD_IN_S + raw_dur), 3)
    return out_stereo, timeline_beats, voice_end


def trim_tts_edges_safe(audio: np.ndarray, thresh_db: float = -46.0, pad_ms: float = 28.0) -> tuple[np.ndarray, int]:
    peak = np.abs(audio).max() + 1e-9
    db = 20.0 * np.log10(np.abs(audio) / peak + 1e-9)
    idx = np.where(db > thresh_db)[0]
    if len(idx) == 0:
        return audio, 0
    pad = int((pad_ms / 1000.0) * SR)
    s = max(0, idx[0] - pad)
    e = min(len(audio), idx[-1] + pad)
    out = audio[s:e].copy()
    fade = min(int(0.012 * SR), len(out) // 4)
    if fade > 0:
        out[:fade] *= np.linspace(0.0, 1.0, fade)
        out[-fade:] *= np.linspace(1.0, 0.0, fade)
    return out, s


async def synth_beat_edge_tts(beat: dict, voice: str, rate: str, pitch: str, out_dir: str) -> dict:
    import inspect
    import edge_tts

    mp3_path = os.path.join(out_dir, f"beat_{beat['id']:02d}.mp3")
    kwargs = {"voice": voice, "rate": rate, "pitch": pitch}
    if "boundary" in inspect.signature(edge_tts.Communicate.__init__).parameters:
        kwargs["boundary"] = "WordBoundary"
    comm = edge_tts.Communicate(beat["tts"], **kwargs)
    marks = []
    with open(mp3_path, "wb") as f:
        async for ev in comm.stream():
            if ev["type"] == "audio":
                f.write(ev["data"])
            elif ev["type"] == "WordBoundary":
                marks.append(
                    {
                        "text": ev["text"],
                        "offset": ev["offset"] / 1e7,
                        "dur": ev["duration"] / 1e7,
                    }
                )
    return {"mp3": mp3_path, "marks": marks}


async def run_edge_tts_fallback(
    beats: list[dict],
    brand: dict,
    work_dir: str,
    beats_cfg: dict | None = None,
) -> tuple[np.ndarray, list[dict], float, str]:
    v_raw = brand.get("voice", "fa-IR-FaridNeural")
    if isinstance(v_raw, dict):
        voice = v_raw.get("voiceName", "fa-IR-FaridNeural")
        rate = v_raw.get("rate", "+16%")
        pitch = v_raw.get("pitch", "-3Hz")
    else:
        voice = v_raw
        rate = brand.get("voiceRate", "+16%")
        pitch = brand.get("voicePitch", "-3Hz")

    if isinstance(beats_cfg, dict):
        voice = beats_cfg.get("voice", voice)
        rate = beats_cfg.get("rate", rate)
        pitch = beats_cfg.get("pitch", pitch)
        cursor = float(beats_cfg.get("lead_silence", 0.18))
    else:
        cursor = 0.18

    print(f"[TTS-FALLBACK] No file in user_inputs/audio/voice/ -> synthesizing clean voice ({voice}, rate={rate})...")

    assembled = [np.zeros(int(cursor * SR), dtype=np.float32)]
    timeline_beats = []

    for b in beats:
        info = await synth_beat_edge_tts(b, voice, rate, pitch, work_dir)
        stereo = decode_original_stereo_f32(Path(info["mp3"]))
        raw = stereo[:, 0]
        trimmed, s_idx = trim_tts_edges_safe(raw, thresh_db=-46.0, pad_ms=28.0)
        trim_s = s_idx / SR
        dur = len(trimmed) / SR

        words = []
        for m in info["marks"]:
            ws = max(0.0, m["offset"] - trim_s)
            we = min(dur, ws + max(0.08, m["dur"]))
            words.append({"t": m["text"], "s": round(cursor + ws, 3), "e": round(cursor + we, 3)})

        if not words:
            w_marks = transcribe_words_with_whisper(
                Path(info["mp3"]),
                b["tts"],
                model_name="small",
                language=brand.get("language", "fa"),
            )
            if w_marks:
                for wm in w_marks:
                    ws = max(0.0, wm["s"] - trim_s)
                    we = min(dur, ws + max(0.06, wm["e"] - wm["s"]))
                    words.append({"t": wm["t"], "s": round(cursor + ws, 3), "e": round(cursor + we, 3)})
            else:
                tokens = b["tts"].split()
                step = dur / max(1, len(tokens))
                words = [
                    {"t": tok, "s": round(cursor + k * step, 3), "e": round(cursor + (k + 1) * step, 3)}
                    for k, tok in enumerate(tokens)
                ]

        pause = float(b.get("pause_after", 0.24))
        timeline_beats.append(
            {
                "id": b["id"],
                "s": round(cursor, 3),
                "e": round(cursor + dur, 3),
                "scene_end": round(cursor + dur + pause, 3),
                "display": b.get("display") or strip_kasreh(b["tts"]),
                "tts": b["tts"],
                "words": words,
            }
        )
        assembled.append(trimmed)
        assembled.append(np.zeros(int(pause * SR), dtype=np.float32))
        cursor += dur + pause

    full_mono = np.concatenate(assembled)
    full_stereo = np.column_stack([full_mono, full_mono]).astype(np.float32)
    return full_stereo, timeline_beats, round(cursor, 3), str(voice)


def build_voice_free_timeline(beats: list[dict], beats_cfg: dict, brand: dict) -> tuple[list[dict], float]:
    """
    Builds a deterministic timeline for Voice-Free Visual Showcase reels (music + SFX + animated SVG/UI),
    using each beat's `duration` (default 3.6s) and optional `pause_after` (default 0.0s).
    """
    cursor = float(beats_cfg.get("lead_silence", 0.0) or 0.0)
    default_dur = float(brand.get("recommendedCadenceSec", 3.6) or 3.6)
    timeline_beats: list[dict] = []

    for idx, b in enumerate(beats):
        bid = b.get("id", idx)
        if "duration" in b:
            dur = max(0.8, float(b["duration"]))
        elif "e" in b and "s" in b:
            dur = max(0.8, float(b["e"]) - float(b["s"]))
        else:
            dur = default_dur
        pause = max(0.0, float(b.get("pause_after", 0.0) or 0.0))

        s_t = round(cursor, 3)
        e_t = round(cursor + dur, 3)
        scene_end = round(cursor + dur + pause, 3)
        disp = (b.get("display") or strip_kasreh(b.get("tts", "")) or "").strip()
        tts = (b.get("tts") or "").strip()

        # Synthetic word timings (reading pace, weighted by word length) so wordTime()/wordAt()
        # drive animation in voice-free reels exactly like in voiced ones.
        toks = [w for w in disp.split() if w.strip()]
        words = []
        if toks:
            span_s, span_e = s_t + 0.12, s_t + max(0.4, (e_t - s_t) * 0.78)
            weights = [max(2, len(w)) for w in toks]
            total_w = float(sum(weights))
            acc = span_s
            for w_txt, wt in zip(toks, weights):
                d = (span_e - span_s) * wt / total_w
                words.append({"t": w_txt, "s": round(acc, 3), "e": round(acc + d * 0.92, 3)})
                acc += d
        timeline_beats.append(
            {
                "id": bid,
                "s": s_t,
                "e": e_t,
                "scene_end": scene_end,
                "display": disp,
                "tts": tts,
                "words": words,
            }
        )
        cursor = scene_end

    return timeline_beats, round(cursor, 3)


def main():
    parser = argparse.ArgumentParser(
        description="Audio-First Zero-DSP Voice Engine: preserves 100% original user/AI voice fidelity + word-level alignment."
    )
    parser.add_argument("--beats", default="beats.json", help="Path to beats.json scenario.")
    parser.add_argument(
        "--voice-file",
        default=None,
        help="Optional explicit path to recorded human voice (.m4a/.wav) or AI voice (.mp3). Auto-detects user_inputs/audio/voice/.",
    )
    parser.add_argument(
        "--force-tts",
        action="store_true",
        help="Ignore files in user_inputs/audio/voice/ and synthesize with built-in edge-tts.",
    )
    parser.add_argument(
        "--no-voice",
        action="store_true",
        help="Build a Voice-Free Visual Showcase timeline (music + SFX only, no speech audio).",
    )
    parser.add_argument(
        "--auto-beats",
        action="store_true",
        help="Auto-generate beats.json from a spontaneous ad-lib voice recording using faster-whisper.",
    )
    parser.add_argument(
        "--tighten",
        action="store_true",
        help="Optional: trim long silent dead-air pauses (>0.18s) using tighten_voice.py before alignment (off by default for 100%% Zero-DSP).",
    )
    parser.add_argument("--language", default=None, help="Whisper language code (e.g. 'fa', 'en', or 'auto').")
    parser.add_argument("--whisper-model", default="small", help="faster-whisper model size (default: small).")
    args = parser.parse_args()

    sync_script = Path(__file__).resolve().parent / "sync_inputs.py"
    if sync_script.exists():
        sys.path.insert(0, str(sync_script.parent))
        from sync_inputs import sync_project_inputs

        sync_project_inputs()

    brand_path = Path("src/brand.json")
    brand = json.loads(brand_path.read_text(encoding="utf-8-sig")) if brand_path.exists() else {}

    beats_path = Path(args.beats)
    raw_beats_data = json.loads(beats_path.read_text(encoding="utf-8-sig")) if beats_path.exists() else {}
    beats_cfg = raw_beats_data if isinstance(raw_beats_data, dict) else {}
    beats = beats_cfg.get("beats", []) if isinstance(raw_beats_data, dict) else raw_beats_data

    work_dir = Path("audio_work")
    work_dir.mkdir(parents=True, exist_ok=True)
    proc_wav = work_dir / "voice_mastered.wav"

    cfg_voice_val = str(beats_cfg.get("voice", "")).strip().lower()
    is_voice_free_cfg = cfg_voice_val in {"none", "off", "silent", "voice_free", "voice-free"}
    user_voice_path = None if (args.force_tts or args.no_voice) else find_user_voice_input(args.voice_file)
    whisper_lang = args.language or brand.get("language", "fa")

    if args.no_voice or (is_voice_free_cfg and user_voice_path is None and not args.force_tts):
        if not beats:
            raise FileNotFoundError(f"Scenario file not found or empty beats[]: {beats_path}")
        if proc_wav.exists():
            proc_wav.unlink()
        timeline_beats, voice_end = build_voice_free_timeline(beats, beats_cfg, brand)
        voice_source_label = "none"
        voice_mode = "voice_free_svg_showcase"
    elif user_voice_path is not None:
        effective_voice_path = user_voice_path
        if args.tighten:
            tighten_script = Path(__file__).resolve().parent / "tighten_voice.py"
            if tighten_script.exists():
                tight_out = work_dir / "voice_tightened_source.wav"
                subprocess.run(
                    [sys.executable, str(tighten_script), "--input", str(user_voice_path), "--output", str(tight_out), "--max-pause", "0.18", "--target-pause", "0.12"],
                    check=True,
                )
                effective_voice_path = tight_out

        print(f"[VOICE] Using 100% ORIGINAL user voice (Zero-DSP / No Denoise / No EQ) -> {effective_voice_path}")
        stereo_orig = decode_original_stereo_f32(effective_voice_path)
        raw_dur = len(stereo_orig) / SR
        print(f"[VOICE] Original duration: {raw_dur:.2f}s (100% untouched waveform & natural dynamics)")

        prompt_txt = " ".join(b.get("tts", "") for b in beats) if beats else ""
        whisper_words = transcribe_words_with_whisper(
            effective_voice_path,
            prompt_txt,
            model_name=args.whisper_model,
            language=whisper_lang,
        )

        is_template_placeholder = len(beats) == 1 and "شروعِ داستان" in beats[0].get("tts", "")
        if (args.auto_beats or not beats or is_template_placeholder) and whisper_words:
            print("[AUTO-BEATS] Building beats.json directly from spontaneous voice recording...")
            beats = auto_build_beats_from_whisper(whisper_words)
            out_beats_obj = {**beats_cfg, "beats": beats} if isinstance(raw_beats_data, dict) else {"beats": beats}
            beats_path.write_text(json.dumps(out_beats_obj, ensure_ascii=False, indent=2), encoding="utf-8")

        if not beats:
            raise RuntimeError("beats.json is empty and faster-whisper returned no words to auto-build beats.")

        if whisper_words:
            aligned_per_beat = align_whisper_to_beats(beats, whisper_words, raw_dur)
        else:
            aligned_per_beat = fallback_vad_align_beats(stereo_orig.mean(axis=1), beats)

        out_stereo, timeline_beats, voice_end = build_original_voice_timeline_and_wav(
            stereo_orig, beats, aligned_per_beat
        )
        write_wav_s24le(proc_wav, out_stereo)
        voice_source_label = user_voice_path.name
        voice_mode = "original_tightened" if args.tighten else "original_untouched"
    else:
        if not beats:
            raise FileNotFoundError(f"Scenario file not found: {beats_path}")
        out_stereo, timeline_beats, voice_end, used_voice_name = asyncio.run(
            run_edge_tts_fallback(beats, brand, str(work_dir), beats_cfg=beats_cfg)
        )
        write_wav_s24le(proc_wav, out_stereo)
        voice_source_label = used_voice_name
        voice_mode = "edge_tts"

    outro_dur = float(beats_cfg.get("outro_dur") or brand.get("outroDurationSec", 2.4))
    total_dur = round(voice_end + outro_dur, 3)

    timeline = {
        "fps": 30,
        "width": 1080,
        "height": 1920,
        "voice_source": voice_source_label,
        "voice_mode": voice_mode,
        "voice_end": voice_end,
        "total_dur": total_dur,
        "beats": timeline_beats,
    }
    os.makedirs("src", exist_ok=True)
    with open("src/timeline.json", "w", encoding="utf-8") as f:
        json.dump(timeline, f, ensure_ascii=False, indent=2)

    has_spoken_text = any((b.get("tts") or "").strip() for b in timeline_beats)
    export_script = Path(__file__).resolve().parent / "export_srt.py"
    if export_script.exists() and voice_mode != "voice_free_svg_showcase" and has_spoken_text:
        subprocess.run(
            [sys.executable, str(export_script), "--timeline", "src/timeline.json", "--out-dir", "exports", "--name", "reel_script"],
            check=True,
        )

    print(
        f"[OK] Timeline ready! Source={voice_source_label} ({voice_mode}) | "
        f"Voice end: {voice_end:.2f}s | Total reel: {total_dur:.2f}s ({int(round(total_dur * 30))} frames)"
    )
    for tb in timeline_beats:
        if tb["words"]:
            w_str = " | ".join(f"[{i}]{w['t']}@{w['s']:.2f}" for i, w in enumerate(tb["words"]))
        else:
            w_str = f"[voice-free {tb['e'] - tb['s']:.2f}s] {tb.get('display') or '(visual beat)'}"
        print(f"  [Beat {tb['id']}] {tb['s']:.2f}s -> {tb['scene_end']:.2f}s :: {w_str}")


if __name__ == "__main__":
    main()

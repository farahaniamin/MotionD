import argparse
import json
import re
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def strip_kasreh(text: str) -> str:
    return text.replace("\u0650", "").strip()


def beat_spoken_text(beat: dict) -> str:
    return (beat.get("tts") or beat.get("display") or beat.get("text") or "").strip()


def word_text(w: dict) -> str:
    return str(w.get("t") or w.get("word") or "")


def norm_word(text: str) -> str:
    return re.sub(r"[^\w\u200c]", "", strip_kasreh(text))


def fmt_srt_time(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000.0)))
    hh = ms_total // 3_600_000
    rem = ms_total % 3_600_000
    mm = rem // 60_000
    rem %= 60_000
    ss = rem // 1000
    ms = rem % 1000
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def to_fa_digits(val: int | str) -> str:
    return str(val).translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))


def align_tts_tokens(tts_text: str, words: list[dict], beat_s: float, beat_e: float) -> list[dict]:
    """
    Maps every whitespace token of verbatim `tts_text` (preserving punctuation & optional kasreh)
    onto exact [s, e] timestamps from `words`, guaranteeing 0% dropped words.
    """
    tokens = tts_text.strip().split()
    if not tokens:
        return []

    if not words:
        weights = [max(1.0, len(t) + 1.2) for t in tokens]
        total_w = sum(weights)
        dur = max(0.3, beat_e - beat_s)
        cur = beat_s
        aligned = []
        for tok, w in zip(tokens, weights):
            nxt = cur + dur * (w / total_w)
            aligned.append({"tok": tok, "s": round(cur, 3), "e": round(nxt, 3)})
            cur = nxt
        return aligned

    if len(tokens) == len(words):
        aligned = []
        for idx, (tok, w) in enumerate(zip(tokens, words)):
            s = float(w["s"]) if idx > 0 else min(beat_s, float(w["s"]))
            e = float(w["e"]) if idx < len(tokens) - 1 else max(beat_e, float(w["e"]))
            aligned.append({"tok": tok, "s": s, "e": e})
        return aligned

    aligned = []
    w_idx = 0
    n_words = len(words)
    for t_idx, tok in enumerate(tokens):
        if w_idx >= n_words:
            prev_e = aligned[-1]["e"] if aligned else beat_s
            aligned.append({"tok": tok, "s": prev_e, "e": max(prev_e + 0.08, beat_e)})
            continue

        target_norm = norm_word(tok)
        start_s = float(words[w_idx]["s"]) if t_idx > 0 else min(beat_s, float(words[w_idx]["s"]))
        end_e = float(words[w_idx]["e"])
        acc_norm = norm_word(word_text(words[w_idx]))
        w_idx += 1

        while w_idx < n_words and len(acc_norm) < len(target_norm) and (n_words - w_idx) >= (len(tokens) - t_idx):
            acc_norm += norm_word(word_text(words[w_idx]))
            end_e = float(words[w_idx]["e"])
            w_idx += 1

        if t_idx == len(tokens) - 1:
            end_e = max(end_e, beat_e)
        aligned.append({"tok": tok, "s": start_s, "e": end_e})

    return aligned


def split_beat_into_srt_cues(beat: dict) -> list[tuple[float, float, str]]:
    """
    Builds verbatim SRT cues from `beat["tts"]` (NEVER shortened `display`),
    splitting long sentences at natural acoustic pauses & punctuation boundaries.
    """
    raw_tts = strip_kasreh(beat_spoken_text(beat))
    if not raw_tts:
        return []

    beat_s = float(beat.get("s", 0.0))
    beat_e = float(beat.get("e", beat_s + 3.0))
    aligned = align_tts_tokens(raw_tts, beat.get("words", []), beat_s, beat_e)
    n = len(aligned)
    if n == 0:
        return []

    cues: list[tuple[float, float, str]] = []
    cue_start_idx = 0

    for k in range(n - 1):
        tok = aligned[k]["tok"]
        cue_len = k - cue_start_idx + 1
        rem_len = n - 1 - k
        gap = aligned[k + 1]["s"] - aligned[k]["e"]

        strong_punct = tok.endswith(("؟", "?", "؛", ";", ":", "!", "."))
        comma_punct = tok.endswith(("،", ","))

        c_s_cand = beat_s if cue_start_idx == 0 else aligned[cue_start_idx]["s"]
        cand_dur = aligned[k]["e"] - c_s_cand

        should_split = False
        if rem_len >= 3 and cue_len >= 2 and cand_dur >= 0.75:
            if gap >= 0.30 and cue_len >= 3:
                should_split = True
            elif strong_punct and (cue_len >= 3 or gap >= 0.14):
                should_split = True
            elif comma_punct and cue_len >= 6:
                should_split = True
            elif cue_len >= 11:
                should_split = True

        if should_split:
            c_s = c_s_cand
            c_e = min(aligned[k + 1]["s"] - 0.02, aligned[k]["e"] + 0.06)
            c_e = max(c_s + 0.35, c_e)
            text = " ".join(x["tok"] for x in aligned[cue_start_idx : k + 1])
            cues.append((c_s, c_e, text))
            cue_start_idx = k + 1

    c_s = beat_s if cue_start_idx == 0 else aligned[cue_start_idx]["s"]
    c_e = max(c_s + 0.35, beat_e)
    text = " ".join(x["tok"] for x in aligned[cue_start_idx:])
    cues.append((c_s, c_e, text))
    return cues


def build_srt(beats: list[dict]) -> str:
    raw_cues: list[tuple[float, float, str]] = []
    for b in beats:
        raw_cues.extend(split_beat_into_srt_cues(b))

    # Guarantee strictly non-overlapping SRT cues across the entire timeline
    clean_cues: list[tuple[float, float, str]] = []
    for idx, (c_s, c_e, text) in enumerate(raw_cues):
        if clean_cues and c_s < clean_cues[-1][1] + 0.02:
            c_s = clean_cues[-1][1] + 0.02
        if idx + 1 < len(raw_cues) and c_e > raw_cues[idx + 1][0] - 0.02:
            c_e = max(c_s + 0.30, raw_cues[idx + 1][0] - 0.02)
        c_e = max(c_s + 0.30, c_e)
        clean_cues.append((c_s, c_e, text))

    blocks = []
    for cue_num, (c_s, c_e, text) in enumerate(clean_cues, start=1):
        blocks.append(f"{cue_num}\n{fmt_srt_time(c_s)} --> {fmt_srt_time(c_e)}\n{text}\n")
    return "\n".join(blocks)


def build_human_recording_script(beats: list[dict]) -> str:
    """
    Clean teleprompter script for human microphone / mobile recording.
    Strips heavy TTS kasrehs for effortless human reading and marks natural breath pauses.
    """
    header = [
        "=== متن خوانش گوینده (مناسب ضبط با میکروفون یا موبایل) ===",
        "راهنما: با لحن طبیعی و محاوره‌ایِ جدی بخوانید. بین هر بخش فقط یک نفس کوتاه (حدود نیم ثانیه) مکث کنید؛",
        "سکوت‌های ابتدای ضبط، انتهای ضبط و مکث‌های طولانی بین بخش‌ها به‌طور خودکار توسط اسکیل تمیز می‌شوند.",
        "------------------------------------------------------------",
        "",
    ]
    body = []
    for idx, b in enumerate(beats, start=1):
        clean_line = strip_kasreh(beat_spoken_text(b))
        if not clean_line:
            continue
        body.append(f"[{to_fa_digits(idx)}] {clean_line}")
        if idx < len(beats):
            body.append("    (مکث کوتاه / نفس)")
            body.append("")
    return "\n".join(header + body) + "\n"


def format_beat_for_elevenlabs(beat: dict, family: str) -> str:
    """
    Formats a single spoken beat for ElevenLabs Playground while KEEPING Persian kasreh (\u0650)
    and written-out numbers for accurate pronunciation:
      - family == 'v2':    Multilingual v2 & Flash/Turbo v2.5 (`...` and `-` micro-pauses)
      - family == 'v3_v4': Eleven v3 & Eleven v4 (`[short pause]`, `...`, and `—` micro-pauses; NO SSML)
    """
    raw_tts = beat_spoken_text(beat)
    if not raw_tts:
        return ""

    has_words = bool(beat.get("words"))
    beat_s = float(beat.get("s", 0.0))
    beat_e = float(beat.get("e", beat_s + max(2.5, len(raw_tts.split()) * 0.34)))
    aligned = align_tts_tokens(raw_tts, beat.get("words", []), beat_s, beat_e)
    n = len(aligned)
    if n == 0:
        return raw_tts

    contrast_starters = {"بلکه", "اما", "ولی"}
    out_parts: list[str] = []
    clause_words = 0

    for k, item in enumerate(aligned):
        tok = item["tok"]
        clause_words += 1
        is_last = k == n - 1
        if is_last:
            out_parts.append(tok)
            continue

        gap = (aligned[k + 1]["s"] - item["e"]) if has_words else 0.25
        next_clean = norm_word(aligned[k + 1]["tok"])
        rem_words = n - 1 - k

        if tok.endswith(("؟", "?")):
            if family == "v2":
                out_parts.append(f"{tok} ...")
            else:
                out_parts.append(f"{tok} [short pause]" if (not has_words or gap >= 0.35) else f"{tok}...")
            clause_words = 0

        elif tok.endswith(":"):
            stem = tok[:-1]
            if family == "v2":
                out_parts.append(f"{stem} ...")
            else:
                out_parts.append(f"{stem}... [short pause]" if gap >= 0.30 else f"{stem}...")
            clause_words = 0

        elif tok.endswith(("؛", ";")):
            stem = tok[:-1]
            if next_clean in contrast_starters and gap >= 0.12:
                out_parts.append(f"{stem} ..." if family == "v2" else f"{stem}...")
            else:
                out_parts.append(f"{stem} -" if family == "v2" else f"{stem} —")
            clause_words = 0

        elif tok.endswith(("،", ",")):
            if clause_words >= 5 and rem_words >= 3:
                stem = tok[:-1]
                out_parts.append(f"{stem} -" if family == "v2" else f"{stem} —")
                clause_words = 0
            else:
                out_parts.append(tok)

        elif has_words and gap >= 0.48 and rem_words >= 2:
            out_parts.append(f"{tok} -" if family == "v2" else f"{tok} [short pause]")
            clause_words = 0

        else:
            out_parts.append(tok)

    return " ".join(out_parts)


def inter_beat_gap(beats: list[dict], idx: int) -> float:
    b = beats[idx]
    if "pause_after" in b:
        return max(0.20, float(b["pause_after"]))
    if "e" in b and idx + 1 < len(beats) and "s" in beats[idx + 1]:
        return max(0.20, float(beats[idx + 1]["s"]) - float(b["e"]))
    if "e" in b and "scene_end" in b:
        return max(0.20, float(b["scene_end"]) - float(b["e"]))
    return 0.25


def build_elevenlabs_v2(beats: list[dict]) -> str:
    lines: list[str] = []
    for idx, b in enumerate(beats):
        formatted = format_beat_for_elevenlabs(b, family="v2")
        if not formatted:
            continue
        lines.append(formatted)
        if idx < len(beats) - 1:
            gap = inter_beat_gap(beats, idx)
            brk = min(3.0, max(0.5, round(gap + 0.25, 1)))
            lines.append(f'<break time="{brk:.1f}s" />')
    return "\n".join(lines) + "\n"


def build_elevenlabs_v3_v4(beats: list[dict]) -> str:
    lines: list[str] = []
    for idx, b in enumerate(beats):
        formatted = format_beat_for_elevenlabs(b, family="v3_v4")
        if not formatted:
            continue
        lines.append(formatted)
        if idx < len(beats) - 1:
            gap = inter_beat_gap(beats, idx)
            tag = "[long pause]" if gap >= 0.42 else "[pause]"
            lines.append(tag)
    return "\n".join(lines) + "\n"


def export_scripts_from_beats(beats_path: Path, out_dir: Path, base_name: str) -> tuple[Path, Path, Path] | None:
    """
    Phase-1 Pre-Production exporter (runs BEFORE any audio or video exists!).
    Generates human teleprompter script + ElevenLabs v2 + ElevenLabs v3/v4 scripts from beats.json.
    """
    with open(beats_path, encoding="utf-8-sig") as f:
        cfg = json.load(f)

    beats = cfg.get("beats", []) if isinstance(cfg, dict) else (cfg if isinstance(cfg, list) else [])
    cfg_voice = str(cfg.get("voice", "")).strip().lower() if isinstance(cfg, dict) else ""
    if cfg_voice in {"none", "off", "silent", "voice_free", "voice-free"} or not any(beat_spoken_text(b) for b in beats):
        print("[SKIP] Voice-free scenario detected in beats.json — skipping voiceover script export.")
        return None

    out_dir.mkdir(parents=True, exist_ok=True)

    rec_path = out_dir / f"{base_name}_recording_script.txt"
    v2_path = out_dir / f"{base_name}_elevenlabs_v2.txt"
    v3_v4_path = out_dir / f"{base_name}_elevenlabs_v3_v4.txt"

    rec_path.write_text(build_human_recording_script(beats), encoding="utf-8")
    v2_path.write_text(build_elevenlabs_v2(beats), encoding="utf-8")
    v3_v4_path.write_text(build_elevenlabs_v3_v4(beats), encoding="utf-8")

    print(f"[PRE-PROD] Human Recording Script       -> {rec_path}")
    print(f"[PRE-PROD] ElevenLabs (v2 / Flash v2.5) -> {v2_path}")
    print(f"[PRE-PROD] ElevenLabs (Eleven v3 / v4)  -> {v3_v4_path}")
    return rec_path, v2_path, v3_v4_path


def export_all_from_timeline(timeline_path: Path, out_dir: Path, base_name: str) -> tuple[Path, Path, Path, Path] | None:
    with open(timeline_path, encoding="utf-8-sig") as f:
        tl = json.load(f)

    beats = tl.get("beats", [])
    if tl.get("voice_mode") == "voice_free_svg_showcase" or not any(beat_spoken_text(b) for b in beats):
        print("[SKIP] Voice-free timeline detected — skipping empty .srt and voiceover scripts.")
        return None

    out_dir.mkdir(parents=True, exist_ok=True)

    srt_path = out_dir / f"{base_name}.srt"
    rec_path = out_dir / f"{base_name}_recording_script.txt"
    v2_path = out_dir / f"{base_name}_elevenlabs_v2.txt"
    v3_v4_path = out_dir / f"{base_name}_elevenlabs_v3_v4.txt"

    srt_path.write_text(build_srt(beats), encoding="utf-8")
    rec_path.write_text(build_human_recording_script(beats), encoding="utf-8")
    v2_path.write_text(build_elevenlabs_v2(beats), encoding="utf-8")
    v3_v4_path.write_text(build_elevenlabs_v3_v4(beats), encoding="utf-8")

    print(f"[EXPORT] Verbatim SRT                  -> {srt_path}")
    print(f"[EXPORT] Human Recording Script        -> {rec_path}")
    print(f"[EXPORT] ElevenLabs (v2 / Flash v2.5)  -> {v2_path}")
    print(f"[EXPORT] ElevenLabs (Eleven v3 / v4)   -> {v3_v4_path}")
    return srt_path, rec_path, v2_path, v3_v4_path


def main():
    parser = argparse.ArgumentParser(
        description="Export pre-production voiceover scripts (from beats.json) or full verbatim .srt + scripts (from timeline.json)."
    )
    parser.add_argument("--from-beats", default=None, help="Pre-production mode: path to beats.json (before audio exists).")
    parser.add_argument("--timeline", default="src/timeline.json", help="Post-audio mode: path to timeline.json.")
    parser.add_argument("--out-dir", default="exports", help="Directory to write exported script files.")
    parser.add_argument("--name", default="reel_script", help="Base filename stem.")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    if args.from_beats:
        bp = Path(args.from_beats)
        if not bp.exists():
            raise FileNotFoundError(f"beats.json not found: {bp}")
        export_scripts_from_beats(bp, out_dir, args.name)
        return

    tl_path = Path(args.timeline)
    if not tl_path.exists():
        # Smart auto-fallback to beats.json if timeline.json doesn't exist yet!
        bp = Path("beats.json")
        if bp.exists():
            export_scripts_from_beats(bp, out_dir, args.name)
            return
        raise FileNotFoundError(f"Timeline file not found: {tl_path}")

    export_all_from_timeline(tl_path, out_dir, args.name)


if __name__ == "__main__":
    main()

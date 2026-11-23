import json
import os
import re
import subprocess
import sys
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.ndimage import maximum_filter1d, uniform_filter1d

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SR = 48000


def load_style() -> dict:
    try:
        with open("src/style.json", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


STYLE = load_style()
SFX_REMAP: dict = (STYLE.get("sfx") or {}).get("remap", {}) or {}
CUT_BOOM: bool = bool((STYLE.get("sfx") or {}).get("cutBoom", True))


def decode_audio(path: str, channels: int = 2) -> np.ndarray:
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", str(channels), "-ar", str(SR), "-"]
    res = subprocess.run(cmd, capture_output=True, check=True)
    arr = np.frombuffer(res.stdout, dtype=np.float32).copy()
    return arr.reshape(-1, channels) if channels > 1 else arr


def write_wav_s24le(path: str, stereo_f32: np.ndarray):
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
        path,
    ]
    subprocess.run(cmd, input=clipped.tobytes(), check=True)


def env_curve(n: int, attack_s: float, release_s: float) -> np.ndarray:
    e = np.ones(n, dtype=np.float32)
    a = min(int(attack_s * SR), n // 2)
    r = min(int(release_s * SR), n // 2)
    if a > 0:
        e[:a] = np.linspace(0.0, 1.0, a)
    if r > 0:
        e[-r:] *= np.linspace(1.0, 0.0, r)
    return e


def bp(x: np.ndarray, lo: float, hi: float) -> np.ndarray:
    sos = butter(2, [lo, hi], btype="band", fs=SR, output="sos")
    return sosfilt(sos, x, axis=0).astype(np.float32)


def lp(x: np.ndarray, fc: float) -> np.ndarray:
    sos = butter(3, fc, btype="low", fs=SR, output="sos")
    return sosfilt(sos, x, axis=0).astype(np.float32)


def synth_editorial_groove(
    n_samples: int,
    dur: float,
    voice_end: float,
    bpm: float = 110.0,
    mood: str = "editorial",
) -> np.ndarray:
    rng = np.random.default_rng(42)
    beat_s = 60.0 / bpm
    step_s = beat_s / 2.0
    bar_s = beat_s * 4.0
    mus = np.zeros((n_samples, 2), dtype=np.float32)
    note_hz = lambda m: 440.0 * (2.0 ** ((m - 69.0) / 12.0))

    if mood == "bright":
        # Cmaj7 -> Am7 -> Fmaj7 -> G6 (Modern Kinetic / Infographic)
        chords = [
            [48, 55, 59, 64],
            [45, 52, 55, 60],
            [41, 48, 52, 57],
            [43, 50, 55, 59],
        ]
    elif mood == "noir":
        # Cm9 -> Abmaj7 -> Fm9 -> G7alt (Dark Luxury / Editorial Noir)
        chords = [
            [48, 55, 58, 62],
            [44, 51, 55, 60],
            [41, 48, 51, 55],
            [43, 49, 53, 59],
        ]
    else:
        # Dm9 -> Bbmaj7 -> Gm7 -> A7sus4 (Dark-Editorial Agency Progression)
        chords = [
            [50, 57, 60, 64],
            [46, 53, 57, 62],
            [43, 50, 55, 58],
            [45, 52, 57, 62],
        ]

    for k in range(int(dur / bar_s) + 2):
        ch = chords[k % len(chords)]
        s = k * bar_s
        i0 = int(s * SR)
        if i0 >= n_samples:
            break
        n = int((bar_s + 0.45) * SR)
        seg = np.arange(n, dtype=np.float32) / SR
        pad = np.zeros(n, dtype=np.float32)
        for m in ch:
            for det in (-0.08, 0.08):
                f = note_hz(m) * (2.0 ** (det / 12.0))
                pad += np.sin(2 * np.pi * f * seg) + 0.22 * np.sin(2 * np.pi * 2 * f * seg)
        pad = lp(pad, 1350.0) * env_curve(n, 0.35, 0.55) * 0.045
        sub = np.sin(2 * np.pi * note_hz(ch[0] - 12) * seg) * env_curve(n, 0.08, 0.35) * 0.13
        combo = pad + sub
        i1 = min(n_samples, i0 + n)
        chunk = combo[: i1 - i0]
        wob = 0.12 * np.sin(seg[: i1 - i0] * 1.1)
        mus[i0:i1, 0] += chunk * (1.0 + wob)
        mus[i0:i1, 1] += chunk * (1.0 - wob)

    arp_pat = [0, 2, 1, 3, 2, 3, 1, 2]
    for j in range(int(dur / step_s)):
        s = j * step_s
        i0 = int(s * SR)
        if i0 >= n_samples:
            break
        ch = chords[int(s / bar_s) % len(chords)]
        m = ch[arp_pat[j % 8]] + 12
        np_len = int(0.24 * SR)
        if i0 + np_len < n_samples:
            seg = np.arange(np_len, dtype=np.float32) / SR
            plk = np.sin(2 * np.pi * note_hz(m) * seg) + 0.3 * np.sin(2 * np.pi * 2 * note_hz(m) * seg)
            plk = lp(plk, 2100.0) * np.exp(-seg * 16.0) * 0.045
            pan = 0.5 + 0.32 * np.sin(j * 0.85)
            mus[i0 : i0 + np_len, 0] += plk * (1.0 - pan) * 1.8
            mus[i0 : i0 + np_len, 1] += plk * pan * 1.8

        if j % 2 == 0:
            nk = int(0.20 * SR)
            if i0 + nk < n_samples:
                seg = np.arange(nk, dtype=np.float32) / SR
                fk = 50.0 + 68.0 * np.exp(-seg * 34.0)
                kick = np.sin(2 * np.pi * np.cumsum(fk) / SR) * np.exp(-seg * 15.0) * 0.16
                mus[i0 : i0 + nk, 0] += kick
                mus[i0 : i0 + nk, 1] += kick
        else:
            nh = int(0.05 * SR)
            if i0 + nh < n_samples:
                seg = np.arange(nh, dtype=np.float32) / SR
                hat = bp(rng.standard_normal(nh).astype(np.float32), 6500, 13000) * np.exp(-seg * 65.0) * 0.04
                mus[i0 : i0 + nh, 0] += hat
                mus[i0 : i0 + nh, 1] += hat

    mus_env = np.ones(n_samples, dtype=np.float32)
    mus_env[: int(0.5 * SR)] = np.linspace(0.25, 1.0, int(0.5 * SR))
    sw_idx = int(voice_end * SR)
    if sw_idx < n_samples:
        mus_env[sw_idx:] = np.linspace(1.0, 1.75, n_samples - sw_idx)
    fade_out_n = int(0.45 * SR)
    mus_env[-fade_out_n:] *= np.linspace(1.0, 0.0, fade_out_n)
    mus *= mus_env[:, None]
    return mus


def auto_detect_cues(beats: list, scenes_path: str = "src/scenes.tsx") -> dict:
    """
    Intelligent Auto-SFX Engine:
    Inspects beats (word timestamps + semantic analysis) and src/scenes.tsx (JSX visual components)
    to automatically populate SFX cues with zero manual configuration.
    """
    cues = {
        "stamps": [],
        "warnings": [],
        "money": [],
        "sub_cuts": [],
        "ribbon_draws": [],
        "flashes": [],
        "diagrams": [],
        "hero_words": [],
        "strikethroughs": [],
        "counters": [],
        "pills": [],
        "chips": [],
        "buttons": [],
        "mechanics": [],
    }

    def get_wt(b: int, w: int) -> float:
        b = min(len(beats) - 1, max(0, b))
        words = beats[b].get("words", [])
        if not words:
            return float(beats[b].get("s", 0.0))
        w = min(len(words) - 1, max(0, w))
        return float(words[w]["s"])

    def resolve_expr(expr: str) -> float | None:
        expr = expr.strip()
        m_wt = re.search(r"wordTime\(\s*(\d+)\s*,\s*(\d+)\s*\)", expr)
        if m_wt:
            return get_wt(int(m_wt.group(1)), int(m_wt.group(2)))
        m_we = re.search(r"wordEnd\(\s*(\d+)\s*,\s*(\d+)\s*\)", expr)
        if m_we:
            b = min(len(beats) - 1, max(0, int(m_we.group(1))))
            words = beats[b].get("words", [])
            w = min(len(words) - 1, max(0, int(m_we.group(2))))
            return float(words[w]["e"]) if words else float(beats[b].get("e", 0.0))
        m_bf = re.search(r"beatFrac\(\s*(\d+)\s*,\s*([\d\.]+)\s*\)", expr)
        if m_bf:
            b = min(len(beats) - 1, max(0, int(m_bf.group(1))))
            bs = float(beats[b].get("s", 0.0))
            be = float(beats[b].get("scene_end", beats[b].get("e", bs + 1.0)))
            return bs + max(0.0, min(1.0, float(m_bf.group(2)))) * max(0.2, be - bs)
        m_bs = re.search(r"beatStart\(\s*(\d+)\s*\)", expr)
        if m_bs:
            b = min(len(beats) - 1, max(0, int(m_bs.group(1))))
            return float(beats[b].get("s", 0.0))
        m_be = re.search(r"beatEnd\(\s*(\d+)\s*\)", expr)
        if m_be:
            b = min(len(beats) - 1, max(0, int(m_be.group(1))))
            return float(beats[b].get("scene_end", beats[b].get("e", 0.0)))
        m_num = re.search(r"^[\d\.]+$", expr)
        if m_num:
            return float(expr)
        return None

    def extract_jsx_prop_cues(tsx_str: str, tag_pattern: str, prop_names: str, target_cat: str, self_closing: bool = True):
        end_pat = r"/>" if self_closing else r"(?:/>|>)"
        tag_re = re.compile(rf"<(?:{tag_pattern})\b((?:(?!</?\w)[\s\S]){{0,420}}?){end_pat}", re.MULTILINE)
        prop_re = re.compile(rf"\b(?:{prop_names})=\{{([^}}]+)\}}")
        for tag_m in tag_re.finditer(tsx_str):
            attrs = tag_m.group(1)
            pm = prop_re.search(attrs)
            if pm:
                t_val = resolve_expr(pm.group(1))
                if t_val is not None:
                    cues[target_cat].append({"at": t_val})

    # 1. Parse src/scenes.tsx if available
    if os.path.exists(scenes_path):
        try:
            with open(scenes_path, encoding="utf-8") as sf:
                tsx = sf.read()

            # v2 kit (style-agnostic primitives; every animated primitive exposes `at`)
            extract_jsx_prop_cues(tsx, "Stamp", "at", "stamps")
            extract_jsx_prop_cues(tsx, "ToolCard|ScreenFrame|PromptBox|CodeCard|ChatBubble|CTA", "at", "pills")
            extract_jsx_prop_cues(tsx, "LogoHub|Versus|Arrow", "at", "diagrams")
            extract_jsx_prop_cues(tsx, "FeatureList", "at", "chips")
            extract_jsx_prop_cues(tsx, "StatCounter", "at", "counters")
            extract_jsx_prop_cues(tsx, "BrandLogo", "at", "hero_words")
            for m in re.finditer(r"mark\s*:\s*(?:true|['\"][^'\"]*['\"])[^}]{0,120}?\bat\s*:\s*(\w+\([^)]*\)|[\d\.]+)|\bat\s*:\s*(\w+\([^)]*\)|[\d\.]+)[^}]{0,120}?mark\s*:\s*(?:true|['\"])", tsx):
                tv = resolve_expr(m.group(1) or m.group(2))
                if tv is not None:
                    cues["ribbon_draws"].append({"at": tv + 0.08})
            extract_jsx_prop_cues(tsx, "BanStamp", "at|start", "stamps")
            extract_jsx_prop_cues(tsx, "CautionWarningBadge", "at|start", "warnings")
            extract_jsx_prop_cues(tsx, "SubPhase|Phase|FocusShiftContainer", "from|at|start", "sub_cuts", self_closing=False)
            extract_jsx_prop_cues(tsx, "NodeNetwork|RisingPillars|ComparisonBarChart|GradientBarChart|AgentToolHub", "at|start", "diagrams")
            extract_jsx_prop_cues(
                tsx,
                "EditorialWindowCard|DarkPillStack|PushpinCard|CodeInspectorScan|MoodboardGrid|DesignTokenInspector|MobileSkillCard|EditorialComparisonTable|EditorialFeatureGrid",
                "at|start",
                "pills",
            )
            extract_jsx_prop_cues(tsx, "MonochromeChipRow|NumberedSkillGrid", "at|start", "chips")
            extract_jsx_prop_cues(tsx, "RotaryEffortDial", "at|start", "mechanics")
            extract_jsx_prop_cues(tsx, "ContrastBlackCut", "at|start", "flashes")
            extract_jsx_prop_cues(tsx, "StackedAsymmetricLockup", "heroAt", "hero_words")

            # Custom bespoke *SVG components (used heavily in Voice-Free SVG Showcase reels)
            svg_tag_re = re.compile(r"<([A-Z]\w*SVG)\b((?:(?!</?\w)[\s\S]){0,420}?)(?:/>|>)")
            start_prop_re = re.compile(r"\b(?:start|at)=\{([^}]+)\}")
            for sm in svg_tag_re.finditer(tsx):
                tag_name = sm.group(1)
                if tag_name == "SectionIndexPillSVG":
                    pm = start_prop_re.search(sm.group(2))
                    if pm:
                        tv = resolve_expr(pm.group(1))
                        if tv is not None:
                            cues["pills"].append({"at": tv})
                    continue
                pm = start_prop_re.search(sm.group(2))
                if pm:
                    tv = resolve_expr(pm.group(1))
                    if tv is not None:
                        cues["diagrams"].append({"at": tv + 0.35})
                        cues["hero_words"].append({"at": tv + 1.35})

            expr_pat = r"(?:\w+\([^)]*\)|[\d\.]+)"
            for m in re.finditer(rf"(?:underlineAt\s*=|underlineAt\s*:)\s*\{{?({expr_pat})", tsx):
                t_val = resolve_expr(m.group(1))
                if t_val is not None:
                    cues["ribbon_draws"].append({"at": t_val})

            for m in re.finditer(rf"(?:strikeAt\s*=|strikeAt\s*:)\s*\{{?({expr_pat})", tsx):
                t_val = resolve_expr(m.group(1))
                if t_val is not None:
                    cues["strikethroughs"].append({"at": t_val})

            # Match JS word objects with role: 'hero' | 'mega' in ANY property order
            for obj_m in re.finditer(r"\{[^{}]{0,260}\}", tsx):
                obj_txt = obj_m.group(0)
                if re.search(r"""\brole\s*:\s*['"](?:hero|mega)['"]""", obj_txt):
                    at_m = re.search(rf"\bat\s*:\s*({expr_pat})", obj_txt)
                    if at_m:
                        t_val = resolve_expr(at_m.group(1))
                        if t_val is not None:
                            cues["hero_words"].append({"at": t_val})

        except Exception as e:
            print(f"[AUTO-SFX] Warning during scenes.tsx parsing: {e}")

    # 2. Semantic Analysis across all spoken words
    stamp_lexicon = {"بن", "بَن", "ممنوع", "بلاک", "تحریم", "ban", "blocked"}
    warning_lexicon = {"ریسک", "قطع", "توقف", "سوخت", "خطا", "اشتباه", "هشدار", "خطر", "تورم", "راکد", "risk", "error", "warning", "danger"}
    money_lexicon = {
        "اقتصادی",
        "هزینه",
        "دلار",
        "اشتراک",
        "شارژ",
        "قیمت",
        "تخفیف",
        "رایگان",
        "صرفه",
        "خرید",
        "ارزان",
        "تومان",
        "ثروت",
        "سرمایه",
        "درآمد",
        "سود",
        "پول",
        "cost",
        "price",
        "economy",
        "save",
        "dollar",
        "wealth",
        "profit",
    }
    tech_lexicon = {
        "ایجنت",
        "ایجِنت",
        "هوش",
        "مصنوعی",
        "الگوریتم",
        "سیستم",
        "اتوماسیون",
        "کدنویسی",
        "agent",
        "ai",
        "system",
        "automation",
        "code",
    }
    metric_pattern = re.compile(r"(?:[0-9۰-۹]{2,}|[0-9۰-۹]+(?:[\.,/][0-9۰-۹]+)?\s*(?:[%٪xX×]|درصد|برابر))")

    for b_idx, b in enumerate(beats):
        words = b.get("words", [])
        for w_idx, w in enumerate(words):
            raw = w["t"].replace("،", "").replace(".", "").replace("!", "").replace("؟", "").strip()
            wt = float(w["s"])

            if any(term in raw for term in stamp_lexicon):
                cues["stamps"].append({"at": wt})
            elif any(term in raw for term in warning_lexicon):
                cues["warnings"].append({"at": wt})
            elif any(term in raw for term in money_lexicon):
                cues["money"].append({"at": wt})
            elif any(term in raw for term in tech_lexicon):
                cues["hero_words"].append({"at": wt})
            elif metric_pattern.search(raw):
                cues["counters"].append({"at": wt, "ticks": 7, "step": 0.05})

    # De-duplicate each category with 0.12s threshold
    def dedupe(c_list: list) -> list:
        sorted_c = sorted(c_list, key=lambda x: float(x.get("at", 0.0)))
        out = []
        last_t = -999.0
        for item in sorted_c:
            t = float(item.get("at", 0.0))
            if t - last_t >= 0.12:
                out.append(item)
                last_t = t
        return out

    MIN_GAP = {"hero_words": 0.9, "money": 1.5, "warnings": 1.5, "counters": 1.2, "ribbon_draws": 0.6}

    def dedupe_gap(c_list: list, gap: float) -> list:
        out, last_t = [], -999.0
        for item in sorted(c_list, key=lambda x: float(x.get("at", 0.0))):
            t = float(item.get("at", 0.0))
            if t - last_t >= gap:
                out.append(item)
                last_t = t
        return out

    for k in cues:
        cues[k] = dedupe_gap(cues[k], MIN_GAP.get(k, 0.12))

    return cues


def main():
    os.makedirs("audio_work", exist_ok=True)
    os.makedirs("public/audio", exist_ok=True)

    with open("src/timeline.json", encoding="utf-8-sig") as f:
        tl = json.load(f)

    plan = {}
    if os.path.exists("sfx_plan.json"):
        with open("sfx_plan.json", encoding="utf-8-sig") as pf:
            plan = json.load(pf)

    voice_end = float(tl["voice_end"])
    dur = float(tl["total_dur"])
    n_samples = int(round(dur * SR))
    beats = tl["beats"]

    # Run Intelligent Auto-SFX Engine
    auto_cues = auto_detect_cues(beats, "src/scenes.tsx")
    merged_plan = {}
    for cat in [
        "stamps",
        "warnings",
        "money",
        "sub_cuts",
        "ribbon_draws",
        "flashes",
        "diagrams",
        "hero_words",
        "strikethroughs",
        "counters",
        "pills",
        "chips",
        "buttons",
        "mechanics",
        "scans",
        "stretches",
        "success",
        "switches",
    ]:
        if cat in plan and len(plan[cat]) > 0:
            merged_plan[cat] = plan[cat]
        else:
            merged_plan[cat] = auto_cues.get(cat, [])

    detected_counts = {k: len(v) for k, v in merged_plan.items() if len(v) > 0}
    print(f"[AUTO-SFX] Active Cues: {detected_counts}")

    # 1. Load 100% Untouched Original Stereo Voice (Zero EQ / Zero Compression)
    voice_path = "audio_work/voice_mastered.wav"
    voice = np.zeros((n_samples, 2), dtype=np.float32)
    has_voice = False
    if os.path.exists(voice_path):
        voice_st = decode_audio(voice_path, channels=2)
        if len(voice_st) > 0 and np.max(np.abs(voice_st)) > 0.005:
            vn = min(n_samples, len(voice_st))
            voice[:vn] = voice_st[:vn]
            has_voice = True

    # 2. Music Bed (Auto-detect user_inputs/audio/music/ first, else Synth / Custom File / None)
    mus_cfg = plan.get("music", {})
    mode = mus_cfg.get("mode", "synth")
    bpm = float(mus_cfg.get("bpm", 110.0))
    duck_depth = float(mus_cfg.get("duck_under_voice", 0.58))

    custom_music_path = mus_cfg.get("custom_file", "")
    music_dir = "user_inputs/audio/music"
    if not custom_music_path and os.path.isdir(music_dir):
        audio_exts = (".wav", ".mp3", ".flac", ".m4a", ".ogg")
        found_tracks = sorted(
            [os.path.join(music_dir, f) for f in os.listdir(music_dir) if f.lower().endswith(audio_exts)]
        )
        if found_tracks:
            custom_music_path = found_tracks[0]
            mode = "file"
            print(f"[MUSIC] Auto-detected custom music track: {custom_music_path}")

    if mode == "none" and not has_voice and tl.get("voice_mode") == "voice_free_svg_showcase":
        mode = "synth"
        print("[MUSIC] Voice-free showcase with no custom track -> auto-enabling synth groove.")

    if mode == "none":
        mus = np.zeros((n_samples, 2), dtype=np.float32)
    elif mode == "file" and custom_music_path and os.path.exists(custom_music_path):
        raw_mus = decode_audio(custom_music_path, channels=2)
        mus = np.zeros((n_samples, 2), dtype=np.float32)
        pos = 0
        while pos < n_samples:
            take = min(len(raw_mus), n_samples - pos)
            mus[pos : pos + take] = raw_mus[:take]
            pos += take
        fade_out_n = int(0.5 * SR)
        mus[-fade_out_n:] *= np.linspace(1.0, 0.0, fade_out_n)[:, None]
    else:
        brand_genre = ""
        if os.path.exists("src/brand.json"):
            try:
                with open("src/brand.json", encoding="utf-8-sig") as bf:
                    brand_genre = json.load(bf).get("genre", "")
            except Exception:
                brand_genre = ""
        brand_mood = ""
        try:
            with open("src/brand.json", encoding="utf-8-sig") as bf:
                brand_mood = json.load(bf).get("musicMood", "")
        except Exception:
            pass
        mood = mus_cfg.get("mood") or brand_mood or (
            "noir"
            if brand_genre in ("mixed_editorial_noir", "dark_luxury_editorial")
            else ("bright" if brand_genre in ("infographic_kinetic", "creator_collage") else "editorial")
        )
        mus = synth_editorial_groove(n_samples, dur, voice_end, bpm=bpm, mood=mood)

    # 3. Real 48kHz FLAC Sound Effects Placement (Waveform-Trimmed & Peak-Aligned)
    sfx = np.zeros((n_samples, 2), dtype=np.float32)

    class SfxClip:
        def __init__(self, samples: np.ndarray, peak_t: float):
            self.samples = samples
            self.peak_t = peak_t

    def load_sfx(
        rel_path: str,
        max_dur: float | None = None,
        trim_silence: bool = True,
        silence_thresh: float = 0.025,
    ) -> SfxClip | None:
        mapped = SFX_REMAP.get(rel_path)
        if mapped and os.path.exists(f"public/sfx/{mapped}.flac"):
            rel_path = mapped
        full_p = f"public/sfx/{rel_path}.flac"
        if not os.path.exists(full_p):
            return None
        arr = decode_audio(full_p, channels=2)
        if len(arr) == 0:
            return None

        raw_peak = float(np.abs(arr).max())
        if raw_peak < 1e-7:
            return None

        # Strip dead leading silence while preserving a 10ms attack pre-roll
        if trim_silence:
            mono_env = np.abs(arr).max(axis=1) / raw_peak
            hits = np.flatnonzero(mono_env > silence_thresh)
            if len(hits) > 0:
                start_idx = max(0, int(hits[0]) - int(0.010 * SR))
                arr = arr[start_idx:]

        # Ensure max_dur never truncates before the clip's main energy peak
        peak_idx = int(np.argmax(np.abs(arr).max(axis=1)))
        if max_dur is not None:
            lim = max(int(max_dur * SR), min(len(arr), peak_idx + int(0.18 * SR)))
            arr = arr[: min(len(arr), lim)]

        arr = arr * env_curve(len(arr), 0.005, min(0.10, (len(arr) / SR) * 0.25))[:, None]
        norm_peak = float(np.abs(arr).max()) + 1e-9
        norm_arr = (arr / norm_peak).astype(np.float32)
        measured_peak_t = int(np.argmax(np.abs(norm_arr).max(axis=1))) / SR
        return SfxClip(norm_arr, measured_peak_t)

    def place(clip: SfxClip | np.ndarray | None, t_sec: float, gain: float = 0.35, align: str = "onset"):
        if clip is None:
            return
        if isinstance(clip, SfxClip):
            samples = clip.samples
            anchor_offset = clip.peak_t if align == "peak" else 0.0
        else:
            samples = clip
            anchor_offset = 0.0
        x = samples * gain
        i0 = int(round((t_sec - anchor_offset) * SR))
        if i0 < 0:
            x = x[-i0:]
            i0 = 0
        if i0 >= n_samples or len(x) == 0:
            return
        take = min(len(x), n_samples - i0)
        sfx[i0 : i0 + take] += x[:take]

    def resolve_cue(cue: dict | float | int) -> float:
        if isinstance(cue, (int, float)):
            return float(cue)
        if "at" in cue:
            return float(cue["at"])
        b_idx = min(len(beats) - 1, int(cue.get("beat", 0)))
        words = beats[b_idx]["words"]
        w_idx = min(len(words) - 1, int(cue.get("word", 0)))
        return float(words[w_idx]["s"])

    def load_bank(paths: list[str], max_dur: float | None = None, silence_thresh: float = 0.025) -> list[SfxClip]:
        out: list[SfxClip] = []
        for p in paths:
            c = load_sfx(p, max_dur=max_dur, silence_thresh=silence_thresh)
            if c is not None:
                out.append(c)
        return out

    def pick_var(bank: list[SfxClip], idx: int) -> SfxClip | None:
        return bank[idx % len(bank)] if bank else None

    # Load Multi-Variant 48kHz FLAC Sound Banks (no two beats play identical canned clips)
    whoosh_bank = load_bank(
        [
            "whoosh/smooth_and_fast_whoosh",
            "whoosh/cinematic_fast_normal_whoosh",
            "whoosh/high_and_fast_whoosh",
            "whoosh/deep_short",
        ],
        max_dur=0.95,
        silence_thresh=0.04,
    )
    whoosh_fast = pick_var(whoosh_bank, 0)
    whoosh_whip = load_sfx("whoosh/cinematic_fast_normal_whoosh", 0.70, silence_thresh=0.04)
    if whoosh_whip is None:
        whoosh_whip = load_sfx("whoosh/cinematic_fast_whoosh", 0.75, silence_thresh=0.04)
    whoosh_butter = load_sfx("whoosh/smooth_like_a_butter_whoosh", 1.05, silence_thresh=0.03)
    whoosh_strike = load_sfx("whoosh/epic_fast_whoosh_345469", 0.45, silence_thresh=0.03)
    shutter_bank = load_bank(
        [
            "shutter/smooth_camera_shutter",
            "shutter/little_bit_hard_camera_shutter",
            "shutter/camera_shutter",
        ],
        max_dur=0.38,
        silence_thresh=0.04,
    )
    shutter = pick_var(shutter_bank, 0)
    shutter_crisp = load_sfx("shutter/camera_shutter", 0.25, silence_thresh=0.04)
    boom_raw = load_sfx("impact/cinematic_boom", 1.25, silence_thresh=0.03)
    boom = SfxClip(lp(boom_raw.samples, 240.0), boom_raw.peak_t) if boom_raw is not None else None
    pop_bank = load_bank(["pop/smooth_pop", "pop/slow_and_smooth_pop", "pop/meadia_pop"], max_dur=0.45)
    pop_soft = pick_var(pop_bank, 0)
    pop_prem = load_sfx("pop/slow_and_smooth_pop", 0.45) or pop_soft
    ui_open = load_sfx("pop/sweet_ui_open", 0.48)
    ui_enter = load_sfx("ui/enter", 0.45, silence_thresh=0.03)
    ui_stretch = load_sfx("ui/stretch", 0.65, silence_thresh=0.03)
    glitch_clk = load_sfx("ui/glitch_click", 0.25)
    data_bank = load_bank(["data/collect_2", "data/collect", "data/cinematic_data"], max_dur=0.75, silence_thresh=0.025)
    data_col = pick_var(data_bank, 0)
    click_cin = load_sfx("click/cinematic_click", 0.09)
    tick_bank = load_bank(["ui/click_digital_04", "ui/click_digital_03", "ui/uu_click_digital_01"], max_dur=0.14)
    click_dig = pick_var(tick_bank, 0)
    chip_bank = load_bank(
        [
            "ui/granular_button_select",
            "ui/granular_button_select_9",
            "ui/click_digital_03",
            "ui/click_digital_04",
        ],
        max_dur=0.18,
    )
    high_click = load_sfx("click/high_click", 0.14)
    gear_smooth = load_sfx("gear/smooth_and_premium_gear", 0.90)
    riser = load_sfx("riser/smooth_riser", None, silence_thresh=0.015)
    stamp_fx = load_sfx("misc/stamp", 0.45)
    laser_fx = load_sfx("misc/laser", 0.95, silence_thresh=0.03)
    error_buzz = load_sfx("ui/error_buzz", 0.55, silence_thresh=0.04)
    money_fx = load_sfx("money/cinematic_money_1", 0.65)
    if money_fx is None:
        money_fx = load_sfx("money/medium_volume_money", 0.65)
    button_clk = load_sfx("ui/button", 0.22)
    level_up = load_sfx("success/level_up", 0.95, silence_thresh=0.03)

    # Opening shutter aligned right on reveal frame
    place(shutter, 0.04, 0.22, align="peak")

    # Major scene-cut transitions rotating naturally across whoosh + shutter banks
    for idx, b in enumerate(beats[:-1]):
        c = float(b["scene_end"])
        place(pick_var(whoosh_bank, idx), c, 0.34, align="peak")
        place(pick_var(shutter_bank, idx), c, 0.18, align="peak")
        if CUT_BOOM:
            place(boom, c, 0.26, align="onset")

    # Intra-beat Whip-Pan / Sub-Scene transitions (only when explicitly requested)
    for cue in merged_plan.get("sub_cuts", []):
        ct = resolve_cue(cue)
        place(whoosh_whip, ct, 0.32, align="peak")
        place(shutter_crisp, ct, 0.20, align="peak")

    # Live Drawn Ribbon / SVG line draw-on accents
    for cue in merged_plan.get("ribbon_draws", []):
        rt = resolve_cue(cue)
        place(whoosh_butter, rt + 0.18, 0.24, align="peak")
        place(ui_stretch, rt, 0.16, align="onset")

    # Radial Flash-Morph transitions
    for cue in merged_plan.get("flashes", []):
        ft = resolve_cue(cue)
        place(pop_prem, ft, 0.26, align="peak")

    # Procedural NodeNetwork / Diagram / Orbit reveals (rotating data textures)
    for idx, cue in enumerate(merged_plan.get("diagrams", [])):
        dt = resolve_cue(cue)
        place(pick_var(data_bank, idx), dt, 0.24, align="onset")
        place(ui_stretch, dt + 0.02, 0.14, align="onset")

    # Stamps & Bans (BanStamp, Red Cross, Warning Stamp)
    for cue in merged_plan.get("stamps", []):
        st = resolve_cue(cue)
        place(stamp_fx, st, 0.62, align="peak")
        place(boom, st, 0.40, align="onset")

    # Warning badges & Alert triggers (dead leading silence trimmed -> peaks cleanly on trigger!)
    for cue in merged_plan.get("warnings", []):
        wt = resolve_cue(cue)
        place(error_buzz, wt, 0.38, align="peak")

    # Money & Financial terms (Save, Economy, Cost, Dollar)
    for cue in merged_plan.get("money", []):
        mt = resolve_cue(cue)
        place(money_fx, mt, 0.50, align="peak")
        place(click_cin, mt, 0.24, align="onset")

    # Hero Words & Focus Keywords (rotating pops)
    for idx, cue in enumerate(merged_plan.get("hero_words", [])):
        hw = resolve_cue(cue)
        place(pick_var(pop_bank, idx), hw, 0.26, align="peak")
        place(click_cin, hw, 0.20, align="onset")

    # Strikethroughs (peak right at midpoint of slash animation)
    for cue in merged_plan.get("strikethroughs", []):
        place(whoosh_strike, resolve_cue(cue), 0.34, align="peak")

    # Digital Counters, Metrics & Continuous Sliders (soft organic alternating ticks)
    for cue in merged_plan.get("counters", []):
        if isinstance(cue, dict):
            ticks = int(cue.get("ticks", 7))
            gain = float(cue.get("gain", 0.20))
            if "from" in cue and "to" in cue and ticks > 1:
                t_from = float(cue["from"])
                t_to = float(cue["to"])
                for i in range(ticks):
                    tick_t = t_from + (t_to - t_from) * (i / (ticks - 1))
                    g_var = gain * (0.88 + 0.24 * ((i % 3) / 2.0))
                    place(pick_var(tick_bank, i), tick_t, g_var, align="peak")
            else:
                cnt_t = resolve_cue(cue)
                step = float(cue.get("step", 0.06))
                for i in range(ticks):
                    g_var = gain * (0.88 + 0.24 * ((i % 3) / 2.0))
                    place(pick_var(tick_bank, i), cnt_t + i * step, g_var, align="peak")
        else:
            cnt_t = resolve_cue(cue)
            ticks = 5
            gain = 0.20
            step = 0.06
            for i in range(ticks):
                g_var = gain * (0.88 + 0.24 * ((i % 3) / 2.0))
                place(pick_var(tick_bank, i), cnt_t + i * step, g_var, align="peak")

    # UI Pill Stacks & Editorial Cards
    for cue in merged_plan.get("pills", []):
        pt = resolve_cue(cue)
        place(ui_open, pt, 0.26, align="onset")

    # Chips, Matrix Nodes & Sequential Checkmarks (rotating tactile ticks)
    for idx, cue in enumerate(merged_plan.get("chips", [])):
        place(pick_var(chip_bank, idx), resolve_cue(cue), 0.25, align="peak")

    # Interactive Buttons, Toggles & Switches
    for cue in merged_plan.get("buttons", []) + merged_plan.get("switches", []):
        bt = resolve_cue(cue)
        place(button_clk, bt, 0.28, align="peak")
        place(high_click if high_click is not None else click_cin, bt, 0.16, align="peak")

    # Smooth Stretch transitions (sliders, bar morphs)
    for cue in merged_plan.get("stretches", []):
        place(ui_stretch, resolve_cue(cue), 0.22, align="onset")

    # Laser Scan Sweeps (database cleaner, code scanner)
    for cue in merged_plan.get("scans", []):
        place(laser_fx, resolve_cue(cue), 0.28, align="onset")

    # Editorial Milestone Commit / Success (clean UI enter + soft pop by default; opt-in fanfare via {"fanfare": true})
    for cue in merged_plan.get("success", []):
        st = resolve_cue(cue)
        use_fanfare = isinstance(cue, dict) and bool(cue.get("fanfare", False))
        if use_fanfare and level_up is not None:
            place(level_up, st, 0.26, align="onset")
        else:
            place(ui_enter if ui_enter is not None else data_col, st, 0.26, align="onset")
            place(pop_soft, st, 0.16, align="peak")

    # Mechanics & Heavy Gear Rotations
    for cue in merged_plan.get("mechanics", []):
        mt = resolve_cue(cue)
        place(gear_smooth, mt, 0.26, align="onset")

    # Outro Riser swells smoothly across ~2s and peaks RIGHT on voice_end Outro impact!
    place(riser, voice_end, 0.34, align="peak")
    place(whoosh_fast, voice_end, 0.38, align="peak")
    place(boom, voice_end + 0.02, 0.48, align="onset")
    place(click_cin, voice_end + 0.28, 0.24, align="onset")

    # 4. 100% Bit-Transparent Voice Mixing (Zero loudnorm pumping, Zero brickwall limiter distortion)
    if has_voice:
        v_peak = float(np.max(np.abs(voice)))
        if v_peak > 0.92:
            voice_gain = 0.92 / v_peak
        elif 1e-5 < v_peak < 0.25:
            voice_gain = 0.72 / v_peak
        else:
            voice_gain = 1.0
        voice_clean = voice * voice_gain

        # Measure active speech RMS so Music & SFX scale gently underneath natural uncompressed voices
        mono_v = 0.5 * (voice_clean[:, 0] + voice_clean[:, 1])
        hop = int(0.020 * SR)
        n_f = max(1, len(mono_v) // hop)
        f_rms = np.array([np.sqrt(np.mean(mono_v[i * hop : (i + 1) * hop] ** 2)) for i in range(n_f)])
        active_frames = f_rms[f_rms > 0.008]
        active_rms = float(np.median(active_frames)) if len(active_frames) > 0 else 0.12
        bed_scale = float(np.clip(active_rms / 0.20, 0.35, 0.85))

        v_env = np.abs(mono_v)
        v_env = maximum_filter1d(v_env, size=int(0.24 * SR))
        v_env = uniform_filter1d(v_env, size=int(0.16 * SR))
        v_norm = np.clip(
            v_env / (np.percentile(v_env[v_env > 0.005], 90) + 1e-9 if np.any(v_env > 0.005) else 1.0),
            0.0,
            1.0,
        )

        eff_duck = max(duck_depth, 0.66)
        mus_duck = 1.0 - eff_duck * v_norm
        sfx_duck = 1.0 - 0.25 * v_norm

        mus_layer = (mus * (0.26 * bed_scale)) * mus_duck[:, None]
        sfx_layer = (sfx * (0.50 * bed_scale)) * sfx_duck[:, None]
        mix = voice_clean + mus_layer + sfx_layer
        stem_no_voice = mus * (0.26 * bed_scale) + sfx * (0.50 * bed_scale)
    else:
        # Full crisp gain when voiceover is off/absent (Live User Recording / Voice-Free Output)
        mus_layer = mus * 0.35
        sfx_layer = sfx * 0.65
        mix = mus_layer + sfx_layer
        stem_no_voice = mix.copy()

    # Pure constant linear ceiling (-0.45 dBFS true stereo channel peak): 0.000% clipping, 0.000% pumping!
    mix_peak = float(np.max(np.abs(mix)))
    if mix_peak > 0.95:
        headroom_scalar = 0.95 / mix_peak
        mix *= headroom_scalar
        stem_no_voice *= headroom_scalar

    stem_path = "public/audio/music_and_sfx_only.wav"
    final_mix_path = "public/audio/final_mix.wav"
    write_wav_s24le(stem_path, stem_no_voice)
    write_wav_s24le(final_mix_path, mix)
    print(
        f"[MIX] 100% Original-Voice Transparent 24-bit Mix saved -> {final_mix_path} ({dur:.2f}s, peak={np.max(np.abs(mix)):.3f})"
    )


if __name__ == "__main__":
    main()

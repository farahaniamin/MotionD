import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def rgb_to_hex(rgb) -> str:
    return "#{:02X}{:02X}{:02X}".format(
        int(np.clip(rgb[0], 0, 255)),
        int(np.clip(rgb[1], 0, 255)),
        int(np.clip(rgb[2], 0, 255)),
    )


def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def kmeans_palette(pixels: np.ndarray, k: int = 3, iters: int = 12) -> list[tuple[np.ndarray, int]]:
    """Lightweight pure-NumPy K-Means to find distinct dominant accent colors without muddy medians."""
    if len(pixels) == 0:
        return []
    if len(pixels) <= k:
        return [(pixels[i], 1) for i in range(len(pixels))]

    rng = np.random.default_rng(42)
    if len(pixels) > 3500:
        idx = rng.choice(len(pixels), 3500, replace=False)
        pts = pixels[idx].astype(np.float32)
    else:
        pts = pixels.astype(np.float32)

    # Farthest-point initialization for diverse color clusters
    centers = [pts[0]]
    for _ in range(1, min(k, len(pts))):
        dists = np.min([np.sum((pts - c) ** 2, axis=1) for c in centers], axis=0)
        centers.append(pts[int(np.argmax(dists))])
    centers_arr = np.array(centers, dtype=np.float32)

    labels = np.zeros(len(pts), dtype=np.int32)
    for _ in range(iters):
        dists = np.stack([np.sum((pts - c) ** 2, axis=1) for c in centers_arr], axis=1)
        new_labels = np.argmin(dists, axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for ci in range(len(centers_arr)):
            mask = labels == ci
            if np.any(mask):
                centers_arr[ci] = np.mean(pts[mask], axis=0)

    clusters = []
    for ci in range(len(centers_arr)):
        cnt = int(np.sum(labels == ci))
        if cnt > 0:
            clusters.append((centers_arr[ci], cnt))
    clusters.sort(key=lambda x: x[1], reverse=True)
    return clusters


def probe_video(video_path: Path) -> dict:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,r_frame_rate:format=duration",
        "-of",
        "json",
        str(video_path),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    info = json.loads(res.stdout)
    stream = info["streams"][0]
    num, den = stream.get("r_frame_rate", "30/1").split("/")
    fps = round(float(num) / max(1.0, float(den)), 2)
    dur = round(float(info["format"].get("duration", 0.0)), 2)
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": fps,
        "duration": dur,
    }


def detect_motion_cadence(video_path: Path, dur: float, tmp_dir: Path) -> dict:
    tmp_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            "fps=6,scale=90:160",
            str(tmp_dir / "m_%04d.jpg"),
        ],
        check=True,
    )
    files = sorted(tmp_dir.glob("m_*.jpg"))
    if len(files) < 4:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return {
            "estimated_spatial_scenes": 1,
            "recommended_scene_duration_s": round(dur, 2),
            "major_chapter_cuts_s": [],
            "in_scene_sub_shifts_s": [],
            "pacing": "steady",
        }

    grays = [np.asarray(Image.open(f).convert("L"), dtype=np.float32) for f in files]
    shutil.rmtree(tmp_dir, ignore_errors=True)

    diffs = [float(np.mean(np.abs(grays[i] - grays[i - 1]))) for i in range(1, len(grays))]
    med = float(np.median(diffs))
    major_thresh = max(15.0, med * 2.8)
    sub_thresh = max(9.5, med * 2.0)

    major_spikes = []
    sub_spikes = []
    last_major_t = -2.0
    last_sub_t = -1.2
    for idx, d in enumerate(diffs):
        t_sec = round((idx + 1) / 6.0, 2)
        if d >= major_thresh and (t_sec - last_major_t) >= 1.6:
            major_spikes.append(t_sec)
            last_major_t = t_sec
        elif d >= sub_thresh and (t_sec - last_sub_t) >= 0.9:
            sub_spikes.append(t_sec)
            last_sub_t = t_sec

    spatial_scenes = max(1, len(major_spikes) + 1)
    raw_cadence = dur / spatial_scenes
    # Support fast-paced creator reels (down to 1.8s) up to measured editorial (4.8s)
    scene_cadence = round(max(1.8, min(4.8, raw_cadence)), 2)
    pacing = "fast" if scene_cadence < 2.6 else ("editorial" if scene_cadence <= 3.8 else "measured")
    return {
        "estimated_spatial_scenes": spatial_scenes,
        "recommended_scene_duration_s": scene_cadence,
        "major_chapter_cuts_s": major_spikes,
        "in_scene_sub_shifts_s": sub_spikes,
        "pacing": pacing,
    }


def analyze_single_video(video_path: Path, out_dir: Path) -> dict:
    meta = probe_video(video_path)
    dur = max(0.5, meta["duration"])

    cadence_info = detect_motion_cadence(video_path, dur, out_dir / f"_cad_{video_path.stem}")

    # Extract 24 evenly spaced frames in ONE single ffmpeg call
    n_samples = 24
    start_s = min(0.18, dur * 0.02)
    span_s = max(0.4, dur * 0.96 - start_s)
    sample_fps = n_samples / span_s
    thumb_w, thumb_h = 270, 480

    tmp_frames_dir = out_dir / f"_frames_{video_path.stem}"
    tmp_frames_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-y",
            "-ss",
            f"{start_s:.3f}",
            "-t",
            f"{span_s:.3f}",
            "-i",
            str(video_path),
            "-vf",
            f"fps={sample_fps:.4f},scale={thumb_w}:{thumb_h}:force_original_aspect_ratio=decrease,pad={thumb_w}:{thumb_h}:(ow-iw)/2:(oh-ih)/2",
            "-frames:v",
            str(n_samples),
            str(tmp_frames_dir / "f_%03d.png"),
        ],
        check=True,
    )

    frame_files = sorted(tmp_frames_dir.glob("f_*.png"))
    actual_n = max(1, len(frame_files))
    timestamps = np.linspace(start_s, start_s + span_s, actual_n)

    thumbs: list[Image.Image] = []
    saturations = []
    max_saturations = []
    edge_densities = []
    center_lums = []
    border_lums = []
    mean_lums = []
    dark_frames_count = 0
    light_frames_count = 0
    dark_bg_samples = []
    light_center_samples = []
    light_edge_samples = []
    vibrant_pixels = []

    for idx, frame_png in enumerate(frame_files):
        ts = float(timestamps[idx])
        im = Image.open(frame_png).convert("RGB")
        arr = np.asarray(im, dtype=np.float32)

        mx = arr.max(axis=2)
        mn = arr.min(axis=2)
        sat = np.where(mx > 1e-3, (mx - mn) / (mx + 1e-3), 0.0)
        lum = 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]

        h_px, w_px = lum.shape
        c_lum = lum[h_px // 4 : 3 * h_px // 4, w_px // 4 : 3 * w_px // 4]
        b_lum = np.concatenate([
            lum[: h_px // 10, :].ravel(),
            lum[-h_px // 10 :, :].ravel(),
            lum[:, : w_px // 10].ravel(),
            lum[:, -w_px // 10 :].ravel(),
        ])

        c_mean = float(np.mean(c_lum))
        b_med = float(np.median(b_lum))
        m_lum = float(np.mean(lum))

        center_lums.append(c_mean)
        border_lums.append(b_med)
        mean_lums.append(m_lum)
        saturations.append(float(np.mean(sat)))
        max_saturations.append(float(np.percentile(sat, 98)))

        grad_y = np.abs(lum[1:, :] - lum[:-1, :])
        grad_x = np.abs(lum[:, 1:] - lum[:, :-1])
        edge_densities.append(float(np.mean((grad_y[:, :-1] > 28.0) | (grad_x[:-1, :] > 28.0))))

        # Center-aware light/dark classification (handles radial studio vignettes accurately!)
        is_dark = c_mean < 78.0 and m_lum < 72.0
        is_light = c_mean > 142.0 or m_lum > 135.0
        border_rgb = np.concatenate([arr[:24, :, :].reshape(-1, 3), arr[-24:, :, :].reshape(-1, 3)], axis=0)
        center_rgb = arr[h_px // 3 : 2 * h_px // 3, w_px // 3 : 2 * w_px // 3].reshape(-1, 3)

        if is_dark:
            dark_frames_count += 1
            dark_bg_samples.append(np.median(border_rgb, axis=0))
        elif is_light:
            light_frames_count += 1
            light_center_samples.append(np.percentile(center_rgb, 80, axis=0))
            light_edge_samples.append(np.median(border_rgb, axis=0))

        # Collect vivid intentional accent pixels (ignore near-black and near-white)
        vibrant_mask = (sat > 0.36) & (lum > 38.0) & (lum < 238.0)
        if np.any(vibrant_mask):
            vib_arr = arr[vibrant_mask]
            if len(vib_arr) > 450:
                indices = np.random.default_rng(idx).choice(len(vib_arr), 450, replace=False)
                vib_arr = vib_arr[indices]
            vibrant_pixels.append(vib_arr)

        annotated = im.copy()
        dr = ImageDraw.Draw(annotated)
        dr.rectangle([4, 4, 88, 26], fill=(12, 12, 12))
        dr.text((10, 8), f"{ts:05.2f}s", fill=(0, 255, 220))
        dr.rectangle([0, 0, thumb_w - 1, thumb_h - 1], outline=(80, 80, 80), width=1)
        thumbs.append(annotated)

    shutil.rmtree(tmp_frames_dir, ignore_errors=True)

    cols = 6
    rows = max(1, math.ceil(len(thumbs) / cols))
    sheet = Image.new("RGB", (cols * thumb_w, rows * thumb_h), (18, 18, 18))
    for idx, im in enumerate(thumbs):
        c = idx % cols
        r = idx // cols
        sheet.paste(im, (c * thumb_w, r * thumb_h))
    sheet_path = out_dir / f"{video_path.stem}_contact_sheet.jpg"
    sheet.save(sheet_path, "JPEG", quality=88)

    has_vivid_accents = float(np.mean(max_saturations)) > 0.30 or len(vibrant_pixels) >= 3
    light_ratio = round(light_frames_count / actual_n, 2)
    dark_scene_ratio = round(dark_frames_count / actual_n, 2)
    vignette_delta = round(float(np.mean(np.array(center_lums) - np.array(border_lums))), 1)

    dom_dark_bg = np.median(np.array(dark_bg_samples), axis=0) if dark_bg_samples else np.array([12, 12, 14])
    dom_light_center = np.median(np.array(light_center_samples), axis=0) if light_center_samples else np.array([250, 250, 248])
    dom_light_edge = np.median(np.array(light_edge_samples), axis=0) if light_edge_samples else np.array([190, 190, 186])

    all_vib = np.concatenate(vibrant_pixels, axis=0) if vibrant_pixels else np.empty((0, 3), dtype=np.float32)
    clusters = kmeans_palette(all_vib, k=3)
    if clusters:
        primary_rgb = clusters[0][0]
        p_norm = primary_rgb / (np.linalg.norm(primary_rgb) + 1e-6)
        secondary_rgb = None
        for c_rgb, c_cnt in clusters[1:]:
            c_norm = c_rgb / (np.linalg.norm(c_rgb) + 1e-6)
            hue_diff = float(np.linalg.norm(c_norm - p_norm))
            if hue_diff > 0.28 and np.linalg.norm(c_rgb - primary_rgb) > 95.0 and c_cnt >= max(12, clusters[0][1] * 0.08):
                secondary_rgb = c_rgb
                break
    else:
        primary_rgb = np.array([230, 43, 68]) if has_vivid_accents else np.array([18, 18, 18])
        secondary_rgb = None

    return {
        "file": video_path.name,
        "resolution": f"{meta['width']}x{meta['height']}",
        "fps": meta["fps"],
        "duration_s": meta["duration"],
        "estimated_spatial_scenes": cadence_info["estimated_spatial_scenes"],
        "recommended_scene_duration_s": cadence_info["recommended_scene_duration_s"],
        "pacing": cadence_info["pacing"],
        "major_chapter_cuts_s": cadence_info["major_chapter_cuts_s"],
        "in_scene_sub_shifts_s": cadence_info["in_scene_sub_shifts_s"],
        "mean_saturation": round(float(np.mean(saturations)), 4),
        "peak_saturation": round(float(np.mean(max_saturations)), 4),
        "mean_edge_density": round(float(np.mean(edge_densities)), 4),
        "vignette_delta": vignette_delta,
        "has_vivid_accents": has_vivid_accents,
        "recommended_asset_color_mode": "color" if has_vivid_accents else "monochrome",
        "light_scene_ratio": light_ratio,
        "dark_scene_ratio": dark_scene_ratio,
        "dominant_bg_hex": rgb_to_hex(dom_light_center if light_ratio >= dark_scene_ratio else dom_dark_bg),
        "dark_bg_hex": rgb_to_hex(dom_dark_bg),
        "light_center_hex": rgb_to_hex(dom_light_center),
        "light_edge_hex": rgb_to_hex(dom_light_edge),
        "dominant_accent_hex": rgb_to_hex(primary_rgb),
        "secondary_accent_hex": rgb_to_hex(secondary_rgb) if secondary_rgb is not None else None,
        "_vibrant_pixels": all_vib,
        "contact_sheet": str(sheet_path),
    }


def compute_adaptive_profiles(reports: list[dict], genre_meta: dict) -> dict:
    """Derives adaptive typography, canvas atmosphere, transition defaults, and ribbon profiles."""
    avg_dark = float(np.mean([r["dark_scene_ratio"] for r in reports]))
    avg_light = float(np.mean([r["light_scene_ratio"] for r in reports]))
    avg_edge = float(np.mean([r.get("mean_edge_density", 0.04) for r in reports]))
    avg_vignette = float(np.mean([r.get("vignette_delta", 15.0) for r in reports]))
    avg_cadence = float(np.mean([r["recommended_scene_duration_s"] for r in reports]))
    is_color = genre_meta["assetColorMode"] == "color"

    if avg_dark >= 0.55 and avg_light < 0.20:
        canvas_rhythm = "dark_dominant"
    elif (avg_dark >= 0.20 and avg_light >= 0.20) or avg_dark > 0.12:
        canvas_rhythm = "mixed_contrast"
    else:
        canvas_rhythm = "light_dominant"

    is_fast = avg_cadence < 2.7
    hero_rem = 8.25 if (is_color and is_fast) else (7.75 if (is_color or avg_edge > 0.045) else 7.5)
    inline_rem = 4.875 if is_color else 4.625
    setup_rem = 3.125 if avg_vignette > 40.0 else 3.375

    return {
        "typography": {
            "style": "bold_editorial_contrast",
            "setupWeight": 500,
            "setupRem": setup_rem,
            "inlineEmphasisWeight": 900,
            "inlineEmphasisRem": inline_rem,
            "heroWeight": 950,
            "heroRem": hero_rem,
            "displayGlow": is_color and avg_dark >= 0.18,
        },
        "atmosphere": {
            "canvasRhythm": canvas_rhythm,
            "backdropStyle": genre_meta.get("backdropStyle", "studio_paper"),
            "vignetteStrength": "strong" if avg_vignette > 45.0 else ("medium" if avg_vignette > 20.0 else "soft"),
            "perspectiveFloor": genre_meta["genre"] == "dark_brutalist_terminal" or avg_dark >= 0.22,
            "ambientParticles": avg_dark >= 0.18,
        },
        "ribbon": {
            "orientation": "horizontal",
            "drawDur": 0.75 if is_fast else 1.05,
            "variants": ["diagonal-up", "diagonal-down", "arch", "s-curve"],
        },
    }


def is_warm_accent(hex_color: str) -> bool:
    r, g, b = hex_to_rgb(hex_color)
    return r > b + 35 and r > 120


def classify_visual_genre(reports: list[dict], is_custom: bool) -> dict:
    """
    Classifies reference videos into 1 of 6 distinct visual genres and emits a COMPLETE
    contrast-safe color token map (including slate, muted, gridStroke, ribbon & surface tokens).
    """
    if not is_custom:
        return {
            "genre": "studio_industrial",
            "name_fa": "استودیویی صنعتی مینیمال (پیش‌فرض)",
            "assetColorMode": "monochrome",
            "cornerMotif": "architectural",
            "backdropStyle": "studio_paper",
            "palette": {
                "paperCenter": "#FFFFFF",
                "paperMid": "#F5F5F3",
                "paperEdge": "#D5D5D0",
                "ink": "#121212",
                "slate": "#6B6B6B",
                "muted": "#4A4A4A",
                "lightMuted": "#8C8C88",
                "gridStroke": "rgba(20, 20, 20, 0.14)",
                "ribbon": "rgba(185, 185, 180, 0.34)",
                "accent": "#121212",
                "accentSecondary": "#6B6B6B",
                "accentGlow": "rgba(18, 18, 18, 0.20)",
                "darkBg": "#0E0E0E",
                "darkDeep": "#050505",
            },
            "object_strategy": "monochrome_industrial_3d",
            "transition_strategy": "whip_and_continuity",
        }

    any_vivid = any(r["has_vivid_accents"] for r in reports)
    avg_dark_ratio = float(np.mean([r["dark_scene_ratio"] for r in reports]))
    avg_light_ratio = float(np.mean([r["light_scene_ratio"] for r in reports]))
    avg_edge = float(np.mean([r.get("mean_edge_density", 0.04) for r in reports]))
    avg_vignette = float(np.mean([r.get("vignette_delta", 15.0) for r in reports]))

    # Pool vibrant pixels across ALL reference videos for accurate multi-video accent extraction
    pooled_vib = [r["_vibrant_pixels"] for r in reports if len(r.get("_vibrant_pixels", [])) > 0]
    if pooled_vib:
        clusters = kmeans_palette(np.concatenate(pooled_vib, axis=0), k=3)
        chosen_accent = rgb_to_hex(clusters[0][0])
        p_norm = clusters[0][0] / (np.linalg.norm(clusters[0][0]) + 1e-6)
        secondary_accent = None
        for c_rgb, c_cnt in clusters[1:]:
            c_norm = c_rgb / (np.linalg.norm(c_rgb) + 1e-6)
            if float(np.linalg.norm(c_norm - p_norm)) > 0.28 and np.linalg.norm(c_rgb - clusters[0][0]) > 95.0 and c_cnt >= max(15, clusters[0][1] * 0.08):
                secondary_accent = rgb_to_hex(c_rgb)
                break
    else:
        accents = [r["dominant_accent_hex"] for r in reports if r["has_vivid_accents"]]
        chosen_accent = accents[0] if accents else "#E3262A"
        secondary_accent = next((r["secondary_accent_hex"] for r in reports if r.get("secondary_accent_hex")), None)

    ar, ag, ab = hex_to_rgb(chosen_accent)
    accent_glow = f"rgba({ar}, {ag}, {ab}, 0.38)"

    light_centers = [r["light_center_hex"] for r in reports if r["light_scene_ratio"] > 0.15]
    light_edges = [r["light_edge_hex"] for r in reports if r["light_scene_ratio"] > 0.15]
    dark_bgs = [r["dark_bg_hex"] for r in reports if r["dark_scene_ratio"] > 0.15]

    best_light_center = "#FFFFFF" if avg_vignette > 35 else (light_centers[0] if light_centers else "#FFFFFF")
    best_light_edge = light_edges[0] if (light_edges and avg_vignette > 30) else "#D5D5D0"
    best_light_mid = "#DCDCDC" if avg_vignette > 40 else "#F2F2F0"
    best_dark_bg = dark_bgs[0] if dark_bgs else "#0C0C0E"

    # Rule 1: Dual-Act Mixed Editorial Noir (significant dark act AND light studio act, e.g. noir + radial spotlight)
    if avg_dark_ratio >= 0.22 and avg_light_ratio >= 0.22:
        return {
            "genre": "mixed_editorial_noir",
            "name_fa": "ادیتوریال دوگانه (نوآر تیره + اسپات‌لایت استودیویی روشن)",
            "assetColorMode": "color" if any_vivid else "monochrome",
            "cornerMotif": "asterisk" if avg_vignette > 35 else "none",
            "backdropStyle": "noir_leather_and_spotlight",
            "palette": {
                "paperCenter": best_light_center,
                "paperMid": best_light_mid,
                "paperEdge": best_light_edge,
                "ink": "#121212",
                "slate": "#5A5A60",
                "muted": "#3A3A40",
                "lightMuted": "#8C8C94",
                "gridStroke": "rgba(20, 20, 20, 0.09)",
                "ribbon": "rgba(185, 185, 180, 0.25)",
                "accent": chosen_accent,
                "accentSecondary": secondary_accent or "#12E6EF",
                "accentGlow": accent_glow,
                "darkBg": best_dark_bg if best_dark_bg != "#000000" else "#0B0B0D",
                "darkDeep": "#040405",
            },
            "object_strategy": "editorial_hero_3d_and_typography",
            "transition_strategy": "contrast_flash_and_zoom",
        }

    # Rule 2: Predominantly Dark (>= 55%) -> Distinguish Luxury Noir vs Technical Terminal
    if avg_dark_ratio >= 0.55:
        is_terminal = (not is_warm_accent(chosen_accent) and any_vivid) or avg_edge >= 0.048
        if not is_terminal:
            return {
                "genre": "dark_luxury_editorial",
                "name_fa": "ادیتوریال لوکس و سینمایی تیره (بافت چرم/مخملی و تایپوگرافی پرکنتراست)",
                "assetColorMode": "color" if any_vivid else "monochrome",
                "cornerMotif": "none",
                "backdropStyle": "noir_leather",
                "palette": {
                    "paperCenter": "#181516",
                    "paperMid": "#0F0E0F",
                    "paperEdge": "#050506",
                    "ink": "#F5F5F5",
                    "slate": "#B4B4BE",
                    "muted": "#D2D2DA",
                    "lightMuted": "#8A8A94",
                    "gridStroke": "rgba(255, 255, 255, 0.07)",
                    "ribbon": "rgba(255, 255, 255, 0.12)",
                    "accent": chosen_accent if any_vivid else "#D9A441",
                    "accentSecondary": secondary_accent or "#FFFFFF",
                    "accentGlow": accent_glow if any_vivid else "rgba(217, 164, 65, 0.35)",
                    "darkBg": "#0B0B0D",
                    "darkDeep": "#040405",
                },
                "object_strategy": "luxury_editorial_3d",
                "transition_strategy": "contrast_flash_and_zoom",
            }

        return {
            "genre": "dark_brutalist_terminal",
            "name_fa": "ترمینال بروتالیست تیره و هوش مصنوعی",
            "assetColorMode": "color",
            "cornerMotif": "wireframe",
            "backdropStyle": "perspective_terminal",
            "palette": {
                "paperCenter": "#14161C",
                "paperMid": "#0E1015",
                "paperEdge": "#06070A",
                "ink": "#F5F7FA",
                "slate": "#A8B3C2",
                "muted": "#CBD5E1",
                "lightMuted": "#7D8898",
                "gridStroke": "rgba(255, 255, 255, 0.10)",
                "ribbon": "rgba(255, 255, 255, 0.14)",
                "accent": chosen_accent if any_vivid else "#00FFC2",
                "accentSecondary": secondary_accent or "#38BDF8",
                "accentGlow": accent_glow if any_vivid else "rgba(0, 255, 194, 0.35)",
                "darkBg": "#08090C",
                "darkDeep": "#040406",
            },
            "object_strategy": "glowing_silicon_hardware",
            "transition_strategy": "contrast_flash_and_zoom",
        }

    # Rule 3: Vivid accents + occasional dark punchline cuts -> Creator Collage
    if any_vivid and avg_dark_ratio > 0.08:
        return {
            "genre": "creator_collage",
            "name_fa": "کلاژ و میکس‌مدیای کریتور (پین، نوار چسب، رنگ‌های تاکیدی تند و کنتراست)",
            "assetColorMode": "color",
            "cornerMotif": "none",
            "backdropStyle": "studio_paper",
            "palette": {
                "paperCenter": "#FFFFFF",
                "paperMid": best_light_mid if best_light_mid != "#000000" else "#F7EDE3",
                "paperEdge": best_light_edge if best_light_edge != "#000000" else "#E8E0D5",
                "ink": "#121212",
                "slate": "#5C5C64",
                "muted": "#3E3E44",
                "lightMuted": "#8C8C92",
                "gridStroke": "rgba(20, 20, 20, 0.10)",
                "ribbon": "rgba(185, 185, 180, 0.28)",
                "accent": chosen_accent,
                "accentSecondary": secondary_accent or "#FF9900",
                "accentGlow": accent_glow,
                "darkBg": "#0E0E0E",
                "darkDeep": "#050505",
            },
            "object_strategy": "tactile_collage_and_colored_physical",
            "transition_strategy": "whip_and_contrast_black_cuts",
        }

    # Rule 4: Vivid accents with pure light backdrops -> Infographic Kinetic
    if any_vivid:
        return {
            "genre": "infographic_kinetic",
            "name_fa": "اینفوگرافیک جنبشی و برندینگ مدرن (چارت‌های گرادیان، ستاره‌ها و رنگ‌های شفاف)",
            "assetColorMode": "color",
            "cornerMotif": "wireframe",
            "backdropStyle": "studio_paper",
            "palette": {
                "paperCenter": "#FFFFFF",
                "paperMid": best_light_center if best_light_center != "#FFFFFF" else "#F4F5F7",
                "paperEdge": best_light_edge,
                "ink": "#121212",
                "slate": "#5E626A",
                "muted": "#40434A",
                "lightMuted": "#8E929B",
                "gridStroke": "rgba(20, 20, 20, 0.10)",
                "ribbon": "rgba(185, 185, 180, 0.30)",
                "accent": chosen_accent,
                "accentSecondary": secondary_accent or "#00D2FF",
                "accentGlow": accent_glow,
                "darkBg": "#0E0E0E",
                "darkDeep": "#050505",
            },
            "object_strategy": "gradient_charts_and_data_spheres",
            "transition_strategy": "smooth_slide_and_morph",
        }

    # Rule 5: Minimalist low-edge monochrome / grayscale typography
    if avg_edge < 0.032:
        return {
            "genre": "minimal_kinetic",
            "name_fa": "تایپوگرافی کینتیک مینیمال (فضای خالی وسیع و کنتراست خالص)",
            "assetColorMode": "monochrome",
            "cornerMotif": "asterisk" if avg_vignette > 35 else "none",
            "backdropStyle": "studio_paper",
            "palette": {
                "paperCenter": best_light_center,
                "paperMid": best_light_mid,
                "paperEdge": best_light_edge,
                "ink": "#121212",
                "slate": "#626268",
                "muted": "#424248",
                "lightMuted": "#8C8C90",
                "gridStroke": "rgba(20, 20, 20, 0.08)",
                "ribbon": "rgba(185, 185, 180, 0.25)",
                "accent": "#121212",
                "accentSecondary": "#626268",
                "accentGlow": "rgba(18, 18, 18, 0.18)",
                "darkBg": "#0E0E0E",
                "darkDeep": "#050505",
            },
            "object_strategy": "minimal_typography_first",
            "transition_strategy": "whip_and_continuity",
        }

    # Rule 6: Fallback Studio Industrial Monochrome
    return {
        "genre": "studio_industrial",
        "name_fa": "استودیویی صنعتی مینیمال (مونوکروم)",
        "assetColorMode": "monochrome",
        "cornerMotif": "architectural",
        "backdropStyle": "studio_paper",
        "palette": {
            "paperCenter": "#FFFFFF",
            "paperMid": "#F5F5F3",
            "paperEdge": "#D5D5D0",
            "ink": "#121212",
            "slate": "#6B6B6B",
            "muted": "#4A4A4A",
            "lightMuted": "#8C8C88",
            "gridStroke": "rgba(20, 20, 20, 0.14)",
            "ribbon": "rgba(185, 185, 180, 0.34)",
            "accent": "#121212",
            "accentSecondary": "#6B6B6B",
            "accentGlow": "rgba(18, 18, 18, 0.20)",
            "darkBg": "#0E0E0E",
            "darkDeep": "#050505",
        },
        "object_strategy": "monochrome_industrial_3d",
        "transition_strategy": "whip_and_continuity",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Adaptive Reference Video Analyzer v3.3: Extracts visual genre, complete palette, vignette/rhythm DNA & contact sheets."
    )
    parser.add_argument("--dir", default=None, help="Directory containing reference videos (.mp4/.mov/.webm).")
    parser.add_argument("--out", default="ref_analysis", help="Output directory for contact sheets and style_report.json.")
    parser.add_argument("--sync-brand", action="store_true", default=False, help="Automatically sync detected palette, genre & typography to user_inputs/brand.json.")
    parser.add_argument("--no-sync-brand", action="store_false", dest="sync_brand", help="Analyze only without modifying user_inputs/brand.json.")
    args = parser.parse_args()

    skill_dir = Path(__file__).resolve().parent.parent
    candidates = []
    if args.dir:
        candidates.append(Path(args.dir).resolve())
    candidates.extend(
        [
            Path("user_inputs/reference_videos/custom"),
            skill_dir / "user_inputs" / "reference_videos" / "custom",
            skill_dir / "user_inputs" / "reference_videos" / "default",
            skill_dir.parent / "skills" / "editorial-motion-reel" / "user_inputs" / "reference_videos" / "default",
        ]
    )

    exts = {".mp4", ".mov", ".webm", ".mkv"}
    chosen_dir = None
    videos: list[Path] = []
    for c in candidates:
        if c.exists():
            vids = sorted([p for p in c.iterdir() if p.is_file() and p.suffix.lower() in exts])
            if vids:
                chosen_dir = c
                videos = vids
                break

    if not videos:
        print("[INFO] No reference videos found to analyze.")
        return

    is_custom = ("custom" in str(chosen_dir).lower()) or (args.dir is not None and "default" not in str(chosen_dir).lower())
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[ANALYZE] Analyzing {len(videos)} reference video(s) from: {chosen_dir} (is_custom={is_custom})")

    reports = [analyze_single_video(v, out_dir) for v in videos]
    avg_cadence = round(float(np.mean([r["recommended_scene_duration_s"] for r in reports])), 2)

    genre_meta = classify_visual_genre(reports, is_custom=is_custom)
    adaptive = compute_adaptive_profiles(reports, genre_meta)

    clean_reports = [{k: v for k, v in r.items() if not k.startswith("_")} for r in reports]
    summary = {
        "source_dir": str(chosen_dir),
        "is_custom_reference": is_custom,
        "video_count": len(clean_reports),
        "detected_genre": genre_meta["genre"],
        "genre_name_fa": genre_meta["name_fa"],
        "asset_color_mode": genre_meta["assetColorMode"],
        "recommended_corner_motif": genre_meta["cornerMotif"],
        "recommended_palette": genre_meta["palette"],
        "recommended_typography": adaptive["typography"],
        "recommended_atmosphere": adaptive["atmosphere"],
        "recommended_ribbon": adaptive["ribbon"],
        "object_strategy": genre_meta["object_strategy"],
        "transition_strategy": genre_meta["transition_strategy"],
        "target_scene_duration_s": avg_cadence,
        "videos": clean_reports,
    }

    report_path = out_dir / "style_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    typo = adaptive["typography"]
    atmo = adaptive["atmosphere"]
    print(f"[DONE] Style Report -> {report_path}")
    print(f"       Detected Genre: {genre_meta['genre'].upper()} ({genre_meta['name_fa']})")
    print(f"       Color Mode: {genre_meta['assetColorMode']} | Accent: {genre_meta['palette']['accent']} | Rhythm: {atmo['canvasRhythm']} | Vignette: {atmo['vignetteStrength']}")
    print(f"       Typography: setup={typo['setupWeight']} ({typo['setupRem']}rem) -> hero={typo['heroWeight']} ({typo['heroRem']}rem)")
    print(f"       Corner Motif: {genre_meta['cornerMotif']} | Transitions: {genre_meta['transition_strategy']} | Cadence: ~{avg_cadence}s/scene")
    for cr in clean_reports:
        print(f"       [VISION-CHECK] Inspect contact sheet visually before scenes.tsx: {cr['contact_sheet']}")

    if args.sync_brand:
        brand_path = Path("user_inputs/brand.json")
        if brand_path.exists():
            try:
                brand_data = json.loads(brand_path.read_text(encoding="utf-8"))
                brand_data["genre"] = genre_meta["genre"]
                brand_data["assetColorMode"] = genre_meta["assetColorMode"]
                brand_data["cornerMotif"] = genre_meta["cornerMotif"]
                brand_data["transitionStrategy"] = genre_meta["transition_strategy"]
                brand_data["recommendedCadenceSec"] = avg_cadence
                brand_data["typography"] = adaptive["typography"]
                brand_data["atmosphere"] = adaptive["atmosphere"]
                if "colors" not in brand_data:
                    brand_data["colors"] = {}
                for k, v in genre_meta["palette"].items():
                    brand_data["colors"][k] = v
                brand_path.write_text(json.dumps(brand_data, ensure_ascii=False, indent=2), encoding="utf-8")
                print(f"[SYNC] Updated {brand_path} with complete adaptive DNA & contrast-safe palette.")

                sync_script = Path(__file__).resolve().parent / "sync_inputs.py"
                if sync_script.exists():
                    sys.path.insert(0, str(sync_script.parent))
                    from sync_inputs import sync_project_inputs

                    sync_project_inputs()
            except Exception as e:
                print(f"[WARN] Failed to sync brand.json: {e}")


if __name__ == "__main__":
    main()

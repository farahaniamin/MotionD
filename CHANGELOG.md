# Changelog

## 2.2.0 — font library
- `resources/fonts/`: v1 YekanBakhFaNum + 8 Persian (Vazirmatn, Lalezar, Reem Kufi, Noto Kufi Arabic, El Messiri, Lemonada, Changa, Baloo Bhaijaan 2) + 10 Latin display/text fonts (Oswald, Nunito, Inter, Anton, Bebas Neue, Archivo Black, Space Grotesk, Playfair Display, DM Serif Display, Special Elite). All OFL/Apache except YekanBakh (user-supplied).
- `brand.json → fontFa / fontLatin` picks from `catalog.json`; fonts whose digits are Arabic-style get Persian digits from Vazirmatn automatically (unicode-range face).
- `specimen.png` preview of every font.

## 2.1.0 — Vox collage style + AI image pipeline

- New default style `vox_collage`: crumpled paper (baked, color-agnostic overlay), torn edges with white core, newsprint strips, halftone accent "sun", masking tape, die-cut cut-outs, torn-wipe / slam / flash transitions, stop-motion on twos. Oswald (OFL) for Latin.
- `palettePresets` per style + `brand.json → palettePreset` (red_noir, neon_yellow, swiss_mustard, newsroom_maroon, tech_blue) — accent colors per content.
- Text color now chosen from the scene background's real luminance (presets can make "light" scenes dark).
- Contract: optional `Paper` and `PropFrame` slots; new kit block `TornReveal`.
- `generate_images.py`: assets_plan.json → style-built prompts → OpenAI Images API (auto-picks newest gpt-image model, transparent bg with chroma-key fallback, re-style user images via edits, prompt-hash cache, dry-run).
- `stylize_assets.py`: background removal, trim, ink/paper tonal remap and accent recolor to the project palette (recolor without regenerating).
- `prompts/chatgpt-image-prompts.md`: manual ChatGPT prompts for the style (base block, cut-outs, plates, 4 reference families, restyle, textures, series).

## 2.0.0 — style-independent engine + real-logo pipeline

**Architecture**
- Theme contract (`engine/contract.ts`): 9 slots (Backdrop, Surface, Highlight, LogoTreatment, Sticker, Overlay, BrandMark, Outro, transitions). All kit components render through it → one command (`set_style.py`) re-skins a reel with zero scene edits.
- Style packs in `styles/` (tokens + theme + guide + fonts + textures). Shipped: `paper_cut` (new, default) and `studio_mono` (v1 look rebuilt on the contract).
- New style-agnostic kit for AI-tool reels: Headline (flow layout, no line collisions), BrandLogo, ToolCard, LogoHub, Versus, FeatureList, StatCounter, ScreenFrame, PromptBox, ChatBubble, CodeCard, Prop, Stamp, Arrow, CTA.
- Every scene owns its backdrop (enables physical paper-over transitions); scene `tone` drives automatic readable text colors (WCAG contrast pick).
- Motion personality is a token: `stepFps` (stop-motion on twos), `boil`, `overshoot`, `stagger`.

**Brands**
- `logo_fetch.py`: user file → svgl.app → Simple Icons → STOP. Provenance (source URL, sha256, date) in `src/logos.json`; Persian aliases in `brands/registry.json`.
- Flat multi-color logos are split into per-color layers so styles can re-materialize the exact vector (paper_cut stacks each color as a paper sheet with die-cut border and fiber).
- `capture_site.py`: real website screenshots via local Chrome for `ScreenFrame`.

**Quality**
- `qa_check.py` gate inside `render_reel.py`: unregistered/hand-made logos block the render; hardcoded colors/px fonts in scenes warned; pacing window; stills check for blank frames and missing-logo placeholders; contact sheet.
- Voice-free mode now generates word timings, so `wordTime()` and word-based SFX work without narration.
- SFX: style-driven bank remap (paper foley bank added), v2 component auto-cues, density limits.
- Render: single near-lossless encode + audio stream copy (was double x264 encode); `--browser-executable`; concurrency clamped to CPU count; font loading resilient (`allSettled`).
- Paper textures pre-baked (≈3.5x faster than live feTurbulence); `surface.roughEdges` toggle for fast drafts.

**Fixed from v1**
- Docs used PowerShell on a Linux workflow → `bash`/`python3`.
- Brand name hardcoded in SKILL.md ("SINA SAMIPOUR") while projects used FRONTBAZ → brand only in `brand.json`.
- Banned clichés were documentation-only (an hourglass shipped in a reel) → QA warns on prop file names.
- ~280 hardcoded colors across the v1 kit made restyling impossible → zero in v2 kit.
- `analyze_references.py` no longer silently overwrites brand.json (analysis → new style pack).

**Not ported**: v1 bespoke components (CodeInspectorScan, MoodboardGrid, RotaryEffortDial, …) — they hardcode the mono look. Rebuild any you need on the theme slots (see references/style-packs.md).

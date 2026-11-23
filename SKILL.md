---
name: motion-reel
description: >-
  Builds professional 9:16 motion-graphics reels (1080x1920, Remotion) for AI-tool / tech explainer
  content in Persian or English. Style-independent: the whole look (Vox-style paper collage, paper cut,
  studio mono, or any new style pack) and its accent palette switch with one command without touching
  scenes. Writes the script, generates style-matched images with the OpenAI image API and harmonizes them. Uses only REAL brand logos fetched
  from verified vector sources and re-materialized in the active style (never drawn or AI-generated).
  Audio-first workflow: brief → script approval → voice/timeline → scenes → stills QA → render.
---

# Motion Reel — v2.0

**سه اصل غیرقابل‌مذاکره:**
1. **استایل جدا از محتوا.** `scenes.tsx` فقط «چه چیزی، کِی» را می‌گوید؛ «چه شکلی» را استایل‌پک فعال (`styles/<name>/`) تعیین می‌کند. در صحنه‌ها هیچ رنگ hex، px فونت، شعاع یا سایه‌ای نوشته نمی‌شود.
2. **لوگوی واقعی، با لباس استایل.** هر برند/ابزار فقط از `tools/logo_fetch.py` (منابع رسمی/معتبر) می‌آید و با `<BrandLogo id>` نمایش داده می‌شود. هندسه لوگو دست‌نخورده می‌ماند؛ استایل فقط «متریال» را عوض می‌کند (در paper_cut: برش کاغذی، لبه دای‌کات، بافت الیاف، لایه‌های رنگی جدا). اگر منبع معتبر پیدا نشد → **توقف و درخواست فایل رسمی از کاربر.** کشیدن، trace یا تولید لوگو با AI ممنوع.
3. **هیچ رندری بدون QA.** `render_reel.py` خودش `qa_check.py` را قبل از باندل (لوگوها، استقلال استایل، ریتم) و بعد از استیل‌ها (فریم خالی، لوگوی گمشده، شیت تماس) اجرا می‌کند. ایجنت موظف است `out_stills/_contact_sheet.jpg` را ببیند.

مسیر اسکیل = `<SKILL_DIR>`، پوشه پروژه = `<PROJECT_DIR>`. همه دستورات با `python3` (روی ویندوز `python`).

---

## نقشه فایل‌ها

```text
<SKILL_DIR>/
├── SKILL.md
├── styles/                       ← استایل‌پک‌ها (هر کدام: style.json + theme.tsx + guide.md + fonts/ + textures/)
│   ├── vox_collage/                کلاژ ادیتوریال Vox: کاغذ مچاله، پارگی، روزنامه، گراوور، یک رنگ تأکیدی (پیش‌فرض)
│   ├── paper_cut/                  کاغذ رنگی لایه‌ای، استاپ‌موشن ۱۲fps، استیکر دای‌کات
│   └── studio_mono/                ادیتوریال مونوکروم نسخه ۱ (whip/zoom، کارت سفید، پیل مشکی)
├── prompts/chatgpt-image-prompts.md ← پرامپت‌های دستی ChatGPT برای همین استایل
├── brands/registry.json          ← نام‌های مستعار (فارسی هم) → منبع لوگو
├── resources/template/src/
│   ├── engine/  tokens · time · contract (قرارداد Theme) · scene
│   ├── kit/     text · brand · blocks   ← کامپوننت‌های مستقل از استایل
│   ├── Reel.tsx                         ← کامپوزیتور (بک‌دراپ هر صحنه + ترنزیشن از تم + اوترو خودکار)
│   └── scenes.tsx                       ← تنها فایلی که برای هر ریلز نوشته می‌شود
├── examples/ai_tools_reel/       ← نمونه کامل (beats.json + scenes.tsx) — قبل از نوشتن صحنه بخوانید
├── scripts/                      ← در init به <PROJECT_DIR>/tools/ کپی می‌شوند
└── references/
    ├── motion-direction.md       ← اصول کارگردانی موشن + الگوی صحنه‌ها + API کیت  (الزامی)
    ├── logo-pipeline.md          ← جزئیات لوگو و اسکرین‌شات واقعی                    (الزامی)
    ├── ai-image-pipeline.md      ← تولید تصویر با GPT Image + هماهنگ‌سازی                (الزامی وقتی تصویر لازم است)
    ├── style-packs.md            ← ساخت/ویرایش استایل جدید
    └── sfx-and-audio-guide.md    ← صدا، Zero-DSP، Auto-SFX
```

---

## فاز ۱ — بریف محتوا‌محور و سناریو

### ۱.۱ سؤال‌ها (ساده، بدون اصطلاح فنی، گزینه اول `(Recommended)`)
هرگز موضوع را از روی فایل‌های پوشه حدس نزن. اول بپرس:
1. **موضوع/متن ویدیو چیه؟** — متن آماده دارم / فقط موضوع (تو بنویس) / خودت پیشنهاد بده
2. **کدوم ابزارها یا برندها معرفی میشن؟** (لیست اسم‌ها — همین‌جا لوگوهاشون رو می‌گیریم)
3. **صدا:** صدای خودم یا ElevenLabs (فایل می‌دم) / بدون گوینده (موزیک + افکت) / صدای AI فارسی
4. **استایل و رنگ:** همون استایل همیشگی (`brand.json → style`) / استایل دیگه (`set_style.py --list`) / شبیه ویدیوی نمونه‌ای که می‌دم — و **رنگ تأکیدی متناسب با موضوع** (preset های استایل، مثلاً `red_noir` برای خبر/هشدار، `neon_yellow` برای تکنولوژی؛ پیشنهاد خودت را با دلیل بگو)
5. **مدت و پایان:** ۳۰ ثانیه آموزشی / ۳۰ ثانیه + دعوت به کامنت / ~۶۰ ثانیه

نام برند، تگ‌لاین و فونت را از `user_inputs/brand.json` بخوان؛ فقط اگر کاربر خواست عوضشان کن.
**فونت:** `brand.json → "fontFa"` (فارسی) و `"fontLatin"` (لاتین) از کاتالوگ `resources/fonts/catalog.json` (نمونه: `resources/fonts/specimen.png`). `null` = پیش‌فرض (یکان‌بخ + فونت لاتین استایل). پیشنهاد: vox_collage → `Changa`/`NotoKufi` + `Oswald`/`Anton`؛ paper_cut → `Lemonada`/`Baloo` + `Nunito`؛ studio_mono → `YekanBakh`/`Vazirmatn` + `Inter`. فونت‌های تک‌وزنی (Lalezar, Anton, Bebas) فقط برای تیتر.

### ۱.۲ ساخت پروژه
```bash
python3 "<SKILL_DIR>/scripts/init_project.py" --target "<PROJECT_DIR>" [--style paper_cut]
cd "<PROJECT_DIR>" && npm install
python3 tools/logo_fetch.py claude cursor "جمنای"        # همه ابزارهای سناریو، همین الان
```
اگر `logo_fetch` برای ابزاری `[STOP]` داد → از کاربر فایل SVG رسمی (صفحه brand/press) بخواه و در `user_inputs/logos/<slug>.svg` بگذار. تا حل نشده، آن صحنه را طراحی نکن.

برای معرفی سایت/محصول، اسکرین‌شات واقعی بگیر (معتبرتر از UI ساختگی):
```bash
python3 tools/capture_site.py https://cursor.com --name cursor-home
```

### ۱.۳ سناریو → `beats.json` → فایل‌های ضبط
- هر beat یک ایده؛ ۲.۸ تا ۴.۵ ثانیه. قلاب (hook) در ۱.۵ ثانیه اول با عدد/ادعای مشخص.
- نریشن: `tts` (با کسره‌های راهنما) و `display` (تمیز). بدون گوینده: `"voice": "none"` و `duration` برای هر beat.
- عددها و ادعاها درباره ابزارها باید درست و به‌روز باشند؛ اگر مطمئن نیستی از کاربر بپرس یا با وب چک کن.
```bash
python3 tools/export_srt.py --from-beats beats.json --out-dir exports --name script
```

---

## فاز ۲ — تأیید، ساخت، کنترل کیفیت، رندر

### ۲.۱ ایستگاه تأیید (اجباری)
جدول استوری‌بورد به کاربر: `# | زمان | متن | کامپوننت kit | لوگوها | tone (light/alt/dark/accent)` + لینک `exports/script_recording_script.txt`.
هر تغییری در متن → ویرایش `beats.json` → اجرای مجدد `export_srt.py` → نمایش دوباره. بدون «تأیید» جلو نرو.

### ۲.۲ تایم‌لاین
```bash
python3 tools/generate_voice.py          # صدای کاربر: Zero-DSP + Whisper کلمه‌به‌کلمه | بدون گوینده: زمان‌بندی مصنوعی کلمات
```
در هر دو حالت `wordTime(b, i)` / `wordAt(b, 'کلمه')` کار می‌کند؛ هیچ ثانیه‌ای را دستی ننویس.

### ۲.۳ تصاویر AI (اگر صحنه‌ها تصویر لازم دارند)
**`references/ai-image-pipeline.md` را بخوان.** خلاصه:
```bash
# assets_plan.json را از روی استوری‌بورد بنویس (id, kind, subject ملموس و استعاری, accent)
python3 tools/generate_images.py --dry-run     # پرامپت‌ها از استایل فعال ساخته می‌شوند → به کاربر نشان بده
python3 tools/generate_images.py               # OPENAI_API_KEY لازم است؛ کش با هش پرامپت
python3 tools/stylize_assets.py                # حذف پس‌زمینه + نگاشت به ink/paper + رنگ‌آمیزی مجدد accent
```
`raw_img/_assets_sheet.jpg` را ببین؛ موارد معیوب را با `--only <id> --force` دوباره بساز. بدون کلید API: پرامپت‌های dry-run را به کاربر بده (یا `prompts/chatgpt-image-prompts.md`) تا در ChatGPT بسازد و در `raw_img/<id>.png` بگذارد.

### ۲.۴ صحنه‌ها (`src/scenes.tsx`)
**اول `references/motion-direction.md` و `examples/ai_tools_reel/scenes.tsx` را بخوان.**
- فقط از `./kit` ایمپورت کن: `Headline, Caption, BrandLogo, ToolCard, LogoHub, Versus, FeatureList, StatCounter, ScreenFrame, PromptBox, ChatBubble, CodeCard, Prop, TornReveal, Stamp, Arrow, CTA` + `PAL`, `THEME`.
- رنگ فقط `PAL.*`، اندازه متن فقط role (`setup/focus/hero/mega`)، زمان فقط از تایم‌لاین.
- هر صحنه `tone` دارد؛ متن‌ها خودکار رنگ خوانا می‌گیرند. ریتم: حداکثر ۲ صحنه پشت‌سرهم با یک tone.
- تعداد آیتم‌ها = عدد گفته‌شده در متن («۳ ابزار» → دقیقاً ۳).
- تصاویر AI (`Prop`, `TornReveal`) فقط از پایپ‌لاین ۲.۳ (هم‌استایل). کلیشه‌ها ممنوع (ساعت شنی، ترازو، پازل، چرخ‌دنده، تاس، بی‌نهایت، ربات/مغز نئونی).

### ۲.۵ میکس، استیل‌ها، رندر
```bash
python3 tools/build_mix.py                        # SFX خودکار؛ استایل می‌تواند بانک صدا را عوض کند (paper → صدای کاغذ)
python3 tools/render_reel.py --stills-only        # QA ایستا + استیل هر beat + QA پیکسلی + _contact_sheet.jpg
```
شیت تماس را **ببین**: متن بیرون از حاشیه ۱۳۰px، هم‌پوشانی، کنتراست ضعیف، صحنه خالی، لوگوی اشتباه. اصلاح → تکرار.
```bash
python3 tools/render_reel.py                      # خروجی: ../<PROJECT_NAME>-output/*.mp4 + .srt
```
نکته سرعت: `surface.roughEdges: false` در `brand.json → styleOverrides` رندر پیش‌نمایش paper_cut را ~۲ برابر سریع‌تر می‌کند؛ برای خروجی نهایی true بماند.

---

## تغییر استایل (بدون دست زدن به صحنه‌ها)
```bash
python3 tools/set_style.py --list
python3 tools/set_style.py studio_mono
```
رنگ برای هر محتوا: `brand.json → "palettePreset": "neon_yellow"` (لیست در `style.json → palettePresets`) یا رنگ دلخواه با `"styleOverrides": {"palette": {"accent": "#..."}}`؛ بعدش `python3 tools/sync_inputs.py && python3 tools/stylize_assets.py` (تصاویر هم رنگ جدید می‌گیرند).
استایل جدید: `references/style-packs.md` (کپی نزدیک‌ترین پک، تغییر توکن‌ها و پیاده‌سازی ۹ اسلات قرارداد `Theme`).

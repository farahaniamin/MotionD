# پوشه ورودی‌های شما (`user_inputs`)

فقط با همین پوشه کار دارید. همه‌چیز اختیاری است.

### `brand.json`
- `style`: استایل ویدیو (`paper_cut`، `studio_mono`، یا هر استایلی که در `styles/` بسازید). تغییر سریع: `python3 tools/set_style.py <name>`
- `palettePreset`: رنگ تأکیدی متناسب با محتوا (مثلاً `red_noir`، `neon_yellow`، `swiss_mustard`، `newsroom_maroon`، `tech_blue`).
- `wordmark`، `outroTagline`، `outroFooter`: نام برند بالای قاب و اوترو.
- `styleOverrides`: تغییر رنگ/حرکت روی استایل فعلی بدون ساخت استایل جدید، مثلاً `{"palette": {"accent": "#7C3AED"}}`
- `fontFa` / `fontLatin`: انتخاب فونت از کتابخانه (فارسی: `YekanBakh`، `Vazirmatn`، `Lalezar`، `ReemKufi`، `NotoKufi`، `ElMessiri`، `Lemonada`، `Changa`، `Baloo` — لاتین: `Oswald`، `Nunito`، `Inter`، `Anton`، `BebasNeue`، `ArchivoBlack`، `SpaceGrotesk`، `Playfair`، `DMSerif`، `SpecialElite`). `null` = پیش‌فرض.

### `logos/`
اگر لوگوی یک ابزار به‌صورت خودکار پیدا نشد، فایل **SVG رسمی** آن را (از صفحه brand یا press سایت خودش) با نام `<slug>.svg` اینجا بگذارید؛ مثلاً `logos/kling.svg`. لوگو هرگز ساخته یا کشیده نمی‌شود.

### `fonts/`
فونت جدید (`.woff2/.ttf/.otf`) اینجا → خودکار فعال می‌شود.

### `assets/`
- `match_theme/`: دوربری + هماهنگ‌سازی رنگ با استایل
- `need_cutout/`: فقط دوربری با رنگ اصلی
- `ready/`: بدون تغییر (اسکرین‌شات، ویدیوی دمو)

### `audio/`
- `voice/`: صدای خودتان یا ElevenLabs — ۱۰۰٪ دست‌نخورده (Zero-DSP)، زمان کلمات با Whisper.
- `music/`: موزیک پس‌زمینه (خودکار زیر صدا Duck می‌شود).

### `reference_videos/custom/`
ویدیوی نمونه برای ساخت یک استایل‌پک جدید شبیه آن.

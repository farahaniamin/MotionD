# استایل‌پک‌ها — تغییر یا ساخت استایل

یک استایل = یک پوشه در `styles/<name>/`:

| فایل | نقش |
| :-- | :-- |
| `style.json` | توکن‌ها: `palette`, `typography` (نقش‌ها + فونت لاتین)، `motion` (stepFps، boil، overshoot، stagger)، `surface`, `logo`, `transitions` (first + cycle)، `sfx.remap`، `assets.propPrompt` |
| `theme.tsx` | پیاده‌سازی قرارداد `Theme` (`src/engine/contract.ts`) |
| `guide.md` | قواعد هنری استایل برای ایجنت (چه بکن/چه نکن) |
| `fonts/` | فونت‌های متعلق به استایل (به `public/fonts/style/` کپی می‌شوند) |
| `textures/` | بافت‌های از پیش‌پخته (به `public/style/textures/`) |

## قرارداد Theme (۹ اسلات)
`Backdrop` · `Surface` · `Highlight` · `LogoTreatment` · `Sticker` · `Overlay` · `BrandMark` · `Outro` · `transitions` (+ `Defs` برای فیلترهای SVG).
کل کیت فقط از این اسلات‌ها شکل می‌گیرد، پس با پیاده‌سازی آن‌ها کل ریلز عوض می‌شود.

## ساخت استایل جدید (مثلاً `clay_3d`, `neo_brutalism`, `blueprint`)
1. `cp -r styles/paper_cut styles/<new>` (یا studio_mono، هر کدام نزدیک‌تر است).
2. `style.json`: پالت (حتماً `ink` روی `bg` و `onDark` روی `bgDark` کنتراست ≥ ۴.۵)، نقش‌های تایپ، `motion.stepFps` (null = نرم، 12 = استاپ‌موشن، 8 = خیلی دست‌ساز)، چرخه ترنزیشن.
3. `theme.tsx`: اسلات‌ها را بازنویسی کن. قانون‌ها:
   - هیچ متنی را فیلتر displacement/blur دائمی نکن؛ افکت فقط روی لایه پس‌زمینه عنصر.
   - `LogoTreatment` هندسه را تغییر نمی‌دهد: فقط حاشیه، سایه، بافت، کپسول، لایه‌بندی رنگ‌ها.
   - نویز/بافت را به PNG پخته کن (`feTurbulence` زنده هر فریم ~۳ برابر رندر را کند می‌کند).
   - نام ترنزیشن‌های `first`/`cycle` باید در `transitions` تعریف شوند؛ `cut` و `pop` را همیشه داشته باش.
4. `sfx.remap`: صداهای پیش‌فرض را به بانک استایل نگاشت کن (مثل `whoosh/... → paper/slide_1`). فایل‌ها در `resources/sfx/<bank>/`.
5. `assets.propPrompt`: پرامپت تصویرسازی هم‌استایل (`<OBJECT>` جایگزین می‌شود).
6. تست: `python3 tools/set_style.py <new>` روی `examples/ai_tools_reel` → `render_reel.py --stills-only` → شیت تماس.

## از روی ویدیوی رفرنس
`python3 tools/analyze_references.py --dir user_inputs/reference_videos/custom` پالت، کادانس و شیت ۲۴ فریمی می‌دهد (دیگر brand.json را بازنویسی نمی‌کند). ایجنت شیت را می‌بیند و با مراحل بالا یک استایل‌پک جدید می‌سازد؛ نتیجه برای همیشه قابل‌استفاده است.

## override سبک برای یک برند
بدون ساخت استایل جدید: در `user_inputs/brand.json`:
```json
"styleOverrides": {"palette": {"accent": "#7C3AED", "highlight": "#FDE047"}, "motion": {"boil": 0.5}}
```

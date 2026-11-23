# صدا و افکت‌ها (v2)

**تغییرات v2:**
- **بانک صدای وابسته به استایل:** `style.json → sfx.remap` هر فایل پیش‌فرض را به بانک استایل نگاشت می‌کند (paper_cut: `whoosh/* → paper/slide_*`، `shutter/* → paper/tap_*`، `misc/stamp → paper/slap`، ...). `sfx.cutBoom: false` بوم سینمایی روی هر کات را خاموش می‌کند. `sfx.musicMood` حال‌وهوای موزیک synth را تعیین می‌کند.
- **تشخیص خودکار کامپوننت‌های کیت v2:** `Stamp`→stamps، `ToolCard/ScreenFrame/PromptBox/CodeCard/ChatBubble/CTA`→pills، `LogoHub/Versus/Arrow`→diagrams، `FeatureList`→chips، `StatCounter`→counters، `BrandLogo`→hero_words، `mark` در Headline→ribbon_draws.
- **کنترل چگالی:** حداقل فاصله بین افکت‌های تأکیدی (hero ۰.۹s، پول/هشدار ۱.۵s، شمارنده ۱.۲s) تا صدا شلوغ نشود.
- **حالت بدون گوینده:** زمان‌بندی مصنوعی کلمات از روی `display`، پس `wordTime` و SFX کلمه‌محور کار می‌کنند.
- پیشنهاد مسترینگ: برای اینستاگرام، خروجی نهایی را حدود −14 LUFS نگه دارید؛ اگر صدا آرام است، فقط gain خطی کل میکس را بالا ببرید (نه کمپرسور روی صدا).

---

# راهنمای مهندسی صدای ۱۰۰٪ اورجینال (`Zero-DSP Original Voice`) و کتابخانه ۹۲ فایلی SFX (پایه v1)

این سند معماری صوتی **۱۰۰٪ وفادار به صدای اصلی (`Bit-Transparent / Zero-DSP`)**، یکپارچه‌سازی با صدای ضبط‌شده کاربر یا ElevenLabs، ترازبندی کلمه‌به‌کلمه فارسی با `faster-whisper` و میکس شفاف افکت‌های `48kHz FLAC` را مشخص می‌کند.

---

## ۱. اصل طلایی نسخه ۳.۱: حفظ ۱۰۰٪ صدای اورجینال بدون هیچ فیلتر مخرب (`Zero Denoise / Zero EQ / Zero Pumping`)

بر اساس بازخورد مهندسی، هرگونه فیلتر حذف نویز (`afftdn`)، اکولایزر، کمپرسور یا `loudnorm` تک‌مرحله‌ای روی صدای ورودی کاربر **به‌طور کامل حذف شده است**:
1. **دیکد ۱۰۰٪ شفاف (`48kHz Stereo Float32 -> 24-bit PCM WAV`):**
   - وقتی فایلی در `user_inputs/audio/voice/` قرار می‌گیرد (چه صدای ساخته‌شده در ElevenLabs و چه صدای ضبط‌شده شخصی)، شکل موج، فرکانس‌های بالا (`> 4kHz`)، زنگ طبیعی صدا، تنفس‌ها و داینامیک آن **۱۰۰٪ دست‌نخورده و اورجینال** باقی می‌ماند (بدون برش و تکه‌تکه کردن جملات و بدون هیچ فیلتر FFmpeg).
2. **ترازبندی کلمه‌به‌کلمه فقط خواندنی (`Read-Only Whisper Alignment`):**
   - مدل آفلاین `faster-whisper` صرفاً از روی یک بافر موقت در حافظه، زمان دقیق ادا شدن تک‌تک کلمات فارسی را استخراج کرده و در `src/timeline.json` و زیرنویس `exports/reel_script.srt` ثبت می‌کند؛ خودِ فایل صوتی خروجی هیچ تغییری نمی‌کند.
3. **میکس خطی بدون پمپ داینامیک (`Zero-Pumping Linear Mix` در [`build_mix.py`](../scripts/build_mix.py)):**
   - فیلترهای `alimiter` و `loudnorm` از مرحله میکس نهایی حذف شده‌اند تا صدای گوینده هرگز پمپ یا کلیپ نشود (`0.000% Clipping`).
   - بلندی موزیک پس‌زمینه و افکت‌های صوتی به‌صورت خودکار **متناسب با RMS طبیعی صدای اورجینال** تنظیم و زیر کلام Duck می‌شوند تا صدای گوینده با همان شفافیت فایل اصلی در مرکز تصویر بدرخشد.
   - خروجی نهایی در `render_reel.py` با بالاترین بیت‌ریت استودیویی **`320kbps AAC`** کنار ویدیو Mux می‌شود.

---

## ۲. پیش‌تولید اسکریپت گویندگی (`Pre-Production Script Export`)
پیش از ساخت تصویر و ویدیو، دستور زیر از روی `beats.json` سه فایل آماده در `exports/` می‌سازد:
```bash
python3 tools/export_srt.py --from-beats beats.json --out-dir exports --name script
```
- `script_recording_script.txt`: متن شماره‌گذاری‌شده تمیز برای ضبط صدای خود کاربر با میکروفون/موبایل.
- `script_elevenlabs_v2.txt`: متن آماده **Multilingual v2 / Flash v2.5** با `<break time="0.5s" />`، `...` و `-`.
- `script_elevenlabs_v3_v4.txt`: متن آماده **Eleven v3 / v4** با `[pause]` / `[short pause]`، `...` و `—`.

---

## ۳. موتور هوشمند طراحی صدا و نقشه افکت‌های صوتی استودیویی (`Auto-SFX Engine`)

در نسخه ۳.۳، موتور پایتون [`build_mix.py`](../scripts/build_mix.py) مجهز به **`Auto-SFX Engine`** یکپارچه است که کلیه کامپوننت‌های واقعی `kit.tsx` و کلمات کوبنده را بدون نیاز به تنظیم دستی صداگذاری می‌کند:
1. **پارس زنده کامپوننت‌های بصری در `src/scenes.tsx`:**
   - هر `<BanStamp>` به صدای مهر استودیویی (`stamp.flac`) + ساب ایمپکت (`cinematic_boom`) + گلیچ متصل می‌شود.
   - هر `<CautionWarningBadge>` به بیپ هشدار (`error_buzz.flac`) + گلیچ دیجیتال متصل می‌شود.
   - هر `<DarkPillStack>`, `<EditorialWindowCard>`, `<PushpinCard>`, `<CodeInspectorScan>`, `<MobileSkillCard>`, `<EditorialComparisonTable>` به باز شدن استودیویی کارت‌ها (`sweet_ui_open.flac`) متصل می‌شود.
   - هر `<MonochromeChipRow>` یا `<NumberedSkillGrid>` به کلیک ریز چیپ‌ها (`granular_button_select.flac`) متصل می‌شود.
   - هر `<NodeNetwork>`, `<RisingPillars>`, `<ComparisonBarChart>`, `<GradientBarChart>` به جمع‌آوری داده (`data/collect_2.flac`) + کشش وکتور (`ui/stretch.flac`) متصل می‌شود.
   - هر `<ContrastBlackCut>` به فلاش دیجیتال (`glitch_click` + `premium_and_smooth_pop`) متصل می‌شود.
   - هر `underlineAt` به خط‌کشی نرم نواری (`smooth_like_a_butter_whoosh.flac`) و هر `strikeAt` به خط‌خوردگی سریع متصل می‌شود.
   - هر `<SubPhase>` به کات شلاقی (`cinematic_fast_whoosh.flac`) و هر `role: 'hero'|'mega'` یا `<StackedAsymmetricLockup heroAt={...}>` به پاپ و کلیک کوبنده متصل می‌شود.
2. **آنالیز معنایی واژگان در `src/timeline.json`:**
   - واژگان تحریم و ممنوعیت (`بَن`، `ممنوع`، `بلاک`) -> افکت مُهر و بوم
   - واژگان ریسک و تورم (`ریسک`، `خطر`، `هشدار`، `تورم`، `راکد`) -> افکت هشدار
   - واژگان مالی و ثروت (`اقتصادی`، `هزینه`، `دلار`، `تومان`، `ثروت`، `سرمایه`، `سود`، `پول`) -> افکت صدای پول (`cinematic_money_1.flac`)
   - واژگان شاخص فناوری و سیستم (`هوش`، `مصنوعی`، `ایجنت`، `سیستم`، `الگوریتم`) -> پاپ و کلیک شاخص (`smooth_pop` + `cinematic_click`)
   - اعداد و شاخص‌های آماری فارسی و لاتین (`۱۰`, `۱۶X`, `۷۰٪`, `10X`) -> تیک‌های شمارنده دیجیتال (`click_digital_04`)
   - همچنین در حالت `music.mode = "synth"`, موتور بر اساس ژانر در `src/brand.json` حال‌وهوای موسیقی (`noir` / `bright` / `editorial`) را خودکار تطبیق می‌دهد.

کاربر همچنین می‌تواند هر رویداد را در `sfx_plan.json` به‌صورت دستی یا سفارشی اورراید کند. جدول کتابخانه ۹۲ افکت استودیویی:

| رویداد بصری | شناسایی خودکار | کلید در `sfx_plan.json` | فایل‌های FLAC استفاده‌شده |
| :--- | :--- | :--- | :--- |
| کات اصلی بین بیت‌ها | خودکار بر اساس `scene_end` | — | `smooth_and_fast_whoosh` + `smooth_camera_shutter` + `soft_gear_1` + `cinematic_boom` |
| مُهر قرمز بَن و ممنوعیت | `<BanStamp>` یا کلمه «بَن/ممنوع» | `stamps` | `misc/stamp` + `impact/cinematic_boom` + `ui/glitch_click` |
| کارت و نشان هشدار ریسک | `<CautionWarningBadge>` یا «ریسک/خطر» | `warnings` | `ui/error_buzz` + `ui/glitch_click` |
| واژگان مالی، هزینه و اشتراک | واژگان «اقتصادی/هزینه/دلار/شارژ/خرید» | `money` | `money/cinematic_money_1` + `click/cinematic_click` |
| کات شلاقی میانی | `<SubPhase>` | `sub_cuts` | `cinematic_fast_whoosh` + `camera_shutter` + `soft_gear_1` |
| رسم زنده نوار و خط زیر کلمات | `underlineAt` | `ribbon_draws` | `smooth_like_a_butter_whoosh` + `ui/stretch` |
| فلاش تبدیل وضعیت | فلش سفید و چرخش موتیف | `flashes` | `ui/glitch_click` + `premium_and_smooth_pop` |
| دیاگرام شبکه، نود و مدارها | `<NodeNetwork>` یا `<RisingPillars>` | `diagrams` | `data/collect_2` + `ui/stretch` |
| کلمات کلیدی بزرگ و مفاهیم هوش مصنوعی | `role="hero"` یا کلمات برند/مدل | `hero_words` | `pop/smooth_pop` + `click/cinematic_click` |
| خط‌خوردگی واژه | خط عبور از کلمه | `strikethroughs` | `whoosh/epic_fast_whoosh_345469` |
| شمارنده دیجیتال اعداد و درصدها | ارقام، درصدها و اعدادی مثل ۷۰٪ یا 10X | `counters` | `ui/click_digital_04` (مجموعه ۷ الی ۱۱ تیک پیاپی) |
| کارت‌های تیره استراتژی و پنجره‌ها | `<DarkPillStack>` یا `<EditorialWindowCard>` | `pills` | `pop/sweet_ui_open` + `ui/click_digital_04` |
| تگ‌ها و چیپ‌ها | `<MonochromeChipRow>` | `chips` | `ui/granular_button_select` |
| دکمه‌ها و تعامل‌های دعوت به اقدام (CTA) | دکمه‌های استودیویی کامنت و کلیک | `buttons` | `ui/button` + `click/cinematic_click` |
| حرکت مکانیکی سنگین چرخ‌دنده | موتیف‌های چرخشی بزرگ | `mechanics` | `smooth_and_premium_gear` |
| لیزر اسکن دیتابیس و کد | اسکنر عمودی روی لیست‌ها | `scans` | `misc/laser` |
| کشش و تغییر حالت نرم اسلایدر/نوار | انیمیشن‌های پیوسته اسلایدر | `stretches` | `ui/stretch` |
| سوئیچ و تاگل پنل تنظیمات | تغییر وضعیت کلیدهای روشن/خاموش | `switches` | `ui/button` + `click/high_click` |
| موفقیت و دستیابی به هدف | قفل شدن روی امتیاز ۹۹ یا تایید نهایی | `success` | پیش‌فرض مینیمال: `ui/enter` + `pop/smooth_pop` (یا `success/level_up` با `"fanfare": true`) |
| سکانس پایانی برند | خودکار در انتهای ویدیو (`voice_end`) | — | `smooth_riser` + `smooth_and_fast_whoosh` + `cinematic_boom` + `cinematic_click` |

> **هم‌زمانی فریم‌به‌فریم و چرخش تنوع (`Peak Alignment & Multi-Variant Banks`):** موتور [`build_mix.py`](../scripts/build_mix.py) تمام فایل‌های `.flac` را هنگام لود از نظر سکوت ابتدایی برش می‌دهد، هرگز قبل از پیک اصلی کوتاه نمی‌کند، افکت‌های زمان‌بندی‌شده مثل `whoosh`، `shutter`، `error_buzz` و `riser` را دقیقاً بر اساس نقطه‌ی اوج واقعی (`peak_t`) با لحظه کات تراز می‌کند، و در دسته‌های چندفایلی (`whoosh/`, `shutter/`, `pop/`, `data/`, `ui/`) بین چند نمونه مختلف چرخش (`round-robin`) انجام می‌دهد تا صداها در سکانس‌های متوالی تکراری نشوند. کلید `counters` همچنین از بازه پیوسته `{"from": ..., "to": ..., "ticks": ...}` برای هم‌گام‌سازی اسلایدرها پشتیبانی می‌کند.

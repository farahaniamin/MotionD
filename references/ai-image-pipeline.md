# پایپ‌لاین تصاویر AI (ایجنت → GPT Image → استایل → صحنه)

ایجنت خودش تصاویر هر صحنه را طراحی، تولید، هماهنگ و بازبینی می‌کند. نیاز: `OPENAI_API_KEY` در محیط (کاربر export می‌کند؛ هرگز کلید را در فایل ننویس).

## جریان کار
1. **طراحی** (بعد از تأیید سناریو): برای هر صحنه‌ای که تصویر لازم دارد یک آیتم در `assets_plan.json`:
   ```json
   {"assets": [
     {"id": "eyes",   "kind": "background", "subject": "extreme close-up of engraved eyes like a banknote portrait", "size": "1024x1536", "scene": 0},
     {"id": "bust",   "kind": "cutout", "subject": "classical Greek marble bust wearing futuristic VR goggles", "accent": "the goggles", "scene": 3},
     {"id": "mic",    "kind": "cutout", "subject": "a 1950s studio microphone", "scene": 5},
     {"id": "phone",  "kind": "cutout", "subject": "vintage rotary phone", "from": "user_inputs/assets/ready/phone.jpg"}
   ]}
   ```
   - `kind`: `cutout` (شیء جدا با پس‌زمینه شفاف) · `portrait` (فیگور ناشناس) · `background` (پلیت تمام‌صفحه برای TornReveal / پس‌زمینه) · `texture`.
   - `accent`: تنها بخشی که رنگ تأکیدی می‌گیرد. خالی = کاملاً سیاه‌وسفید.
   - `from`: تصویر موجود کاربر که باید به همین استایل «بازکشیده» شود (edits endpoint).
   - `subject` را **ملموس و استعاری** بنویس، نه انتزاعی: «تمرکز» → «a magnifying glass over a tangled telephone cord»، نه «focus concept».
2. **پیش‌نمایش پرامپت‌ها**: `python3 tools/generate_images.py --dry-run` — لیست را در جدول استوری‌بورد به کاربر نشان بده (تعداد تصاویر = هزینه).
3. **تولید**: `python3 tools/generate_images.py` — مدل به‌صورت خودکار جدیدترین `gpt-image-*` حساب کاربر انتخاب می‌شود (`--model` برای انتخاب دستی، `--list-models`). نتایج با هش پرامپت کش می‌شوند.
4. **هماهنگ‌سازی**: `python3 tools/stylize_assets.py` — حذف پس‌زمینه (آلفای API یا کروماکی)، تریم مربعی، نگاشت تونال به ink/paper دقیق استایل، رنگ‌آمیزی مجدد المان تأکیدی به accent پروژه. خروجی `public/img/<id>.png`.
5. **بازبینی (اجباری)**: `raw_img/_assets_sheet.jpg` را ببین. رد کن و دوباره بساز اگر: متن/حروف/واترمارک، لوگو، دست/صورت دفرمه، بیش از یک رنگ، پس‌زمینه کامل حذف نشده، شیء بریده‌شده. اصلاح `subject` + `--only <id> --force`.
6. **استفاده**: `<Prop src="img/bust.png" .../>`، `<TornReveal src="img/eyes.png" .../>`، `<ScreenFrame>` برای اسکرین‌شات واقعی.

## قوانین
- **لوگوها هرگز تولید نمی‌شوند** (فقط `logo_fetch.py`). اگر شیء تولیدی باید «برند» داشته باشد، لوگوی واقعی را با `<BrandLogo>` رویش بگذار.
- آدم واقعی و قابل‌شناسایی تولید نکن؛ فیگورها ناشناس یا مجسمه‌های کلاسیک.
- حداکثر ۳–۵ تصویر برای یک ریلز ۳۰ ثانیه‌ای؛ بقیه صحنه‌ها با کیت (کارت، لوگو، عدد، پرامپت‌باکس).
- تغییر رنگ/preset بعد از تولید → فقط `stylize_assets.py` دوباره (نه تولید مجدد).
- بدون کلید API: پرامپت‌های `--dry-run` را به کاربر بده تا در ChatGPT بسازد و فایل‌ها را در `raw_img/<id>.png` بگذارد؛ ادامه کار یکسان است.

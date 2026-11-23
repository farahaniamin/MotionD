# پرامپت‌های ساخت تصویر در ChatGPT — استایل Vox Collage / Paper Cut ادیتوریال

این فایل برای استفاده **دستی** در ChatGPT (یا هر مدل تصویر دیگر) است. ایجنت همین منطق را خودکار از `styles/vox_collage/style.json` می‌سازد.

## نحوه استفاده
1. **یک بار در اول گفتگو** «بلوک استایل پایه» را بفرست تا ChatGPT استایل را یاد بگیرد.
2. بعد برای هر تصویر فقط پرامپت کوتاه همان نوع را بفرست و `[...]` ها را پر کن.
3. `[ACCENT]` را با رنگ تأکیدی همان ویدیو عوض کن (مثلاً `red #D3221B`، `neon yellow #F2E205`، `cobalt blue #1F4BFF`). مهم نیست دقیق باشد؛ `stylize_assets.py` رنگ را دقیقاً با پالت پروژه یکی می‌کند.
4. کات‌اوت‌ها را **PNG با پس‌زمینه شفاف** بخواه. اگر شفاف نداد، پس‌زمینه سبز یکدست `#00FF00` بخواه؛ اسکیل خودش حذفش می‌کند.
5. فایل را با نام `id` در `raw_img/<id>.png` پروژه بگذار و `python3 tools/stylize_assets.py` را اجرا کن.

> ⚠️ **لوگوی برندها را هرگز با AI نساز.** لوگوها فقط از `logo_fetch.py` می‌آیند. آدم واقعی و قابل‌شناسایی هم نساز.

---

## ۰) بلوک استایل پایه (اول گفتگو بفرست)

```text
For this whole conversation, every image you create must follow this exact art direction:

STYLE: Vintage editorial paper-collage, like a Vox explainer video.
- Subjects are rendered as detailed black-and-white copperplate ENGRAVING / etching (fine crosshatching, line-screen and halftone dots, like the portrait on a banknote), high contrast, printed-on-paper look with subtle paper grain.
- Exactly ONE spot color: [ACCENT]. It is used flat (like screen-printed ink) on ONE key element only. Everything else is black ink on off-white paper (#F4EFE4).
- Materials of the collage world: crumpled paper, torn paper edges showing the white paper core, old newspaper scraps, halftone dots, masking tape, postage-stamp perforations.
- Never: gradients, glossy 3D, plastic, neon glow, photorealistic color photos, text, letters, numbers, logos, watermarks, real identifiable people.
- Composition: bold, simple, one clear focal point, lots of breathing room.

Reply "Ready" and wait for my image requests.
```

---

## ۱) کات‌اوت شیء (پرکاربردترین — برای `Prop`)

```text
Create a cut-out: [OBJECT — e.g. "a 1950s studio microphone"].
Paint ONLY [ACCENT ELEMENT — e.g. "the microphone grille"] in flat [ACCENT]; everything else black-and-white engraving.
Single object, centered, fully visible with generous margin, clean silhouette for a die-cut sticker.
Transparent background PNG, square 1:1. No shadow, no frame, no text.
```

**ایده‌های استعاری برای محتوای AI/تکنولوژی** (به‌جای کلیشه‌های ربات و مغز نئونی):
| مفهوم | شیء پیشنهادی | المان رنگی |
| :-- | :-- | :-- |
| هوش مصنوعی / مدل زبانی | مجسمه نیم‌تنه یونانی با هدست VR یا عینک | عینک |
| سرعت / اتوماسیون | تلگراف یا ماشین‌تحریر قدیمی | کلیدها |
| داده / حافظه | کابینت کارت‌های کتابخانه، کشوی باز | کارت بیرون‌آمده |
| جستجو | ذره‌بین روی نقشه قدیمی | دسته ذره‌بین |
| کدنویسی | ماشین‌حساب مکانیکی / کارت پانچ | کارت پانچ |
| خبر / اعلام | بلندگوی قیفی، میکروفون رادیویی | دهانه بلندگو |
| پول / قیمت | سکه یا اسکناس حکاکی‌شده، گاوصندوق | قفل گاوصندوق |
| رقابت | مهره شطرنج اسب | مهره |
| توجه / تمرکز | چشم حکاکی‌شده (اسکناسی) | عنبیه |
| خطر / هشدار | تله موش قدیمی، فیتیله دینامیت | فیتیله |
| خلاقیت | دست مجسمه که قلم‌مو گرفته | قلم‌مو |

---

## ۲) پلیت پس‌زمینه تمام‌صفحه (برای `TornReveal` و پس‌زمینه صحنه)

```text
Create a full-bleed vertical background plate (2:3): [SCENE — e.g. "extreme close-up of a pair of engraved eyes, like a banknote portrait, staring forward"].
Black-and-white engraving filling the frame, crumpled paper texture visible. The middle band must be strong and readable when shown through a torn strip.
Use [ACCENT] only on [ELEMENT or "nothing"]. No text, no logos.
```

---

## ۳) چهار خانواده استایل از رفرنس‌های تو

### A — «Torn Reveal Noir» (رفرنس چشم‌ها + کاغذ قرمز پاره)
```text
Create a vertical 2:3 image: a sheet of crumpled [ACCENT] paper torn open horizontally in the middle, revealing a detailed black-and-white banknote-style engraving of [SUBJECT — e.g. "eyes looking up"] underneath. Torn edges show white paper fibers. Vintage postage stamps scattered at the edges, slightly out of focus. Dramatic soft side light, shallow depth of field. No text, no real person.
```

### B — «Swiss Engraving Poster» (رفرنس شیر با عینک)
```text
Create a vertical 9:16 poster collage: a huge black-and-white engraving of [ANIMAL/SUBJECT — e.g. "a lion looking up proudly"], wearing [ACCENT OBJECT — e.g. "round sunglasses"] in flat [ACCENT]. Behind it: large flat [ACCENT] circles with halftone dot texture, a small mustard-yellow rectangle with swirling engraved texture, thin technical grid lines and dot matrices like a Swiss modernist poster. Off-white paper background. No text.
```

### C — «Statue Pop» (رفرنس مجسمه با عینک نئون)
```text
Create a 2:3 image: a classical Greek marble bust (anonymous, not a real person) rendered in gritty grayscale with stone texture, wearing [ACCENT OBJECT — e.g. "translucent futuristic shield glasses"] in glowing flat [ACCENT]. Behind the head: one big flat [ACCENT] circle with speckled print texture. Solid matte black background. Isolated, centered. No text.
```
*برای کات‌اوت همین مجسمه: انتهای پرامپت بنویس `transparent background PNG, no circle`.*

### D — «Newsroom Collage» (رفرنس روزنامه پاره + میکروفون)
```text
Create a vertical 9:16 background collage: crumpled black paper and crumpled deep [ACCENT] paper, divided by a diagonal torn strip of old newspaper (illegible tiny text, no real headlines). Around the edges, black-and-white halftone cut-out objects with white die-cut borders: [OBJECTS — e.g. "a megaphone, a vintage camera, a stage spotlight, a stack of microphones, a paper question mark"]. Keep the center empty for text. No readable words, no logos.
```

---

## ۴) تبدیل تصویر خودت به همین استایل (آپلود عکس)

```text
Redraw the attached image in the art direction above: keep the same subject, pose and composition, but render it as a black-and-white copperplate engraving with crosshatching and halftone dots. Paint only [ELEMENT] in flat [ACCENT]. [Transparent background PNG / Keep a crumpled off-white paper background]. Remove any text and logos.
```

---

## ۵) بافت‌ها (فقط اگر بخواهی بافت‌های پیش‌فرض اسکیل را عوض کنی)

```text
Flat top-down scan of [TEXTURE — "crumpled off-white paper" / "crumpled black paper" / "a torn strip of old newspaper with illegible text" / "a piece of beige masking tape"], evenly lit, no perspective, no objects, high detail paper fibers, square. No readable text.
```

---

## ۶) سری هماهنگ (چند شیء با یک ظاهر)

```text
Create [N] separate cut-out images, one per message, in the identical style (same line weight, same paper tone, same lighting, same [ACCENT]):
1. [OBJECT] — accent on [ELEMENT]
2. [OBJECT] — accent on [ELEMENT]
3. [OBJECT] — no accent
Each: centered, transparent background PNG, square, no text.
```

---

## چک‌لیست قبل از استفاده
- [ ] هیچ حرف، عدد یا واترمارکی در تصویر نیست
- [ ] فقط یک المان رنگی دارد
- [ ] لوگو یا چهره آدم واقعی ندارد
- [ ] شیء کامل است و لبه‌هایش بریده نشده
- [ ] پس‌زمینه شفاف یا سبز یکدست است (برای کات‌اوت)

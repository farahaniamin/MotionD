# کارگردانی موشن، الگوی صحنه‌ها و API کیت (v2)

## ۱. اصول حرفه‌ای (مستقل از استایل)

1. **یک ایده در هر قاب.** هر صحنه یک نقطه تمرکز دارد. اگر دو چیز مهم است، دو صحنه یا یک ساب‌بیت (`at` دیرتر) بساز.
2. **حرکت با کلام.** هر ورود به کلمه‌ای گره می‌خورد (`wordTime`/`wordAt`). عنصر ۰.۰۵ تا ۰.۱۵ ثانیه *قبل* از ادای کلمه وارد شود، نه بعد.
3. **سلسله‌مراتب زمانی (stagger).** عنوان → عنصر اصلی → جزئیات. فاصله‌ها از `MOTION.stagger` (توکن استایل) — هرگز همه با هم.
4. **Anticipation / Overshoot / Settle.** ورودی‌های کیت (`enter()`) خودشان overshoot استایل را دارند؛ دستی انیمیشن خطی ننویس.
5. **ریتم بوم.** `tone` صحنه‌ها را بچرخان: light → alt → light → dark/accent. یک صحنه dark/accent در هر ۴–۵ صحنه برای «نفس» و تأکید.
6. **قلاب ۱.۵ ثانیه‌ای.** صحنه اول: عدد/ادعا + لوگوهای واقعی در همان ثانیه اول. بدون مقدمه، بدون لوگوی برند خودت در ابتدا.
7. **مقیاس موبایل.** کوچک‌ترین متن `caption` (۲۴px). تیترها hero/mega. محتوای مهم بین y=240 و y=1520 (زیرنویس و UI اینستاگرام پایین قاب است).
8. **اثبات به‌جای ادعا.** برای ابزارها: اسکرین‌شات واقعی (`ScreenFrame`)، پرامپت تایپ‌شونده (`PromptBox`)، نتیجه (`ChatBubble`/`CodeCard`)، عدد (`StatCounter`). UI ساختگی فقط وقتی نسخه واقعی در دسترس نیست.
9. **صدا = نیمی از موشن.** هر ورود مهم صدا دارد؛ `build_mix.py` از روی کامپوننت‌ها خودکار می‌گذارد و چگالی را محدود می‌کند. صحنه‌ای که همه‌چیزش «پاپ» دارد، هیچ چیزش تأکید ندارد.
10. **پایان.** CTA یک‌جمله‌ای با کلمه کلیدی هایلایت (`CTA keyword`)؛ اوترو برند خودکار از تم.

## ۲. الگوی صحنه‌ها برای ویدیوهای معرفی ابزار AI

| کاربرد | ترکیب پیشنهادی |
| :-- | :-- |
| قلاب «N ابزار برای X» | `Headline` (عدد با `mark`) + N × `BrandLogo` با فاصله زمانی |
| معرفی یک ابزار | `Headline` («اولی: Name» با hero لاتین) + `ToolCard` (لوگو، تگ‌لاین، url) + `Stamp` اختیاری |
| «چطور کار می‌کنه» | `PromptBox` (تایپ) → `Arrow` → `ChatBubble`/`CodeCard` |
| نمایش سایت/محصول | `ScreenFrame` با اسکرین‌شات `capture_site.py` + `scrollDur` |
| عدد/قابلیت | `StatCounter` (+ لوگوی کوچک بالای آن) |
| مقایسه | `Versus` یا `FeatureList` با `logo` در هر آیتم |
| اکوسیستم/ادغام‌ها | `LogoHub` (مرکز: ابزار اصلی، ماهواره‌ها: ادغام‌ها) |
| لیست مراحل/ترفندها | `FeatureList` (تعداد = عدد گفته‌شده) |
| هشدار/قیمت/رایگان | `Stamp` («رایگان»، «NEW»، «$20») |
| پایان | `LogoHub` یا `ToolCard` خلاصه + `CTA` |

## ۳. API کیت (همه از `./kit`)

همه کامپوننت‌ها `t` (زمان فعلی) و `at` (زمان ورود) می‌گیرند. موقعیت مطلق با `x`,`y` (مرکز) یا `top`.

```tsx
<Headline t top={330} align="center|right|left" lines={[[{text, at, role:'setup|focus|hero|mega', mark?: true|PAL.x, tone?: 'ink|soft|accent|accent2'}], ...]} />
<Caption t at text top tone="soft|ink" />
<BrandLogo id="claude" t at size={220} x? y? variant="icon|wordmark" />
<ToolCard id t at name? tagline? url? w={680} logoSize={200} x y fill? />
<LogoHub t at center={{id}|{text}} satellites={['a','b']} cx cy radius satSize />
<Versus t at left="cursor" right="claude" y />
<FeatureList t at top items={[{title, sub?, logo?}]} times?={[wordTime(..)]} itemH gap />
<StatCounter t at to from? dur? prefix? suffix? label y persianDigits? />
<ScreenFrame t at src="img/screens/x.png" url? top w h scrollDur? />
<PromptBox t at text top cps logo? />
<ChatBubble t at text from="user|ai" top logo? />
<CodeCard t at lines={[...]} top title? />
<Prop t at src="img/x.png" x y w rot? float? out? />
<Stamp t at text x y fill? rotate? size? />
<Arrow t at from={[x,y]} to={[x,y]} bend? />
<CTA t at text keyword? y />
```

صحنه:
```tsx
export const SCENES: SceneDef[] = [{fn: S0, s: beatStart(0), e: beatEnd(0), tone: 'light', transition?: 'tear'}];
```
`transition` اختیاری است (نام از `THEME.transitions` استایل فعال؛ پیش‌فرض: چرخه `style.transitions.cycle`). اگر نام در استایل دیگر وجود نداشت، cut می‌شود — پس برای استقلال استایل معمولاً آن را خالی بگذار.

کامپوننت جدید لازم شد؟ آن را در `src/kit/` بنویس، فقط با `THEME.Surface/Highlight/Sticker/LogoTreatment` و `PAL`/`roleStyle` — تا در همه استایل‌ها درست دیده شود.

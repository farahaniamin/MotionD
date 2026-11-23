// Example reel: "3 AI coding tools". Style-agnostic: no colors, radii or shadows here —
// run `python3 tools/set_style.py studio_mono` and the same file renders in a different style.
import React from 'react';
import {
  SceneDef,
  SceneFn,
  Headline,
  Caption,
  BrandLogo,
  ToolCard,
  LogoHub,
  Versus,
  StatCounter,
  PromptBox,
  ChatBubble,
  CodeCard,
  Stamp,
  Arrow,
  CTA,
  PAL,
  beatStart,
  beatEnd,
  wordTime,
} from './kit';

// 0 — Hook: big claim + the three real logos land one after another
const S0: SceneFn = (t) => (
  <>
    <Headline
      t={t}
      top={330}
      lines={[
        [
          {text: 'سه', at: wordTime(0, 0), role: 'hero', mark: true},
          {text: 'ابزار', at: wordTime(0, 1), role: 'focus'},
        ],
        [
          {text: 'هوش مصنوعی', at: wordTime(0, 2), role: 'focus', tone: 'accent'},
          {text: 'که', at: wordTime(0, 4), role: 'setup', tone: 'soft'},
        ],
        [
          {text: 'کدنویسی', at: wordTime(0, 5), role: 'setup'},
          {text: 'رو عوض کردن', at: wordTime(0, 6), role: 'setup'},
        ],
      ]}
    />
    <BrandLogo id="claude" t={t} at={wordTime(0, 5)} size={190} x={790} y={1180} />
    <BrandLogo id="cursor" t={t} at={wordTime(0, 5) + 0.25} size={190} x={540} y={1260} />
    <BrandLogo id="gemini" t={t} at={wordTime(0, 5) + 0.5} size={190} x={290} y={1180} />
  </>
);

// 1 — Tool #1
const S1: SceneFn = (t) => (
  <>
    <Headline
      t={t}
      top={300}
      lines={[[{text: 'اولی:', at: wordTime(1, 0), role: 'setup', tone: 'soft'}, {text: 'Claude', at: wordTime(1, 1), role: 'hero'}]]}
    />
    <ToolCard id="claude" t={t} at={wordTime(1, 2)} tagline="برای فکر کردن روی کدهای بزرگ" url="claude.ai" w={760} logoSize={250} x={540} y={1060} />
    <Stamp t={t} at={wordTime(1, 6)} text="#۱" x={800} y={700} fill={PAL.highlight} />
  </>
);

// 2 — Tool #2 + code proof
const S2: SceneFn = (t) => (
  <>
    <Headline
      t={t}
      top={300}
      lines={[[{text: 'دومی:', at: wordTime(2, 0), role: 'setup', tone: 'soft'}, {text: 'Cursor', at: wordTime(2, 1), role: 'hero'}]]}
    />
    <BrandLogo id="cursor" t={t} at={wordTime(2, 1)} size={150} x={540} y={640} />
    <CodeCard
      t={t}
      at={wordTime(2, 2)}
      top={800}
      title="@codebase  ·  agent mode"
      lines={['> refactor auth to use sessions', '  ✓ read 214 files', '  ✓ edited 9 files', '  ✓ tests passing']}
    />
    <Caption t={t} at={wordTime(2, 4)} top={1390} text="ادیتوری که کل پروژه رو می‌فهمه" tone="ink" />
  </>
);

// 3 — Tool #3 as a stat (dark scene to break rhythm)
const S3: SceneFn = (t) => (
  <>
    <Headline
      t={t}
      top={300}
      lines={[[{text: 'سومی:', at: wordTime(3, 0), role: 'setup', tone: 'soft'}, {text: 'Gemini', at: wordTime(3, 1), role: 'hero'}]]}
    />
    <BrandLogo id="gemini" t={t} at={wordTime(3, 1)} size={170} x={540} y={660} />
    <StatCounter t={t} at={wordTime(3, 2)} to={1000000} label="توکن حافظه در یک درخواست" y={1060} persianDigits />
  </>
);

// 4 — Prompt → answer (the signature AI-tool shot)
const S4: SceneFn = (t) => (
  <>
    <Headline
      t={t}
      top={300}
      lines={[[{text: 'فقط بنویس', at: wordTime(4, 0), role: 'focus'}, {text: 'چی می‌خوای', at: wordTime(4, 2), role: 'focus', mark: true}]]}
    />
    <PromptBox t={t} at={wordTime(4, 1)} top={620} text="Build a landing page for my bakery" logo="claude" cps={26} />
    <Arrow t={t} at={beatStart(4) + 2.2} from={[700, 840]} to={[600, 1010]} />
    <ChatBubble t={t} at={beatStart(4) + 2.5} from="ai" logo="claude" top={1060} text="Done — hero, menu, map & contact form ✓" />
  </>
);

// 5 — Head to head
const S5: SceneFn = (t) => (
  <>
    <Headline t={t} top={330} lines={[[{text: 'کدوم', at: wordTime(5, 0), role: 'hero', mark: true}, {text: 'برای تو بهتره؟', at: wordTime(5, 1), role: 'focus'}]]} />
    <Versus t={t} at={wordTime(5, 1)} left="cursor" right="claude" y={1020} />
  </>
);

// 6 — CTA
const S6: SceneFn = (t) => (
  <>
    <LogoHub t={t} at={beatStart(6)} center={{text: 'لیست کامل'}} satellites={['claude', 'cursor', 'gemini', 'chatgpt', 'perplexity']} cy={820} radius={300} satSize={120} />
    <CTA t={t} at={wordTime(6, 0)} text="کامنت کن" keyword="ابزار" y={1330} />
  </>
);

export const SCENES: SceneDef[] = [
  {fn: S0, s: beatStart(0), e: beatEnd(0), tone: 'light'},
  {fn: S1, s: beatStart(1), e: beatEnd(1), tone: 'alt'},
  {fn: S2, s: beatStart(2), e: beatEnd(2), tone: 'light'},
  {fn: S3, s: beatStart(3), e: beatEnd(3), tone: 'dark'},
  {fn: S4, s: beatStart(4), e: beatEnd(4), tone: 'light'},
  {fn: S5, s: beatStart(5), e: beatEnd(5), tone: 'alt'},
  {fn: S6, s: beatStart(6), e: beatEnd(6), tone: 'light'},
];

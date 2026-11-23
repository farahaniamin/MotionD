// Content blocks for AI-tool / tech explainer reels. All visuals come from THEME + PAL.
import React from 'react';
import {Img, staticFile} from 'remotion';
import {THEME} from '../theme/active';
import {FONT_FAMILY, LATIN_FAMILY, MONO_FAMILY, MOTION, PAL, SAFE_X, fontWeightStyle, hasPersian, paperColor, rem, roleStyle, textOn, toFaDigits, withAlpha} from '../engine/tokens';
import {boil, clamp, easeInOut, easeOut, enter, enterSoft, range, stepT} from '../engine/time';
import {useInk} from '../engine/scene';
import {BrandLogo} from './brand';

const fam = (s: string) => (hasPersian(s) ? FONT_FAMILY : LATIN_FAMILY);

/** Numbered list. Render exactly as many items as the script says (count consistency). */
export const FeatureList: React.FC<{
  t: number;
  at: number;
  items: {title: string; sub?: string; logo?: string}[];
  top: number;
  itemH?: number;
  gap?: number;
  /** per-item reveal times (e.g. wordTime per item); defaults to staggered from `at` */
  times?: number[];
}> = ({t, at, items, top, itemH = 190, gap = 34, times}) => (
  <div style={{position: 'absolute', top, left: SAFE_X - 20, right: SAFE_X - 20, direction: 'rtl'}}>
    {items.map((it, i) => {
      const a = times?.[i] ?? at + i * MOTION.stagger * 3;
      const p = enter(t, a);
      const badge = paperColor(i + 1);
      return (
        <div key={i} style={{marginBottom: gap, opacity: clamp(p * 3), transform: `translateX(${(1 - clamp(p)) * -260}px) rotate(${(1 - clamp(p)) * -3}deg)`}}>
          <THEME.Surface w="100%" h={itemH} elevation={1} seed={i + 3} padding="0 34px">
            <div style={{display: 'flex', alignItems: 'center', height: '100%', gap: 30}}>
              <THEME.Sticker fill={badge} seed={i + 1} rotate={-4 + i * 3}>
                <span style={{fontFamily: FONT_FAMILY, ...roleStyle('focus'), lineHeight: 1}}>{toFaDigits(i + 1)}</span>
              </THEME.Sticker>
              <div style={{flex: 1}}>
                <div style={{fontFamily: fam(it.title), fontSize: rem(2.9), ...fontWeightStyle(850), lineHeight: 1.15}}>{it.title}</div>
                {it.sub && <div style={{fontFamily: fam(it.sub), fontSize: rem(1.7), ...fontWeightStyle(550), opacity: 0.75, marginTop: 6}}>{it.sub}</div>}
              </div>
              {it.logo && <BrandLogo id={it.logo} t={t} at={a + 0.1} size={110} />}
            </div>
          </THEME.Surface>
        </div>
      );
    })}
  </div>
);

/** Counting number with label. */
export const StatCounter: React.FC<{
  t: number;
  at: number;
  from?: number;
  to: number;
  dur?: number;
  prefix?: string;
  suffix?: string;
  label: string;
  decimals?: number;
  persianDigits?: boolean;
  y?: number;
  w?: number;
}> = ({t, at, from = 0, to, dur = 1.1, prefix = '', suffix = '', label, decimals = 0, persianDigits = true, y = 1000, w = 720}) => {
  const p = enter(t, at);
  const v = from + (to - from) * easeOut(range(stepT(t), at + 0.1, dur));
  const num = Number(v.toFixed(decimals)).toLocaleString('en-US', {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
  const shown = `${prefix}${persianDigits ? toFaDigits(num).replace(/,/g, '٬') : num}${suffix}`;
  return (
    <div style={{position: 'absolute', left: 540, top: y, transform: `translate(-50%, -50%) scale(${0.7 + 0.3 * clamp(p, 0, 1.1)})`, opacity: clamp(p * 3)}}>
      <THEME.Surface w={w} elevation={2} seed={8} padding="46px 40px">
        <div style={{textAlign: 'center', direction: 'rtl'}}>
          <div style={{fontFamily: FONT_FAMILY, ...roleStyle('mega'), lineHeight: 1}}>{shown}</div>
          <div style={{fontFamily: fam(label), ...roleStyle('body'), marginTop: 14, opacity: 0.8}}>{label}</div>
        </div>
      </THEME.Surface>
    </div>
  );
};

/** A real screenshot (public/img/screens/*.png from tools/capture_site.py) in a browser frame. */
export const ScreenFrame: React.FC<{
  t: number;
  at: number;
  src: string;
  url?: string;
  top?: number;
  w?: number;
  h?: number;
  /** scroll the screenshot from 0..1 of its overflow over this many seconds */
  scrollDur?: number;
}> = ({t, at, src, url, top = 560, w = 860, h = 940, scrollDur}) => {
  const p = enter(t, at);
  const scroll = scrollDur ? easeInOut(range(t, at + 0.5, scrollDur)) : 0;
  const bar = 70;
  return (
    <div style={{position: 'absolute', left: (1080 - w) / 2, top, opacity: clamp(p * 3), transform: `translateY(${(1 - clamp(p)) * 300}px) rotate(${(1 - clamp(p)) * 4}deg)`}}>
      <THEME.Surface w={w} h={h} elevation={2} seed={6} padding={14}>
        <div style={{height: bar, display: 'flex', alignItems: 'center', gap: 12, padding: '0 18px', direction: 'ltr'}}>
          {[PAL.papers[2], PAL.papers[1], PAL.papers[4]].map((c, i) => (
            <div key={i} style={{width: 20, height: 20, borderRadius: 10, background: c}} />
          ))}
          {url && (
            <div style={{marginLeft: 18, flex: 1, height: 40, borderRadius: 20, background: withAlpha(PAL.ink, 0.07), display: 'flex', alignItems: 'center', padding: '0 20px', fontFamily: LATIN_FAMILY, fontSize: rem(1.35), ...fontWeightStyle(600)}}>
              {url}
            </div>
          )}
        </div>
        <div style={{position: 'relative', height: `calc(100% - ${bar}px)`, overflow: 'hidden', borderRadius: 12}}>
          <Img src={staticFile(src)} style={{position: 'absolute', left: 0, top: 0, width: '100%', transform: `translateY(${-scroll * 55}%)`}} />
        </div>
      </THEME.Surface>
    </div>
  );
};

/** Generated/cut-out image prop (style-matched via the style's assets.propPrompt). */
export const Prop: React.FC<{t: number; at: number; src: string; x: number; y: number; w: number; rot?: number; float?: number; out?: number; seed?: number}> = ({
  t,
  at,
  src,
  x,
  y,
  w,
  rot = 0,
  float = 10,
  out,
  seed = 1,
}) => {
  const p = enter(t, at);
  const st = stepT(t);
  const b = boil(seed, t);
  const bob = Math.sin((st - at) * 2.2 + seed) * float;
  const leave = out !== undefined ? easeInOut(range(st, out, 0.3)) : 0;
  const style: React.CSSProperties = {
    position: 'absolute',
    left: x - w / 2,
    top: y - w / 2,
    width: w,
    opacity: clamp(p * 3) * (1 - leave),
    transform: `translate(${b.dx}px, ${bob + (1 - clamp(p)) * 240 + leave * 200}px) scale(${0.6 + 0.4 * p}) rotate(${rot + b.rot * 2 + (1 - clamp(p)) * 14}deg)`,
  };
  if (THEME.PropFrame) {
    return (
      <div style={style}>
        <THEME.PropFrame src={src} w={w} seed={seed} t={t} />
      </div>
    );
  }
  return <Img src={staticFile(src)} style={{...style, filter: `drop-shadow(0 22px 26px ${withAlpha(PAL.shadow, 0.3)})`}} />;
};

/** Slapped-on sticker / stamp ("رایگان", "NEW", "BANNED"). */
export const Stamp: React.FC<{t: number; at: number; text: string; x: number; y: number; fill?: string; rotate?: number; size?: number}> = ({t, at, text, x, y, fill, rotate = -8, size = 3.2}) => {
  const p = clamp(range(stepT(t), at, 0.2));
  const s = p < 1 ? 1.8 - 0.8 * easeOut(p) : 1;
  return (
    <div style={{position: 'absolute', left: x, top: y, transform: `translate(-50%, -50%) scale(${s})`, opacity: p > 0 ? 1 : 0, zIndex: 20}}>
      <THEME.Sticker fill={fill ?? PAL.accent} rotate={rotate}>
        <span style={{fontFamily: fam(text), fontSize: rem(size), ...fontWeightStyle(900), whiteSpace: 'nowrap'}}>{text}</span>
      </THEME.Sticker>
    </div>
  );
};

/** Prompt input with typing animation — the signature shot of AI-tool demos. */
export const PromptBox: React.FC<{t: number; at: number; text: string; top?: number; cps?: number; logo?: string; placeholder?: string}> = ({
  t,
  at,
  text,
  top = 1080,
  cps = 22,
  logo,
}) => {
  const p = enter(t, at);
  const typed = Math.floor(clamp((t - at - 0.35) * cps, 0, text.length));
  const done = typed >= text.length;
  const cursorOn = Math.floor(t * 2.4) % 2 === 0 || !done;
  const sendP = done ? enter(t, at + 0.35 + text.length / cps + 0.15) : 0;
  const rtl = hasPersian(text);
  return (
    <div style={{position: 'absolute', left: SAFE_X - 40, right: SAFE_X - 40, top, opacity: clamp(p * 3), transform: `translateY(${(1 - clamp(p)) * 160}px)`}}>
      <THEME.Surface w="100%" elevation={2} seed={12} padding="30px 30px">
        <div style={{display: 'flex', alignItems: 'center', gap: 22, direction: rtl ? 'rtl' : 'ltr'}}>
          {logo && <BrandLogo id={logo} t={t} at={at} size={74} />}
          <div style={{flex: 1, fontFamily: rtl ? FONT_FAMILY : LATIN_FAMILY, fontSize: rem(2.1), ...fontWeightStyle(600), minHeight: '1.4em', lineHeight: 1.35}}>
            {text.slice(0, typed)}
            <span style={{opacity: cursorOn ? 1 : 0, color: PAL.accent}}>|</span>
          </div>
          <div style={{width: 78, height: 78, borderRadius: 39, background: PAL.accent, color: textOn(PAL.accent), display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 40, transform: `scale(${1 + 0.18 * Math.sin(clamp(sendP) * Math.PI)})`}}>
            ↑
          </div>
        </div>
      </THEME.Surface>
    </div>
  );
};

/** Chat bubble (user or AI). */
export const ChatBubble: React.FC<{t: number; at: number; text: string; from: 'user' | 'ai'; top: number; logo?: string}> = ({t, at, text, from, top, logo}) => {
  const p = enter(t, at);
  const isAi = from === 'ai';
  const fill = isAi ? PAL.surface : PAL.papers[3];
  return (
    <div
      style={{
        position: 'absolute',
        top,
        left: SAFE_X - 30,
        right: SAFE_X - 30,
        display: 'flex',
        justifyContent: isAi ? 'flex-start' : 'flex-end',
        alignItems: 'flex-end',
        gap: 18,
        direction: 'ltr',
        opacity: clamp(p * 3),
        transform: `translateY(${(1 - clamp(p)) * 60}px) scale(${0.85 + 0.15 * clamp(p, 0, 1.05)})`,
        transformOrigin: isAi ? 'left bottom' : 'right bottom',
      }}
    >
      {isAi && logo && <BrandLogo id={logo} t={t} at={at} size={84} />}
      <div style={{maxWidth: 640}}>
        <THEME.Surface w="auto" fill={fill} elevation={1} seed={isAi ? 21 : 22} padding="22px 30px" radius={30}>
          <div style={{fontFamily: fam(text), fontSize: rem(2), ...fontWeightStyle(600), direction: hasPersian(text) ? 'rtl' : 'ltr', lineHeight: 1.4}}>{text}</div>
        </THEME.Surface>
      </div>
    </div>
  );
};

/** Hand-drawn arrow between two points. */
export const Arrow: React.FC<{t: number; at: number; from: [number, number]; to: [number, number]; bend?: number; dur?: number}> = ({t, at, from, to, bend = 0.25, dur = 0.45}) => {
  const {ink} = useInk();
  const d = easeInOut(range(stepT(t), at, dur));
  const mx = (from[0] + to[0]) / 2 - (to[1] - from[1]) * bend;
  const my = (from[1] + to[1]) / 2 + (to[0] - from[0]) * bend;
  const path = `M ${from[0]} ${from[1]} Q ${mx} ${my} ${to[0]} ${to[1]}`;
  const ang = Math.atan2(to[1] - my, to[0] - mx);
  const head = (s: number) => `${to[0] + Math.cos(ang + s) * -34},${to[1] + Math.sin(ang + s) * -34}`;
  return (
    <svg width={1080} height={1920} style={{position: 'absolute', inset: 0, pointerEvents: 'none'}}>
      <path d={path} fill="none" stroke={ink} strokeWidth={9} strokeLinecap="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - d} />
      {d > 0.98 && <polyline points={`${head(0.5)} ${to[0]},${to[1]} ${head(-0.5)}`} fill="none" stroke={ink} strokeWidth={9} strokeLinecap="round" strokeLinejoin="round" />}
    </svg>
  );
};

/** Call to action ("کامنت کن ‹کلاد› تا لینک رو بفرستم"). */
export const CTA: React.FC<{t: number; at: number; text: string; keyword?: string; y?: number}> = ({t, at, text, keyword, y = 1250}) => {
  const p = enter(t, at);
  return (
    <div style={{position: 'absolute', left: 540, top: y, transform: `translate(-50%, -50%) scale(${0.6 + 0.4 * clamp(p, 0, 1.1)})`, opacity: clamp(p * 3), whiteSpace: 'nowrap', direction: 'rtl'}}>
      <THEME.Sticker fill={PAL.surface} seed={31} rotate={-2}>
        <span style={{fontFamily: FONT_FAMILY, fontSize: rem(2.6), ...fontWeightStyle(800)}}>
          {text}{' '}
          {keyword && (
            <THEME.Highlight progress={enterSoft(t, at + 0.3)} seed={7}>
              {keyword}
            </THEME.Highlight>
          )}
        </span>
      </THEME.Sticker>
    </div>
  );
};

/** Inline code / terminal snippet card. */
export const CodeCard: React.FC<{t: number; at: number; lines: string[]; top: number; title?: string}> = ({t, at, lines, top, title}) => {
  const p = enter(t, at);
  return (
    <div style={{position: 'absolute', left: SAFE_X - 30, right: SAFE_X - 30, top, opacity: clamp(p * 3), transform: `translateY(${(1 - clamp(p)) * 200}px)`}}>
      <THEME.Surface w="100%" fill={PAL.bgDark} elevation={2} seed={14} padding="26px 34px">
        {title && <div style={{fontFamily: MONO_FAMILY, fontSize: rem(1.4), color: PAL.onDarkSoft, marginBottom: 14, direction: 'ltr'}}>{title}</div>}
        {lines.map((ln, i) => {
          const lp = enterSoft(t, at + 0.2 + i * MOTION.stagger * 2);
          return (
            <div key={i} style={{fontFamily: MONO_FAMILY, fontSize: rem(1.75), lineHeight: 1.55, color: PAL.onDark, direction: 'ltr', whiteSpace: 'pre', opacity: lp}}>
              {ln}
            </div>
          );
        })}
      </THEME.Surface>
    </div>
  );
};

// ---------- Torn reveal: two pieces of paper rip apart to reveal an image (Vox-style) ----------
const tornEdgeY = (seed: number, n = 26, amp = 2.2) =>
  Array.from({length: n + 1}, (_, i) => `${((i / n) * 100).toFixed(2)}% ${(50 + Math.sin(seed * 9.1 + i * 2.7) * amp + Math.sin(seed * 3.3 + i * 7.9) * amp * 0.6).toFixed(2)}%`);

export const TornReveal: React.FC<{
  t: number;
  at: number;
  src: string;
  top: number;
  h: number;
  /** how far the gap opens (px each side) */
  open?: number;
  fill?: string;
  seed?: number;
  /** object-position of the image, e.g. '50% 30%' */
  focus?: string;
}> = ({t, at, src, top, h, open = 170, fill, seed = 3, focus = '50% 40%'}) => {
  const p = easeOut(range(stepT(t), at, 0.55));
  const color = fill ?? PAL.accent;
  const edge = tornEdgeY(seed);
  const topClip = `polygon(0% 0%, 100% 0%, ${[...edge].reverse().join(', ')})`;
  const botClip = `polygon(${edge.join(', ')}, 100% 100%, 0% 100%)`;
  const sheet = (clip: string, dy: number, rot: number, k: number) => {
    const inner = THEME.Paper ? (
      <THEME.Paper fill={color} seed={seed + k} style={{position: 'absolute', inset: 0}} />
    ) : (
      <div style={{position: 'absolute', inset: 0, background: color}} />
    );
    return (
      <div style={{position: 'absolute', inset: 0, transform: `translateY(${dy}px) rotate(${rot}deg)`, filter: `drop-shadow(0 ${k ? -8 : 10}px 14px ${withAlpha(PAL.shadow, 0.45)})`}}>
        {/* white paper core visible along the tear */}
        <div style={{position: 'absolute', inset: 0, clipPath: clip, background: PAL.papers[0], transform: `translateY(${k ? -7 : 7}px)`}} />
        <div style={{position: 'absolute', inset: 0, clipPath: clip}}>{inner}</div>
      </div>
    );
  };
  return (
    <div style={{position: 'absolute', left: -40, right: -40, top, height: h, overflow: 'visible'}}>
      <div style={{position: 'absolute', left: 0, right: 0, top: h / 2 - open - 20, height: open * 2 + 40, overflow: 'hidden'}}>
        <Img src={staticFile(src)} style={{width: '100%', height: '100%', objectFit: 'cover', objectPosition: focus, transform: `scale(${1.12 - 0.08 * p})`}} />
      </div>
      {sheet(topClip, -p * open, -p * 1.2, 0)}
      {sheet(botClip, p * open, p * 0.8, 1)}
    </div>
  );
};

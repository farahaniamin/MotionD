// Real-brand components. Logos come ONLY from src/logos.json (written by tools/logo_fetch.py from
// official/verified vector sources). A missing id renders a loud placeholder that fails Stills QA —
// a brand logo is never drawn, approximated or AI-generated.
import React from 'react';
import LOGOS_RAW from '../logos.json';
import {THEME} from '../theme/active';
import {LATIN_FAMILY, FONT_FAMILY, PAL, MOTION, fontWeightStyle, rem, roleStyle, hasPersian} from '../engine/tokens';
import {clamp, enter, enterSoft, range, stepT, easeInOut} from '../engine/time';
import {useInk, useScene} from '../engine/scene';

export type LogoEntry = {
  name: string;
  src: string;
  layers: string[];
  aspect: number;
  colors: string[];
  provider: string;
  source: string;
  wordmark?: string;
  wordmarkAspect?: number;
};
export const LOGOS = LOGOS_RAW as unknown as Record<string, LogoEntry>;

type Pos = {x?: number; y?: number};
const posStyle = ({x, y}: Pos): React.CSSProperties =>
  x === undefined && y === undefined ? {position: 'relative'} : {position: 'absolute', left: x ?? 540, top: y ?? 960, transform: 'translate(-50%, -50%)'};

const MissingLogo: React.FC<{id: string; size: number}> = ({id, size}) => (
  <div
    data-qa="missing-logo"
    style={{width: size, height: size, border: '6px dashed #FF0033', background: '#FFE5EA', color: '#FF0033', display: 'flex', alignItems: 'center', justifyContent: 'center', textAlign: 'center', fontFamily: LATIN_FAMILY, fontSize: 22, fontWeight: 800, padding: 12, boxSizing: 'border-box'}}
  >
    LOGO MISSING: {id}
    <br />
    run tools/logo_fetch.py {id}
  </div>
);

export const BrandLogo: React.FC<
  {id: string; t: number; at?: number; size?: number; variant?: 'icon' | 'wordmark'; seed?: number} & Pos
> = ({id, t, at = 0, size = 220, variant = 'icon', seed, x, y}) => {
  const {onDark} = useScene();
  const entry = LOGOS[id];
  const p = enter(t, at);
  const wrap: React.CSSProperties = {
    ...posStyle({x, y}),
    opacity: clamp(range(stepT(t), at, 0.12)),
  };
  const inner = `scale(${0.55 + 0.45 * p}) rotate(${(1 - clamp(p)) * -10}deg)`;
  if (!entry) return <div style={wrap}><MissingLogo id={id} size={size} /></div>;
  const useWordmark = variant === 'wordmark' && entry.wordmark;
  return (
    <div style={wrap}>
      <div style={{transform: inner}}>
        <THEME.LogoTreatment
          src={useWordmark ? entry.wordmark! : entry.src}
          layers={useWordmark ? [entry.wordmark!] : entry.layers}
          size={size}
          aspect={useWordmark ? entry.wordmarkAspect ?? 4 : entry.aspect}
          seed={seed ?? id.length * 7 + 3}
          onDark={onDark}
          t={t}
        />
      </div>
    </div>
  );
};

/** Logo + product name + one-line pitch (+ optional url chip). The workhorse of tool-intro reels. */
export const ToolCard: React.FC<
  {id: string; t: number; at: number; name?: string; tagline?: string; url?: string; w?: number; logoSize?: number; seed?: number; fill?: string} & Pos
> = ({id, t, at, name, tagline, url, w = 680, logoSize = 200, seed = 2, fill, x, y}) => {
  const p = enter(t, at);
  const textIn = enterSoft(t, at + MOTION.stagger * 2);
  const entry = LOGOS[id];
  const title = name ?? entry?.name ?? id;
  return (
    <div style={{...posStyle({x, y}), transform: `${posStyle({x, y}).transform ?? ''} translateY(${(1 - clamp(p)) * 220}px) rotate(${(1 - clamp(p)) * 6}deg)`, opacity: clamp(p * 3)}}>
      <THEME.Surface w={w} elevation={2} seed={seed} fill={fill} padding="48px 44px 44px">
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22}}>
          <BrandLogo id={id} t={t} at={at + MOTION.stagger} size={logoSize} />
          <div style={{fontFamily: hasPersian(title) ? FONT_FAMILY : LATIN_FAMILY, ...roleStyle('focus'), lineHeight: 1.05, opacity: textIn, transform: `translateY(${(1 - textIn) * 24}px)`}}>
            {title}
          </div>
          {tagline && (
            <div style={{fontFamily: FONT_FAMILY, ...roleStyle('body'), textAlign: 'center', direction: 'rtl', opacity: textIn, maxWidth: w - 100}}>{tagline}</div>
          )}
          {url && (
            <div style={{fontFamily: LATIN_FAMILY, fontSize: rem(1.9), direction: 'ltr', ...fontWeightStyle(700), opacity: enterSoft(t, at + MOTION.stagger * 4)}}>
              <THEME.Highlight progress={enterSoft(t, at + MOTION.stagger * 4)} fill={PAL.papers[3]} seed={seed}>
                {url}
              </THEME.Highlight>
            </div>
          )}
        </div>
      </THEME.Surface>
    </div>
  );
};

/** Center node with satellites connected by drawn lines (ecosystem / integrations / "tools that…"). */
export const LogoHub: React.FC<{
  t: number;
  at: number;
  center: {id?: string; text?: string};
  satellites: string[];
  cx?: number;
  cy?: number;
  radius?: number;
  satSize?: number;
}> = ({t, at, center, satellites, cx = 540, cy = 1000, radius = 330, satSize = 130}) => {
  const {ink} = useInk();
  const n = satellites.length;
  const st = stepT(t);
  return (
    <div style={{position: 'absolute', inset: 0}}>
      <svg width={1080} height={1920} style={{position: 'absolute', inset: 0}}>
        {satellites.map((_, i) => {
          const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
          const sx = cx + Math.cos(a) * radius;
          const sy = cy + Math.sin(a) * radius;
          const d = easeInOut(range(st, at + 0.25 + i * MOTION.stagger, 0.45));
          return (
            <line key={i} x1={cx} y1={cy} x2={cx + (sx - cx) * d} y2={cy + (sy - cy) * d} stroke={ink} strokeOpacity={0.55} strokeWidth={5} strokeDasharray="14 12" strokeLinecap="round" />
          );
        })}
      </svg>
      {satellites.map((id, i) => {
        const a = -Math.PI / 2 + (i / n) * Math.PI * 2;
        return <BrandLogo key={id} id={id} t={t} at={at + 0.4 + i * MOTION.stagger} size={satSize} x={cx + Math.cos(a) * radius} y={cy + Math.sin(a) * radius} />;
      })}
      <div style={{position: 'absolute', left: cx, top: cy, transform: 'translate(-50%, -50%)'}}>
        {center.id ? (
          <BrandLogo id={center.id} t={t} at={at} size={satSize * 1.7} />
        ) : (
          <THEME.Sticker seed={9}>
            <span style={{fontFamily: FONT_FAMILY, ...roleStyle('focus')}}>{center.text}</span>
          </THEME.Sticker>
        )}
      </div>
    </div>
  );
};

/** Two tools head-to-head. */
export const Versus: React.FC<{t: number; at: number; left: string; right: string; leftLabel?: string; rightLabel?: string; y?: number}> = ({
  t,
  at,
  left,
  right,
  leftLabel,
  rightLabel,
  y = 980,
}) => {
  const vs = enter(t, at + MOTION.stagger * 4);
  return (
    <div style={{position: 'absolute', inset: 0}}>
      <ToolCard id={right} t={t} at={at} name={rightLabel} w={380} logoSize={150} x={770} y={y} seed={3} />
      <ToolCard id={left} t={t} at={at + MOTION.stagger * 2} name={leftLabel} w={380} logoSize={150} x={310} y={y + 40} seed={5} />
      <div style={{position: 'absolute', left: 540, top: y - 10, transform: `translate(-50%, -50%) scale(${clamp(vs, 0, 1.2)})`}}>
        <THEME.Sticker seed={4} fill={PAL.accent}>
          <span style={{fontFamily: LATIN_FAMILY, fontSize: rem(3.4), ...fontWeightStyle(900)}}>VS</span>
        </THEME.Sticker>
      </div>
    </div>
  );
};

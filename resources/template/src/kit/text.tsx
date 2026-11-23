// Kinetic typography. Lines are laid out with normal CSS flow (flex-wrap), so lines can never collide
// regardless of word sizes — no manual `top` arithmetic per line.
import React from 'react';
import {THEME} from '../theme/active';
import {FONT_FAMILY, LATIN_FAMILY, MOTION, PAL, SAFE_X, TYPE, hasPersian, roleStyle} from '../engine/tokens';
import {boil, clamp, enter, enterSoft} from '../engine/time';
import {useInk} from '../engine/scene';

export type Role = 'setup' | 'focus' | 'hero' | 'mega';
export type Word = {
  text: string;
  at: number;
  role?: Role;
  /** true = theme highlight with default color, or pass a color */
  mark?: boolean | string;
  tone?: 'ink' | 'soft' | 'accent' | 'accent2';
};

const Kinetic: React.FC<{w: Word; t: number; seed: number}> = ({w, t, seed}) => {
  const {ink, soft} = useInk();
  const role = w.role ?? 'setup';
  const p = enter(t, w.at);
  const b = boil(seed, t, MOTION.boil * 0.5);
  const color = w.tone === 'soft' ? soft : w.tone === 'accent' ? PAL.accent : w.tone === 'accent2' ? PAL.accent2 : ink;
  const big = role === 'hero' || role === 'mega';
  const body = (
    <span
      style={{
        display: 'inline-block',
        fontFamily: hasPersian(w.text) ? FONT_FAMILY : LATIN_FAMILY,
        ...roleStyle(role),
        color,
        opacity: clamp(p * 2.5),
        transform: `translate(${b.dx}px, ${(1 - clamp(p)) * (big ? 70 : 40) + b.dy}px) scale(${big ? 0.7 + 0.3 * p : 1}) rotate(${b.rot}deg)`,
        whiteSpace: 'pre',
      }}
    >
      {w.mark ? (
        <THEME.Highlight progress={enterSoft(t, w.at + 0.1)} fill={typeof w.mark === 'string' ? w.mark : undefined} seed={seed}>
          {w.text}
        </THEME.Highlight>
      ) : (
        w.text
      )}
    </span>
  );
  return body;
};

export const Headline: React.FC<{
  t: number;
  lines: Word[][];
  top: number;
  align?: 'center' | 'right' | 'left';
  /** extra vertical space between lines in em of the line's font */
  gap?: number;
  maxWidth?: number;
}> = ({t, lines, top, align = 'center', gap = 0.12, maxWidth}) => {
  const justify = align === 'center' ? 'center' : align === 'right' ? 'flex-start' : 'flex-end';
  return (
    <div
      style={{
        position: 'absolute',
        top,
        left: SAFE_X,
        right: SAFE_X,
        maxWidth,
        margin: '0 auto',
        direction: 'rtl',
        display: 'flex',
        flexDirection: 'column',
        alignItems: align === 'center' ? 'center' : 'stretch',
        rowGap: `${gap}em`,
        lineHeight: TYPE.lineHeight,
      }}
    >
      {lines.map((line, li) => (
        <div key={li} style={{display: 'flex', flexWrap: 'wrap', justifyContent: justify, alignItems: 'baseline', columnGap: '0.28em', rowGap: '0.1em'}}>
          {line.map((w, wi) => (
            <Kinetic key={wi} w={w} t={t} seed={li * 17 + wi * 5 + 1} />
          ))}
        </div>
      ))}
    </div>
  );
};

/** Small supporting line (source, footnote, label). Never below caption size. */
export const Caption: React.FC<{t: number; at: number; text: string; top: number; tone?: 'ink' | 'soft'}> = ({t, at, text, top, tone = 'soft'}) => {
  const {ink, soft} = useInk();
  const p = enterSoft(t, at);
  return (
    <div
      style={{
        position: 'absolute',
        top,
        left: SAFE_X,
        right: SAFE_X,
        textAlign: 'center',
        direction: hasPersian(text) ? 'rtl' : 'ltr',
        fontFamily: hasPersian(text) ? FONT_FAMILY : LATIN_FAMILY,
        ...roleStyle('caption'),
        color: tone === 'ink' ? ink : soft,
        opacity: p,
        transform: `translateY(${(1 - p) * 16}px)`,
      }}
    >
      {text}
    </div>
  );
};

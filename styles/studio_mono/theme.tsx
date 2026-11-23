// STUDIO MONO theme — the v1 "editorial monochrome studio" look rebuilt on the v2 contract:
// spotlit studio paper, blueprint grid, crisp white cards, black pill highlights, whip/zoom transitions.
import React from 'react';
import {Img, staticFile} from 'remotion';
import {Theme, TransitionFn} from '../engine/contract';
import {BRAND, PAL, STYLE, FONT_FAMILY, LATIN_FAMILY, fontWeightStyle, rem, withAlpha, textOn} from '../engine/tokens';
import {clamp, easeBack, easeInOut, easeOutQuart, range} from '../engine/time';

const S = STYLE.surface as {radius: number; gridOpacity: number};
const L = STYLE.logo as {capsuleOnDark: boolean; shadow: number};

const Defs: React.FC = () => null;

const Surface: Theme['Surface'] = ({w, h, fill, elevation = 1, radius, padding = 36, style, children}) => {
  const base = fill ?? PAL.surface;
  return (
    <div
      style={{
        position: 'relative',
        width: w,
        height: h,
        background: base,
        borderRadius: radius ?? S.radius,
        border: `1.5px solid ${withAlpha(PAL.line, 0.12)}`,
        boxShadow: `0 ${4 + elevation * 8}px ${18 + elevation * 22}px ${withAlpha(PAL.shadow, 0.08 + elevation * 0.05)}`,
        padding,
        boxSizing: 'border-box',
        color: textOn(base),
        ...style,
      }}
    >
      {children}
    </div>
  );
};

const Highlight: Theme['Highlight'] = ({progress, fill, children}) => {
  const p = clamp(progress);
  const color = fill ?? PAL.highlight;
  return (
    <span style={{position: 'relative', display: 'inline-block', padding: '0 0.24em', color: p > 0.5 ? (fill ? textOn(color) : PAL.onHighlight) : 'inherit'}}>
      <span
        style={{
          position: 'absolute',
          inset: '0.08em -0.04em 0.0em -0.04em',
          background: color,
          borderRadius: 22,
          transformOrigin: 'right center',
          transform: `scaleX(${p})`,
          boxShadow: `0 10px 26px ${withAlpha(PAL.shadow, 0.22)}`,
        }}
      />
      <span style={{position: 'relative'}}>{children}</span>
    </span>
  );
};

const LogoTreatment: Theme['LogoTreatment'] = ({src, size, aspect, onDark}) => {
  const w = size * aspect;
  const logo = (
    <Img
      src={staticFile(src)}
      style={{width: w, height: size, display: 'block', filter: `drop-shadow(0 ${L.shadow}px ${L.shadow * 2}px ${withAlpha(PAL.shadow, 0.18)})`}}
    />
  );
  if (onDark && L.capsuleOnDark) {
    return (
      <div style={{background: PAL.surface, borderRadius: size * 0.28, padding: size * 0.18, boxShadow: `0 18px 40px ${withAlpha('#000000', 0.35)}`}}>{logo}</div>
    );
  }
  return logo;
};

const Sticker: Theme['Sticker'] = ({children, fill, rotate = -4}) => {
  const f = fill ?? PAL.accent;
  return (
    <div
      style={{
        display: 'inline-block',
        background: f,
        color: textOn(f),
        border: `5px solid ${textOn(f)}`,
        borderRadius: 14,
        padding: '14px 30px',
        transform: `rotate(${rotate}deg)`,
        boxShadow: `0 14px 30px ${withAlpha(PAL.shadow, 0.3)}`,
      }}
    >
      {children}
    </div>
  );
};

const Backdrop: Theme['Backdrop'] = ({tone, focus}) => {
  const dark = tone === 'dark';
  const center = dark ? PAL.bgDark : tone === 'accent' ? PAL.accent : PAL.surface;
  const edge = dark ? '#000000' : tone === 'alt' ? PAL.bgAlt : PAL.bg;
  const gridC = dark ? withAlpha(PAL.onDark, 0.06) : withAlpha(PAL.line, 0.1);
  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `radial-gradient(ellipse 75% 55% at ${focus[0]}% ${focus[1]}%, ${center} 0%, ${edge} 100%)`,
      }}
    >
      <div
        style={{
          position: 'absolute',
          left: 150,
          right: 150,
          top: 300,
          height: 910,
          opacity: S.gridOpacity,
          backgroundImage: `linear-gradient(${gridC} 1.5px, transparent 1.5px), linear-gradient(90deg, ${gridC} 1.5px, transparent 1.5px)`,
          backgroundSize: '130px 130px',
          maskImage: 'radial-gradient(ellipse at center, black 40%, transparent 78%)',
          WebkitMaskImage: 'radial-gradient(ellipse at center, black 40%, transparent 78%)',
        }}
      />
    </div>
  );
};

const Overlay: Theme['Overlay'] = ({t}) => {
  const f = Math.floor(t * 30);
  return (
    <div
      style={{
        position: 'absolute',
        inset: -300,
        backgroundImage: `url(${staticFile('img/grain.png')})`,
        transform: `translate(${(f * 37) % 300}px, ${(f * 89) % 300}px)`,
        opacity: 0.065,
        mixBlendMode: 'overlay',
        pointerEvents: 'none',
        zIndex: 90,
      }}
    />
  );
};

const BrandMark: Theme['BrandMark'] = ({onDark}) => (
  <div style={{position: 'absolute', top: 96, left: 0, right: 0, textAlign: 'center', zIndex: 60}}>
    <span style={{fontFamily: LATIN_FAMILY, fontSize: rem(1.45), letterSpacing: '0.32em', color: onDark ? PAL.onDark : PAL.ink, ...fontWeightStyle(800)}}>
      {BRAND.wordmark}
    </span>
  </div>
);

const Outro: Theme['Outro'] = ({localT}) => {
  const a = easeOutQuart(range(localT, 0.15, 0.6));
  const b = easeOutQuart(range(localT, 0.55, 0.5));
  return (
    <div style={{position: 'absolute', inset: 0, background: `radial-gradient(circle at 50% 46%, ${PAL.bgDark}, #000)`, fontFamily: FONT_FAMILY}}>
      <div style={{position: 'absolute', top: 820, left: 0, right: 0, textAlign: 'center', opacity: a, transform: `scale(${0.9 + 0.1 * a})`}}>
        <span style={{fontFamily: LATIN_FAMILY, fontSize: rem(6.2), letterSpacing: '0.18em', color: PAL.onDark, ...fontWeightStyle(900)}}>{BRAND.wordmark}</span>
      </div>
      <div style={{position: 'absolute', top: 990, left: 130, right: 130, textAlign: 'center', opacity: b}}>
        <span style={{fontSize: rem(2.2), color: PAL.onDarkSoft, ...fontWeightStyle(600)}}>{BRAND.outroTagline}</span>
      </div>
      <div style={{position: 'absolute', bottom: 300, left: 0, right: 0, textAlign: 'center', opacity: b * 0.7}}>
        <span style={{fontFamily: LATIN_FAMILY, fontSize: rem(1.3), letterSpacing: '0.3em', color: PAL.onDarkSoft, ...fontWeightStyle(600)}}>{BRAND.outroFooter}</span>
      </div>
    </div>
  );
};

const whip = (dx: number, dy: number, rot: number): TransitionFn => (p, dir) => {
  if (dir === 'in') {
    const inv = 1 - easeOutQuart(p);
    const blur = inv * 16;
    return {transform: `translate(${inv * dx}px, ${inv * dy}px) rotate(${inv * rot}deg)`, opacity: clamp(p * 4), filter: blur > 0.5 ? `blur(${blur.toFixed(1)}px)` : undefined};
  }
  const e = easeInOut(p);
  return {transform: `translate(${-e * dx}px, ${-e * dy}px) rotate(${-e * rot}deg)`, opacity: 1 - e, filter: e > 0.03 ? `blur(${(e * 16).toFixed(1)}px)` : undefined};
};

const transitions: Theme['transitions'] = {
  'whip-left': whip(-620, -30, -4),
  'whip-right': whip(620, -30, 4),
  'whip-up': whip(0, 660, 2.5),
  'zoom-through': (p, dir) => {
    if (dir === 'in') {
      const e = easeOutQuart(p);
      return {transform: `scale(${1.18 - 0.18 * e})`, opacity: clamp(p * 3), filter: e < 0.97 ? `blur(${((1 - e) * 14).toFixed(1)}px)` : undefined};
    }
    const e = easeInOut(p);
    return {transform: `scale(${1 + 0.6 * e * e})`, opacity: 1 - e, filter: `blur(${(e * 16).toFixed(1)}px)`};
  },
  continuity: (p, dir) => {
    const e = easeInOut(p);
    return dir === 'in'
      ? {transform: `translateY(${(1 - e) * 24}px)`, opacity: e, filter: e < 0.97 ? `blur(${((1 - e) * 12).toFixed(1)}px)` : undefined}
      : {transform: `translateY(${-e * 24}px)`, opacity: 1 - e, filter: `blur(${(e * 12).toFixed(1)}px)`};
  },
  pop: (p, dir) => (dir === 'in' ? {transform: `scale(${0.92 + 0.08 * easeBack(p)})`, opacity: clamp(p * 2.5)} : {opacity: 1 - p}),
  cut: () => ({}),
};

export const THEME: Theme = {name: 'studio_mono', Backdrop, Surface, Highlight, LogoTreatment, Sticker, Overlay, BrandMark, Outro, transitions, Defs};


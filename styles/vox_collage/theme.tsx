// VOX COLLAGE theme — editorial paper collage (Vox explainer look): crumpled paper, torn edges with a
// white paper core, newsprint scraps, engraved/halftone cut-outs with die-cut borders, masking tape,
// one loud accent color, stop-motion on twos. Accent/palette are fully token-driven (palettePresets).
import React from 'react';
import {Img, staticFile} from 'remotion';
import {Theme, TransitionFn} from '../engine/contract';
import {BRAND, H, PAL, STYLE, W, FONT_FAMILY, LATIN_FAMILY, fontWeightStyle, rem, withAlpha, textOn} from '../engine/tokens';
import {boil, clamp, easeBack, easeInOut, easeOutQuart, noise, range, stepT} from '../engine/time';

const S = STYLE.surface as {radius: number; tearAmp: number; tape: boolean; halftone: number; shadowDepth: number; newsprint: number};
const L = STYLE.logo as {dieCut: number; lift: number};

const CRUMPLE = `url(${staticFile('style/textures/crumpled.png')})`;
const NEWS = `url(${staticFile('style/textures/newsprint.png')})`;
const GRAIN = `url(${staticFile('style/textures/grain.png')})`;
const halftone = (color: string, size = 14, dot = 0.32) =>
  `radial-gradient(circle, ${color} ${(dot * 100).toFixed(0)}%, transparent ${(dot * 100 + 6).toFixed(0)}%) 0 0 / ${size}px ${size}px`;

/** crumpled-paper material in any color (overlay blend keeps the hue, adds creases) */
const crumpled = (fill: string): React.CSSProperties => ({
  backgroundImage: `${CRUMPLE}`,
  backgroundColor: fill,
  backgroundBlendMode: 'overlay',
  backgroundSize: '700px 700px',
});

/** Torn-paper polygon for a rectangle; jag in px via calc() so any size works. */
const tornRect = (seed: number, jag = S.tearAmp, n = 16, sides: [boolean, boolean, boolean, boolean] = [true, true, true, true]) => {
  const j = (i: number, k: number) => (sides[k] ? (Math.abs(noise(seed + k * 13, i)) * jag).toFixed(1) : '0');
  const pts: string[] = [];
  for (let i = 0; i <= n; i++) pts.push(`${((i / n) * 100).toFixed(2)}% calc(0% + ${j(i, 0)}px)`);
  for (let i = 1; i <= n; i++) pts.push(`calc(100% - ${j(i, 1)}px) ${((i / n) * 100).toFixed(2)}%`);
  for (let i = n - 1; i >= 0; i--) pts.push(`${((i / n) * 100).toFixed(2)}% calc(100% - ${j(i, 2)}px)`);
  for (let i = n - 1; i >= 1; i--) pts.push(`calc(0% + ${j(i, 3)}px) ${((i / n) * 100).toFixed(2)}%`);
  return `polygon(${pts.join(', ')})`;
};

const hardShadow = (d: number) =>
  `drop-shadow(${(d * 0.4).toFixed(1)}px ${d.toFixed(1)}px 0 ${withAlpha(PAL.shadow, 0.35)}) drop-shadow(0 ${(d * 2).toFixed(1)}px ${(d * 3).toFixed(1)}px ${withAlpha(PAL.shadow, 0.35)})`;

const Tape: React.FC<{x: number | string; y: number | string; rot: number; w?: number}> = ({x, y, rot, w = 120}) =>
  S.tape ? (
    <div
      style={{
        position: 'absolute',
        left: x,
        top: y,
        width: w,
        height: 38,
        transform: `translate(-50%, -50%) rotate(${rot}deg)`,
        background: 'rgba(236, 228, 205, 0.78)',
        clipPath: 'polygon(3% 0, 97% 4%, 100% 50%, 96% 100%, 2% 96%, 0 50%)',
        boxShadow: `0 2px 4px ${withAlpha(PAL.shadow, 0.2)}`,
        zIndex: 5,
      }}
    />
  ) : null;

const Defs: React.FC = () => null;

const Paper: NonNullable<Theme['Paper']> = ({fill, style, children}) => (
  <div style={{...crumpled(fill), ...style}}>{children}</div>
);

// ---------- Surface: torn sheet with white core, crumpled, taped ----------
const Surface: Theme['Surface'] = ({w, h, fill, elevation = 1, seed = 1, padding = 40, style, children}) => {
  const base = fill ?? PAL.surface;
  const clip = tornRect(seed);
  const core = tornRect(seed + 50, S.tearAmp * 1.4);
  const tilt = noise(seed, 4) * 1.2;
  return (
    <div style={{position: 'relative', width: w, height: h, transform: `rotate(${tilt}deg)`, ...style}}>
      <div style={{position: 'absolute', inset: -5, filter: hardShadow(S.shadowDepth * (0.7 + elevation * 0.4))}}>
        <div style={{position: 'absolute', inset: 0, clipPath: core, background: PAL.papers[0]}} />
      </div>
      <div style={{position: 'absolute', inset: 0, clipPath: clip, ...crumpled(base)}} />
      {elevation >= 2 && <Tape x="50%" y={0} rot={noise(seed, 9) * 6} />}
      <div style={{position: 'relative', padding, height: '100%', boxSizing: 'border-box', color: textOn(base)}}>{children}</div>
    </div>
  );
};

// ---------- Highlight: hand-swiped marker / torn label in the accent ----------
const Highlight: Theme['Highlight'] = ({progress, fill, seed = 1, children}) => {
  const p = clamp(progress);
  const color = fill ?? PAL.highlight;
  return (
    <span style={{position: 'relative', display: 'inline-block', padding: '0 0.2em', color: p > 0.45 ? textOn(color) : 'inherit'}}>
      <span
        style={{
          position: 'absolute',
          inset: '0.1em -0.08em 0.02em -0.08em',
          ...crumpled(color),
          clipPath: tornRect(seed + 30, 5, 10),
          transformOrigin: 'right center',
          transform: `scaleX(${p}) rotate(${noise(seed, 2) * 1.5}deg)`,
        }}
      />
      <span style={{position: 'relative'}}>{children}</span>
    </span>
  );
};

// ---------- Logo: the real vector as a die-cut sticker, halftone grain, taped ----------
const LogoTreatment: Theme['LogoTreatment'] = ({layers, src, size, aspect, seed = 1, t}) => {
  const w = size * aspect;
  const k = size / 240;
  const fid = `vx-diecut-${seed}`;
  const b = boil(seed, t, STYLE.motion.boil * 0.5);
  return (
    <div style={{position: 'relative', width: w, height: size, transform: `rotate(${b.rot + noise(seed, 1) * 3}deg)`}}>
      <svg width={w} height={size} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <defs>
          <filter id={fid} x="-40%" y="-40%" width="180%" height="180%">
            <feMorphology in="SourceAlpha" operator="dilate" radius={L.dieCut * k} result="grow" />
            <feFlood floodColor={PAL.papers[0]} />
            <feComposite in2="grow" operator="in" result="sheet" />
            <feDropShadow dx={2 * k} dy={L.lift * k} stdDeviation={0.6 * k} floodColor={PAL.shadow} floodOpacity="0.45" />
          </filter>
        </defs>
        <image href={staticFile(src)} width={w} height={size} filter={`url(#${fid})`} />
      </svg>
      {layers.map((ly) => (
        <Img key={ly} src={staticFile(ly)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}} />
      ))}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: GRAIN,
          mixBlendMode: 'multiply',
          opacity: 0.8,
          WebkitMaskImage: `url(${staticFile(src)})`,
          maskImage: `url(${staticFile(src)})`,
          WebkitMaskSize: '100% 100%',
          maskSize: '100% 100%',
        }}
      />
      <Tape x="78%" y="6%" rot={28 + noise(seed, 5) * 10} w={size * 0.42} />
    </div>
  );
};

// ---------- Cut-out props (AI images): white die-cut border + halftone texture ----------
const PropFrame: NonNullable<Theme['PropFrame']> = ({src, w, seed}) => {
  const fid = `vx-prop-${seed}`;
  return (
    <div style={{position: 'relative', width: w, height: w}}>
      <svg width={w} height={w} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <defs>
          <filter id={fid} x="-30%" y="-30%" width="160%" height="160%">
            <feMorphology in="SourceAlpha" operator="dilate" radius={w / 70} result="grow" />
            <feFlood floodColor={PAL.papers[0]} />
            <feComposite in2="grow" operator="in" result="sheet" />
            <feDropShadow dx={w / 160} dy={w / 60} stdDeviation={w / 400} floodColor={PAL.shadow} floodOpacity="0.5" />
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <image href={staticFile(src)} width={w} height={w} filter={`url(#${fid})`} />
      </svg>
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: GRAIN,
          mixBlendMode: 'multiply',
          WebkitMaskImage: `url(${staticFile(src)})`,
          maskImage: `url(${staticFile(src)})`,
          WebkitMaskSize: '100% 100%',
          maskSize: '100% 100%',
        }}
      />
    </div>
  );
};

const Sticker: Theme['Sticker'] = ({children, fill, seed = 1, rotate}) => {
  const f = fill ?? PAL.ink;
  return (
    <div style={{position: 'relative', display: 'inline-block', transform: `rotate(${rotate ?? noise(seed, 2) * 5}deg)`, filter: hardShadow(5)}}>
      <div style={{position: 'absolute', inset: -6, clipPath: tornRect(seed + 70, 6, 10), background: PAL.papers[0]}} />
      <div style={{position: 'absolute', inset: 0, clipPath: tornRect(seed + 71, 5, 10), ...crumpled(f)}} />
      <div style={{position: 'relative', padding: '14px 30px', color: textOn(f), textTransform: 'uppercase'}}>{children}</div>
    </div>
  );
};

// ---------- Backdrop: crumpled base + torn diagonal strips + halftone sun ----------
const Strip: React.FC<{seed: number; angle: number; y: number; h: number; kind: 'news' | 'accent' | 'ink'; t: number}> = ({seed, angle, y, h, kind, t}) => {
  const bb = boil(seed, t, 1.2);
  const bg: React.CSSProperties =
    kind === 'news'
      ? {backgroundImage: NEWS, backgroundSize: '760px 760px', filter: 'grayscale(1) contrast(1.05)'}
      : crumpled(kind === 'accent' ? PAL.accent : PAL.ink);
  return (
    <div
      style={{
        position: 'absolute',
        left: -400,
        width: W + 800,
        top: y,
        height: h,
        transform: `rotate(${angle + bb.rot * 0.3}deg) translateY(${bb.dy}px)`,
        filter: hardShadow(6),
      }}
    >
      <div style={{position: 'absolute', inset: -8, clipPath: tornRect(seed + 9, S.tearAmp * 2.2, 40, [true, false, true, false]), background: PAL.papers[0]}} />
      <div style={{position: 'absolute', inset: 0, clipPath: tornRect(seed, S.tearAmp * 2, 40, [true, false, true, false]), ...bg}} />
    </div>
  );
};

const Backdrop: Theme['Backdrop'] = ({t, tone, sceneIdx}) => {
  const base = tone === 'dark' ? PAL.bgDark : tone === 'accent' ? PAL.accent : tone === 'alt' ? PAL.bgAlt : PAL.bg;
  const seed = sceneIdx * 5.3 + 2;
  const flip = sceneIdx % 2 ? -1 : 1;
  // the halftone "sun" sits behind the content zone, never behind headlines (y < 700)
  const sunX = sceneIdx % 3 === 0 ? 820 : sceneIdx % 3 === 1 ? 260 : 700;
  const sunY = 1020 + (sceneIdx % 2) * 140;
  const st = stepT(t);
  return (
    <div style={{position: 'absolute', inset: 0, ...crumpled(base)}}>
      {tone !== 'accent' && (
        <div
          style={{
            position: 'absolute',
            left: sunX - 330,
            top: sunY - 330,
            width: 660,
            height: 660,
            borderRadius: '50%',
            background: tone === 'dark' ? PAL.accent : withAlpha(PAL.accent, 0.92),
            transform: `scale(${1 + Math.sin(st * 0.8) * 0.01})`,
          }}
        >
          <div style={{position: 'absolute', inset: 0, borderRadius: '50%', background: halftone(withAlpha(PAL.ink, 0.35), 16, 0.28), opacity: S.halftone, WebkitMaskImage: 'linear-gradient(135deg, transparent 35%, black 100%)'}} />
        </div>
      )}
      {S.newsprint > 0 && <Strip seed={seed} angle={-24 * flip} y={flip > 0 ? 1460 : 1520} h={230} kind="news" t={t} />}
      <Strip seed={seed + 4} angle={-18 * flip} y={flip > 0 ? 1660 : 1700} h={200} kind={tone === 'accent' ? 'ink' : tone === 'dark' ? 'accent' : 'ink'} t={t} />
    </div>
  );
};

const Overlay: Theme['Overlay'] = ({t}) => {
  const step = Math.floor(t * (STYLE.motion.stepFps || 12));
  const flicker = 1 + noise(3, step) * 0.012;
  return (
    <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 90}}>
      <div style={{position: 'absolute', inset: 0, backgroundImage: GRAIN, backgroundSize: '360px 360px', backgroundPosition: `${(step * 37) % 360}px ${(step * 91) % 360}px`, mixBlendMode: 'multiply', opacity: 0.55}} />
      <div style={{position: 'absolute', inset: 0, background: `radial-gradient(ellipse 80% 65% at 50% 45%, transparent 50%, ${withAlpha('#000000', 0.38)} 100%)`, opacity: flicker}} />
    </div>
  );
};

const BrandMark: Theme['BrandMark'] = () => (
  <div style={{position: 'absolute', top: 96, left: 0, right: 0, display: 'flex', justifyContent: 'center', zIndex: 60}}>
    <Sticker fill={PAL.ink} seed={77} rotate={-2}>
      <span style={{fontFamily: LATIN_FAMILY, fontSize: rem(1.4), letterSpacing: '0.28em', ...fontWeightStyle(700)}}>{BRAND.wordmark}</span>
    </Sticker>
  </div>
);

const Outro: Theme['Outro'] = ({localT}) => {
  const lt = stepT(localT);
  const a = easeOutQuart(range(lt, 0.0, 0.45));
  const b = easeBack(range(lt, 0.35, 0.4));
  const c = easeOutQuart(range(lt, 0.7, 0.4));
  return (
    <div style={{position: 'absolute', inset: 0, ...crumpled(PAL.bgDark), fontFamily: FONT_FAMILY}}>
      <div style={{position: 'absolute', left: -200, right: -200, top: 760, height: 420, transform: `rotate(-8deg) translateX(${(1 - a) * -1400}px)`, filter: hardShadow(8)}}>
        <div style={{position: 'absolute', inset: -10, clipPath: tornRect(5, 16, 40, [true, false, true, false]), background: PAL.papers[0]}} />
        <div style={{position: 'absolute', inset: 0, clipPath: tornRect(6, 14, 40, [true, false, true, false]), ...crumpled(PAL.accent)}} />
      </div>
      <div style={{position: 'absolute', top: 870, left: 0, right: 0, textAlign: 'center', transform: `scale(${0.5 + 0.5 * b}) rotate(-3deg)`, opacity: clamp(b * 2)}}>
        <span style={{fontFamily: LATIN_FAMILY, fontSize: rem(7.5), letterSpacing: '0.02em', color: textOn(PAL.accent), textTransform: 'uppercase', ...fontWeightStyle(700)}}>{BRAND.wordmark}</span>
      </div>
      <div style={{position: 'absolute', top: 1230, left: 130, right: 130, textAlign: 'center', opacity: c}}>
        <Sticker fill={PAL.papers[0]} seed={12} rotate={2}>
          <span style={{fontSize: rem(2.3), ...fontWeightStyle(800), textTransform: 'none'}}>{BRAND.outroTagline}</span>
        </Sticker>
      </div>
    </div>
  );
};

// ---------- Transitions: torn wipes, collage slams, flash frames ----------
const tornWipe = (p: number, seed: number) => {
  const n = 24;
  const e = easeInOut(p) * 140 - 20; // diagonal sweep
  const pts: string[] = [];
  for (let i = 0; i <= n; i++) {
    const y = (i / n) * 100;
    const x = e - y * 0.35 + noise(seed, i) * 3.5;
    pts.push(`${x.toFixed(2)}% ${y}%`);
  }
  return `polygon(-50% 0%, ${pts.join(', ')}, -50% 100%)`;
};

const slam = (dx: number, dy: number, rot: number): TransitionFn => (p, dir) => {
  if (dir === 'in') {
    const e = easeOutQuart(p);
    return {transform: `translate(${(1 - e) * dx}px, ${(1 - e) * dy}px) rotate(${(1 - e) * rot}deg)`, shadow: true};
  }
  return {filter: `brightness(${1 - 0.25 * p})`};
};

const transitions: Theme['transitions'] = {
  'tear-wipe': (p, dir, seed) => (dir === 'in' ? {clipPath: tornWipe(p, seed), shadow: true} : {}),
  'slam-left': slam(-W * 1.15, 80, 7),
  'slam-right': slam(W * 1.15, -60, -7),
  'slam-up': slam(0, H * 1.1, -4),
  'zoom-in': (p, dir) => (dir === 'in' ? {transform: `scale(${1.35 - 0.35 * easeOutQuart(p)}) rotate(${(1 - p) * -2}deg)`, opacity: clamp(p * 4)} : {transform: `scale(${1 + 0.15 * p})`, opacity: 1 - p}),
  flash: (p, dir) => (dir === 'in' ? {filter: p < 0.25 ? 'brightness(2.4) contrast(0.6)' : undefined} : {opacity: p < 0.25 ? 1 : 0}),
  pop: (p, dir) => (dir === 'in' ? {transform: `scale(${0.9 + 0.1 * easeBack(p)})`, opacity: clamp(p * 2.5)} : {opacity: 1 - p}),
  cut: () => ({}),
};

export const THEME: Theme = {name: 'vox_collage', Backdrop, Surface, Highlight, LogoTreatment, Sticker, Overlay, BrandMark, Outro, transitions, Defs, Paper, PropFrame};

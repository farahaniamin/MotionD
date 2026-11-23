// PAPER CUT theme — layered craft paper, die-cut stickers, stop-motion "on twos".
// Copied to src/theme/active.tsx by tools/set_style.py. Implements engine/contract.ts.
import React from 'react';
import {Img, staticFile} from 'remotion';
import {Theme, TransitionFn} from '../engine/contract';
import {BRAND, H, PAL, STYLE, W, FONT_FAMILY, LATIN_FAMILY, fontWeightStyle, rem, shade, withAlpha, paperColor, textOn} from '../engine/tokens';
import {boil, clamp, easeBack, easeOutQuart, easeInOut, noise, range, stepT} from '../engine/time';

const S = STYLE.surface as {radius: number; roughness: number; grain: number; layerOffset: number; shadowDepth: number; roughEdges: boolean};
// Rough cut edges are the single most expensive effect (~2x render time). Set surface.roughEdges=false for drafts.
const ROUGH = S.roughEdges !== false ? 'url(#pc-rough) ' : '';
const ROUGH_STRONG = S.roughEdges !== false ? 'url(#pc-rough-strong) ' : '';
const L = STYLE.logo as {dieCut: number; lift: number; texture: number; layerLift: number};

// Paper fiber texture: pre-baked tiles (styles/paper_cut/textures/*.png). Procedural feTurbulence
// backgrounds look identical but cost ~10x render time, so they are baked once.
const FIBER = `url(${staticFile('style/textures/fiber.png')})`;
const DISPLACE = staticFile('style/textures/displace.png');
const BLOTCH = `url(${staticFile('style/textures/blotch.png')})`;
const PAPER_TEX = `${FIBER}, ${BLOTCH}`;

// Hard paper-stack shadow: a crisp contact edge + a soft ambient drop
const paperShadow = (elev: number) => {
  const d = S.shadowDepth * (0.6 + elev * 0.5);
  return `drop-shadow(0 ${Math.max(1, d * 0.35).toFixed(1)}px 0 ${withAlpha(PAL.shadow, 0.55)}) drop-shadow(0 ${(d * 1.6).toFixed(1)}px ${(d * 2.2).toFixed(1)}px ${withAlpha(PAL.shadow, 0.35)})`;
};

const Defs: React.FC = () => (
  <svg width="0" height="0" style={{position: 'absolute'}}>
    <defs>
      {/* Rough cut edge — applied only to background sheets, never to text or logos' interiors */}
      <filter id="pc-rough" x="-5%" y="-5%" width="110%" height="110%">
        <feImage href={DISPLACE} preserveAspectRatio="none" result="t" />
        <feDisplacementMap in="SourceGraphic" in2="t" scale={S.roughness * 2.2} xChannelSelector="R" yChannelSelector="G" />
      </filter>
      <filter id="pc-rough-strong" x="-8%" y="-8%" width="116%" height="116%">
        <feImage href={DISPLACE} preserveAspectRatio="none" result="t" />
        <feDisplacementMap in="SourceGraphic" in2="t" scale={S.roughness * 4.5} xChannelSelector="R" yChannelSelector="G" />
      </filter>
    </defs>
  </svg>
);

// ---------- Surface: a cut sheet of paper (optionally on top of another sheet) ----------
const Surface: Theme['Surface'] = ({w, h, fill, elevation = 1, radius, seed = 1, padding = 36, style, children}) => {
  const r = radius ?? S.radius;
  const base = fill ?? PAL.surface;
  const under = paperColor(seed + 2);
  const tilt = noise(seed, 3) * 1.6;
  return (
    <div style={{position: 'relative', width: w, height: h, ...style}}>
      {elevation >= 2 && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            transform: `translate(${S.layerOffset * 0.8}px, ${S.layerOffset}px) rotate(${tilt}deg)`,
            background: `${PAPER_TEX}, ${under}`,
            borderRadius: r,
            filter: `${ROUGH}${paperShadow(elevation - 1)}`,
          }}
        />
      )}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: `${PAPER_TEX}, ${base}`,
          borderRadius: r,
          filter: `${ROUGH}${paperShadow(elevation)}`,
        }}
      />
      <div style={{position: 'relative', padding, height: '100%', boxSizing: 'border-box', color: textOn(base)}}>{children}</div>
    </div>
  );
};

// ---------- Highlight: a torn strip of colored paper slid behind the word ----------
const Highlight: Theme['Highlight'] = ({progress, fill, seed = 1, children}) => {
  const p = clamp(progress);
  const color = fill ?? PAL.highlight;
  return (
    <span style={{position: 'relative', display: 'inline-block', padding: '0 0.22em', color: p > 0.45 ? (fill ? textOn(color) : PAL.onHighlight) : 'inherit'}}>
      <span
        style={{
          position: 'absolute',
          left: '-0.06em',
          right: '-0.06em',
          top: '0.12em',
          bottom: '0.02em',
          background: `${PAPER_TEX}, ${color}`,
          transformOrigin: 'right center',
          transform: `scaleX(${p}) rotate(${noise(seed, 1) * 1.8}deg)`,
          filter: `${ROUGH_STRONG}${paperShadow(0)}`,
          zIndex: 0,
        }}
      />
      <span style={{position: 'relative', zIndex: 1}}>{children}</span>
    </span>
  );
};

// ---------- Logo treatment: the REAL vector, re-materialized as layered cut paper ----------
// Geometry is never redrawn: we only (1) die-cut a white sticker border from the logo's own alpha,
// (2) lift each original color layer as a separate sheet, (3) multiply paper fiber inside the shapes.
const LogoTreatment: Theme['LogoTreatment'] = ({layers, src, size, aspect, seed = 1, t}) => {
  const w = size * aspect;
  const h = size;
  const fid = `pc-diecut-${seed}`;
  const cut = L.dieCut * (size / 240);
  const b = boil(seed, t, STYLE.motion.boil * 0.6);
  return (
    <div style={{position: 'relative', width: w, height: h, transform: `rotate(${b.rot}deg)`}}>
      <svg width={w} height={h} style={{position: 'absolute', inset: 0, overflow: 'visible'}}>
        <defs>
          <filter id={fid} x="-40%" y="-40%" width="180%" height="180%">
            <feMorphology in="SourceAlpha" operator="dilate" radius={cut} result="grow" />
            <feTurbulence type="fractalNoise" baseFrequency="0.05" numOctaves="2" seed={seed} result="tb" />
            <feDisplacementMap in="grow" in2="tb" scale={cut * 0.35} result="rough" />
            <feFlood floodColor={PAL.papers[0]} />
            <feComposite in2="rough" operator="in" result="sheet" />
            <feDropShadow dx="0" dy={L.lift * (size / 240)} stdDeviation={L.lift * 0.9 * (size / 240)} floodColor={PAL.shadow} floodOpacity="0.55" />
          </filter>
        </defs>
        <image href={staticFile(src)} width={w} height={h} filter={`url(#${fid})`} />
      </svg>
      {layers.map((ly, i) => (
        <div
          key={ly}
          style={{
            position: 'absolute',
            inset: 0,
            transform: `translateY(${-i * L.layerLift * (size / 240)}px)`,
            filter: i > 0 ? `drop-shadow(0 ${(1.2 + i * 0.6) * (size / 240)}px 0 ${withAlpha(PAL.shadow, 0.45)})` : undefined,
          }}
        >
          <Img src={staticFile(ly)} style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}} />
          <div
            style={{
              position: 'absolute',
              inset: 0,
              background: PAPER_TEX,
              mixBlendMode: 'multiply',
              opacity: L.texture,
              WebkitMaskImage: `url(${staticFile(ly)})`,
              maskImage: `url(${staticFile(ly)})`,
              WebkitMaskSize: '100% 100%',
              maskSize: '100% 100%',
            }}
          />
        </div>
      ))}
    </div>
  );
};

const Sticker: Theme['Sticker'] = ({children, fill, seed = 1, rotate}) => {
  const f = fill ?? PAL.accent;
  return (
    <div style={{position: 'relative', display: 'inline-block', transform: `rotate(${rotate ?? noise(seed, 2) * 6}deg)`}}>
      <div
        style={{
          position: 'absolute',
          inset: -10,
          background: `${PAPER_TEX}, ${PAL.papers[0]}`,
          borderRadius: 26,
          filter: `${ROUGH}${paperShadow(2)}`,
        }}
      />
      <div style={{position: 'absolute', inset: 0, background: `${PAPER_TEX}, ${f}`, borderRadius: 18, filter: ROUGH || undefined}} />
      <div style={{position: 'relative', padding: '18px 34px', color: textOn(f)}}>{children}</div>
    </div>
  );
};

const mix = (a: string, b: string, t: number) => {
  const pa = a.replace('#', ''), pb = b.replace('#', '');
  const ch = (i: number) => Math.round(parseInt(pa.slice(i, i + 2), 16) * (1 - t) + parseInt(pb.slice(i, i + 2), 16) * t);
  return `#${[0, 2, 4].map((i) => ch(i).toString(16).padStart(2, '0')).join('')}`;
};

// ---------- Backdrop: a paper diorama — base sheet + layered torn hills, seeded per scene ----------
const hillPath = (seed: number, y: number, amp: number) => {
  const pts: string[] = [`M -40 ${H + 40}`, `L -40 ${y}`];
  const n = 7;
  for (let i = 0; i <= n; i++) {
    const x = (i / n) * (W + 80) - 40;
    const yy = y + noise(seed, i) * amp;
    const cx = x - (W + 80) / n / 2;
    pts.push(`Q ${cx.toFixed(0)} ${(yy - amp * 0.9 * Math.abs(noise(seed + 3, i))).toFixed(0)} ${x.toFixed(0)} ${yy.toFixed(0)}`);
  }
  pts.push(`L ${W + 40} ${H + 40} Z`);
  return pts.join(' ');
};

const Backdrop: Theme['Backdrop'] = ({t, tone, sceneIdx}) => {
  const base = tone === 'dark' ? PAL.bgDark : tone === 'accent' ? PAL.accent : tone === 'alt' ? PAL.bgAlt : PAL.bg;
  const isDark = tone === 'dark';
  const seed = sceneIdx * 3.7 + 1;
  const st = stepT(t);
  const front = mix(paperColor(sceneIdx + 2), base, isDark ? 0.55 : 0.42);
  const layers = [
    {y: 1470, amp: 80, c: shade(base, isDark ? 0.1 : -0.08), par: 6},
    {y: 1620, amp: 66, c: shade(base, isDark ? 0.2 : -0.16), par: 10},
    {y: 1770, amp: 50, c: front, par: 14},
  ];
  return (
    <div style={{position: 'absolute', inset: 0, background: `${PAPER_TEX}, ${base}`}}>
      <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
        {layers.map((ly, i) => (
          <path
            key={i}
            d={hillPath(seed + i * 11, ly.y + Math.sin(st * 0.9 + i) * ly.par * 0.3, ly.amp)}
            fill={ly.c}
            style={{filter: `${ROUGH}${paperShadow(i)}`}}
          />
        ))}
      </svg>
      {/* confetti scraps */}
      {[0, 1, 2, 3].map((k) => {
        const x = 90 + ((noise(seed, k + 20) + 1) / 2) * (W - 180);
        const y = 260 + ((noise(seed, k + 40) + 1) / 2) * 1050;
        const s = 18 + Math.abs(noise(seed, k + 60)) * 26;
        const bb = boil(seed + k, t, 1.2);
        return (
          <div
            key={k}
            style={{
              position: 'absolute',
              left: x + bb.dx,
              top: y + bb.dy,
              width: s,
              height: s * 0.62,
              background: `${PAPER_TEX}, ${paperColor(seed + k + 1)}`,
              borderRadius: 4,
              transform: `rotate(${noise(seed, k) * 50 + bb.rot * 4}deg)`,
              filter: `${ROUGH}${paperShadow(0)}`,
              opacity: 0.85,
            }}
          />
        );
      })}
    </div>
  );
};

const Overlay: Theme['Overlay'] = () => (
  <div style={{position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 90}}>
    <div style={{position: 'absolute', inset: 0, backgroundImage: FIBER, backgroundSize: '384px 384px', opacity: S.grain, mixBlendMode: 'multiply'}} />
    <div
      style={{
        position: 'absolute',
        inset: 0,
        background: `radial-gradient(ellipse 85% 70% at 50% 48%, transparent 55%, ${withAlpha(PAL.shadow, 0.28)} 100%)`,
      }}
    />
  </div>
);

const BrandMark: Theme['BrandMark'] = ({t}) => {
  const b = boil(91, t, 0.6);
  return (
    <div style={{position: 'absolute', top: 92, left: 0, right: 0, display: 'flex', justifyContent: 'center', zIndex: 60}}>
      <div style={{transform: `rotate(${-1.5 + b.rot}deg)`}}>
        <Surface w="auto" fill={PAL.papers[0]} elevation={1} radius={12} padding="10px 26px" seed={5}>
          <span style={{fontFamily: LATIN_FAMILY, fontSize: rem(1.5), letterSpacing: '0.24em', color: PAL.ink, ...fontWeightStyle(800)}}>
            {BRAND.wordmark}
          </span>
        </Surface>
      </div>
    </div>
  );
};

const Outro: Theme['Outro'] = ({localT}) => {
  const lt = stepT(localT);
  const sheets = [PAL.papers[1], PAL.papers[2], PAL.papers[3]];
  const title = easeBack(range(lt, 0.35, 0.5));
  const tag = easeOutQuart(range(lt, 0.7, 0.45));
  return (
    <div style={{position: 'absolute', inset: 0, background: `${PAPER_TEX}, ${PAL.bg}`, fontFamily: FONT_FAMILY}}>
      {sheets.map((c, i) => {
        const p = easeOutQuart(range(lt, i * 0.09, 0.42));
        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: -60,
              right: -60,
              top: 640 + i * 70,
              height: 900,
              background: `${PAPER_TEX}, ${c}`,
              borderRadius: 40,
              transform: `translateY(${(1 - p) * 1300}px) rotate(${(i - 1) * 3.5}deg)`,
              filter: `${ROUGH}${paperShadow(2)}`,
            }}
          />
        );
      })}
      <div style={{position: 'absolute', top: 760, left: 0, right: 0, textAlign: 'center', transform: `scale(${0.6 + title * 0.4})`, opacity: clamp(title * 2)}}>
        <Sticker fill={PAL.papers[0]} seed={3} rotate={-3}>
          <span style={{fontFamily: LATIN_FAMILY, fontSize: rem(6), letterSpacing: '0.06em', color: PAL.ink, ...fontWeightStyle(900)}}>{BRAND.wordmark}</span>
        </Sticker>
      </div>
      <div style={{position: 'absolute', top: 1030, left: 130, right: 130, textAlign: 'center', opacity: tag, transform: `translateY(${(1 - tag) * 30}px)`}}>
        <span style={{fontSize: rem(2.6), color: textOn(sheets[2]), ...fontWeightStyle(800)}}>{BRAND.outroTagline}</span>
      </div>
      <div style={{position: 'absolute', bottom: 300, left: 0, right: 0, textAlign: 'center', opacity: tag}}>
        <span style={{fontFamily: LATIN_FAMILY, fontSize: rem(1.4), letterSpacing: '0.3em', color: textOn(sheets[2]), ...fontWeightStyle(700)}}>{BRAND.outroFooter}</span>
      </div>
    </div>
  );
};

// ---------- Transitions: sheets of paper placed over each other ----------
const tornEdge = (p: number, seed: number, vertical: boolean) => {
  const n = 22;
  const edge = (1 - p) * 112 - 6; // percentage
  const pts: string[] = [];
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * 100;
    const jag = edge + noise(seed, i) * 2.6;
    pts.push(vertical ? `${jag}% ${a}%` : `${a}% ${jag}%`);
  }
  return vertical ? `polygon(100% 0%, ${pts.join(', ')}, 100% 100%)` : `polygon(${pts.join(', ')}, 100% 100%, 0% 100%)`;
};

const slide = (dx: number, dy: number, rot: number): TransitionFn => (p, dir) => {
  const e = easeInOut(p);
  if (dir === 'in') return {transform: `translate(${(1 - e) * dx}px, ${(1 - e) * dy}px) rotate(${(1 - e) * rot}deg)`, shadow: true};
  return {transform: `scale(${1 - 0.05 * e})`, filter: `brightness(${1 - 0.18 * e})`};
};

const transitions: Theme['transitions'] = {
  'paper-up': slide(0, H * 1.08, -5),
  'paper-left': slide(-W * 1.1, 60, 4),
  'paper-right': slide(W * 1.1, 60, -4),
  stack: (p, dir) => {
    const e = easeOutQuart(p);
    if (dir === 'in') return {transform: `translateY(${(1 - e) * -140}px) scale(${1 + (1 - e) * 0.12}) rotate(${(1 - e) * 3}deg)`, opacity: clamp(p * 3), shadow: true};
    return {filter: `brightness(${1 - 0.15 * e})`};
  },
  tear: (p, dir, seed) => (dir === 'in' ? {clipPath: tornEdge(easeInOut(p), seed, false), shadow: true} : {}),
  'tear-side': (p, dir, seed) => (dir === 'in' ? {clipPath: tornEdge(easeInOut(p), seed, true), shadow: true} : {}),
  pop: (p, dir) => (dir === 'in' ? {transform: `scale(${0.9 + 0.1 * easeBack(p)})`, opacity: clamp(p * 2.5)} : {opacity: 1 - p}),
  cut: () => ({}),
};

export const THEME: Theme = {name: 'paper_cut', Backdrop, Surface, Highlight, LogoTreatment, Sticker, Overlay, BrandMark, Outro, transitions, Defs};

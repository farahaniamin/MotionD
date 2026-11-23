// Style-agnostic tokens. NOTHING in engine/ or kit/ may hardcode a color, radius or shadow:
// every visual decision comes from STYLE (styles/<name>/style.json, synced to src/style.json)
// or is delegated to the active theme (src/theme/active.tsx).
import BRAND_RAW from '../brand.json';
import STYLE_RAW from '../style.json';

export const W = 1080;
export const H = 1920;
export const FPS = 30;

// Mobile safe zones (Instagram / TikTok / Shorts UI overlays)
export const SAFE_X = 130;
export const SAFE_Y_TOP = 240;
export const SAFE_Y_BOTTOM = 1520;

export const BRAND = BRAND_RAW as Record<string, any>;

export type Palette = {
  bg: string;
  bgAlt: string;
  bgDark: string;
  ink: string;
  inkSoft: string;
  onDark: string;
  onDarkSoft: string;
  accent: string;
  accent2: string;
  highlight: string;
  onHighlight: string;
  surface: string;
  surfaceAlt: string;
  line: string;
  shadow: string;
  papers: string[];
};

export type TypeRole = {weight: number; rem: number; tracking?: number};

export type StyleSpec = {
  name: string;
  label: string;
  palette: Palette;
  typography: {
    fontFamily?: string | null;
    fontFile?: string | null;
    latinFamily: string;
    latinFile?: string | null;
    monoFamily: string;
    setup: TypeRole;
    focus: TypeRole;
    hero: TypeRole;
    mega: TypeRole;
    body: TypeRole;
    caption: TypeRole;
    lineHeight: number;
  };
  motion: {
    stepFps: number | null; // e.g. 12 => stop-motion "on twos"; null => smooth 30fps
    boil: number; // per-step jitter amount (deg / px). 0 = none
    overshoot: number;
    enterDur: number;
    stagger: number;
    cameraPush: number;
  };
  surface: Record<string, any>;
  logo: Record<string, any>;
  transitions: {first: string; cycle: string[]; durIn: number; durOut: number};
  darkScenes: 'never' | 'accent' | 'mixed';
  [k: string]: any;
};

export const STYLE = STYLE_RAW as unknown as StyleSpec;
export const PAL = STYLE.palette;
export const TYPE = STYLE.typography;
export const MOTION = STYLE.motion;

// 'FaDigits' (only U+06F0-06F9 etc.) comes first when the chosen Persian font draws Arabic-style digits
export const FONT_FAMILY = `${BRAND.digitFontFile ? "'FaDigits', " : ''}'${TYPE.fontFamily || BRAND.fontFamily}', ${TYPE.latinFamily}, sans-serif`;
export const LATIN_FAMILY = `${TYPE.latinFamily}, sans-serif`;
export const MONO_FAMILY = `${TYPE.monoFamily}, monospace`;
export const FONT_FILE: string = TYPE.fontFile || BRAND.fontFile;

export const rem = (val: number): string => `${val}rem`;

export const fontWeightStyle = (weight: number): {fontWeight: number; fontVariationSettings: string} => {
  const w = Math.round(Math.min(950, Math.max(100, weight)));
  return {fontWeight: Math.min(900, w), fontVariationSettings: `'wght' ${w}`};
};

export const roleStyle = (role: keyof StyleSpec['typography'] & ('setup' | 'focus' | 'hero' | 'mega' | 'body' | 'caption')) => {
  const r = TYPE[role] as TypeRole;
  return {fontSize: rem(r.rem), letterSpacing: r.tracking ? `${r.tracking}em` : undefined, ...fontWeightStyle(r.weight)};
};

// ---------- Color helpers ----------
const hexToRgb = (hex: string): [number, number, number] | null => {
  let c = (hex || '').trim().replace('#', '');
  if (c.length === 3) c = c.split('').map((ch) => ch + ch).join('');
  if (c.length !== 6) return null;
  return [parseInt(c.slice(0, 2), 16), parseInt(c.slice(2, 4), 16), parseInt(c.slice(4, 6), 16)];
};

export const withAlpha = (color: string, alpha: number): string => {
  const rgb = hexToRgb(color);
  return rgb ? `rgba(${rgb[0]}, ${rgb[1]}, ${rgb[2]}, ${alpha})` : color;
};

export const luminance = (hex: string): number => {
  const rgb = hexToRgb(hex);
  if (!rgb) return 0.5;
  const [r, g, b] = rgb.map((v) => {
    const s = v / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};

export const contrastRatio = (a: string, b: string): number => {
  const la = luminance(a);
  const lb = luminance(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
};

/** Pick the readable text color for a given fill (WCAG >= 4.5 preferred). */
export const textOn = (fill: string): string =>
  contrastRatio(fill, PAL.ink) >= contrastRatio(fill, PAL.onDark) ? PAL.ink : PAL.onDark;

export const shade = (hex: string, amount: number): string => {
  const rgb = hexToRgb(hex);
  if (!rgb) return hex;
  const f = (v: number) => Math.round(Math.min(255, Math.max(0, amount < 0 ? v * (1 + amount) : v + (255 - v) * amount)));
  return `#${rgb.map((v) => f(v).toString(16).padStart(2, '0')).join('')}`;
};

/** Deterministic paper/accent pick so the same seed always gets the same color. */
export const paperColor = (seed: number): string => PAL.papers[Math.abs(Math.floor(seed)) % PAL.papers.length];

export const toFaDigits = (input: string | number): string =>
  String(input).replace(/\d/g, (d) => '۰۱۲۳۴۵۶۷۸۹'[Number(d)]);

export const hasPersian = (text: string): boolean => /[؀-ۿ]/.test(text || '');

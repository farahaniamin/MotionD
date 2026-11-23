// Timing, easing, timeline lookup and stop-motion helpers. Style-agnostic: the "feel" (smooth vs
// stepped, jitter amount, overshoot) is read from STYLE.motion so switching style changes the motion
// personality without touching scenes.
import TIMELINE from '../timeline.json';
import {MOTION} from './tokens';

export const clamp = (x: number, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a: number, b: number, p: number) => a + (b - a) * p;
export const range = (t: number, from: number, dur: number) => clamp((t - from) / Math.max(0.001, dur));

export const easeOut = (x: number) => 1 - Math.pow(1 - clamp(x), 3);
export const easeOutQuart = (x: number) => 1 - Math.pow(1 - clamp(x), 4);
export const easeOutExpo = (x: number) => {
  const c = clamp(x);
  return c === 1 ? 1 : 1 - Math.pow(2, -10 * c);
};
export const easeIn = (x: number) => Math.pow(clamp(x), 3);
export const easeInOut = (x: number) => {
  const c = clamp(x);
  return c < 0.5 ? 4 * c * c * c : 1 - Math.pow(-2 * c + 2, 3) / 2;
};
export const easeBack = (x: number, overshoot = MOTION.overshoot) => {
  const c = clamp(x);
  const c3 = overshoot + 1;
  return 1 + c3 * Math.pow(c - 1, 3) + overshoot * Math.pow(c - 1, 2);
};
/** Damped spring that settles at 1 (natural overshoot + settle). */
export const spring = (x: number, damping = 6.5, freq = 9.5) => {
  const c = clamp(x);
  if (c <= 0) return 0;
  if (c >= 1) return 1;
  return 1 - Math.exp(-damping * c) * Math.cos(freq * c);
};

// ---------- Stop-motion ----------
/** Quantize time to the style's step rate (paper cut animates "on twos" = 12fps). */
export const stepT = (t: number): number => (MOTION.stepFps ? Math.floor(t * MOTION.stepFps + 1e-6) / MOTION.stepFps : t);

/** Deterministic hash noise in [-1, 1]. */
export const noise = (seed: number, i: number): number => {
  const s = Math.sin(seed * 127.1 + i * 311.7) * 43758.5453;
  return (s - Math.floor(s)) * 2 - 1;
};

/** "Line boil": tiny per-step wobble that makes hand-made styles feel alive. Zero for smooth styles. */
export const boil = (seed: number, t: number, amount = MOTION.boil) => {
  if (!amount) return {dx: 0, dy: 0, rot: 0};
  const step = Math.floor(t * (MOTION.stepFps || 8));
  return {dx: noise(seed, step) * amount, dy: noise(seed + 7, step) * amount, rot: noise(seed + 13, step) * amount * 0.6};
};

/** Standard entrance progress honoring the style's stepping + overshoot. Returns 0..~1.1 */
export const enter = (t: number, at: number, dur = MOTION.enterDur) => easeBack(range(stepT(t), at, dur));
export const enterSoft = (t: number, at: number, dur = MOTION.enterDur) => easeOutQuart(range(stepT(t), at, dur));

// ---------- Timeline (audio-driven — never hardcode seconds in scenes) ----------
type Word = {t: string; s: number; e: number};
type Beat = {id: number; s: number; e: number; scene_end: number; words: Word[]};
const BEATS = (TIMELINE as any).beats as Beat[];

export const VOICE_END = (TIMELINE as any).voice_end as number;
export const TOTAL_DUR = (TIMELINE as any).total_dur as number;
export const beatStart = (b: number): number => BEATS[b]?.s ?? 0;
export const beatEnd = (b: number): number => BEATS[b]?.scene_end ?? 0;
export const beatDur = (b: number): number => Math.max(0.2, beatEnd(b) - beatStart(b));
export const beatFrac = (b: number, f: number): number => beatStart(b) + clamp(f) * beatDur(b);
export const wordTime = (b: number, idx: number): number => {
  const words = BEATS[b]?.words ?? [];
  if (!words.length) return beatStart(b);
  return words[Math.min(words.length - 1, Math.max(0, idx))].s;
};
export const wordEnd = (b: number, idx: number): number => {
  const words = BEATS[b]?.words ?? [];
  if (!words.length) return beatEnd(b);
  const w = words[Math.min(words.length - 1, Math.max(0, idx))];
  return w.e ?? w.s + 0.25;
};
/** Find the first word in beat b containing `needle` (diacritics-insensitive). Falls back to beat start. */
export const wordAt = (b: number, needle: string): number => {
  const norm = (s: string) => s.replace(/[ً-ْ‌،.!؟?]/g, '');
  const words = BEATS[b]?.words ?? [];
  const hit = words.find((w) => norm(w.t).includes(norm(needle)));
  return hit ? hit.s : beatStart(b);
};

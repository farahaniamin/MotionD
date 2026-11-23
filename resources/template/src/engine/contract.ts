// The Theme contract. A style pack (styles/<name>/theme.tsx) implements this interface; every kit/
// component renders its *shape language* through these slots, so swapping the theme file restyles the
// whole reel (backgrounds, cards, highlights, logo treatment, transitions, outro) with zero scene edits.
import React from 'react';

export type SceneTone = 'light' | 'alt' | 'dark' | 'accent';

export type BackdropProps = {t: number; tone: SceneTone; sceneIdx: number; focus: [number, number]};

export type SurfaceProps = {
  w: number | string;
  h?: number | string;
  /** fill color; defaults to palette.surface */
  fill?: string;
  /** visual depth level 0..3 */
  elevation?: number;
  radius?: number;
  seed?: number;
  padding?: number | string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
};

export type HighlightProps = {
  /** 0..1 reveal progress */
  progress: number;
  fill?: string;
  seed?: number;
  children: React.ReactNode;
};

export type LogoTreatmentProps = {
  /** public/ relative paths of color layers (bottom → top). Always the REAL vector, never redrawn. */
  layers: string[];
  /** full original logo (used for silhouette effects: shadow, die-cut border) */
  src: string;
  size: number;
  aspect: number; // width / height of the logo artwork
  seed?: number;
  onDark?: boolean;
  t: number;
};

export type StickerProps = {children: React.ReactNode; fill?: string; seed?: number; rotate?: number};

export type TransitionFrame = {
  transform?: string;
  opacity?: number;
  filter?: string;
  clipPath?: string;
  shadow?: boolean;
};

/** p goes 0→1 over the transition window. `dir` = 'in' for the entering scene, 'out' for the leaving one. */
export type TransitionFn = (p: number, dir: 'in' | 'out', seed: number) => TransitionFrame;

export type OutroProps = {localT: number; dur: number};

/** A sheet of the style's paper/material (used by TornReveal and collage blocks). */
export type PaperProps = {fill: string; seed?: number; style?: React.CSSProperties; children?: React.ReactNode};

/** How an AI-generated cut-out image (Prop) is mounted in this style. */
export type PropFrameProps = {src: string; w: number; seed: number; t: number};

export type Theme = {
  name: string;
  Backdrop: React.FC<BackdropProps>;
  Surface: React.FC<SurfaceProps>;
  Highlight: React.FC<HighlightProps>;
  LogoTreatment: React.FC<LogoTreatmentProps>;
  Sticker: React.FC<StickerProps>;
  /** Full-frame texture / grain drawn above everything */
  Overlay: React.FC<{t: number}>;
  /** Persistent brand mark (top of frame) */
  BrandMark: React.FC<{t: number; onDark: boolean}>;
  Outro: React.FC<OutroProps>;
  transitions: Record<string, TransitionFn>;
  /** SVG <defs> (filters, patterns) mounted once at the root */
  Defs: React.FC;
  /** optional: material sheet; kit falls back to a flat fill */
  Paper?: React.FC<PaperProps>;
  /** optional: cut-out image mounting (die-cut border, tape, halftone…); kit falls back to a drop shadow */
  PropFrame?: React.FC<PropFrameProps>;
};

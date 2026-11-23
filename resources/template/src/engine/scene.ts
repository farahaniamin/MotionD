import React from 'react';
import {SceneTone} from './contract';
import {PAL, contrastRatio} from './tokens';

export type SceneFn = (t: number, localT: number, dur: number) => React.ReactNode;

export type SceneDef = {
  fn: SceneFn;
  s: number;
  e: number;
  /** background tone of this scene; drives automatic text colors in every kit component */
  tone?: SceneTone;
  /** transition name from the active theme (falls back to the style's cycle) */
  transition?: string;
  /** light focus point [x%, y%] for themes that use one */
  focus?: [number, number];
  /** hide the persistent brand mark during this scene */
  hideBrandMark?: boolean;
};

export type SceneInfo = {tone: SceneTone; idx: number; onDark: boolean};
export const SceneContext = React.createContext<SceneInfo>({tone: 'light', idx: 0, onDark: false});
export const useScene = () => React.useContext(SceneContext);

/** Background color of a tone in the active palette. */
export const toneColor = (tone: SceneTone): string =>
  tone === 'dark' ? PAL.bgDark : tone === 'accent' ? PAL.accent : tone === 'alt' ? PAL.bgAlt : PAL.bg;

/** True when the tone's ACTUAL color is dark (palette presets may make even 'light' scenes dark). */
export const isDarkTone = (tone: SceneTone) => contrastRatio(toneColor(tone), PAL.onDark) > contrastRatio(toneColor(tone), PAL.ink);

/** Text colors that adapt to the current scene tone. */
export const useInk = () => {
  const {onDark} = useScene();
  return {ink: onDark ? PAL.onDark : PAL.ink, soft: onDark ? PAL.onDarkSoft : PAL.inkSoft};
};

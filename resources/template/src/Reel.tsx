// Style-agnostic compositor. Every scene owns its backdrop (so paper sheets can physically cover the
// previous scene), transitions come from the active theme, and the outro is appended automatically.
import React, {useEffect, useState} from 'react';
import {AbsoluteFill, Audio, continueRender, delayRender, staticFile, useCurrentFrame} from 'remotion';
import {THEME} from './theme/active';
import {BRAND, FONT_FILE, FPS, MOTION, PAL, STYLE, withAlpha} from './engine/tokens';
import {VOICE_END, TOTAL_DUR, clamp, stepT} from './engine/time';
import {SceneContext, isDarkTone} from './engine/scene';
import {SceneTone} from './engine/contract';
import {SCENES} from './scenes';

export const DURATION = TOTAL_DUR;
const TR = STYLE.transitions as {first: string; cycle: string[]; durIn: number; durOut: number; stepped?: boolean};
const OUTRO_START = VOICE_END + 0.35;

type Slot = {render: (t: number, l: number, d: number) => React.ReactNode; s: number; e: number; tone: SceneTone; transition: string; focus: [number, number]; outro?: boolean; hideBrandMark?: boolean};

const SLOTS: Slot[] = [
  ...SCENES.map((sc, i) => ({
    render: sc.fn,
    s: sc.s,
    e: i === SCENES.length - 1 ? Math.max(sc.e, OUTRO_START) : sc.e,
    tone: sc.tone ?? 'light',
    transition: sc.transition ?? (i === 0 ? TR.first : TR.cycle[(i - 1) % TR.cycle.length]),
    focus: sc.focus ?? [50, 46],
    hideBrandMark: sc.hideBrandMark,
  })),
  {render: () => null, s: OUTRO_START, e: TOTAL_DUR + 1, tone: 'light', transition: TR.cycle[0], focus: [50, 46], outro: true},
];

const fontFormat = (file: string) => (file.endsWith('.woff2') ? 'woff2' : file.endsWith('.woff') ? 'woff' : file.endsWith('.otf') ? 'opentype' : 'truetype');
const family = (STYLE.typography.fontFamily as string) || BRAND.fontFamily;

export const Reel: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / FPS;
  const tt = TR.stepped ? stepT(t) : t;
  const [handle] = useState(() => delayRender('font'));

  useEffect(() => {
    const faces = [new FontFace(family, `url(${staticFile(FONT_FILE)}) format('${fontFormat(FONT_FILE)}')`, {weight: '100 950'})];
    if (BRAND.digitFontFile) {
      faces.push(new FontFace('FaDigits', `url(${staticFile(BRAND.digitFontFile)}) format('${fontFormat(BRAND.digitFontFile)}')`, {weight: '100 900', unicodeRange: 'U+06F0-06F9, U+0660-0669, U+066A-066C'}));
    }
    const latinFile = STYLE.typography.latinFile;
    if (latinFile) {
      const latinName = STYLE.typography.latinFamily.split(',')[0].replace(/['"]/g, '').trim();
      faces.push(new FontFace(latinName, `url(${staticFile(latinFile)}) format('${fontFormat(latinFile)}')`, {weight: '100 1000'}));
    }
    // allSettled: one missing font must never take the others down with it
    Promise.allSettled(faces.map((f) => f.load())).then((results) => {
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') (document as any).fonts.add(r.value);
        else console.error(`Font load error (${faces[i].family})`, r.reason);
      });
      continueRender(handle);
    });
  }, [handle]);

  let current = SLOTS[0];
  for (const s of SLOTS) if (t >= s.s) current = s;
  const brandOnDark = isDarkTone(current.tone);

  return (
    <AbsoluteFill style={{background: PAL.bg, overflow: 'hidden'}}>
      <THEME.Defs />
      <Audio src={staticFile('audio/final_mix.wav')} />

      {SLOTS.map((sc, idx) => {
        const next = SLOTS[idx + 1];
        const inT = idx === 0 ? Math.min(TR.durIn, 0.4) : TR.durIn;
        // scene is visible from its start until the next scene's IN transition has fully covered it
        if (tt < sc.s || (next && tt > next.s + TR.durIn + 0.02)) return null;
        const local = Math.max(0, t - sc.s);
        const dur = Math.max(0.2, sc.e - sc.s);
        const fnIn = THEME.transitions[sc.transition] ?? THEME.transitions.cut;
        let frameIn = {} as ReturnType<typeof fnIn>;
        if (tt - sc.s < inT) frameIn = fnIn(clamp((tt - sc.s) / inT), 'in', idx + 1);
        let frameOut = {} as ReturnType<typeof fnIn>;
        if (next && tt >= next.s) {
          const fnOut = THEME.transitions[next.transition] ?? THEME.transitions.cut;
          frameOut = fnOut(clamp((tt - next.s) / TR.durOut), 'out', idx + 2);
        }
        const push = 1 + MOTION.cameraPush * clamp(local / dur);
        const transforms = [frameIn.transform, frameOut.transform, `scale(${push.toFixed(4)})`].filter(Boolean).join(' ');
        const filters = [frameIn.filter, frameOut.filter].filter(Boolean).join(' ');
        const tone = sc.tone;
        return (
          <div
            key={idx}
            style={{
              position: 'absolute',
              inset: 0,
              transform: transforms,
              opacity: (frameIn.opacity ?? 1) * (frameOut.opacity ?? 1),
              filter: [filters, frameIn.shadow ? `drop-shadow(0 -18px 40px ${withAlpha(PAL.shadow, 0.35)})` : ''].filter(Boolean).join(' ') || undefined,
              clipPath: frameIn.clipPath,
              zIndex: idx,
            }}
          >
            <SceneContext.Provider value={{tone, idx, onDark: isDarkTone(tone)}}>
              {sc.outro ? (
                <THEME.Outro localT={Math.max(0, t - sc.s)} dur={Math.max(0.5, TOTAL_DUR - sc.s)} />
              ) : (
                <>
                  <THEME.Backdrop t={t} tone={tone} sceneIdx={idx} focus={sc.focus} />
                  {sc.render(t, local, dur)}
                </>
              )}
            </SceneContext.Provider>
          </div>
        );
      })}

      {t < OUTRO_START && !current.hideBrandMark && (
        <div style={{position: 'absolute', inset: 0, zIndex: 70, opacity: clamp((OUTRO_START - t) / 0.25)}}>
          <THEME.BrandMark t={t} onDark={brandOnDark} />
        </div>
      )}
      <THEME.Overlay t={t} />
    </AbsoluteFill>
  );
};

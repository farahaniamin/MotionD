// Project scenes. Import EVERYTHING from './kit'. Never hardcode colors (use PAL.*), px font sizes
// (use roles) or seconds (use wordTime/wordAt/beatStart). See examples/ai_tools_reel/scenes.tsx.
import React from 'react';
import {SceneDef, SceneFn, Headline, beatStart, beatEnd, wordTime} from './kit';

const S0: SceneFn = (t) => (
  <Headline
    t={t}
    top={520}
    lines={[
      [{text: 'اینجا', at: wordTime(0, 0), role: 'setup', tone: 'soft'}, {text: 'شروع', at: wordTime(0, 1), role: 'focus'}],
      [{text: 'داستان', at: wordTime(0, 2), role: 'hero', mark: true}],
    ]}
  />
);

export const SCENES: SceneDef[] = [{fn: S0, s: beatStart(0), e: beatEnd(0), tone: 'light'}];

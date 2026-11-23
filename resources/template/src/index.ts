import React from 'react';
import {Composition, registerRoot} from 'remotion';
import {Reel, DURATION} from './Reel';
import {W, H, FPS} from './engine/tokens';

const Root: React.FC = () =>
  React.createElement(Composition, {
    id: 'Reel',
    component: Reel,
    durationInFrames: Math.max(30, Math.round(DURATION * FPS)),
    fps: FPS,
    width: W,
    height: H,
  });

registerRoot(Root);

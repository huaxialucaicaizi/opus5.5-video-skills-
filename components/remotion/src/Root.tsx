// Root.tsx — registers one Remotion <Composition> per storyboard. Add more by importing other storyboards.
import React from 'react';
import { Composition } from 'remotion';
import { CanvasComposition } from './CanvasComposition';
import storyboard from '../../../examples/ai-explainer-15s/storyboard.json';
import style from '../../../templates/visual-style/style.default.json';

const fromStoryboard = (sb: any) => ({
  durationInFrames: Math.round(sb.duration_s * sb.fps),
  fps: sb.fps,
  width: sb.width,
  height: sb.height,
});

export const RemotionRoot: React.FC = () => (
  <>
    <Composition
      id={storyboard.task_id}
      component={CanvasComposition}
      {...fromStoryboard(storyboard)}
      defaultProps={{ storyboard, style /* , audio: 'audio.wav'  (after copying it into public/) */ }}
    />
  </>
);

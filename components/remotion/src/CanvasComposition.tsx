// CanvasComposition — renders the shared html-canvas engine inside Remotion.
// The scenes are the same files the HTML player uses, so a storyboard renders identically on both paths.
import React, { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { AbsoluteFill, Audio, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
// @ts-ignore — plain ES module shared with the HTML player
import { createComposition } from '../../html-canvas/engine.js';
// @ts-ignore
import { scenes } from '../../html-canvas/scenes/index.js';

export type CanvasCompositionProps = {
  storyboard: Record<string, any>;
  style: Record<string, any>;
  /** File in the Remotion project's public/ folder, e.g. "audio.wav" (made by scripts/render/synth_music.py). */
  audio?: string;
};

const makeCanvas = (w: number, h: number) => {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
};

async function loadFonts(stack: string[]) {
  const family = stack.map(f => `"${f}"`).join(',');
  await Promise.all([400, 600, 800, 900].map(w => document.fonts.load(`${w} 40px ${family}`, '测试AIabc0')));
  await document.fonts.ready;
}

export const CanvasComposition: React.FC<CanvasCompositionProps> = ({ storyboard, style, audio }) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const ref = useRef<HTMLCanvasElement>(null);
  // Hold the render until fonts are loaded AND the first frame is painted.
  const [handle] = useState(() => delayRender('ai-video-skills: fonts + first frame'));
  const released = useRef(false);
  const [fontsReady, setFontsReady] = useState(false);

  const comp = useMemo(
    () => createComposition({ storyboard, style, scenes, makeCanvas }),
    [storyboard, style],
  );

  useLayoutEffect(() => {
    let alive = true;
    loadFonts(style.typography.font_stack).then(() => alive && setFontsReady(true));
    return () => { alive = false; };
  }, [style]);

  useLayoutEffect(() => {
    if (!fontsReady || !ref.current) return;
    const ctx = ref.current.getContext('2d');
    if (!ctx) throw new Error('2D canvas context unavailable');
    comp.draw(ctx, frame / fps);
    if (!released.current) { released.current = true; continueRender(handle); }
  }, [frame, fps, comp, fontsReady, handle]);

  if (width !== storyboard.width || height !== storyboard.height) {
    throw new Error(`Composition is ${width}x${height} but storyboard is ${storyboard.width}x${storyboard.height}`);
  }
  return (
    <AbsoluteFill>
      <canvas ref={ref} width={width} height={height} style={{ width: '100%', height: '100%' }} />
      {audio ? <Audio src={staticFile(audio)} /> : null}
    </AbsoluteFill>
  );
};

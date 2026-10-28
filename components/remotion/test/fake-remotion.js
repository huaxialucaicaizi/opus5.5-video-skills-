// Minimal stand-in for the parts of the Remotion API that CanvasComposition uses. TEST ONLY.
// It lets the smoke test run the real wrapper with real React in Chromium when Remotion itself
// cannot be installed. It does not prove compatibility with Remotion's renderer.
import React, { useSyncExternalStore } from 'react';

let frame = 0; const subs = new Set();
const cfg = { fps: 30, width: 1080, height: 1920, durationInFrames: 1 };
let pending = 0;
window.__remotionShim = {
  setFrame(f) { frame = f; subs.forEach(s => s()); },
  setConfig(c) { Object.assign(cfg, c); },
  get pending() { return pending; },
};
export const useCurrentFrame = () => useSyncExternalStore(cb => { subs.add(cb); return () => subs.delete(cb); }, () => frame);
export const useVideoConfig = () => cfg;
export const delayRender = () => { pending++; return pending; };
export const continueRender = () => { pending--; };
export const staticFile = f => `/public/${f}`;
export const AbsoluteFill = ({ children }) => React.createElement('div', { style: { position: 'absolute', inset: 0 } }, children);
export const Audio = () => null;
export const Composition = () => null;
export const registerRoot = () => {};

// presenter-placeholder: a stand-in for real talking-head footage in style demos. Draws a simple, clearly
// fake presenter silhouette in a warm room with a slight breathing motion and a label. Never ship it.
// params: { label?='主理人出镜画面（示意）' }
import { rgba, roundRect, TAU } from '../engine.js';

export default function presenterPlaceholder(f, p) {
  const { ctx, u, W, H, t, pal } = f;
  const g = ctx.createLinearGradient(0, 0, 0, H);
  g.addColorStop(0, '#3A332E'); g.addColorStop(1, '#1E1B19');
  ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  // soft window light
  const lg = ctx.createRadialGradient(W * 0.2, H * 0.25, 0, W * 0.2, H * 0.25, H * 0.6);
  lg.addColorStop(0, 'rgba(255,214,170,0.20)'); lg.addColorStop(1, 'rgba(255,214,170,0)');
  ctx.fillStyle = lg; ctx.fillRect(0, 0, W, H);
  const bob = Math.sin(t * TAU * 0.25) * 6 * u, sway = Math.sin(t * TAU * 0.13) * 5 * u;
  const cx = W / 2 + sway, headY = H * 0.40 + bob;
  ctx.fillStyle = '#5A4E46';
  // shoulders
  ctx.beginPath(); ctx.ellipse(cx, H * 0.80 + bob, W * 0.42, H * 0.22, 0, Math.PI, 0); ctx.lineTo(cx + W * 0.42, H); ctx.lineTo(cx - W * 0.42, H); ctx.fill();
  // neck + head
  roundRect(ctx, cx - 70 * u, headY + 120 * u, 140 * u, 180 * u, 40 * u); ctx.fill();
  ctx.beginPath(); ctx.ellipse(cx, headY, 190 * u, 235 * u, 0, 0, TAU); ctx.fill();
  // rim light from the window side
  ctx.strokeStyle = rgba(pal.accent, 0.35); ctx.lineWidth = 6 * u;
  ctx.beginPath(); ctx.ellipse(cx, headY, 190 * u, 235 * u, 0, Math.PI * 0.75, Math.PI * 1.35); ctx.stroke();
  f.text(p.label || '主理人出镜画面（示意）', W / 2, H * 0.56, { role: 'caption', align: 'center', color: 'rgba(242,239,233,0.55)', id: 'ph:label' });
}

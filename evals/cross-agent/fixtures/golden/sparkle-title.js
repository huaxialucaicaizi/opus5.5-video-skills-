// sparkle-title (golden fix for E5): same look, but every value is a pure function of t.
import { ease, seg, hash, TAU } from '../engine.js';

export default function sparkleTitle(f, p) {
  const { ctx, u, pal, W, H, t, lt } = f;
  for (let i = 0; i < 60; i++) {
    const x = hash(`sp${i}x`) * W;
    const y0 = hash(`sp${i}y`) * H * 0.8;
    const y = y0 - 0.4 * u * 30 * t;              // the old per-frame drift, integrated in closed form (30 fps)
    const r = 2 + hash(`sp${i}r`) * 4;
    const tw = 0.5 + 0.5 * Math.sin(t * 3 + x);   // twinkle driven by video time, not wall clock
    ctx.fillStyle = `rgba(255,200,140,${0.25 + 0.6 * tw})`;
    ctx.beginPath(); ctx.arc(x, y, r * u * tw, 0, TAU); ctx.fill();
  }
  const k = ease.easeOutCubic(seg(lt, 0.3, 1.0));
  f.text(p.title, W / 2, H * 0.45 + (1 - k) * 60 * u, { role: 'title', align: 'center', alpha: k, maxWidth: f.safe.w, fit: true, id: 'sp:title' });
  if (p.sub) f.text(p.sub, W / 2, H * 0.45 + 140 * u, { role: 'body', align: 'center', color: pal.text_muted, alpha: seg(lt, 0.9, 1.4), id: 'sp:sub', maxWidth: f.safe.w });
}

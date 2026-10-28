// takeaway: the payoff card. Optional recap row (motif from earlier scenes), headline, subline, and a term badge.
// params: { recap?: [string], kicker?, headline, sub?, term?, termAt?: 1.2 }
import { ease, seg, rgba, roundRect } from '../engine.js';
import { chip, flowLayout, rise } from './_ui.js';

export default function takeaway(f, p) {
  const { ctx, u, pal, W, H, lt, dur, safe } = f;
  f.camera({ push: 0.04 });
  let y = safe.y + 120 * u;
  if (p.recap && p.recap.length) {
    const lay = flowLayout(f, p.recap, { cx: W / 2, top: y, maxW: safe.w, gap: 10, role: 'body', size: 50, padX: 16, padY: 12 });
    lay.items.forEach((it, i) => {
      const r = rise(f, 0.05 + i * 0.04, 14);
      chip(f, it.label, it.x, it.y + r.dy, { role: 'body', size: 50, padX: 16, padY: 12, alpha: r.a * 0.9, id: `tk:r${i}`, radius: 18 });
    });
    y += lay.height + 260 * u;
  } else y = H * 0.4;
  if (p.kicker) {
    const r = rise(f, 0.35, 20);
    f.text(p.kicker, W / 2, y + r.dy, { role: 'caption', align: 'center', color: pal.text_muted, alpha: r.a, id: 'tk:kicker' });
    y += 160 * u;
  }
  const h = rise(f, 0.5, 40);
  const hb = f.text(p.headline, W / 2, y + h.dy, { role: 'title', size: 116, align: 'center', alpha: h.a, id: 'tk:head', maxWidth: safe.w * 0.92, fit: true });
  y += hb.h + 90 * u;
  if (p.sub) {
    const r = rise(f, 0.85, 24);
    const sb = f.text(p.sub, W / 2, y + r.dy, { role: 'body', align: 'center', color: pal.text_muted, alpha: r.a, id: 'tk:sub', maxWidth: safe.w });
    y += sb.h + 150 * u;
  }
  if (p.term) {
    const t0 = p.termAt ?? 1.2;
    const k = ease.easeOutCubic(seg(lt, t0, t0 + 0.5));
    chip(f, p.term, W / 2, y + (1 - k) * 30 * u, {
      role: 'headline', alpha: k, id: 'tk:term', scale: 0.9 + 0.1 * k,
      fill: rgba(pal.accent, 0.18), stroke: pal.accent, strokeW: 5, color: pal.accent,
    });
  }
}

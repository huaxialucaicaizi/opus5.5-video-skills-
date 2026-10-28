// token-split: a sentence appears whole, then splits into token chips; optional ids appear under each chip.
// params: { caption, tokens: [string], ids?: [number|string], idsNote?, splitAt?: 0.9, idsAt?: 1.7, note? }
import { ease, seg, springTo, lerp, rgba } from '../engine.js';
import { chip, flowLayout, stepCaption, rise } from './_ui.js';

export default function tokenSplit(f, p) {
  const { ctx, u, pal, W, H, lt, dur, safe } = f;
  f.camera({ push: 0.025 });
  const out = f.exit; // composition owns transitions; 1 unless the cut is hard
  stepCaption(f, p.caption, rise(f, 0.0, 20).a * out);

  const tokens = p.tokens || [];
  const splitAt = p.splitAt ?? 0.9, idsAt = p.idsAt ?? 1.7;
  const cy = H * 0.45;
  // Final (split) layout.
  const lay = flowLayout(f, tokens, { cx: W / 2, top: cy - 90 * u, maxW: safe.w, gap: 30, role: 'title', padX: 34, padY: 26 });
  // Joined layout: chips touching, as if one sentence.
  const widths = lay.items.map(i => i.w - 68 * u);
  const total = widths.reduce((a, b) => a + b, 0);
  let x0 = W / 2 - total / 2;
  const joined = widths.map(w => { const c = x0 + w / 2; x0 += w; return c; });

  const enter = rise(f, 0.15, 40);
  lay.items.forEach((it, i) => {
    const s = springTo(lt, [[0, 0], [splitAt + i * 0.06, 1]], { stiffness: 190, damping: 20 });
    const x = lerp(joined[i], it.x, s);
    const y = lerp(cy, it.y, s) + enter.dy;
    const boxA = seg(lt, splitAt + 0.18, splitAt + 0.45) * out; // frames appear once chips have separated
    // chip frame fades in as tokens separate; text visible from the start
    chip(f, it.label, x, y, {
      role: 'title', padX: 34, padY: 26, alpha: enter.a * out, id: `tok:${i}`,
      fill: rgba(i % 2 ? pal.support : pal.accent, 0.16 * boxA), stroke: rgba(i % 2 ? pal.support : pal.accent, boxA), strokeW: 4,
    });
    if (p.ids && p.ids[i] != null) {
      const r = rise(f, idsAt + i * 0.1, 16);
      f.text(String(p.ids[i]), it.x, it.y + it.h / 2 + 70 * u + r.dy, { role: 'caption', align: 'center', color: pal.text_muted, alpha: r.a * out, mono: true, id: `tok:id${i}` });
    }
  });
  if (p.note) {
    const r = rise(f, idsAt + 0.5, 16);
    f.text(p.note, W / 2, cy + lay.height + 260 * u + r.dy, { role: 'caption', align: 'center', color: pal.text_muted, alpha: r.a * out, id: 'tok:note', maxWidth: safe.w });
  }
}

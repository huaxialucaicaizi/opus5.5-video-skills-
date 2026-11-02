// list-reveal: a titled vertical list; each row (label chip + explanation) slides in on its own beat and the
// newest row is highlighted. Good for formulas, steps, checklists.
// params: { caption?, title?, items: [{label, text}], firstAt?=0.5, step?=0.6, labelW?: px at reference width }
import { rgba, roundRect, seg } from '../engine.js';
import { stepCaption, rise } from './_ui.js';

export default function listReveal(f, p) {
  const { ctx, u, pal, W, lt, safe, style } = f;
  f.camera({ push: 0.025 });
  const out = f.exit;
  stepCaption(f, p.caption, rise(f, 0, 20).a * out);
  const items = p.items || [], first = p.firstAt ?? 0.5, step = p.step ?? 0.6;
  const inset = safe.w * 0.03;
  let y = safe.y + 190 * u;
  if (p.title) {
    const r = rise(f, 0.1, 30);
    const tb = f.text(p.title, W / 2, y + r.dy, { role: 'headline', align: 'center', alpha: r.a * out, id: `${f.scene.id}:title`, maxWidth: safe.w - inset * 2, fit: true });
    y += tb.h + 90 * u;
  }
  const rowH = Math.min(230 * u, (safe.y + safe.h - y) / Math.max(1, items.length));
  const labelW = (p.labelW ?? 220) * u, chipH = Math.min(120 * u, rowH * 0.72);
  const x0 = safe.x + inset;
  const newest = Math.floor((lt - first) / step);
  items.forEach((it, i) => {
    const t0 = first + i * step;
    const r = rise(f, t0, 0, 0.4);
    const dx = (1 - r.a) * 60 * u;
    const cy = y + i * rowH + chipH / 2;
    const isNew = i === Math.min(newest, items.length - 1);
    const a = r.a * out;
    if (a <= 0.001) return;
    ctx.save(); ctx.globalAlpha *= a;
    roundRect(ctx, x0 - dx, cy - chipH / 2, labelW, chipH, chipH / 2);
    ctx.fillStyle = isNew ? rgba(pal.accent, 0.22) : pal.bg_raised; ctx.fill();
    ctx.strokeStyle = isNew ? pal.accent : pal.line; ctx.lineWidth = 4 * u; ctx.stroke();
    ctx.restore();
    const bid = f.box(`${f.scene.id}:l${i}:box`, x0 - dx, cy - chipH / 2, labelW, chipH, a);
    f.text(it.label, x0 - dx + labelW / 2, cy, { role: 'headline', size: Math.min(style.typography.scale_px.headline, (chipH / u) * 0.62), align: 'center', baseline: 'middle',
      color: isNew ? pal.accent : pal.text, alpha: a, id: `${f.scene.id}:l${i}`, parent: bid });
    f.text(it.text, x0 + labelW + 36 * u + dx * 0.5, cy, { role: 'body', baseline: 'middle', alpha: a * (isNew ? 1 : 0.85),
      color: isNew ? pal.text : pal.text_muted, id: `${f.scene.id}:t${i}`, maxWidth: safe.w - labelW - inset * 2 - 36 * u });   // wraps to 2 lines rather than shrinking
  });
}

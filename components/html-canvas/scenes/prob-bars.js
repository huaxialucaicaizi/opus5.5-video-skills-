// prob-bars: context chips + a question, then horizontal probability bars grow; the winner is picked.
// params: { caption, context: [string], question, options: [{label, p}], pick: index, pickAt?: 2.6, note? }
import { ease, seg, springTo, lerp, rgba, roundRect, clamp } from '../engine.js';
import { chip, flowLayout, stepCaption, rise } from './_ui.js';

export default function probBars(f, p) {
  const { ctx, u, pal, W, H, lt, dur, safe } = f;
  f.camera({ push: 0.03 });
  const out = f.exit; // composition owns transitions; 1 unless the cut is hard
  stepCaption(f, p.caption, rise(f, 0, 20).a * out);

  // Context row with a "?" slot at the end.
  const labels = [...(p.context || []), '？'];
  const lay = flowLayout(f, labels, { cx: W / 2, top: safe.y + 150 * u, maxW: safe.w, gap: 20, role: 'headline' });
  const pickAt = p.pickAt ?? 2.6;
  const picked = seg(lt, pickAt, pickAt + 0.35);
  lay.items.forEach((it, i) => {
    const isSlot = i === labels.length - 1;
    const r = rise(f, 0.1 + i * 0.05, 24);
    const label = isSlot && picked > 0.5 ? p.options[p.pick].label : it.label;
    const pul = isSlot ? 1 + 0.05 * Math.sin(lt * 7) * (1 - picked) : 1;
    chip(f, label, it.x, it.y + r.dy, {
      role: 'headline', alpha: r.a * out, scale: pul, id: `pb:ctx${i}`,
      stroke: isSlot ? pal.accent : pal.line, fill: isSlot ? rgba(pal.accent, 0.12 + 0.2 * picked) : pal.bg_raised,
      color: isSlot && picked <= 0.5 ? pal.accent : pal.text, minW: isSlot ? 110 : 0,
    });
  });

  const qy = lay.items[0].y + lay.height + 100 * u;
  const q = rise(f, 0.45, 24);
  f.text(p.question, W / 2, qy + q.dy, { role: 'headline', align: 'center', alpha: q.a * out, id: 'pb:q', maxWidth: safe.w });

  // Bars
  const opts = p.options || [];
  const top = qy + 130 * u, rowH = 160 * u, labelW = 150 * u;
  const barX = safe.x + labelW, barMaxW = safe.w - labelW - 190 * u;
  opts.forEach((o, i) => {
    const t0 = 0.9 + i * 0.12;
    const r = rise(f, t0, 20);
    const g = clamp(springTo(lt, [[0, 0], [t0 + 0.1, 1]], { stiffness: 120, damping: 20 }), 0, 1.04);
    const win = i === p.pick;
    const dim = win ? 1 : 1 - 0.55 * picked;
    const y = top + i * rowH + r.dy;
    const a = r.a * out * dim;
    f.text(o.label, safe.x + labelW / 2 - 10 * u, y + 80 * u, { role: 'headline', align: 'center', alpha: a, color: win ? pal.accent : pal.text, id: `pb:l${i}` });
    // track + bar
    ctx.save(); ctx.globalAlpha *= a;
    roundRect(ctx, barX, y + 4 * u, barMaxW, 80 * u, 40 * u); ctx.fillStyle = rgba(pal.line, 0.6); ctx.fill();
    const w = Math.max(80 * u, barMaxW * o.p * g);
    roundRect(ctx, barX, y + 4 * u, w, 80 * u, 40 * u);
    ctx.fillStyle = win ? pal.accent : pal.support; ctx.globalAlpha *= win ? 1 : 0.75; ctx.fill();
    ctx.restore();
    const pct = Math.round(o.p * 100 * clamp(g));
    f.text(`${pct}%`, barX + barMaxW + 24 * u, y + 68 * u, { role: 'body', alpha: a, color: win ? pal.accent : pal.text_muted, mono: true, id: `pb:p${i}` });
    if (win && picked > 0) {
      ctx.save(); ctx.globalAlpha *= out * picked;
      roundRect(ctx, safe.x - 18 * u, y - 22 * u, safe.w + 36 * u, rowH - 22 * u, 34 * u);
      ctx.strokeStyle = pal.accent; ctx.lineWidth = 4 * u; ctx.stroke();
      ctx.restore();
    }
  });
  if (p.note) {
    const r = rise(f, pickAt + 0.3, 16);
    f.text(p.note, W / 2, top + opts.length * rowH + 30 * u + r.dy, { role: 'caption', align: 'center', color: pal.text_muted, alpha: r.a * out, id: 'pb:note', maxWidth: safe.w });
  }
}

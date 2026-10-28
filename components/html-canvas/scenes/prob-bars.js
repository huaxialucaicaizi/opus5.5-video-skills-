// prob-bars: context chips + a question, then horizontal probability bars grow; the winner is picked.
// params: { caption, context: [string], question, options: [{label, p}], pick: index, pickAt?: 2.6, note? }
// Layout adapts to the frame: portrait stacks context / question / bars; landscape puts context + question
// on the left and gives the bars the full height on the right.
import { seg, springTo, rgba, roundRect, clamp } from '../engine.js';
import { chip, flowLayout, stepCaption, rise } from './_ui.js';

export default function probBars(f, p) {
  const { ctx, u, pal, W, H, lt, safe } = f;
  f.camera({ push: 0.03 });
  const out = f.exit; // composition owns transitions; 1 unless the cut is hard
  stepCaption(f, p.caption, rise(f, 0, 20).a * out);
  const landscape = W > H;
  const ty = f.style.typography;
  const opts = p.options || [];
  const pickAt = p.pickAt ?? 2.6;
  const picked = seg(lt, pickAt, pickAt + 0.35);

  // ---- regions
  // 3 % inset: the camera push magnifies distance from centre, so edge-flush content would leave the safe area.
  const left = landscape ? { x: safe.x + safe.w * 0.03, w: safe.w * 0.40 } : { x: safe.x, w: safe.w };
  const right = landscape ? { x: safe.x + safe.w * 0.47, w: safe.w * 0.50 } : left;
  const leftCx = left.x + left.w / 2;

  // ---- context row with a "?" slot at the end
  const labels = [...(p.context || []), '？'];
  const ctxTop = landscape ? safe.y + safe.h * 0.28 : safe.y + 150 * u;
  const lay = flowLayout(f, labels, { cx: leftCx, top: ctxTop, maxW: left.w, gap: 20, role: 'headline' });
  lay.items.forEach((it, i) => {
    const isSlot = i === labels.length - 1;
    const r = rise(f, 0.1 + i * 0.05, 24);
    const label = isSlot && picked > 0.5 ? opts[p.pick].label : it.label;
    const pul = isSlot ? 1 + 0.05 * Math.sin(lt * 7) * (1 - picked) : 1;
    chip(f, label, it.x, it.y + r.dy, {
      role: 'headline', alpha: r.a * out, scale: pul, id: `pb:ctx${i}`,
      stroke: isSlot ? pal.accent : pal.line, fill: isSlot ? rgba(pal.accent, 0.12 + 0.2 * picked) : pal.bg_raised,
      color: isSlot && picked <= 0.5 ? pal.accent : pal.text, minW: isSlot ? 110 : 0,
    });
  });
  const qy = lay.items[0].y + lay.height + 100 * u;
  const q = rise(f, 0.45, 24);
  f.text(p.question, leftCx, qy + q.dy, { role: 'headline', align: 'center', alpha: q.a * out, id: 'pb:q', maxWidth: left.w * 0.94, fit: landscape }); // margin absorbs camera push

  // ---- bars
  const noteH = p.note ? 80 * u : 0;
  const top = landscape ? safe.y + 110 * u : qy + 130 * u;
  const room = safe.y + safe.h - top - noteH;
  const rowH = Math.min(160 * u, room / Math.max(1, opts.length));
  const k = rowH / (160 * u);                                      // everything in a row scales together
  const lblSize = Math.max(ty.min_px, ty.scale_px.headline * k), pctSize = Math.max(ty.min_px, ty.scale_px.body * k);
  const labelW = 150 * u, pctW = 190 * u;
  const barX = right.x + labelW, barMaxW = right.w - labelW - pctW;
  opts.forEach((o, i) => {
    const t0 = 0.9 + i * 0.12;
    const r = rise(f, t0, 20);
    const g = clamp(springTo(lt, [[0, 0], [t0 + 0.1, 1]], { stiffness: 120, damping: 20 }), 0, 1.04);
    const win = i === p.pick;
    const dim = win ? 1 : 1 - 0.55 * picked;
    const y = top + i * rowH + r.dy;
    const a = r.a * out * dim;
    f.text(o.label, right.x + labelW / 2 - 10 * u, y + 80 * u * k, { role: 'headline', size: lblSize, align: 'center', alpha: a, color: win ? pal.accent : pal.text, id: `pb:l${i}` });
    ctx.save(); ctx.globalAlpha *= a;
    roundRect(ctx, barX, y + 4 * u * k, barMaxW, 80 * u * k, 40 * u * k); ctx.fillStyle = rgba(pal.line, 0.6); ctx.fill();
    const w = Math.max(80 * u * k, barMaxW * o.p * g);
    roundRect(ctx, barX, y + 4 * u * k, w, 80 * u * k, 40 * u * k);
    ctx.fillStyle = win ? pal.accent : pal.support; ctx.globalAlpha *= win ? 1 : 0.75; ctx.fill();
    ctx.restore();
    const pct = Math.round(o.p * 100 * clamp(g));
    f.text(`${pct}%`, barX + barMaxW + 24 * u, y + 68 * u * k, { role: 'body', size: pctSize, alpha: a, color: win ? pal.accent : pal.text_muted, mono: true, id: `pb:p${i}` });
    if (win && picked > 0) {
      ctx.save(); ctx.globalAlpha *= out * picked;
      roundRect(ctx, right.x + 2 * u, y - 22 * u * k, right.w - 4 * u, rowH - 22 * u * k, 34 * u * k);
      ctx.strokeStyle = pal.accent; ctx.lineWidth = 4 * u; ctx.stroke();
      ctx.restore();
    }
  });
  if (p.note) {
    const r = rise(f, pickAt + 0.3, 16);
    const nx = landscape ? right.x + right.w / 2 : W / 2;
    f.text(p.note, nx, top + opts.length * rowH + 30 * u + r.dy, { role: 'caption', align: 'center', color: pal.text_muted, alpha: r.a * out, id: 'pb:note', maxWidth: right.w });
  }
}

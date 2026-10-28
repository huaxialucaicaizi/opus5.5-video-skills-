// append-loop: autoregressive loop. A row of chips grows; each step shows a "?" slot, a mini probability, then the chip lands.
// params: { caption, start: [string], steps: [{token, p}], stepDur?: 0.62, firstAt?: 0.5, loopLabel? }
import { ease, seg, springTo, lerp, rgba, roundRect, TAU } from '../engine.js';
import { chip, flowLayout, stepCaption, rise } from './_ui.js';

export default function appendLoop(f, p) {
  const { ctx, u, pal, W, H, lt, dur, safe } = f;
  f.camera({ push: 0.02 });
  const out = f.exit; // composition owns transitions; 1 unless the cut is hard
  stepCaption(f, p.caption, rise(f, 0, 20).a * out);

  const steps = p.steps || [], sd = p.stepDur ?? 0.62, first = p.firstAt ?? 0.5;
  // How many steps have landed at lt, and progress inside the current one.
  const raw = (lt - first) / sd;
  const n = Math.max(0, Math.min(steps.length, Math.floor(raw)));
  const k = raw < 0 ? 0 : n >= steps.length ? 1 : raw - n;

  const all = [...(p.start || []), ...steps.map(s => s.token)];
  const shown = (p.start || []).length + n;
  const showing = n < steps.length && raw >= 0;
  const labels = all.slice(0, shown).concat(showing ? ['？'] : []);
  // Layout is computed on the FINAL sentence so chips never jump to another row mid-scene.
  const full = flowLayout(f, all, { cx: W / 2, top: H * 0.36, maxW: safe.w, gap: 16, role: 'headline' });
  const lay = { height: full.height, items: labels.map((label, i) => ({ ...full.items[i], label })) };

  lay.items.forEach((it, i) => {
    const isSlot = showing && i === labels.length - 1;
    const isNew = !isSlot && i === shown - 1 && n > 0;
    const landT = first + n * sd; // time the newest chip landed
    const s = isNew ? springTo(lt, [[0, 0], [landT, 1]], { stiffness: 260, damping: 18 }) : 1;
    const base = i < (p.start || []).length;
    chip(f, it.label, it.x, it.y - (1 - s) * 40 * u, {
      role: 'headline', alpha: out * (isSlot ? 0.4 + 0.6 * Math.abs(Math.sin(lt * 6)) : 1), scale: isNew ? lerp(1.25, 1, s) : 1,
      id: `al:c${i}`, padX: 22, padY: 16,
      stroke: isSlot ? pal.accent : base ? pal.line : pal.accent,
      fill: base ? pal.bg_raised : rgba(pal.accent, isNew ? 0.28 : 0.14),
      color: isSlot ? pal.accent : pal.text,
    });
  });

  // Mini "thinking" readout under the row for the current step.
  if (showing) {
    const st = steps[n];
    const y = H * 0.36 + lay.height + 170 * u;
    const a = Math.min(seg(k, 0.05, 0.25), 1 - seg(k, 0.85, 1)) * out;
    ctx.save(); ctx.globalAlpha *= a;
    const w = 620 * u, x = W / 2 - w / 2;
    roundRect(ctx, x, y - 56 * u, w, 112 * u, 56 * u); ctx.fillStyle = pal.bg_raised; ctx.fill();
    ctx.strokeStyle = pal.line; ctx.lineWidth = 3 * u; ctx.stroke();
    // spinner arc
    ctx.beginPath(); ctx.arc(x + 60 * u, y, 22 * u, lt * 8, lt * 8 + TAU * 0.7);
    ctx.strokeStyle = pal.accent; ctx.lineWidth = 6 * u; ctx.lineCap = 'round'; ctx.stroke();
    ctx.restore();
    f.text(`最可能：「${st.token}」 ${Math.round(st.p * 100)}%`, x + 110 * u, y, { role: 'caption', baseline: 'middle', alpha: a, mono: false, id: 'al:readout' });
  }
  // Loop arrow + label once a couple of steps have gone by.
  if (p.loopLabel) {
    const r = rise(f, first + sd * 1.5, 20);
    const y = safe.y + safe.h - 120 * u;
    f.text(p.loopLabel, W / 2, y + r.dy, { role: 'body', align: 'center', color: pal.support, alpha: r.a * out, id: 'al:loop', maxWidth: safe.w });
  }
}

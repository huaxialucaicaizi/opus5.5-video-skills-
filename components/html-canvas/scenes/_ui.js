// Shared UI primitives for scene components. All pure functions of the frame API.
import { roundRect, rgba, clamp, ease, seg } from '../engine.js';

// A rounded "token chip". Returns its geometry. (x, y) is the chip centre.
export function chip(f, label, x, y, o = {}) {
  const { ctx, u, pal, style } = f;
  const role = o.role || 'body';
  const m = f.measure(label, { role, size: o.size, weight: o.weight });
  const padX = (o.padX ?? 30) * u, padY = (o.padY ?? 20) * u;
  const w = Math.max(m.w + padX * 2, (o.minW ?? 0) * u), h = m.px + padY * 2;
  const alpha = clamp(o.alpha ?? 1), s = o.scale ?? 1;
  if (alpha <= 0.001) return { x: x - w / 2, y: y - h / 2, w, h };
  ctx.save();
  ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-x, -y);
  ctx.globalAlpha *= alpha;
  roundRect(ctx, x - w / 2, y - h / 2, w, h, (o.radius ?? style.layout.corner_radius) * u);
  ctx.fillStyle = o.fill || pal.bg_raised; ctx.fill();
  ctx.lineWidth = (o.strokeW ?? 3) * u; ctx.strokeStyle = o.stroke || pal.line; ctx.stroke();
  ctx.restore();
  // Text is drawn outside the alpha save so its recorded alpha is the real one.
  ctx.save();
  ctx.translate(x, y); ctx.scale(s, s); ctx.translate(-x, -y);
  f.text(label, x, y, { role, size: o.size, weight: o.weight, align: 'center', baseline: 'middle', color: o.color || pal.text, alpha, id: o.id, mono: o.mono });
  ctx.restore();
  return { x: x - w / 2, y: y - h / 2, w, h };
}

// Lay out chips in rows (centred), returning centre positions. Measures only; does not draw.
export function flowLayout(f, labels, { cx, top, maxW, gap = 22, rowGap = 26, role = 'body', size, padX = 30, padY = 20, minW = 0 }) {
  const { u } = f;
  const items = labels.map(l => {
    const m = f.measure(l, { role, size });
    return { label: l, w: Math.max(m.w + padX * 2 * u, minW * u), h: m.px + padY * 2 * u };
  });
  const rows = []; let row = [], rw = 0;
  const isPunct = s => /^[，。、！？；：,.!?;:）》」』]$/.test(s);
  for (const it of items) {
    const add = (row.length ? gap * u : 0) + it.w;
    if (row.length && rw + add > maxW) {
      // Never start a row with closing punctuation: carry the previous chip down with it.
      if (isPunct(it.label) && row.length > 1) {
        const carried = row.pop(); rw -= carried.w + gap * u;
        rows.push({ row, rw }); row = [carried]; rw = carried.w;
        row.push(it); rw += gap * u + it.w; continue;
      }
      rows.push({ row, rw }); row = []; rw = 0;
    }
    row.push(it); rw += (row.length > 1 ? gap * u : 0) + it.w;
  }
  if (row.length) rows.push({ row, rw });
  const out = []; let y = top;
  for (const { row: r, rw: w } of rows) {
    let x = cx - w / 2; const h = Math.max(...r.map(i => i.h));
    for (const it of r) { out.push({ label: it.label, x: x + it.w / 2, y: y + h / 2, w: it.w, h }); x += it.w + gap * u; }
    y += h + rowGap * u;
  }
  return { items: out, height: y - top - rowGap * u };
}

// Step caption at the top of the safe area: small accent dot + muted label.
export function stepCaption(f, label, alpha) {
  const { ctx, u, pal, safe } = f;
  if (!label || alpha <= 0) return;
  const y = safe.y + 64 * u; // margin absorbs the camera push
  ctx.save(); ctx.globalAlpha *= alpha;
  ctx.fillStyle = pal.accent; ctx.beginPath(); ctx.arc(safe.x + 14 * u, y, 10 * u, 0, Math.PI * 2); ctx.fill();
  ctx.restore();
  f.text(label, safe.x + 40 * u, y, { role: 'caption', color: pal.text_muted, baseline: 'middle', alpha, id: `${f.scene.id}:caption`, maxWidth: f.safe.w - 40 * u });
}

// Rise-in envelope helper: returns {a, dy} for an element entering at time t0.
export function rise(f, t0, dist = 40, dur) {
  const k = ease.easeOutCubic(seg(f.lt, t0, t0 + (dur ?? f.style.motion.enter_s)));
  return { a: k, dy: (1 - k) * dist * f.u };
}

// kinetic-title: kicker + 1–3 title lines that rise in with a mask, one highlighted span, optional blinking cursor.
// params: { kicker?, lines: [string], highlight?: { line, text }, cursor?: bool, sub? }
import { ease, seg, roundRect, rgba } from '../engine.js';
import { rise } from './_ui.js';

export default function kineticTitle(f, p) {
  const { ctx, u, pal, W, H, lt, dur, safe } = f;
  f.camera({ push: 0.035 });
  const lines = p.lines || [];
  const px = f.style.typography.scale_px.title;
  const lh = px * 1.22 * u;
  const blockH = lines.length * lh;
  const top = H * 0.46 - blockH / 2;
  const out = f.exit; // composition owns transitions; 1 unless the cut is hard

  if (p.kicker) {
    const r = rise(f, 0.05, 30);
    const k = f.measure(p.kicker, { role: 'label' });
    const kx = W / 2, ky = top - 90 * u + r.dy;
    ctx.save(); ctx.globalAlpha *= r.a * out;
    roundRect(ctx, kx - k.w / 2 - 26 * u, ky - k.h / 2 - 12 * u, k.w + 52 * u, k.h + 24 * u, 40 * u);
    ctx.strokeStyle = rgba(pal.accent, 0.8); ctx.lineWidth = 3 * u; ctx.stroke();
    ctx.restore();
    f.text(p.kicker, kx, ky, { role: 'label', align: 'center', baseline: 'middle', color: pal.accent, alpha: r.a * out, id: 'title:kicker' });
  }

  let cursorX = W / 2, cursorY = top;
  lines.forEach((line, i) => {
    const t0 = 0.25 + i * 0.32;
    const k = ease.easeOutQuart(seg(lt, t0, t0 + 0.55));
    const y = top + i * lh + lh * 0.8;
    // Mask: the line slides up from below its own baseline band.
    ctx.save();
    ctx.beginPath(); ctx.rect(0, y - lh * 0.95, W, lh * 1.15); ctx.clip();
    const dy = (1 - k) * lh * 1.1;
    const hl = p.highlight && p.highlight.line === i ? p.highlight.text : null;
    if (hl && line.includes(hl)) {
      // draw in three runs so the highlighted span gets the accent colour
      const [a, b] = [line.slice(0, line.indexOf(hl)), line.slice(line.indexOf(hl) + hl.length)];
      const wa = f.measure(a, { role: 'title' }).w, wh = f.measure(hl, { role: 'title' }).w, wb = f.measure(b, { role: 'title' }).w;
      let x = W / 2 - (wa + wh + wb) / 2;
      const opts = { role: 'title', alpha: out * Math.min(1, k * 4), recordAlpha: k };
      if (a) f.text(a, x, y + dy, { ...opts, id: `title:l${i}a` }); x += wa;
      // underline sweeps after the line lands
      const s = ease.easeOutCubic(seg(lt, t0 + 0.5, t0 + 0.9));
      ctx.fillStyle = rgba(pal.accent, 0.28 * out);
      ctx.fillRect(x - 6 * u, y + dy + 14 * u, (wh + 12 * u) * s, 22 * u);
      f.text(hl, x, y + dy, { ...opts, color: pal.accent, id: `title:l${i}h` }); x += wh;
      if (b) f.text(b, x, y + dy, { ...opts, id: `title:l${i}b` }); x += wb;
      cursorX = x; cursorY = y;
    } else {
      const r = f.text(line, W / 2, y + dy, { role: 'title', align: 'center', alpha: out * Math.min(1, k * 4), recordAlpha: k, id: `title:l${i}` });
      cursorX = r.x + r.w; cursorY = y;
    }
    ctx.restore();
  });

  if (p.cursor) {
    const on = Math.floor(lt * 2.5) % 2 === 0 || lt < 1.2;
    const a = seg(lt, 1.0, 1.15) * out * (on ? 1 : 0);
    ctx.fillStyle = rgba(pal.accent, a);
    ctx.fillRect(cursorX + 14 * u, cursorY - px * 0.82 * u, 10 * u, px * 0.95 * u);
  }
  if (p.sub) {
    const r = rise(f, 1.1, 24);
    f.text(p.sub, W / 2, top + blockH + 90 * u + r.dy, { role: 'caption', align: 'center', color: pal.text_muted, alpha: r.a * out, id: 'title:sub', maxWidth: safe.w });
  }
}

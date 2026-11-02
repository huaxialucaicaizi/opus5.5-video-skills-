// prompt-compare: a chat exchange. The user's prompt bubble rises in on the right, the AI's answer appears
// line by line on the left, then a verdict badge lands. Use two in a row for a bad/good comparison.
// params: { caption?, askLabel?='你问', prompt, answerLabel?='AI 回答', answer: [string] (one entry per line),
//           verdict?, tone?: 'bad'|'good', answerAt?=0.9, lineGap?=0.32, verdictAt? }
import { wrapText, roundRect, rgba } from '../engine.js';
import { stepCaption, rise } from './_ui.js';

function measureLines(f, text, role, maxW) {
  const { ctx, u, style } = f;
  const px = style.typography.scale_px[role] * u;
  ctx.save(); ctx.font = f.font(px, style.typography.weight[role]);
  const lines = wrapText(ctx, text, maxW);
  const w = Math.max(...lines.map(l => ctx.measureText(l).width));
  ctx.restore();
  return { lines, w, px, lh: px * style.typography.line_height };
}

export default function promptCompare(f, p) {
  const { ctx, u, pal, W, lt, safe } = f;
  f.camera({ push: 0.025 });
  const out = f.exit;
  const good = p.tone === 'good';
  const tone = good ? pal.success : pal.accent;
  stepCaption(f, p.caption, rise(f, 0, 20).a * out);

  const pad = 34 * u, bubbleMax = safe.w * 0.86;
  const inset = safe.w * 0.03;                       // camera-push margin
  let y = safe.y + 140 * u;
  const ansSize = p.answerSize;            // optional smaller type for long answers

  // ---- user prompt (right)
  const q = measureLines(f, p.prompt, 'body', bubbleMax - pad * 2);
  const qw = q.w + pad * 2, qh = (q.lines.length - 1) * q.lh + q.px * 1.12 + pad * 1.6;
  const qx = safe.x + safe.w - inset - qw;
  const r1 = rise(f, 0.15, 40);
  f.text(p.askLabel ?? '你问', safe.x + safe.w - inset, y + r1.dy, { role: 'caption', align: 'right', color: pal.text_muted, alpha: r1.a * out, id: `${f.scene.id}:asklbl` });
  y += 46 * u;
  ctx.save(); ctx.globalAlpha *= r1.a * out;
  roundRect(ctx, qx, y + r1.dy, qw, qh, 34 * u); ctx.fillStyle = rgba(pal.support, 0.16); ctx.fill();
  ctx.strokeStyle = rgba(pal.support, 0.7); ctx.lineWidth = 3 * u; ctx.stroke();
  ctx.restore();
  const qid = f.box(`${f.scene.id}:qbox`, qx, y + r1.dy, qw, qh, r1.a * out);
  q.lines.forEach((l, i) => f.text(l, qx + pad, y + r1.dy + pad * 0.8 + q.px * 0.88 + i * q.lh,
    { role: 'body', alpha: r1.a * out, id: `${f.scene.id}:q${i}`, parent: qid }));
  y += qh + 64 * u;

  // ---- AI answer (left), line by line
  const answerAt = p.answerAt ?? 0.9, gap = p.lineGap ?? 0.32;
  const ml = t => { const m = measureLines(f, t, 'body', bubbleMax - pad * 2); if (!ansSize) return m;
    const k = ansSize / f.style.typography.scale_px.body; const { ctx } = f; ctx.save(); ctx.font = f.font(m.px * k, f.style.typography.weight.body);
    const ls = wrapText(ctx, t, bubbleMax - pad * 2); ctx.restore(); return { lines: ls, px: m.px * k, lh: m.lh * k }; };
  const lines = (p.answer || []).flatMap(a => ml(a).lines);
  const A = ml((p.answer || [])[0] || '');
  const aw = Math.min(bubbleMax, Math.max(...lines.map(l => f.measure(l, { role: 'body', size: ansSize }).w)) + pad * 2);
  const ah = (lines.length - 1) * A.lh + A.px * 1.12 + pad * 1.6;
  const ax = safe.x + inset;
  const r2 = rise(f, answerAt, 40);
  f.text(p.answerLabel ?? 'AI 回答', ax, y + r2.dy, { role: 'caption', color: pal.text_muted, alpha: r2.a * out, id: `${f.scene.id}:anslbl` });
  y += 46 * u;
  ctx.save(); ctx.globalAlpha *= r2.a * out;
  roundRect(ctx, ax, y + r2.dy, aw, ah, 34 * u); ctx.fillStyle = pal.bg_raised; ctx.fill();
  ctx.strokeStyle = pal.line; ctx.lineWidth = 3 * u; ctx.stroke();
  ctx.restore();
  const aid = f.box(`${f.scene.id}:abox`, ax, y + r2.dy, aw, ah, r2.a * out);
  lines.forEach((l, i) => {
    const ri = rise(f, answerAt + 0.2 + i * gap, 12, 0.3);
    f.text(l, ax + pad, y + r2.dy + pad * 0.8 + A.px * 0.88 + i * A.lh + ri.dy,
      { role: 'body', size: ansSize, alpha: ri.a * out, color: good ? pal.text : pal.text_muted, id: `${f.scene.id}:a${i}`, parent: aid });
  });
  y += ah + 70 * u;

  // ---- verdict
  if (p.verdict) {
    const vAt = p.verdictAt ?? answerAt + 0.4 + lines.length * gap;
    const rv = rise(f, vAt, 24);
    const m = f.measure(p.verdict, { role: 'headline' });
    const vw = m.w + 70 * u, vh = m.px + 44 * u, vx = W / 2 - vw / 2;
    y = Math.min(y, safe.y + safe.h - vh - safe.h * 0.04);   // never below the safe area (camera-push margin)
    ctx.save(); ctx.globalAlpha *= rv.a * out;
    roundRect(ctx, vx, y + rv.dy, vw, vh, vh / 2); ctx.fillStyle = rgba(tone, 0.18); ctx.fill();
    ctx.strokeStyle = tone; ctx.lineWidth = 5 * u; ctx.stroke();
    ctx.restore();
    const vid = f.box(`${f.scene.id}:vbox`, vx, y + rv.dy, vw, vh, rv.a * out);
    f.text(p.verdict, W / 2, y + rv.dy + vh / 2, { role: 'headline', align: 'center', baseline: 'middle', color: tone, alpha: rv.a * out, id: `${f.scene.id}:verdict`, parent: vid });
  }
}

// engine.js — framework-agnostic, deterministic 2D video engine.
//
// Contract (shared by the HTML player and the Remotion wrapper):
//   const comp = createComposition({ storyboard, style, scenes, makeCanvas });
//   comp.draw(ctx, t)   -> paints the full frame for time t (seconds). Pure function of t.
//   comp.layout(t)      -> [{id, text, role, x, y, w, h, px, alpha, scene}] text boxes drawn at t.
//   comp.meta           -> { width, height, fps, duration, frames }
//
// Rules for scene authors (enforced by review + check_determinism):
//   - No Math.random(), Date.now(), performance.now(), timers, CSS animations, or state between frames.
//   - Use hash(i) for stable randomness. Compute everything from t in closed form.
//   - A scene paints only its own content; the composition paints the background and transitions.

// ---------------------------------------------------------------- math
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, k) => a + (b - a) * k;
export const seg = (t, a, b) => (b <= a ? (t >= b ? 1 : 0) : clamp((t - a) / (b - a)));
export const TAU = Math.PI * 2;

export const ease = {
  linear: k => k,
  easeInCubic: k => k * k * k,
  easeOutCubic: k => 1 - Math.pow(1 - k, 3),
  easeInOutCubic: k => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2),
  easeOutQuart: k => 1 - Math.pow(1 - k, 4),
  easeInOutSine: k => -(Math.cos(Math.PI * k) - 1) / 2,
  easeOutExpo: k => (k >= 1 ? 1 : 1 - Math.pow(2, -10 * k)),
};

// Closed-form damped spring step response (0 -> 1), so it is a pure function of time.
// Values that change target several times: sum one spring per change (see springTo).
export function spring(dt, { stiffness = 170, damping = 22, mass = 1 } = {}) {
  if (dt <= 0) return 0;
  const w0 = Math.sqrt(stiffness / mass);
  const zeta = damping / (2 * Math.sqrt(stiffness * mass));
  if (zeta < 1) {
    const wd = w0 * Math.sqrt(1 - zeta * zeta);
    return 1 - Math.exp(-zeta * w0 * dt) * (Math.cos(wd * dt) + (zeta * w0 / wd) * Math.sin(wd * dt));
  }
  return 1 - Math.exp(-w0 * dt) * (1 + w0 * dt); // critically damped (and over-damped approx)
}
// springTo(t, [[t0, v0], [t1, v1], ...]) -> value that springs to each new target at its time.
export function springTo(t, keys, cfg) {
  let v = keys[0][1];
  for (let i = 1; i < keys.length; i++) v += (keys[i][1] - keys[i - 1][1]) * spring(t - keys[i][0], cfg);
  return v;
}
// Keyframes with easing: kf(t, [[t0,v0],[t1,v1],...], ease.easeInOutCubic)
export function kf(t, keys, fn = ease.easeInOutCubic) {
  if (t <= keys[0][0]) return keys[0][1];
  for (let i = 1; i < keys.length; i++) {
    const [t1, v1] = keys[i], [t0, v0] = keys[i - 1];
    if (t <= t1) return lerp(v0, v1, fn(seg(t, t0, t1)));
  }
  return keys[keys.length - 1][1];
}
// Enter/exit envelope: 0 -> 1 over [a, a+inS], 1 -> 0 over [b-outS, b].
export function envelope(t, a, b, inS = 0.4, outS = 0.3, fnIn = ease.easeOutCubic, fnOut = ease.easeInCubic) {
  if (t < a || t > b) return 0;
  const i = fnIn(seg(t, a, a + inS));
  const o = 1 - fnOut(seg(t, b - outS, b));
  return Math.min(i, o);
}
// Stable pseudo-random in [0,1) from an integer/string key.
export function hash(k) {
  let h = 2166136261 >>> 0;
  const s = String(k);
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  h ^= h >>> 13; h = Math.imul(h, 0x5bd1e995); h ^= h >>> 15;
  return (h >>> 0) / 4294967296;
}
export const beatPhase = (t, bpm, offset = 0) => ((t - offset) * bpm) / 60;
export const pulse = (t, bpm, offset = 0, decay = 6) => {
  const p = beatPhase(t, bpm, offset);
  return p < 0 ? 0 : Math.exp(-decay * (p - Math.floor(p)) * (60 / bpm));
};

// ---------------------------------------------------------------- colour
export function hexToRgb(hex) {
  const h = hex.replace('#', '');
  const n = parseInt(h.length === 3 ? h.split('').map(c => c + c).join('') : h, 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
export function mix(a, b, k) {
  const A = hexToRgb(a), B = hexToRgb(b);
  return `rgb(${A.map((v, i) => Math.round(lerp(v, B[i], clamp(k)))).join(',')})`;
}
export function rgba(hex, a) { const [r, g, b] = hexToRgb(hex); return `rgba(${r},${g},${b},${clamp(a)})`; }
function relLum(hex) {
  return hexToRgb(hex).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); })
    .reduce((s, v, i) => s + v * [0.2126, 0.7152, 0.0722][i], 0);
}
export function contrastRatio(a, b) {
  const [l1, l2] = [relLum(a), relLum(b)].sort((x, y) => y - x);
  return (l1 + 0.05) / (l2 + 0.05);
}

// ---------------------------------------------------------------- drawing helpers
export function roundRect(ctx, x, y, w, h, r) {
  r = Math.max(0, Math.min(r, w / 2, h / 2));
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

const CJK = /[　-〿㐀-鿿豈-﫿＀-￯]/;
// Break text into lines that fit maxWidth. CJK breaks per character, latin per word.
export function wrapText(ctx, text, maxWidth) {
  const out = [];
  for (const para of String(text).split('\n')) {
    const tokens = [];
    let buf = '';
    for (const ch of para) {
      if (CJK.test(ch)) { if (buf) tokens.push(buf); buf = ''; tokens.push(ch); }
      else if (ch === ' ') { buf += ch; tokens.push(buf); buf = ''; }
      else buf += ch;
    }
    if (buf) tokens.push(buf);
    let line = '';
    for (const tok of tokens) {
      const trial = line + tok;
      if (line && ctx.measureText(trial.trimEnd()).width > maxWidth) {
        // keep closing punctuation with the previous line (simple kinsoku)
        if (/^[，。、！？；：”’）》」』,.!?;:)]/.test(tok)) { out.push(trial.trimEnd()); line = ''; continue; }
        out.push(line.trimEnd()); line = tok.trimStart();
      } else line = trial;
    }
    out.push(line.trimEnd());
  }
  return out;
}

// ---------------------------------------------------------------- frame API
function makeFrameApi(ctx, comp, t, scene, lt, dur, layoutSink) {
  const { style, W, H, u } = comp;
  const ty = style.typography;
  const font = (px, weight = 600, mono = false) =>
    `${weight} ${px}px ${(mono ? ty.mono_stack : ty.font_stack).map(f => (f.includes(' ') ? `"${f}"` : f)).join(', ')}`;
  const safe = {
    x: style.layout.safe_area.left * u,
    y: style.layout.safe_area.top * u,
    w: W - (style.layout.safe_area.left + style.layout.safe_area.right) * u,
    h: H - (style.layout.safe_area.top + style.layout.safe_area.bottom) * u,
  };

  function record(id, str, role, px, x, y, w, h, alpha, extra) {
    if (!layoutSink || alpha < 0.05) return;
    const m = ctx.getTransform();
    const pts = [[x, y], [x + w, y], [x, y + h], [x + w, y + h]].map(([px_, py]) => [m.a * px_ + m.c * py + m.e, m.b * px_ + m.d * py + m.f]);
    const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
    const sx = Math.hypot(m.a, m.b);
    layoutSink.push({
      id, text: str, role, scene: scene.id, alpha: +alpha.toFixed(3),
      px: +(px * sx).toFixed(1),
      x: +Math.min(...xs).toFixed(1), y: +Math.min(...ys).toFixed(1),
      w: +(Math.max(...xs) - Math.min(...xs)).toFixed(1), h: +(Math.max(...ys) - Math.min(...ys)).toFixed(1),
      ...(extra || {}),
    });
  }

  // text(str, x, y, opts) -> {w, h, lines}. Records the box for layout QA.
  function text(str, x, y, o = {}) {
    const role = o.role || 'body';
    let px = (o.size ?? ty.scale_px[role] ?? ty.scale_px.body) * u;
    const weight = o.weight ?? ty.weight[role] ?? 600;
    const alpha = o.alpha ?? 1;
    ctx.save();
    ctx.font = font(px, weight, o.mono);
    // fit: shrink a single line to maxWidth instead of wrapping (never below style min_px).
    if (o.fit && o.maxWidth) {
      const w0 = ctx.measureText(str).width, minPx = ty.min_px * u;
      if (w0 > o.maxWidth) { px = Math.max(minPx, px * o.maxWidth / w0); ctx.font = font(px, weight, o.mono); }
    }
    const lh = (o.lineHeight ?? ty.line_height) * px;
    ctx.textBaseline = 'alphabetic';
    const lines = o.maxWidth ? wrapText(ctx, str, o.maxWidth) : String(str).split('\n');
    const widths = lines.map(l => ctx.measureText(l).width);
    const w = Math.max(0, ...widths);
    const ascent = px * 0.88, descent = px * 0.24;
    const h = ascent + descent + (lines.length - 1) * lh;
    const align = o.align || 'left';
    const bx = align === 'center' ? x - w / 2 : align === 'right' ? x - w : x;
    const by = o.baseline === 'middle' ? y - h / 2 : o.baseline === 'top' ? y : y - ascent; // top of box
    ctx.globalAlpha *= alpha;
    ctx.fillStyle = o.color || style.palette.text;
    if (o.letterSpacing != null && 'letterSpacing' in ctx) ctx.letterSpacing = `${o.letterSpacing * px}px`;
    lines.forEach((l, i) => {
      const lx = align === 'center' ? x - widths[i] / 2 : align === 'right' ? x - widths[i] : x;
      ctx.fillText(l, lx, by + ascent + i * lh);
    });
    ctx.restore();
    record(o.id || `${scene.id}:${str.slice(0, 12)}`, str, role, px, bx, by, w, h, alpha * (o.recordAlpha ?? 1), o.parent ? { parent: o.parent } : null);
    return { x: bx, y: by, w, h, lines };
  }
  // box(id, x, y, w, h, alpha): declare a visual container for layout QA. Returns id for text({parent}).
  function box(id, x, y, w, h, alpha = 1) {
    record(id, '', 'container', 0, x, y, w, h, alpha, { kind: 'container' });
    return id;
  }
  function measure(str, o = {}) {
    const role = o.role || 'body';
    const px = (o.size ?? ty.scale_px[role]) * u;
    ctx.save(); ctx.font = font(px, o.weight ?? ty.weight[role] ?? 600, o.mono);
    const w = ctx.measureText(str).width; ctx.restore();
    return { w, h: px * 1.12, px };
  }
  // Slow camera push around a point: call at the start of a scene's draw.
  function camera({ push = 0.03, cx = W / 2, cy = H / 2, drift = 0 } = {}) {
    const k = ease.easeInOutSine(seg(lt, 0, dur));
    const s = 1 + push * k;
    ctx.translate(cx + drift * u * Math.sin(lt * 0.7), cy);
    ctx.scale(s, s);
    ctx.translate(-cx, -cy);
  }
  // exit: scenes fade themselves only when the next seam is a hard cut (otherwise the composition's
  // transition removes them, and a self-fade would leave a dead gap). Last scene: handled by transition_out.
  const next = comp.next(scene), hard = next && ['none', 'smash-cut', 'cut-on-action'].includes((next.transition_in || {}).type || 'none');
  const exit = hard && (next.transition_in || {}).type === 'none' ? 1 - ease.easeInCubic(seg(lt, dur - 0.25, dur)) : 1;
  return {
    ctx, t, lt, dur, W, H, u, style, pal: style.palette, safe, scene, exit,
    bpm: comp.storyboard.bpm, beatOffset: comp.storyboard.beat_offset_s || 0,
    text, box, measure, font, camera,
    env: (a, b, i, o) => envelope(lt, a, b, i ?? style.motion.enter_s, o ?? style.motion.exit_s),
  };
}

// ---------------------------------------------------------------- composition
export function createComposition({ storyboard, style, scenes, makeCanvas }) {
  const W = storyboard.width, H = storyboard.height, fps = storyboard.fps, duration = storyboard.duration_s;
  const u = W / (style.reference_width || 1080);
  const list = [...storyboard.scenes].sort((a, b) => a.start - b.start);
  for (const s of list) if (!scenes[s.component]) throw new Error(`Unknown scene component "${s.component}" in scene "${s.id}"`);
  const comp = { storyboard, style, W, H, u, meta: { width: W, height: H, fps, duration, frames: Math.round(duration * fps) } };
  const off = [makeCanvas(W, H), makeCanvas(W, H)];
  comp.next = s => list[list.indexOf(s) + 1];

  function background(ctx, t) {
    const p = style.palette;
    ctx.fillStyle = p.bg; ctx.fillRect(0, 0, W, H);
    // Quiet, always-moving dot field: keeps every frame alive without competing for attention.
    const gap = 54 * u, drift = (t * 9 * u) % gap;
    ctx.fillStyle = rgba(p.line, 0.55);
    for (let y = -gap; y < H + gap; y += gap)
      for (let x = -gap; x < W + gap; x += gap) {
        const k = hash(`${Math.round(x / gap)},${Math.round(y / gap)}`);
        const r = (1.6 + 1.4 * (0.5 + 0.5 * Math.sin(t * 1.3 + k * TAU))) * u;
        ctx.beginPath(); ctx.arc(x + drift * 0.5, y + drift, r, 0, TAU); ctx.fill();
      }
    const g = ctx.createRadialGradient(W / 2, H * 0.42, 0, W / 2, H * 0.42, H * 0.75);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,0.45)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }

  function paintScene(ctx, scene, t, sink) {
    const dur = scene.end - scene.start, lt = t - scene.start;
    ctx.save();
    scenes[scene.component](makeFrameApi(ctx, comp, t, scene, lt, dur, sink), scene.params || {});
    ctx.restore();
  }
  function sceneAt(t) {
    let i = list.findIndex(s => t >= s.start && t < s.end);
    if (i < 0) i = t < list[0].start ? 0 : list.length - 1;
    return i;
  }

  function render(ctx, t, sink) {
    t = clamp(t, 0, duration - 1e-6);
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    background(ctx, t);
    const i = sceneAt(t), cur = list[i], prev = list[i - 1];
    const tin = cur.transition_in || { type: 'none' };
    const d = tin.duration ?? 0.4, p = d > 0 ? seg(t, cur.start, cur.start + d) : 1;
    const inTrans = p < 1 && tin.type !== 'none' && tin.type !== 'cut-on-action' && tin.type !== 'smash-cut';

    // recAlpha: how visible this layer's text really is (for layout QA); defaults to the layer alpha.
    const layer = (canvasIdx, scene, alpha, dx = 0, dy = 0, clip = null, scale = 1, recAlpha = alpha) => {
      const oc = off[canvasIdx], octx = oc.getContext('2d');
      octx.setTransform(1, 0, 0, 1, 0, 0); octx.clearRect(0, 0, W, H);
      octx.globalAlpha = 1;
      // layout boxes need final screen coords: pre-apply the layer offset to the offscreen ctx.
      octx.translate(W / 2 + dx, H / 2 + dy); octx.scale(scale, scale); octx.translate(-W / 2, -H / 2);
      let sub = null;
      if (sink) sub = { push: b => sink.push({ ...b, alpha: +(b.alpha * recAlpha).toFixed(3), layer: canvasIdx ? 'prev' : 'cur' }) };
      paintScene(octx, scene, t, sub);
      ctx.save();
      octx.setTransform(1, 0, 0, 1, 0, 0);
      if (clip) { ctx.beginPath(); ctx.rect(...clip); ctx.clip(); }
      ctx.globalAlpha = alpha;
      ctx.drawImage(oc, 0, 0);
      ctx.restore();
    };

    if (!inTrans) {
      layer(0, cur, 1);
    } else {
      const k = ease.easeInOutCubic(p);
      switch (tin.type) {
        case 'push': {
          // Staged: outgoing leaves in the first 55%, incoming arrives in the last 55% -> no double exposure.
          const ko = ease.easeInCubic(seg(p, 0, 0.55)), ki = ease.easeOutCubic(seg(p, 0.45, 1));
          if (prev && ko < 1) layer(1, prev, 1 - ko, 0, -ko * H * 0.18, null, 1 - 0.03 * ko);
          layer(0, cur, ki, 0, (1 - ki) * H * 0.12);
          break;
        }
        case 'wipe':
          if (prev) layer(1, prev, 1);
          layer(0, cur, 1, 0, 0, [0, 0, W * k, H], 1, k);
          ctx.fillStyle = style.palette.accent; ctx.fillRect(W * k - 6 * u, 0, 12 * u, H);
          break;
        case 'iris': {
          if (prev) layer(1, prev, 1);
          const r = Math.hypot(W, H) * k;
          ctx.save(); ctx.beginPath(); ctx.arc(W / 2, H / 2, r, 0, TAU); ctx.clip();
          background(ctx, t); layer(0, cur, 1, 0, 0, null, 1, k); ctx.restore();
          break;
        }
        case 'morph': case 'match-cut': case 'whip': case 'fade': default: {
          // Dip through the background (staged), with a slight scale so it never feels static.
          const ko = ease.easeInCubic(seg(p, 0, 0.55)), ki = ease.easeOutCubic(seg(p, 0.45, 1));
          if (prev && ko < 1) layer(1, prev, 1 - ko, 0, 0, null, 1 + 0.03 * ko);
          layer(0, cur, ki, 0, 0, null, 1.03 - 0.03 * ki);
        }
      }
    }
    // Global fade out of the last scene, if requested.
    const last = list[list.length - 1], tout = last.transition_out;
    if (cur === last && tout && tout.type === 'fade') {
      const q = seg(t, last.end - (tout.duration ?? 0.5), last.end);
      if (q > 0) { ctx.fillStyle = rgba(style.palette.bg, ease.easeInCubic(q)); ctx.fillRect(0, 0, W, H); }
    }
    ctx.restore();
  }

  comp.draw = (ctx, t) => render(ctx, t, null);
  comp.layout = t => {
    const sink = [];
    const c = makeCanvas(W, H);
    render(c.getContext('2d'), t, sink);
    return sink;
  };
  comp.sceneAt = t => list[sceneAt(t)].id;
  comp.inTransition = t => {
    const cur = list[sceneAt(t)], tin = cur.transition_in || {}, d = tin.duration ?? 0.4;
    const last = list[list.length - 1], tout = last.transition_out;
    const inT = !['none', 'cut-on-action', 'smash-cut', undefined].includes(tin.type) && t < cur.start + d;
    const outT = cur === last && tout && tout.type === 'fade' && t > last.end - (tout.duration ?? 0.5);
    return !!(inT || outT);
  };
  return comp;
}

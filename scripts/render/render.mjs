#!/usr/bin/env node
// render.mjs — drive components/html-canvas/player.html in headless Chromium.
//
//   node scripts/render/render.mjs --project=examples/ai-explainer-15s --sheet            contact sheet (auto times per scene)
//   node scripts/render/render.mjs --project=... --sheet=0.5,1,2 --cols=3 --w=360           contact sheet at given times
//   node scripts/render/render.mjs --project=... --stills=1.2,6.8                           full-res PNG stills
//   node scripts/render/render.mjs --project=... --keyframes                                 full-res PNG per auto check time
//   node scripts/render/render.mjs --project=... --layout                                    text-box layout dump for QA
//   node scripts/render/render.mjs --project=... --frames [--workers=2] [--blur=3]           JPEG frames (resumable)
//   node scripts/render/render.mjs --project=... --encode [--audio=out/music.wav]            frames (+audio) -> MP4
//   node scripts/render/render.mjs --project=... --mp4 [--audio=...]                         frames + encode
// Options: --out=<dir> (default <project>/out)  --chrome=<path>  --quality=0.95  --crf=18
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, readFileSync, existsSync, statSync, renameSync, readdirSync, rmSync } from 'node:fs';
import { join, resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { openPlayer, b64, REPO } from './lib/browser.mjs';

const args = Object.fromEntries(process.argv.slice(2).map(a => { const [k, ...v] = a.replace(/^--/, '').split('='); return [k, v.length ? v.join('=') : true]; }));
if (!args.project) { console.error('usage: render.mjs --project=<dir> [--sheet|--stills=..|--keyframes|--layout|--frames|--encode|--mp4]'); process.exit(2); }
const project = args.project.replace(/\/$/, '');
const projAbs = resolve(REPO, project);
const OUT = resolve(args.out || join(projAbs, 'out'));
const sb = JSON.parse(readFileSync(join(projAbs, 'storyboard.json'), 'utf8'));
const fps = sb.fps, DUR = sb.duration_s, NFR = Math.round(DUR * fps);
mkdirSync(OUT, { recursive: true });

const run = (cmd, a) => new Promise((ok, bad) => { const p = spawn(cmd, a, { stdio: 'inherit' }); p.on('close', c => (c ? bad(new Error(`${cmd} exited ${c}`)) : ok())); });
const times = s => String(s).split(',').map(Number).filter(Number.isFinite);
const tag = t => t.toFixed(2).replace('.', '_');

// Review times: first/middle/last of every scene + explicit check_at, snapped to frame times.
function autoTimes(storyboard) {
  const f = 1 / storyboard.fps, ts = new Set();
  for (const s of storyboard.scenes) {
    const d = s.end - s.start;
    for (const t of [s.start + Math.min(0.15, d / 4), s.start + d / 2, s.end - Math.min(0.15, d / 4), ...(s.check_at || [])])
      ts.add(+(Math.round(t / f) * f).toFixed(4));
  }
  return [...ts].sort((a, b) => a - b);
}

function fingerprint() {
  const h = createHash('sha256');
  const walk = d => readdirSync(d, { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name)).forEach(e => {
    const p = join(d, e.name); if (e.isDirectory()) walk(p); else if (/\.(js|html|json)$/.test(e.name)) h.update(p).update(readFileSync(p));
  });
  walk(join(REPO, 'components/html-canvas'));
  h.update(readFileSync(join(projAbs, 'storyboard.json')));
  h.update(readFileSync(resolve(projAbs, sb.style || '../../templates/visual-style/style.default.json')));
  h.update(JSON.stringify({ q: args.quality, blur: args.blur }));
  return h.digest('hex');
}

const needBrowser =!args.encode || args.mp4;
let P;
if (needBrowser) {
  P = await openPlayer({ project, chrome: args.chrome, width: sb.width, height: sb.height, verbose: !!args.verbose });
  console.log(`player ready: ${P.meta.width}x${P.meta.height} @${P.meta.fps}fps, ${P.meta.duration}s (${P.meta.frames} frames) chrome=${P.chrome}`);
}

try {
  if (args.sheet) {
    const ts = args.sheet === true ? autoTimes(sb) : times(args.sheet);
    const cols = +(args.cols || Math.min(6, ts.length)), w = +(args.w || 240);
    const t0 = Date.now();
    const url = await P.page.evaluate(([ts, c, w]) => window.__video.sheet(ts, c, w), [ts, cols, w]);
    const f = args.outfile || join(OUT, 'contact_sheet.jpg');
    writeFileSync(f, b64(url));
    console.log(`${f}  (${ts.length} frames, ${((Date.now() - t0) / ts.length).toFixed(0)} ms/frame)`);
  }
  if (args.stills || args.keyframes) {
    const ts = args.stills ? times(args.stills) : autoTimes(sb);
    const dir = join(OUT, args.stills ? 'stills' : 'keyframes'); mkdirSync(dir, { recursive: true });
    const index = [];
    for (const t of ts) {
      const url = await P.page.evaluate(([t]) => window.__video.frame(t, 'image/png'), [t]);
      const scene = await P.page.evaluate(([t]) => window.__video.sceneAt(t), [t]);
      const f = join(dir, `t${tag(t)}.png`); writeFileSync(f, b64(url)); index.push({ t, scene, file: f });
    }
    writeFileSync(join(dir, 'index.json'), JSON.stringify(index, null, 2));
    console.log(`${ts.length} PNGs -> ${dir}`);
  }
  if (args.layout) {
    const step = +(args.step || 0.1), all = [];
    for (let t = 0; t < DUR - 1e-6; t += step) {
      const tt = +t.toFixed(3);
      const [scene, transition, boxes] = await P.page.evaluate(([t]) => [window.__video.sceneAt(t), window.__video.inTransition(t), window.__video.layout(t)], [tt]);
      all.push({ t: tt, scene, transition, boxes });
    }
    const f = join(OUT, 'layout.json'); writeFileSync(f, JSON.stringify({ width: sb.width, height: sb.height, step, samples: all }));
    console.log(`layout: ${all.length} samples -> ${f}`);
  }
  if (args.frames || args.mp4) {
    const dir = join(OUT, 'frames'); mkdirSync(dir, { recursive: true });
    // Resumable, but never stale: fingerprint everything that affects pixels; mismatch -> wipe frames.
    const fp = fingerprint();
    const fpFile = join(dir, '.fingerprint');
    if (!existsSync(fpFile) || readFileSync(fpFile, 'utf8') !== fp) {
      for (const f of readdirSync(dir)) if (/^f\d{5}\.jpg(\.tmp)?$/.test(f)) rmSync(join(dir, f));
      writeFileSync(fpFile, fp);
    }
    const q = +(args.quality || 0.95), blur = +(args.blur || 1), workers = Math.max(1, +(args.workers || 2));
    const todo = [];
    for (let i = 0; i < NFR; i++) { const f = join(dir, `f${String(i).padStart(5, '0')}.jpg`); if (!existsSync(f) || statSync(f).size < 1000) todo.push(i); }
    console.log(`${todo.length}/${NFR} frames to render, ${workers} workers, blur subframes=${blur}`);
    let next = 0, done = 0; const start = Date.now();
    await Promise.all(Array.from({ length: workers }, async (_, w) => {
      const page = w === 0 ? P.page : await P.newPage();
      while (next < todo.length) {
        const i = todo[next++], f = join(dir, `f${String(i).padStart(5, '0')}.jpg`), t = i / fps;
        const url = blur > 1
          ? await page.evaluate(([t, n, q]) => window.__video.frameBlur(t, n, 'image/jpeg', q), [t, blur, q])
          : await page.evaluate(([t, q]) => window.__video.frame(t, 'image/jpeg', q), [t, q]);
        writeFileSync(f + '.tmp', b64(url)); renameSync(f + '.tmp', f); // atomic: a killed render never leaves a half frame
        if (++done % 30 === 0 || done === todo.length) {
          const el = (Date.now() - start) / 1000;
          console.log(`  frame ${done}/${todo.length}  ${(el / done * 1000).toFixed(0)} ms/frame  eta ${((todo.length - done) * el / done).toFixed(0)} s`);
        }
      }
    }));
  }
} finally { if (P) await P.close(); }

if (args.encode || args.mp4) {
  const dir = join(OUT, 'frames'), n = readdirSync(dir).filter(f => /^f\d{5}\.jpg$/.test(f)).length;
  if (n < NFR) throw new Error(`only ${n}/${NFR} frames present in ${dir}; run --frames first`);
  const out = args.mp4file || join(OUT, `${sb.task_id}.mp4`);
  const audio = args.audio && args.audio !== true ? resolve(args.audio) : null;
  const a = ['-y', '-loglevel', 'error', ...(args.verbose ? ['-stats'] : []), '-framerate', String(fps), '-i', join(dir, 'f%05d.jpg')];
  if (audio) a.push('-i', audio);
  a.push('-map', '0:v');
  if (audio) a.push('-map', '1:a', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000');
  a.push('-c:v', 'libx264', '-preset', args.preset || 'medium', '-crf', String(args.crf || 18), '-pix_fmt', 'yuv420p',
    '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
    '-r', String(fps), '-frames:v', String(NFR), '-t', String(DUR), '-movflags', '+faststart', out);
  console.log(`encoding ${NFR} frames${audio ? ' + audio' : ''} -> ${out}`);
  await run('ffmpeg', a);
  if (args.clean) rmSync(dir, { recursive: true, force: true });
  console.log(`wrote ${out}`);
}

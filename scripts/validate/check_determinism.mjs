#!/usr/bin/env node
// check_determinism.mjs — T4: frames must be pure functions of t.
//   node scripts/validate/check_determinism.mjs --project=examples/ai-explainer-15s [--n=8] [--out=<file>]
// Renders N times in two independent pages, in forward order on page A and shuffled + repeated on page B,
// then compares SHA-256 of the PNG bytes. Any mismatch means hidden state, randomness or wall-clock use.
import { createHash } from 'node:crypto';
import { writeFileSync, readFileSync, mkdirSync } from 'node:fs';
import { join, resolve, dirname } from 'node:path';
import { openPlayer, b64, REPO } from '../render/lib/browser.mjs';

const args = Object.fromEntries(process.argv.slice(2).map(a => { const [k, ...v] = a.replace(/^--/, '').split('='); return [k, v.length ? v.join('=') : true]; }));
const project = String(args.project || '').replace(/\/$/, '');
if (!project) { console.error('usage: check_determinism.mjs --project=<dir>'); process.exit(2); }
const sb = JSON.parse(readFileSync(join(resolve(REPO, project), 'storyboard.json'), 'utf8'));
const n = +(args.n || 8);
const ts = Array.from({ length: n }, (_, i) => +((i + 0.5) * sb.duration_s / n).toFixed(4));
const sha = d => createHash('sha256').update(b64(d)).digest('hex').slice(0, 16);

const P = await openPlayer({ project, chrome: args.chrome, width: sb.width, height: sb.height });
const A = P.page, B = await P.newPage();
const ha = {}, hb = {}, hb2 = {};
for (const t of ts) ha[t] = sha(await A.evaluate(([t]) => window.__video.frame(t, 'image/png'), [t]));
const shuffled = [...ts].reverse();
for (const t of shuffled) hb[t] = sha(await B.evaluate(([t]) => window.__video.frame(t, 'image/png'), [t]));
for (const t of ts) hb2[t] = sha(await B.evaluate(([t]) => window.__video.frame(t, 'image/png'), [t])); // repeat after other frames
await P.close();

const mism = ts.filter(t => ha[t] !== hb[t] || hb[t] !== hb2[t]);
const result = { id: 'T4.determinism', level: 'P0', status: mism.length ? 'fail' : 'pass', title: `same t → identical pixels (${n} times × 3 renders, 2 pages)`,
  detail: mism.length ? `mismatch at t=${mism.join(', ')}` : '', hashes: ts.map(t => ({ t, a: ha[t], b: hb[t], b2: hb2[t] })) };
const out = args.out || join(resolve(REPO, project), 'out', 'determinism.json');
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, JSON.stringify(result, null, 2));
console.log(`== determinism: ${project}\n  ${result.status === 'pass' ? '✓' : '✗'} [P0] T4.determinism ${result.title}${result.detail ? ' — ' + result.detail : ''}`);
process.exit(result.status === 'pass' ? 0 : 1);

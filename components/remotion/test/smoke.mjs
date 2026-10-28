#!/usr/bin/env node
// smoke.mjs — run the REAL CanvasComposition (real React, bundled by esbuild) against a Remotion API shim
// in headless Chromium, and require pixel-identical frames versus the HTML player.
//   node components/remotion/test/smoke.mjs [--project=examples/ai-explainer-15s] [--frames=0,75,170,300,440]
// What this proves: frame->time mapping, font gating (delayRender/continueRender), React lifecycle, drawing.
// What it does NOT prove: compatibility with Remotion's own bundler/renderer — run `npm run render` for that.
import { createRequire } from 'node:module';
import { execSync } from 'node:child_process';
import { existsSync, mkdirSync, writeFileSync, readFileSync } from 'node:fs';
import { createHash } from 'node:crypto';
import { join, resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { openPlayer, b64, REPO, findChrome, serve } from '../../../scripts/render/lib/browser.mjs';

const here = dirname(fileURLToPath(import.meta.url));
const args = Object.fromEntries(process.argv.slice(2).map(a => { const [k, ...v] = a.replace(/^--/, '').split('='); return [k, v.join('=') || true]; }));
const project = args.project || 'examples/ai-explainer-15s';
const sb = JSON.parse(readFileSync(join(REPO, project, 'storyboard.json'), 'utf8'));
const frames = String(args.frames || '0,75,170,300,440').split(',').map(Number);

// Resolve esbuild/react/react-dom from the repo, the global npm root, or a known tools dir.
const roots = [join(REPO, 'node_modules'), join(REPO, 'components/remotion/node_modules')];
try { roots.push(execSync('npm root -g', { encoding: 'utf8' }).trim()); } catch {}
roots.push('/opt/npm-tools/node_modules');
const nodePaths = roots.filter(r => existsSync(join(r, 'react')));
const esbuildRoot = roots.find(r => existsSync(join(r, 'esbuild')));
if (!nodePaths.length || !esbuildRoot) { console.error('smoke test needs react, react-dom and esbuild installed'); process.exit(2); }
const esbuild = createRequire(join(esbuildRoot, 'x.js'))('esbuild');

const outDir = join(here, '.build'); mkdirSync(outDir, { recursive: true });
const entry = join(outDir, 'entry.jsx');
writeFileSync(entry, `
import React from 'react';
import { createRoot } from 'react-dom/client';
import { CanvasComposition } from '../../src/CanvasComposition';
import storyboard from '${join(REPO, project, 'storyboard.json').replace(/\\/g, '/')}';
const styleUrl = new URL(storyboard.style, location.origin + '/${project}/storyboard.json').href;
window.__ready = (async () => {
  const style = await (await fetch(styleUrl)).json();
  window.__remotionShim.setConfig({ fps: storyboard.fps, width: storyboard.width, height: storyboard.height });
  createRoot(document.getElementById('root')).render(React.createElement(CanvasComposition, { storyboard, style }));
})();
`);
await esbuild.build({
  entryPoints: [entry], bundle: true, format: 'esm', outfile: join(outDir, 'bundle.js'), jsx: 'automatic', loader: { '.json': 'json' },
  nodePaths, alias: { remotion: join(here, 'fake-remotion.js') }, logLevel: 'error', define: { 'process.env.NODE_ENV': '"production"' },
});
writeFileSync(join(outDir, 'index.html'), `<!doctype html><meta charset="utf-8"><link rel="icon" href="data:,"><body style="margin:0"><div id="root" style="position:relative;width:${sb.width}px;height:${sb.height}px"></div><script type="module" src="bundle.js"></script>`);

// Reference frames from the HTML player.
const P = await openPlayer({ project, width: sb.width, height: sb.height });
const ref = {};
for (const f of frames) ref[f] = await P.page.evaluate(([t]) => window.__video.frame(t, 'image/png'), [f / sb.fps]);
const { srv, port } = await serve();
const page = await P.newPage().catch(() => null) || P.page;
await page.goto(`http://127.0.0.1:${port}/components/remotion/test/.build/index.html`);
await page.waitForFunction('window.__ready').then(() => page.evaluate('window.__ready'));

const sha = d => createHash('sha256').update(b64(d)).digest('hex').slice(0, 16);
const results = [];
for (const f of frames) {
  await page.evaluate(n => window.__remotionShim.setFrame(n), f);
  await page.waitForFunction(() => window.__remotionShim.pending === 0, null, { timeout: 30000 });
  const got = await page.evaluate(() => document.querySelector('canvas').toDataURL('image/png'));
  results.push({ frame: f, remotion: sha(got), player: sha(ref[f]), equal: sha(got) === sha(ref[f]) });
}
srv.close(); await P.close();
const ok = results.every(r => r.equal);
console.log(`== remotion wrapper smoke (shim): ${project}`);
for (const r of results) console.log(`  ${r.equal ? '✓' : '✗'} frame ${r.frame}: wrapper ${r.remotion} vs player ${r.player}`);
writeFileSync(join(outDir, 'result.json'), JSON.stringify({ ok, results }, null, 2));
process.exit(ok ? 0 : 1);

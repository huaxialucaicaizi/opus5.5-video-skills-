// Shared: static file server over the repo root + headless Chromium page bound to player.html.
import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { existsSync, readdirSync } from 'node:fs';
import { extname, join, resolve, normalize, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

// AVS_WORKSPACE lets a trusted harness copy of these scripts render someone else's workspace (evals).
export const HARNESS = resolve(dirname(fileURLToPath(import.meta.url)), '../../..');
export const REPO = process.env.AVS_WORKSPACE ? resolve(process.env.AVS_WORKSPACE) : HARNESS;

const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.mjs': 'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg', '.svg': 'image/svg+xml',
  '.woff2': 'font/woff2', '.ttf': 'font/ttf', '.otf': 'font/otf', '.wav': 'audio/wav', '.mp3': 'audio/mpeg' };

export function serve(root = REPO) {
  return new Promise(ok => {
    const srv = http.createServer(async (req, res) => {
      try {
        const p = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname)).replace(/^([/\\])+/, '');
        const f = join(root, p);
        if (!f.startsWith(root)) { res.writeHead(403); return res.end(); }
        const s = await stat(f);
        if (s.isDirectory()) { res.writeHead(404); return res.end(); }
        res.writeHead(200, { 'content-type': TYPES[extname(f)] || 'application/octet-stream', 'cache-control': 'no-store' });
        res.end(await readFile(f));
      } catch { res.writeHead(404); res.end(); }
    });
    srv.listen(0, '127.0.0.1', () => ok({ srv, port: srv.address().port }));
  });
}

async function loadPlaywright() {
  try { return await import('playwright-core'); }
  catch { try { return await import('playwright'); } catch {
    throw new Error('playwright-core not found. Run `npm install` (or scripts/setup.sh) in the repo root.');
  } }
}

export function findChrome(explicit) {
  const cands = [explicit, process.env.CHROME_PATH].filter(Boolean);
  for (const c of cands) if (existsSync(c)) return c;
  // Playwright-managed browsers (PLAYWRIGHT_BROWSERS_PATH, ~/.cache/ms-playwright, /opt/pw-browsers)
  const roots = [process.env.PLAYWRIGHT_BROWSERS_PATH, join(process.env.HOME || '', '.cache/ms-playwright'), '/opt/pw-browsers'].filter(Boolean);
  for (const r of roots) {
    if (!existsSync(r)) continue;
    for (const d of readdirSync(r).filter(d => /^chromium-\d+/.test(d)).sort().reverse()) {
      for (const sub of ['chrome-linux64/chrome', 'chrome-linux/chrome', 'chrome-mac/Chromium.app/Contents/MacOS/Chromium',
        'chrome-mac-arm64/Chromium.app/Contents/MacOS/Chromium', 'chrome-win/chrome.exe', 'chrome-win64/chrome.exe']) {
        const p = join(r, d, sub); if (existsSync(p)) return p;
      }
    }
  }
  for (const p of ['/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', 'C:/Program Files/Google/Chrome/Application/chrome.exe']) if (existsSync(p)) return p;
  return null; // let Playwright try its default
}

export async function openPlayer({ project, chrome, width, height, verbose = false }) {
  const { chromium } = await loadPlaywright();
  const { srv, port } = await serve();
  const exe = findChrome(chrome);
  const browser = await chromium.launch({
    executablePath: exe || undefined, headless: true,
    args: ['--no-sandbox', '--font-render-hinting=none', '--disable-lcd-text', '--force-color-profile=srgb',
      '--disable-background-timer-throttling', '--disable-renderer-backgrounding'],
  });
  const pages = [];
  async function newPage() {
    const page = await browser.newPage({ viewport: { width: width || 1080, height: height || 1920 }, deviceScaleFactor: 1 });
    page.on('pageerror', e => console.error('[page error]', e.message));
    page.on('console', m => { if (verbose || m.type() === 'error') console.error(`[page ${m.type()}]`, m.text()); });
    await page.goto(`http://127.0.0.1:${port}/components/html-canvas/player.html?render&project=${encodeURIComponent(project)}`);
    await page.waitForFunction('window.__video && (window.__video.ready || window.__video.error)', null, { timeout: 60000 });
    const err = await page.evaluate('window.__video.error');
    if (err) throw new Error('player failed to boot:\n' + err);
    pages.push(page);
    return page;
  }
  const first = await newPage();
  const meta = await first.evaluate('window.__video.meta');
  return {
    meta, page: first, newPage, chrome: exe || '(playwright default)',
    async close() { await browser.close(); srv.close(); },
  };
}

export const b64 = dataUrl => Buffer.from(dataUrl.slice(dataUrl.indexOf(',') + 1), 'base64');

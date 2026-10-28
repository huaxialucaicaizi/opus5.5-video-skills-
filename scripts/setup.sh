#!/usr/bin/env bash
# setup.sh — install the one JS dependency (playwright-core) and check system tools.
# Works offline if playwright-core already exists somewhere on the machine (links it instead).
set -euo pipefail
cd "$(dirname "$0")/.."

ok()   { printf '  \033[32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[33m!\033[0m %s\n' "$*"; }
fail() { printf '  \033[31m✗\033[0m %s\n' "$*"; MISSING=1; }
MISSING=0

echo "== JS dependency"
if [ -d node_modules/playwright-core ]; then ok "playwright-core present"
elif npm install --no-audit --no-fund >/dev/null 2>&1; then ok "npm install done"
else
  warn "npm install failed (offline / blocked registry?) — looking for an existing playwright-core"
  for d in "$(npm root -g 2>/dev/null)" /opt/npm-tools/node_modules /usr/lib/node_modules /usr/local/lib/node_modules; do
    if [ -n "$d" ] && [ -d "$d/playwright-core" ]; then mkdir -p node_modules && ln -sfn "$d/playwright-core" node_modules/playwright-core && ok "linked $d/playwright-core" && break; fi
  done
  [ -d node_modules/playwright-core ] || fail "playwright-core not available: run 'npm install' with network access"
fi

echo "== Browser"
if node -e "import('./scripts/render/lib/browser.mjs').then(m=>{const p=m.findChrome();console.log(p||'');process.exit(p?0:1)})" >/tmp/.avs_chrome 2>/dev/null; then ok "chromium: $(cat /tmp/.avs_chrome)"
else warn "no Chromium found; set CHROME_PATH or run 'npx playwright install chromium'"; fi

echo "== System tools"
for t in ffmpeg ffprobe python3; do command -v $t >/dev/null && ok "$t" || fail "$t missing"; done
ENC=$(ffmpeg -hide_banner -encoders 2>/dev/null || true); grep -q libx264 <<<"$ENC" && ok "ffmpeg has libx264" || fail "ffmpeg lacks libx264"

echo "== Python packages"
for m in numpy jsonschema PIL; do python3 -c "import $m" 2>/dev/null && ok "$m" || fail "python: $m missing (pip install numpy jsonschema pillow)"; done

echo "== CJK font (for Chinese text)"
FONTS=$(fc-list 2>/dev/null || true)
if grep -qiE 'Noto Sans CJK|Source Han Sans|PingFang|WenQuanYi|Microsoft YaHei' <<<"$FONTS"; then ok "CJK font found"
else warn "no CJK font detected; Chinese text may render as boxes (install fonts-noto-cjk)"; fi

[ "$MISSING" = 0 ] && echo "setup OK" || { echo "setup incomplete"; exit 1; }

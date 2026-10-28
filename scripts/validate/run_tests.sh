#!/usr/bin/env bash
# run_tests.sh — toolkit self-test.
#   bash scripts/validate/run_tests.sh           unit tests + determinism + Remotion-wrapper parity + footage smoke + full example build
#   bash scripts/validate/run_tests.sh --quick   skip the full example build
set -uo pipefail
cd "$(dirname "$0")/../.."
QUICK=0; [ "${1:-}" = "--quick" ] && QUICK=1
PASS=0; FAIL=0; RESULTS=()
t() { local name="$1"; shift; printf '\n\033[1m▶ %s\033[0m\n' "$name"
  if "$@"; then PASS=$((PASS+1)); RESULTS+=("✓ $name"); else FAIL=$((FAIL+1)); RESULTS+=("✗ $name"); fi; }

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
t "environment (setup.sh)"            bash scripts/setup.sh
t "validator unit tests"              python3 scripts/validate/tests/test_validators.py
t "example spec validates"            python3 scripts/validate/validate_spec.py examples/ai-explainer-15s
t "engine determinism (example)"      node scripts/validate/check_determinism.mjs --project=examples/ai-explainer-15s --out="$TMP/det.json"
t "remotion wrapper pixel parity"     node components/remotion/test/smoke.mjs
footage_smoke() {
  ffmpeg -v error -y -f lavfi -i testsrc2=size=1080x1920:rate=30:duration=3 -c:v libx264 -pix_fmt yuv420p "$TMP/bg.mp4" &&
  ffmpeg -v error -y -f lavfi -i smptebars=size=640x360:rate=25:duration=2.5 -f lavfi -i sine=frequency=300:duration=2.5 -c:v libx264 -pix_fmt yuv420p -c:a aac -shortest "$TMP/fg.mp4" &&
  printf '1\n00:00:00,200 --> 00:00:02,000\n测试\n' > "$TMP/s.srt" &&
  python3 scripts/render/footage.py pip "$TMP/bg.mp4" "$TMP/fg.mp4" -o "$TMP/pip.mp4" --circle >/dev/null &&
  python3 scripts/render/footage.py subs "$TMP/pip.mp4" "$TMP/s.srt" -o "$TMP/out.mp4" >/dev/null &&
  python3 - "$TMP/out.mp4" <<'EOF'
import sys, json, subprocess
j = json.loads(subprocess.run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',sys.argv[1]],capture_output=True,text=True).stdout)
kinds = sorted(s['codec_type'] for s in j['streams']); d = float(j['format']['duration'])
assert kinds == ['audio','subtitle','video'], kinds
assert abs(d - 2.5) < 0.1, d
print('footage smoke ok', kinds, d)
EOF
}
t "footage pip + subtitle track"      footage_smoke
if [ "$QUICK" = 0 ]; then
  t "full example build (15 s MP4)"   bash scripts/render/build.sh examples/ai-explainer-15s --agent=selftest
  t "example QA verdict not FAIL"     python3 -c "import json,sys;v=json.load(open('examples/ai-explainer-15s/out/qa_report.json'))['verdict'];print(v);sys.exit(v=='FAIL')"
fi
printf '\n== self-test: %d passed, %d failed\n' "$PASS" "$FAIL"; printf '  %s\n' "${RESULTS[@]}"
[ "$FAIL" = 0 ]

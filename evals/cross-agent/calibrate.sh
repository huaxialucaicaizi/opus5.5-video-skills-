#!/usr/bin/env bash
# calibrate.sh — prove the scorer separates "did nothing" from "did it right" on every task.
# For each task: fresh workspace -> score NULL (untouched) -> apply GOLDEN solution -> score again.
#   bash evals/cross-agent/calibrate.sh [--tasks=E1,E4,E5,E6,E7] [--runs=/tmp/avs-calib]
# Writes evals/cross-agent/results/calibration.md. E2/E3 are not calibrated (no single golden answer).
set -euo pipefail
AVS="$(cd "$(dirname "$0")/../.." && pwd)"; EV="$AVS/evals/cross-agent"
TASKS="E1,E4,E5,E6,E7"; RUNS="${TMPDIR:-/tmp}/avs-calib"
for a in "$@"; do case "$a" in --tasks=*) TASKS="${a#*=}";; --runs=*) RUNS="${a#*=}";; esac; done
rm -rf "$RUNS"; mkdir -p "$RUNS" "$EV/results"
score() { python3 "$EV/score_run.py" --task "$1" --workspace "$2" 2>/dev/null | python3 -c "import json,sys;r=json.load(sys.stdin);print(r['total'])"; }

golden() {  # $1 task, $2 workspace
  local T=$1 W=$2
  case "$T" in
  E1)  P=$W/projects/e1-how-ai-talks; mkdir -p "$P"
       python3 - "$W" <<'EOF'
import json, sys, pathlib
w = pathlib.Path(sys.argv[1]); src = w / 'examples/ai-explainer-15s'; dst = w / 'projects/e1-how-ai-talks'
for name in ('storyboard.json', 'task.json', 'review.json'):
    d = json.loads((src / name).read_text())
    if 'task_id' in d: d['task_id'] = 'e1-how-ai-talks'
    if name == 'task.json': d['id'] = 'e1-how-ai-talks'
    (dst / name).write_text(json.dumps(d, ensure_ascii=False, indent=2))
EOF
       (cd "$W" && bash scripts/render/build.sh projects/e1-how-ai-talks --agent=golden >/dev/null);;
  E4)  python3 - "$W" <<'EOF'
import json, sys, pathlib
p = pathlib.Path(sys.argv[1]) / 'projects/e4-broken'
sb = json.loads((p / 'storyboard.json').read_text()); task = json.loads((p / 'task.json').read_text())
sc = {s['id']: s for s in sb['scenes']}
sc['s3_probs']['start'] = 5.5
sc['s2_tokens']['reads'][1]['end'] = 3.9
sc['s4_loop']['on_screen_text'][-1].update(start=10.7, end=12.5)
sc['s3_probs']['component'] = 'prob-bars'
sc['s5_takeaway']['transition_out'] = {'type': 'fade', 'duration': 0.35}
task['assets'] = []; task['audio']['music'] = {'source': 'synth', 'bpm': 120}
(p / 'storyboard.json').write_text(json.dumps(sb, ensure_ascii=False, indent=2)); (p / 'task.json').write_text(json.dumps(task, ensure_ascii=False, indent=2))
EOF
       ;;
  E5)  cp "$EV/fixtures/golden/sparkle-title.js" "$W/components/html-canvas/scenes/sparkle-title.js"
       (cd "$W" && bash scripts/render/build.sh projects/e5-sparkle --agent=golden >/dev/null);;
  E6)  I=$W/projects/e6-pip/inputs; O=$W/projects/e6-pip/out; mkdir -p "$O"
       python3 "$W/scripts/render/footage.py" pip "$I/broll.mp4" "$I/talk.mp4" -o "$O/pip.mp4" --circle --audio fg >/dev/null
       python3 "$W/scripts/render/footage.py" subs "$O/pip.mp4" "$I/subs.srt" -o "$O/final.mp4" >/dev/null;;
  E7)  P=$W/projects/e7-review
       (cd "$W" && node scripts/render/render.mjs --project=projects/e7-review --sheet --keyframes --layout >/dev/null && node scripts/validate/check_determinism.mjs --project=projects/e7-review >/dev/null || true)
       cat > "$P/review.json" <<'EOF'
{"reviewer": "golden (calibration)", "checks": [
 {"id": "M1", "status": "fail", "note": "s3 概率条 62%+30%+20%+9% 加起来 121%，超过 100%，事实错误", "evidence": ["out/keyframes/t8_20.png"]},
 {"id": "M2", "status": "pass", "note": "每镜有事件"}, {"id": "M3", "status": "warn", "note": "s3 底部长注释抢焦点"},
 {"id": "M4", "status": "pass", "note": "无禁用效果"}, {"id": "M5", "status": "pass", "note": "回顾行呼应"}]}
EOF
       printf '# 修改清单\n1. [P0] s3 概率总和 121%%：改为总和 100%%（如 62/17/12/9）\n2. [P0] s3 注释超出安全区底部（V1），缩短为「概率仅为示意」\n3. [P1] 响度 -24 LUFS，平台要求 -14 LUFS：按 -14 重新生成音频\n4. [P1] s4「一遍又一遍」只停留 0.5 s，阅读时间不够（S3），延长到 ≥0.83 s\n' > "$P/FIXES.md"
       (cd "$W" && python3 scripts/validate/qa_report.py projects/e7-review --agent=golden >/dev/null || true);;
  esac
}

{ echo "# Scorer calibration"; echo; echo "Generated $(date '+%F %T') at toolkit commit $(git -C "$AVS" rev-parse --short HEAD 2>/dev/null || echo ?)."; echo
  echo "| task | null (untouched) | golden | separation |"; echo "|---|---|---|---|"; } > "$EV/results/calibration.md"
for T in ${TASKS//,/ }; do
  bash "$EV/run_agent.sh" --agent=manual --task="$T" --runs="$RUNS" >/dev/null
  W=$(ls -d "$RUNS"/manual-"$T"-*/workspace | tail -1)
  N=$(score "$T" "$W"); golden "$T" "$W"; G=$(score "$T" "$W")
  printf '%s  null=%s  golden=%s\n' "$T" "$N" "$G"
  echo "| $T | $N | $G | $(python3 -c "print(round($G-$N,1))") |" >> "$EV/results/calibration.md"
done
echo; cat "$EV/results/calibration.md"

#!/usr/bin/env bash
# build.sh — full pipeline for one project: validate → audio → preview sheet → frames → MP4 → QA.
#   bash scripts/render/build.sh <project_dir> [--agent=<name>] [--workers=N] [--blur=N] [--skip-audio]
# Stops at the first blocking failure. Re-running resumes: existing frames are reused.
set -euo pipefail
cd "$(dirname "$0")/../.."
P="${1:?usage: build.sh <project_dir> [--agent=name] [--workers=N] [--blur=N] [--skip-audio]}"; shift || true
AGENT=unknown; WORKERS=2; BLUR=1; AUDIO=1
for a in "$@"; do case "$a" in
  --agent=*) AGENT="${a#*=}";; --workers=*) WORKERS="${a#*=}";; --blur=*) BLUR="${a#*=}";; --skip-audio) AUDIO=0;;
  *) echo "unknown option $a"; exit 2;; esac; done
OUT="$P/out"; mkdir -p "$OUT"
ID=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['task_id'])" "$P/storyboard.json")
T0=$(date +%s)
step() { printf '\n\033[1m[%s] %s\033[0m\n' "$(($(date +%s)-T0))s" "$*"; }

step "1/7 validate spec";        python3 scripts/validate/validate_spec.py "$P" --json "$OUT/spec_checks.json"
step "2/7 preview contact sheet"; node scripts/render/render.mjs --project="$P" --sheet
step "3/7 keyframes + layout";    node scripts/render/render.mjs --project="$P" --keyframes --layout
python3 scripts/validate/layout_check.py "$P" || { echo "layout check failed — fix before the full render"; exit 1; }
AUDIO_ARG=()
if [ "$AUDIO" = 1 ]; then
  SRC=$(python3 -c "import json,sys,os;t=sys.argv[1];print(json.load(open(t)).get('audio',{}).get('music',{}).get('source','synth') if os.path.exists(t) else 'synth')" "$P/task.json")
  if [ "$SRC" = synth ]; then step "4/7 synthesise audio"; python3 scripts/render/synth_music.py "$P"; AUDIO_ARG=(--audio="$OUT/audio.wav")
  elif [ "$SRC" = file ]; then
    F=$(python3 -c "import json,sys;print(json.load(open(sys.argv[1]))['audio']['music']['path'])" "$P/task.json"); step "4/7 use audio file $F"; AUDIO_ARG=(--audio="$P/$F")
  else step "4/7 no audio"; fi
else step "4/7 audio skipped"; fi
step "5/7 render frames + encode"; node scripts/render/render.mjs --project="$P" --mp4 --workers="$WORKERS" --blur="$BLUR" "${AUDIO_ARG[@]}"
step "6/7 determinism";           node scripts/validate/check_determinism.mjs --project="$P"
step "7/7 QA report";             python3 scripts/validate/qa_report.py "$P" --agent="$AGENT"
echo; echo "done in $(($(date +%s)-T0))s → $OUT/$ID.mp4"

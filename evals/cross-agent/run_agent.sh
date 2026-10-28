#!/usr/bin/env bash
# run_agent.sh — run ONE agent on ONE eval task in a fresh, isolated workspace, then score it.
#
#   bash evals/cross-agent/run_agent.sh --agent=claude|codex|grok|manual --task=E1 [--model=<id>] [--runs=evals/cross-agent/runs] [--timeout=3600]
#
# Agent commands (override with CLAUDE_CMD / CODEX_CMD / GROK_CMD; the prompt is appended as the last argument):
#   claude : claude -p --permission-mode bypassPermissions --output-format json
#   codex  : codex exec --full-auto            (flags differ between Codex versions — check `codex exec --help`)
#   grok   : must be provided via GROK_CMD     (e.g. your Grok Build headless command)
#   manual : prepares the workspace and prints the prompt; you run any agent yourself, then call score_run.py
# Workspaces are disposable copies of this toolkit (without .git, runs/ and build outputs).
set -euo pipefail
AVS="$(cd "$(dirname "$0")/../.." && pwd)"
AGENT=""; TASK=""; RUNS="$AVS/evals/cross-agent/runs"; TIMEOUT=3600; MODEL=""
for a in "$@"; do case "$a" in
  --agent=*) AGENT="${a#*=}";; --task=*) TASK="${a#*=}";; --model=*) MODEL="${a#*=}";; --runs=*) RUNS="${a#*=}";; --timeout=*) TIMEOUT="${a#*=}";;
  *) echo "unknown option $a" >&2; exit 2;; esac; done
[ -n "$AGENT" ] && [ -n "$TASK" ] || { sed -n '2,13p' "$0"; exit 2; }

STAMP=$(date +%Y%m%d-%H%M%S); RUN="$RUNS/$AGENT${MODEL:+-$MODEL}-$TASK-$STAMP"; WS="$RUN/workspace"
mkdir -p "$WS"
# Fresh copy of the toolkit at its current commit. node_modules is linked, not copied.
tar -C "$AVS" --exclude=.git --exclude='./evals/cross-agent/runs' --exclude='*/out' --exclude=node_modules \
    --exclude='.claude/skills' --exclude='.agents/skills' --exclude='.grok/skills' --exclude='.avs-root' -cf - . | tar -C "$WS" -xf -
[ -d "$AVS/node_modules" ] && ln -s "$(readlink -f "$AVS/node_modules/playwright-core" | xargs dirname)" "$WS/node_modules" 2>/dev/null || true
[ -e "$WS/node_modules/playwright-core" ] || (cd "$WS" && bash scripts/setup.sh >/dev/null 2>&1 || true)
python3 "$AVS/evals/cross-agent/fixtures/setup.py" "$TASK" "$WS"
# Reference copy of fixture inputs (to detect modified inputs).
if [ -d "$WS/projects/e6-pip/inputs" ]; then mkdir -p "$RUN/fixture_ref" && cp "$WS/projects/e6-pip/inputs/"* "$RUN/fixture_ref/"; fi
case "$AGENT" in claude|codex|grok) bash "$WS/scripts/install-skills.sh" --agent="$AGENT" >/dev/null;; esac
PROMPT=$(python3 -c "import json,sys;print({t['id']:t for t in json.load(open(sys.argv[1]))['tasks']}[sys.argv[2]]['prompt'])" "$AVS/evals/cross-agent/tasks.json" "$TASK")
printf '%s\n' "$PROMPT" > "$RUN/prompt.txt"
COMMIT=$(git -C "$AVS" rev-parse --short HEAD 2>/dev/null || echo unknown)

T0=$(date +%s); RC=0
case "$AGENT" in
  claude) CMD=${CLAUDE_CMD:-"claude -p --permission-mode bypassPermissions --output-format json${MODEL:+ --model $MODEL}"};;
  codex)  CMD=${CODEX_CMD:-"codex exec --full-auto${MODEL:+ -m $MODEL}"};;
  grok)   CMD=${GROK_CMD:?set GROK_CMD to your Grok headless command};;
  manual) echo "workspace: $WS"; echo "prompt:"; cat "$RUN/prompt.txt"
          echo "after the agent finishes: python3 $AVS/evals/cross-agent/score_run.py --task $TASK --workspace $WS --json $RUN/score.json"; exit 0;;
  *) echo "unknown agent $AGENT" >&2; exit 2;;
esac
echo "[$AGENT/$TASK] running in $WS (timeout ${TIMEOUT}s)"
(cd "$WS" && timeout "$TIMEOUT" $CMD "$PROMPT" > "$RUN/agent_output.txt" 2> "$RUN/agent_stderr.txt") || RC=$?
T1=$(date +%s)

AVS_FIXTURE_REF="$RUN/fixture_ref" python3 "$AVS/evals/cross-agent/score_run.py" --task "$TASK" --workspace "$WS" --json "$RUN/score.json" > /dev/null || true
python3 - "$RUN" "$AGENT" "$TASK" "$RC" "$((T1-T0))" "$COMMIT" "$MODEL" <<'EOF'
import json, sys, pathlib
run, agent, task, rc, secs, commit, model = sys.argv[1:]
run = pathlib.Path(run); s = json.loads((run / 'score.json').read_text()) if (run / 'score.json').exists() else {'total': 0}
meta = {'agent': agent, 'model_requested': model or 'default', 'task': task, 'exit_code': int(rc), 'wall_s': int(secs), 'toolkit_commit': commit, 'score': s.get('total'), 'components': s.get('components'), 'p0_fail': s.get('p0_fail')}
try:  # Claude Code JSON output carries cost/turns
    o = json.loads((run / 'agent_output.txt').read_text())
    meta.update({k: o.get(k) for k in ('total_cost_usd', 'num_turns', 'duration_ms', 'is_error') if k in o})
    mu = o.get('modelUsage') or {}
    meta['models_used'] = sorted(mu, key=lambda m: -(mu[m].get('outputTokens', 0) if isinstance(mu[m], dict) else 0))
except Exception: pass
(run / 'run.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2))
print(json.dumps(meta, ensure_ascii=False))
EOF

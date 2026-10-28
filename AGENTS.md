# AGENTS.md — AI Video Skills

Instructions for any coding agent working in this repository (Codex reads this file natively; Claude Code reads it via `CLAUDE.md`; other agents: paste or point to it).

## What this repo is
A toolkit for making short videos **with code**: plan a storyboard → render deterministic frames in headless Chromium → encode MP4 with FFmpeg → run automatic QA → review keyframes. The skills in `skills/` describe each stage.

| Stage | Skill | Main commands |
|---|---|---|
| Plan | `skills/video-planner/SKILL.md` | `python3 scripts/validate/validate_spec.py <project>` |
| Build | `skills/code-video-builder/SKILL.md` | `bash scripts/render/build.sh <project> --agent=<you>` |
| Review | `skills/video-quality-reviewer/SKILL.md` | `python3 scripts/validate/qa_report.py <project>` |
| Footage | `skills/footage-editing/SKILL.md` | `python3 scripts/render/footage.py <cmd> ...` |

If your agent does not auto-load skills, **open the relevant SKILL.md and follow it** before starting that stage.

## Setup (once)
```bash
bash scripts/setup.sh        # links/installs playwright-core, checks Chromium, ffmpeg+libx264, numpy, jsonschema, CJK font
bash scripts/validate/run_tests.sh   # self-test: unit checks + full 15 s example build
```

## Hard rules
1. **Storyboard first.** No scene code before `storyboard.json` validates. The renderer reads the storyboard directly.
2. **Frames are pure functions of `t`.** No `Math.random`, `Date.now`, `performance.now`, timers, CSS animations or cross-frame state in scene code. `check_determinism.mjs` enforces this.
3. **All text through `f.text()`** so layout QA sees it. Keep text inside the style's safe area.
4. **Look at the frames.** Open `out/contact_sheet.jpg` and seam strips with your image viewer before claiming a video is done. A report with no visual review is `NEEDS_REVIEW`, not `PASS`.
5. **Licences.** Every external file goes into `task.json.assets[]` with author + licence. `unknown` fails validation. Do not copy prompts or code from the reference repos listed in `SOURCES.md` unless they are category A.
6. **Never modify input footage.** Write new files.
7. **Secrets** (TTS/API keys) live in `.env`, which agents must not read; scripts read it themselves.

## Layout
```
spec/                    video-task.schema.json, ACCEPTANCE_CHECKLIST.md
templates/storyboard/    storyboard.schema.json
templates/visual-style/  style.default.json (tokens), VISUAL_GUIDE.md
components/html-canvas/  engine.js, player.html, scenes/  (primary renderer)
components/remotion/     Remotion wrapper over the same engine
scripts/render/          render.mjs, build.sh, synth_music.py, footage.py
scripts/validate/        validate_spec.py, layout_check.py, probe_video.py, check_determinism.mjs, qa_report.py, run_tests.sh
examples/                ai-explainer-15s (reference project)
evals/cross-agent/       task set, runner, scorer for comparing agents
adapters/                per-agent notes (claude-code, codex, grok)
```

## Definition of done for a video
`out/qa_report.json` verdict is `PASS` or `PASS_WITH_WARNINGS`, with every manual check (M1–M5) backed by evidence files.

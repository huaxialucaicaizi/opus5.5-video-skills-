## Video production (AI Video Skills)

This project uses the AI Video Skills toolkit at `<AVS_ROOT>` (replace with the absolute path).
- Skills are installed in `.claude/skills/` (`bash <AVS_ROOT>/scripts/install-skills.sh --agent=claude --target=. --mode=copy`).
- Follow `<AVS_ROOT>/AGENTS.md` hard rules: storyboard first, frames are pure functions of t, all text via `f.text()`, look at contact sheets before calling a video done, register every asset licence.
- Build: `bash <AVS_ROOT>/scripts/render/build.sh <project dir> --agent=claude-code`.

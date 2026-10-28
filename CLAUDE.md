# CLAUDE.md

Read `AGENTS.md` in this directory first — it is the shared instruction file for every agent and applies to you in full.

Claude Code specifics:
- Skills: `bash scripts/install-skills.sh --agent=claude` links `skills/*` into `.claude/skills/`, after which they load automatically by description or via `/video-planner`, `/code-video-builder`, `/video-quality-reviewer`, `/footage-editing`.
- Use the Read tool on `out/contact_sheet.jpg` and strip images — that is the visual review step, not optional.
- Suggested permissions are in `adapters/claude-code/settings.example.json` (allows the render/validate scripts, denies reading `.env`).

#!/usr/bin/env bash
# install-skills.sh — make the four skills discoverable by a specific agent.
#
#   bash scripts/install-skills.sh --agent=claude|codex|grok [--scope=project|user] [--target=<repo dir>] [--mode=link|copy] [--dry-run]
#
#   agent   discovery directory (verify against your agent version; see docs/AGENT_INTEGRATION.md)
#   claude  <target>/.claude/skills/<name>/SKILL.md      user: ~/.claude/skills/
#   codex   <target>/.agents/skills/<name>/SKILL.md      user: ~/.agents/skills/
#   grok    <target>/.grok/skills/<name>/SKILL.md        user: ~/.grok/skills/   (per third-party docs; unverified)
#
# --target defaults to this toolkit's root. --mode=link (default) symlinks so updates propagate;
# --mode=copy is for tools that do not follow symlinks. Every installed skill gets an `.avs-root`
# file holding the absolute toolkit path, so skills keep working when copied into another repo.
set -euo pipefail
AVS="$(cd "$(dirname "$0")/.." && pwd)"
AGENT=""; SCOPE=project; TARGET="$AVS"; MODE=link; DRY=0
for a in "$@"; do case "$a" in
  --agent=*) AGENT="${a#*=}";; --scope=*) SCOPE="${a#*=}";; --target=*) TARGET="$(cd "${a#*=}" && pwd)";;
  --mode=*) MODE="${a#*=}";; --dry-run) DRY=1;; -h|--help) sed -n '2,16p' "$0"; exit 0;;
  *) echo "unknown option: $a" >&2; exit 2;; esac; done
case "$AGENT" in
  claude) SUB=.claude/skills;; codex) SUB=.agents/skills;; grok) SUB=.grok/skills;;
  *) echo "--agent=claude|codex|grok is required" >&2; exit 2;; esac
if [ "$SCOPE" = user ]; then DEST="$HOME/$SUB"; else DEST="$TARGET/$SUB"; fi
run() { if [ "$DRY" = 1 ]; then echo "+ $*"; else "$@"; fi; }

run mkdir -p "$DEST"
for s in "$AVS"/skills/*/; do
  name="$(basename "$s")"
  # Agent Skills format: `name` must equal the directory name (Codex enforces this).
  fm="$(sed -n '2p' "$s/SKILL.md")"
  [ "$fm" = "name: $name" ] || { echo "skills/$name/SKILL.md: frontmatter line 2 must be 'name: $name' (got '$fm')" >&2; exit 1; }
  dst="$DEST/$name"
  if [ -e "$dst" ] || [ -L "$dst" ]; then run rm -rf "$dst"; fi
  if [ "$MODE" = copy ]; then
    run cp -R "$s" "$dst"
    [ "$DRY" = 1 ] || printf '%s\n' "$AVS" > "$dst/.avs-root"
  else
    run ln -s "${s%/}" "$dst"
  fi
  echo "installed $name -> $dst ($MODE)"
done
# For links, .avs-root lives in the source dir and is resolved through the link.
if [ "$MODE" = link ] && [ "$DRY" = 0 ]; then for s in "$AVS"/skills/*/; do printf '%s\n' "$AVS" > "$s/.avs-root"; done; fi

case "$AGENT" in
  codex)  [ "$TARGET" != "$AVS" ] && [ ! -f "$TARGET/AGENTS.md" ] && echo "tip: copy $AVS/AGENTS.md into $TARGET (Codex reads AGENTS.md for repo instructions)";;
  claude) [ "$TARGET" != "$AVS" ] && [ ! -f "$TARGET/CLAUDE.md" ] && echo "tip: copy $AVS/adapters/claude-code/CLAUDE.snippet.md into $TARGET/CLAUDE.md";;
  grok)   echo "note: Grok Build skill discovery path is from third-party docs — run '/skills' (or your version's equivalent) to confirm they loaded; otherwise use adapters/grok/PROMPT.md";;
esac
echo "done. Toolkit root: $AVS"

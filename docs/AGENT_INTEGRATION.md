# 接入 Codex、Claude Code、Grok

三个 Agent 的 Skill 加载机制、指令文件和工具权限**都不同**。本工具包的做法：Skill 正文保持 Agent 中立（只依赖 shell 命令和读文件），差异全部放在安装脚本和本页。

核查日期 2026-10-28。机制会随版本变化，安装后请按"自检"一栏确认。

## 总览

| | Claude Code | Codex CLI | Grok Build | Grok（API/对话，无技能目录） |
|---|---|---|---|---|
| 仓库指令文件 | `CLAUDE.md` | `AGENTS.md` | 待确认（第三方报道称兼容 Claude Code 的指令文件） | 粘贴 `adapters/grok/PROMPT.md` |
| Skill 目录（项目级） | `.claude/skills/<name>/SKILL.md` | `.agents/skills/<name>/SKILL.md` | `.grok/skills/<name>/SKILL.md` | 不适用 |
| Skill 目录（用户级） | `~/.claude/skills/` | `~/.agents/skills/` | `~/.grok/skills/` | 不适用 |
| 显式调用 | `/video-planner` | `$video-planner` | 版本相关 | "先读 skills/…/SKILL.md" |
| 自动触发 | 按 `description` 匹配 | 按 `description` 匹配 | 按 `description` 匹配（据报道） | 无 |
| frontmatter 要求 | 均可选，推荐 `description` | `name`（=目录名，小写短横线，≤64）+ `description`（≤1024）必填 | 据报道与 Claude Code 兼容 | — |
| 看图（审片必需） | Read 工具可直接看 JPG/PNG | 取决于版本/模型；不确定时让人审 | 版本相关 | 版本相关 |
| 信息来源 | [官方文档](https://code.claude.com/docs/en/skills) | [第三方整理](https://codex.danielvaughan.com/2026/05/05/agent-skills-open-standard-portable-skills-codex-cli-cross-agent/)（官方文档页本次未能直接访问） | [第三方报道](https://codersera.com/blog/xai-grok-build-skills-connectors-guide-2026/amp/)，请以 docs.x.ai 为准 | — |

本仓库四个 SKILL.md 同时满足最严格的要求（Codex 的 `name`=目录名 + `description` ≤1024 字符），`install-skills.sh` 安装前会检查。

## Claude Code
```bash
bash scripts/install-skills.sh --agent=claude                  # 本仓库内使用（软链接）
bash scripts/install-skills.sh --agent=claude --target=~/my-proj --mode=copy   # 装到别的项目
cp adapters/claude-code/settings.example.json .claude/settings.json            # 可选：预授权脚本 + 禁读 .env
```
- 自检：在 Claude Code 里输入 `/` 应看到四个 Skill；或问"有哪些 skill 可用"。
- 权限：`settings.example.json` 只预授权本工具包的脚本；`allowed-tools` 未写进 SKILL.md，避免在别人的项目里扩大权限。

## Codex CLI
```bash
bash scripts/install-skills.sh --agent=codex                   # → .agents/skills/
# 别的项目：同时复制 AGENTS.md（Codex 从仓库根读取指令）
bash scripts/install-skills.sh --agent=codex --target=~/my-proj --mode=copy && cp AGENTS.md ~/my-proj/
```
- 自检：在 Codex TUI 输入 `$` 查看可用 Skill，或运行 `codex exec "list available skills"`。
- 沙箱：Codex 默认沙箱可能禁止启动浏览器或写入仓库外路径；`build.sh` 需要启动 Chromium、执行 FFmpeg，请在允许执行本地命令的模式下运行，或由你手动执行 `build.sh` 后让 Codex 读结果。
- 若 Skill 发现路径与你的 Codex 版本不符：AGENTS.md 已列出每阶段要读的 SKILL.md，Codex 按文件路径读取同样可用。

## Grok
两种情况：
1. **Grok Build（终端 Agent）**：`bash scripts/install-skills.sh --agent=grok`，然后在 Grok Build 中确认技能已加载。若未加载，把 `AGENTS.md` 作为首条消息让它读取，按其中的表格逐阶段读 SKILL.md。
2. **API / 对话 + 代码执行**：用 `adapters/grok/PROMPT.md`。先让它运行 `setup.sh` 确认环境；托管沙箱缺浏览器/FFmpeg 时，Grok 只负责计划和代码，渲染在你本机跑。

## 不要假设的事情
- 不要假设某个 Agent 能看图：审片的 M2–M5 依赖看图。看不了就标 `pending`，由人或别的 Agent 补审。
- 不要假设工具权限一致：同一条 `build.sh` 在不同沙箱里可能被拦截。失败时贴原始报错。
- 不要假设联网：`setup.sh` 在 npm 不可用时会尝试链接本机已有的 `playwright-core`，不会绕过网络策略。

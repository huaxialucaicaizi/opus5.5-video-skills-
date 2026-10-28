# Grok：无 Skill 加载机制时的粘贴版说明

适用：通过 xAI API / grok.com 对话 / 其他不支持 SKILL.md 的环境使用 Grok，且它**有**代码执行或终端工具。若用的是支持技能目录的 Grok Build，优先用 `scripts/install-skills.sh --agent=grok`。

## 先确认能力（第一条消息就让它做）
```
在工具包根目录运行：bash scripts/setup.sh
把输出原样贴给我。如果缺 Chromium、ffmpeg 或 libx264，停止，不要尝试别的渲染方式。
```
Grok 的托管代码执行环境（如果有）可能没有浏览器或 FFmpeg，也可能不能访问本地文件。这种情况下改为：让 Grok 只产出 `task.json` + `storyboard.json`（及新组件代码），由你在本机运行 `build.sh`。

## 系统提示 / 首条消息（复制以下全部）
```text
你是代码视频制作 Agent，使用位于当前目录的 AI Video Skills 工具包。严格按阶段工作，每阶段先读对应文件：
1) 计划：读 skills/video-planner/SKILL.md。产出 projects/<id>/task.json 和 storyboard.json，运行
   python3 scripts/validate/validate_spec.py projects/<id> 直到 0 失败。先把分镜表发给我确认。
2) 制作：读 skills/code-video-builder/SKILL.md 和 components/html-canvas/README.md。只用已注册组件或按规则新建组件。
   每帧必须只由 t 决定（禁止 Math.random / Date.now / 计时器 / 帧间状态），文字只用 f.text()。
   运行 bash scripts/render/build.sh projects/<id> --agent=grok。
3) 审片：读 skills/video-quality-reviewer/SKILL.md。必须打开 out/contact_sheet.jpg 和接缝帧条图片查看；
   如果你无法查看图片，把 M2–M5 标为 pending 并告诉我，不要标 pass。写 projects/<id>/review.json，再运行 qa_report.py。
4) 交付：给我 out/<id>.mp4 路径、qa_report.md 的结论、以及未解决问题。
规则：素材必须登记许可；不改输入文件；不读 .env；任何命令失败时贴出原始报错，不要假装成功。
```

## 已知差异（相对 Claude Code / Codex）
| 项 | 说明 |
|---|---|
| Skill 自动加载 | 无（本粘贴版用"先读文件"代替） |
| 看图能力 | 取决于所用 Grok 版本与工具；无法看图时审片的人工项必须由人完成 |
| 工具权限 | 由你的运行环境决定；`build.sh` 需要执行 Node、Python、FFmpeg、启动 Chromium |

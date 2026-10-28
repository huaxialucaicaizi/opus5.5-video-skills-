---
name: code-video-builder
description: Build and render a code-generated video (HTML canvas or Remotion) from an approved storyboard.json into an MP4. Writes or adapts deterministic scene components (every frame a pure function of t), checks contact sheets and seam strips while building, synthesises or muxes audio, and exports H.264 MP4 with a QA report. Use after video-planner, or when asked to render, implement, fix or re-time scenes of a code-made video.
---

# code-video-builder

把已确认的 `storyboard.json` 变成 MP4。主路线是 HTML-Canvas（零依赖，最容易跨 Agent）；团队已经在用 Remotion 时走 Remotion 路线（见文末）。

工具包根目录（下文记作 `$AVS`）：本 Skill 目录里若有 `.avs-root` 文件，其内容就是 `$AVS`（由 `scripts/install-skills.sh` 写入）；否则为本 SKILL.md **真实路径**向上两级（`realpath SKILL.md` 后取 `../..`）。可用：`AVS=$(cat <skill_dir>/.avs-root 2>/dev/null || (cd "$(dirname "$(realpath <skill_dir>/SKILL.md)")/../.." && pwd))`。

## 触发条件
- 有 storyboard，需要实现 / 渲染 / 导出 MP4。
- 修改某个镜头的动画、时间、文字后重新出片。
- storyboard 引用了尚未注册的组件，需要新建。

## 输入
- `<project>/storyboard.json`（必需，最好已通过 `validate_spec.py`）、`<project>/task.json`（可选，有则用于技术参数与音频设置）
- 运行环境：Node ≥ 18、`playwright-core`、Chromium、FFmpeg(libx264)、Python3 + numpy。先跑 `bash $AVS/scripts/setup.sh`。

## 确定性规则（违反即 T4 失败）
1. 每帧只由 `t` 决定。**禁止** `Math.random()`、`Date.now()`、`performance.now()`、`setTimeout/setInterval`、CSS animation/transition、帧间累积状态、逐帧积分的物理。
2. 随机用 `hash(key)`；弹簧用 `spring()`/`springTo()` 闭式解；关键帧用 `kf()`；入退场用 `envelope()`/`rise()`。
3. 场景只画自己的内容；背景和转场由 composition 负责。**场景不要自己做退场淡出**（会和转场叠加造成"空帧"），用 `f.exit`。
4. 所有文字走 `f.text()`：它会记录真实文字框，供安全区/重叠/字号检查。不要用 `ctx.fillText` 直接画文字。方框里的文字先 `f.box()` 声明方框，再用 `f.text(..., {parent})`，否则溢出检查（V5）看不到。
5. 字体先加载再出第一帧（player 已处理）；不要在场景里改 `ctx.font` 后画文字而不经 `f.text()`。

## 执行步骤
1. **环境自检**：`bash $AVS/scripts/setup.sh`。缺浏览器/FFmpeg 时停止，报告缺什么（不要换成录屏等不确定方式）。横屏 16:9 用 `templates/visual-style/style.landscape.json`（默认风格是 9:16 的，S7 会拦下）。
2. **对照组件**：storyboard 每个 `component` 是否已在 `$AVS/components/html-canvas/scenes/index.js` 注册。缺的组件：
   - 在 `scenes/<name>.js` 写 `export default function (f, params) {...}`，只用 `f`（帧 API）和 `engine.js` 的纯函数；
   - 在 `scenes/index.js` 注册；在 `components/html-canvas/README.md` 记录 params。
3. **先看静帧再做动作**：`node $AVS/scripts/render/render.mjs --project=<p> --sheet`，用图片查看工具**真的打开** `out/contact_sheet.jpg`。确认每个场景的关键姿态能读懂、焦点清楚、没出界。
4. **看接缝和动作**：对每个接缝及关键动作渲染帧条：`--sheet=<t-0.1>,<t>,<t+0.1>,<t+0.2>,... --cols=6 --outfile=out/strip_<n>.jpg`。检查：空帧、双重曝光、跳变、元素同时动（twinning）、匀速机械运动。
5. **版式检查**：`render.mjs --layout` 后 `python3 $AVS/scripts/validate/layout_check.py <p>`，修到 V1/V2/V3 全过。
6. **整片**：`bash $AVS/scripts/render/build.sh <p> --agent=<你的名字>`。它依次做：规格校验 → 联系表 → 关键帧+版式 → 音频（synth 或素材文件）→ 帧渲染+编码 → 确定性 → QA 报告。帧渲染可续跑；代码/分镜变化后旧帧自动作废（指纹）。
7. **交给审片**：调用 video-quality-reviewer（或把 `out/` 交给另一个 Agent/人）。按它返回的问题清单修改，回到第 3 步。
8. 运动模糊（可选）：`--blur=3` 每帧 3 个子帧平均；渲染时间约 ×3，草稿阶段不要开。

## 输出
- `<p>/out/<task_id>.mp4`（H.264 yuv420p，faststart，AAC 48 kHz，-14 LUFS）
- `<p>/out/contact_sheet.jpg`、`out/keyframes/*.png`、`out/layout.json`、`out/determinism.json`
- `<p>/out/qa_report.md|json`
- 新组件代码 + README 中的参数文档

## 失败处理
| 现象 | 原因 / 处理 |
|---|---|
| `player failed to boot` | 读报错堆栈；常见：storyboard 的 `style` 路径错、组件未注册、JS 语法错 |
| T4 确定性失败 | 搜索 `Math.random|Date.now|performance.now|setTimeout|let .* = .*;` 等跨帧状态；改为 `hash()`/闭式函数 |
| 中文显示成方块 | 系统缺 CJK 字体；装 `fonts-noto-cjk` 或在 style 的 `font_stack` 放已安装字体 |
| 文字发糊 | 不要对文字做亚像素缩放动画以外的滤镜；JPEG 质量 `--quality=0.97`；必要时 `--crf=16` |
| 渲染太慢 | 减少每帧路径/渐变数量；`--workers` 设为 CPU 核数；草稿先出联系表不出整片 |
| `npm install` 不可用 | `setup.sh` 会尝试链接本机已有的 playwright-core；仍不行就报告，不要绕开网络策略 |
| V1 安全区失败 | 相机推近会放大，靠边元素留 ≥ 3% 余量；用 `fit:true` 让标题缩放而不是越界 |

## 验收标准
- [ ] `qa_report.json.verdict` 不是 `FAIL`；自动检查 P0 全过
- [ ] 每个接缝的帧条都看过，无空帧、无双重曝光
- [ ] 视频时长、分辨率、帧率与规格一致；有音频时响度在目标 ±2 LU
- [ ] 新组件有参数文档，且没有违反确定性规则

## Remotion 路线
团队要用 Remotion Studio 预览/协作时：`$AVS/components/remotion/` 提供 `CanvasComposition`，用 `useCurrentFrame()` 把同一套 engine + scenes 画到 canvas 上，无需重写场景。使用前确认 Remotion 许可（≤3 人公司/个人免费，更大公司需购买 Company License）。步骤见该目录 README。

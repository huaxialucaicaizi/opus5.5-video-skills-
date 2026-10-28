# 调研：Claude Opus 5.5「用代码拍视频」的方法

调研对象：[joeseesun/opus-video-prompts](https://github.com/joeseesun/opus-video-prompts)（18 份提示词、54 个案例，2026-09-22 至 09-25 公开内容），以及其中链接的、带源码的仓库。提示词版权归原作者，以下只做分析和改写，不转载原文。许可分类见 [`../SOURCES.md`](../SOURCES.md)。

## 1. 核心事实

模型不直接输出视频。它写代码把每一帧画出来，再用无头浏览器截帧、FFmpeg 合成。因此它擅长动态图形、线稿/手绘、科普讲解、产品发布片；不擅长写实真人画面（常见做法是调用外部视频模型，自己负责编排与剪辑）。

## 2. 九种技术路线（按可复用性重排）

| 路线 | 工具栈 | 代表案例 | 对本工具包的意义 |
|---|---|---|---|
| 单 HTML + Canvas/JS 逐帧 | 原生 JS、Canvas 2D、Playwright/Puppeteer、FFmpeg | 像素巫师（Majid Manzarpour）、UI 形态变换（zero）、Negroni 图解（Rory Flynn）、特殊相对论（チャエン） | **零依赖、最易跨 Agent** → 本包主路线，已实测 |
| Remotion（React） | React/TS、Remotion Studio/CLI | Danny Stuart 两支 App 宣传片、Chubby 的 AI 发展史（约 7400 行） | 团队协作和可视化预览好；许可有条件 → 次路线，提供包装组件 |
| p5.js + p5.brush 手绘 | p5.js、p5.brush、无头 Chrome | PDoomVideo MV、Opus 的一生 | 风格强，依赖 GPU（水彩填充在核显上每帧数秒）→ 可选风格 |
| HyperFrames | 单 index.html + HyperFrames 渲染 | Shotbase、Small Print | Apache-2.0，可作为替代渲染器 |
| Manim | Manim + Kokoro TTS | Deedy 的论文讲解 | 数学/公式类最佳 → 列为后续 |
| Python 逐像素线稿 | PIL + TTS + FFmpeg | 中华五千年、大气环流、口播转线稿（WY、Axton） | 无浏览器环境的兜底路线 → 列为后续 |
| Three.js/WebGL | Three.js、程序化模型与音效 | 奥斯特里茨战役、史前岛屿 | 3D 场景；软件 GL 下很慢（Austerlitz 约 1.7 s/帧） |
| 操控专业软件 | AE、Blender、Runway/Seedance API | SEIIIRU 的 AE 广告、Stefan 的 Blender 镜头 | 依赖付费软件/API，不在本包范围 |
| 剪辑已有素材 | video-use、FFmpeg | gregpr07 用 13 条素材剪发布片 | → `skills/footage-editing` |

## 3. 代表案例深挖

### 3.1 zero (@twoclipping) 的两份专业模板（UI 形态变换循环、高端极简产品片）
结构最值得学：提示词分成 **inputs / direction / structure / build / gotchas / start** 六块。
- **分镜设计**：按音乐小节写结构（120 BPM、每小节 2 秒），每个切点落在强拍；开工前先交"节拍网格上的分镜"。
- **动画实现**：所有样式在 `seek(t)` 里由时间计算；弹簧用闭式解（一个值多次改变目标 = 每次改变一个弹簧响应之和，因此仍是 t 的纯函数）；拖拽时值由光标位置决定，松手后从当前位置回弹。
- **渲染**：Playwright 每帧 3–4 个子帧，FFmpeg `tmix` 混合做真实运动模糊，60fps；音乐用 numpy 分析节拍，音效按**实测峰值**而非文件起点对齐；响度归一到 -14 LUFS。
- **QA**：正式渲染前每拍渲一帧（或抽 20+ 帧）检查拥挤/重叠/看不清；明确的禁用清单（粒子爆炸、RGB 分离、镜头光晕、霓虹辉光、弹跳缓动）。
- **坑**：被相机缩放的元素不要加 `will-change`（文字会糊）；`preserve-3d` 元素上设 opacity/filter 会被拍平；循环片首尾帧必须完全一致（含光标速度）。

### 3.2 PDoomVideo / ClaudeAnimationBase（John Heibel，后者 MIT）
- **分镜**：表格化 STORYBOARD（时间 / 歌词 / 镜头 / 出场方式），每镜"必须有事件发生"，转场有动机（chomp 到黑、iris、brush wipe）。
- **动画**：章节文件 IIFE 隔离；镜头函数 `fn(t, lt, dur)` 画整帧；禁止 `Math.random()`，用 `hash(i)` 做稳定随机，`jit()` 每秒 12 次重设种子，制造手绘"沸腾线"。
- **并行**：模型写 ANIMATION_GUIDE.md 给并行子代理做简报，规定共享文件只读、各改各的章节文件。
- **渲染**：`render.mjs` 支持 `--sheet`（联系表）、`--stills`、`--strip`（连续每帧）、`--crop`（局部放大）、`--frames`（多 worker、可续渲、原子写入）、`--encode`。
- **QA 方法（最系统）**：三级缩放自检——联系表看整体，帧条看动作，裁切看脸/接触点；把每个镜头拆成观众必须依次理解的 *reads*，每个 read 要有被发现和理解的时间，两个重要 read 不重叠。这直接启发了本包的分镜 Schema 中的 `reads` 字段。

### 3.3 Battle of Austerlitz（Winter，无许可，仅参考）
- **旁白驱动时间轴**：`script.js` 逐拍写旁白，所有镜头对旁白节拍计时；TTS 离线（Kokoro）生成并导出 timings.json。
- **声音从画面推导**：`events.js` 由画面事件生成音效提示（含声速 343 m/s 延迟、距离滤波、左右声像）。
- **渲染**：Chromium → FFmpeg，分块可续渲；字幕同时输出为 SRT 与内嵌轨道。

### 3.4 Danny Stuart 的 Remotion 宣传片
- 先分镜、后代码，之后可以只改单个镜头；描述质量时**给参考视频比堆形容词有效**；用镜头语言（dramatic cuts、orbiting camera）。
- 草稿阶段关运动模糊、半分辨率，或在 Remotion Studio 拖动预览。

### 3.5 中文科普线（WY、Axton）
- 一句话即可出片，但带 TTS/双语字幕的长片用时 26–29 分钟。
- 把 API Key 放 `.env`，并在 `.claude/settings.json` 用 `deny: ["Read(./.env)"]` 防止 Agent 读到密钥。
- 口播改线稿：按字幕切约 30 个镜头，保持原声/原字幕/时长不变 → 典型 footage-editing 任务。

## 4. 提炼出的可复用原则（本包据此实现）

| 原则 | 落地位置 |
|---|---|
| 先分镜、确认后再写代码 | `skills/video-planner`，`storyboard.schema.json` |
| 每帧是 `t` 的纯函数 | `components/html-canvas/engine.js`，`scripts/validate/check_determinism.mjs` |
| 观众 reads 时间表、一次只读一件事 | Schema 的 `reads` 字段 + `validate_spec.py` 重叠/最短时长检查 |
| 切点落拍 | Schema 的 `beat_grid`，`validate_spec.py` 检查切点偏离 |
| 禁用清单 | `templates/visual-style/style.default.json` 的 `banned` |
| 正式渲染前抽帧自检 | `render.mjs --sheet`，`skills/video-quality-reviewer` |
| 音频响度、黑帧、冻帧、技术参数 | `scripts/validate/probe_video.py` |
| 素材许可登记 | 任务规格的 `assets[].license` 必填 |

## 5. 局限与成本（来自原仓库汇总）
- 一句话短片几美元；几分钟 MV 单次会话可达约 200 美元或 Max 周额度的 7–10%。
- "一次成型"多数跑了两轮以上，预算按多轮迭代估。

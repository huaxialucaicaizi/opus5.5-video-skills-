# AI Video Skills

跨 Agent 的「用代码做视频」工具包：**分镜 → 确定性逐帧渲染 → MP4 → 自动 QA → 审片**。可被 Claude Code、Codex、Grok 等具备代码执行能力的 Agent 复用。

方法论来自对 [joeseesun/opus-video-prompts](https://github.com/joeseesun/opus-video-prompts) 收录案例的调研（见 [`docs/research.md`](docs/research.md)）；所有参考来源与许可分类见 [`SOURCES.md`](SOURCES.md)。本仓库**不包含**任何第三方提示词原文或无许可代码。

## 快速开始
```bash
bash scripts/setup.sh                                   # 检查/安装依赖：Node≥18、playwright-core、Chromium、FFmpeg(libx264)、Python3+numpy+jsonschema、CJK 字体
bash scripts/render/build.sh examples/ai-explainer-15s  # 15 s 示例：校验→联系表→关键帧→配乐→渲染→确定性→QA，约 45 s
open examples/ai-explainer-15s/out/ai-explainer-15s.mp4 # 成片；报告在 out/qa_report.md
bash scripts/validate/run_tests.sh                      # 自测（加 --quick 跳过整片渲染）
```
给 Agent 用：`bash scripts/install-skills.sh --agent=claude|codex|grok`，详见 [`docs/AGENT_INTEGRATION.md`](docs/AGENT_INTEGRATION.md)。

## 结构
```
skills/                         四个 Skill（Agent Skills 通用格式）
  video-planner/                需求 → task.json + storyboard.json（含观众 reads 时间表），校验后请求确认
  code-video-builder/           storyboard → 确定性场景代码 → 联系表/接缝自检 → MP4
  video-quality-reviewer/       自动检查 + 看关键帧 → review.json + QA 报告 + 修改清单
  footage-editing/              已有素材：裁切/拼接/画中画/字幕轨/混音/响度
spec/                           video-task.schema.json · ACCEPTANCE_CHECKLIST.md（P0/P1/P2，自动/人工）
templates/storyboard/           storyboard.schema.json
templates/visual-style/         style.default.json（9:16）· style.landscape.json（16:9）· VISUAL_GUIDE.md
components/html-canvas/         engine.js（纯函数引擎）· player.html（渲染契约）· scenes/（5 个参数化组件）
components/remotion/            Remotion 包装层（复用同一引擎，像素一致性已测）
scripts/render/                 render.mjs · build.sh · synth_music.py（原创配乐）· footage.py
scripts/validate/               validate_spec.py · layout_check.py · probe_video.py · check_determinism.mjs · qa_report.py · run_tests.sh · tests/
examples/ai-explainer-15s/      15 s 竖屏 AI 科普完整案例（task、storyboard、review、results/ 成片与报告）
examples/ai-explainer-landscape/ 同一分镜的 16:9 横屏版
evals/cross-agent/              7 个任务、夹具、评分器、校准、运行器、结果
adapters/                       claude-code（权限示例、CLAUDE.md 片段）· grok（无 Skill 机制时的粘贴版）
AGENTS.md · CLAUDE.md           Agent 指令入口
```

## 设计要点
- **分镜即数据**：storyboard 的每个场景 = 组件名 + 参数 + 观众 reads + 屏幕文字时间。渲染器直接读它，校验器在渲染前就能发现时间缝隙、阅读时间不足、未注册组件、许可不明等问题。
- **每帧是 t 的纯函数**：闭式弹簧、`hash()` 随机、无计时器/帧间状态 → 可并行、可续渲、可复现；`check_determinism.mjs` 在两个页面、打乱顺序、重复渲染后比对像素哈希。
- **从真实渲染结果做版式 QA**：所有文字经 `f.text()` 绘制并上报屏幕坐标，检查安全区（含相机推近后的实际位置）、最小字号、重叠、保留区域（画中画）。
- **审片必须看图**：自动检查之外，M1–M5 由审片者看联系表、接缝帧条、关键帧判定；没看图只能是 `NEEDS_REVIEW`。

## 测试结果（开发环境：2 核 / 7 GB，无 GPU）
- 两条示例成片（9:16 与 16:9，各 15 s）从代码到 MP4 一键构建约 45 s，QA 结论 PASS；自测 8/8 通过。
- 跨模型对照（Claude Code 无头模式，Haiku / Sonnet / Opus 5.5，共 18 次运行）：自动分全部达到上限，差异体现在成本、轮数与成片质量；测评还暴露了 6 个工具包问题，均已修复。
- Remotion 包装层与 React 渲染像素一致，但**未在真实 Remotion 中运行**；Codex、Grok **未实测**。

详见 [`docs/TEST_RESULTS.md`](docs/TEST_RESULTS.md)。

## 许可
原创代码与文档：MIT（[`LICENSE`](LICENSE)）。Remotion 为可选依赖，适用其自身许可。第三方来源与分类见 [`SOURCES.md`](SOURCES.md)。

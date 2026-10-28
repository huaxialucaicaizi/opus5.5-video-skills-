---
name: video-planner
description: Plan a short code-rendered video before any code is written. Turns a brief ("做一个 15 秒 AI 科普", "explainer about X", "promo for Y") into a validated task.json + storyboard.json with timed scenes, viewer reads, transitions and on-screen text, then asks for approval. Use when someone asks to make, plan, storyboard or script an animated explainer, motion-graphics, promo or kinetic-typography video. Not for editing existing footage (use footage-editing) or for writing render code (use code-video-builder).
---

# video-planner

先分镜，后代码。这个 Skill 只产出**计划**：`task.json`（要什么）+ `storyboard.json`（怎么拍）。两者都是机器可读的，渲染器直接读 storyboard，所以计划和成片不会走样。

工具包根目录（下文记作 `$AVS`）：本 Skill 目录里若有 `.avs-root` 文件，其内容就是 `$AVS`（由 `scripts/install-skills.sh` 写入）；否则为本 SKILL.md **真实路径**向上两级（`realpath SKILL.md` 后取 `../..`）。可用：`AVS=$(cat <skill_dir>/.avs-root 2>/dev/null || (cd "$(dirname "$(realpath <skill_dir>/SKILL.md)")/../.." && pwd))`。

## 触发条件
- 要求制作 / 策划 / 写分镜 / 写脚本：动画讲解、科普短片、动态图形、产品宣传片、文字动效视频。
- 已有分镜但需要改时长、改结构、加减场景。
- **不触发**：只改某个镜头的代码（→ code-video-builder）；剪辑已有素材（→ footage-editing）；写实真人视频（代码渲染做不了，告知用户需外部视频模型）。

## 输入
| 必需 | 可选（缺失时用默认值并在计划里写明） |
|---|---|
| 主题 / 要讲清楚的一件事 | 时长（默认 15 s）、画幅（默认 1080×1920 竖屏 30 fps）、平台、受众、语言（默认 zh-CN） |
| | 风格文件（默认 `$AVS/templates/visual-style/style.default.json`）、品牌色、参考视频/图、配乐（默认程序化合成）、必须避免的内容 |

只在**改错代价高**时提问（例如 >60 s、多个交付物、品牌规范不明确）。15–30 s 的科普，直接按默认值出计划，把假设写在 `task.json.notes`。

## 执行步骤
1. **建项目目录** `projects/<id>/`（或用户指定位置）。`id` 用小写短横线。
2. **写 `task.json`**，符合 `$AVS/spec/video-task.schema.json`。`goal` 必须是一句"看完能说出……"。所有外部素材登记进 `assets[]`（作者、许可、能否商用）；没有就留空数组。
3. **定结构**：先写 `logline`（问题 → 答案，或 想要 → 阻碍 → 结果）和 `motif`（贯穿首尾的视觉母题）。15 s 通常 4–5 个场景：hook → 定义 → 机制 → 机制推进 → 结论。
4. **逐场景写 reads**（最关键）：观众必须依次理解的事情，每条有起止时间。规则：
   - 每个 read ≥ `readability.min_read_s`（默认 0.6 s）；同一场景内 reads 不重叠。
   - 每个场景必须有 `event`：首帧和末帧之间发生了什么变化。"站着展示"不算。
   - 一个场景一个焦点。reads 放不下就加长场景或删 read，**不要挤**。
5. **配屏幕文字** `on_screen_text`：停留 ≥ `max(min_text_hold_s, 汉字数/zh_chars_per_s)`；竖屏一行 ≤ 12 字；标题不加句号；示意性数据必须在画面标注"示意"。
6. **选组件**：每个场景的 `component` 必须是已注册的组件（见 `$AVS/components/html-canvas/README.md` 的组件目录），`params` 按该组件文档填写。没有合适组件时，写 `"component": "<new-name>"` 并在 `visual` 里把画面描述清楚，交给 code-video-builder 新建。
7. **转场与卡点**：每个接缝（含开头、结尾）都要有转场；有 `bpm` 时切点落在拍上（120 BPM → 0.5 s 网格）。`audio_cues` 标出需要音效的瞬间。
8. **校验**：`python3 $AVS/scripts/validate/validate_spec.py <project>`，修到 0 失败（新组件未注册导致的 S6 失败允许保留，交接时说明）。
9. **出预览并请确认**：如果组件都已存在，运行 `node $AVS/scripts/render/render.mjs --project=<project> --sheet` 得到联系表，连同分镜摘要（每场景一行：时间 / 事件 / 文字）发给用户确认。无人值守时跳过确认，在交接说明里写明采用了哪些默认值。

## 输出
- `<project>/task.json`、`<project>/storyboard.json`（均通过 Schema）
- `<project>/out/contact_sheet.jpg`（若组件齐全）
- 给用户/下一个 Skill 的交接说明：场景表、假设、需要新建的组件、未决问题

## 失败处理
| 情况 | 处理 |
|---|---|
| `validate_spec.py` 报 S2/S3（reads 太短、文字停留不够） | 延长场景或删文字；不要靠加快动画解决 |
| 总时长放不下要讲的内容 | 删 key_messages，只留一个核心结论；告诉用户删了什么 |
| 素材许可不明 | 不要使用；改为代码生成，或请用户提供有许可的素材 |
| 用户要写实画面 | 说明代码渲染的边界；可规划"代码动画 + 外部视频模型素材"，素材须登记许可 |
| 没有 Python / jsonschema | 按 Schema 人工核对，并在交接说明标注"未经自动校验" |

## 验收标准
- [ ] `validate_spec.py` 0 个 P0 失败，P1 失败均有说明
- [ ] 每个场景有 `event`、≥1 个 read、`transition_in`
- [ ] 第一句 `goal` 能在 storyboard 的最后一个场景里找到对应结论
- [ ] 示意数据已标注；无未登记素材
- [ ] 用户确认过分镜（或交接说明写明了无人值守下的假设）

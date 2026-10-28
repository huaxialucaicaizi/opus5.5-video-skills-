# 视觉设计规范

机器可读版本：[`style.default.json`](style.default.json)（9:16 竖屏）、[`style.landscape.json`](style.landscape.json)（16:9 横屏，按 1920 宽设计）。渲染引擎和校验脚本都读它们；`validate_spec.py` 的 S7 会拦下与画幅不匹配的风格。本文件解释"为什么"，给人和 Agent 读。新风格：复制 JSON 改名，只改值不改键。

## 1. 一个画面只讲一件事
- 每个场景一个焦点动作；观众同一时刻只需要理解一个 read。
- 次要元素用 `text_muted` 或降低不透明度，不要和焦点抢。

## 2. 颜色
- 底色暗、正文暖白，**每个场景最多一个强调色**（`accent`）。`support`（蓝）用于数据和次要标记，**不算强调色**——例如概率条里非选中项用蓝、选中项用橙是允许的。
- 不用纯黑 `#000` / 纯白 `#FFF`。
- 正文对比度 ≥ 4.5:1（`readability.min_contrast_ratio`）。

## 3. 文字
- 字号按 1080 宽设计，渲染时按 `width / reference_width` 等比缩放。
- 竖屏中文一行 ≤ 12 字；标题不加句号。
- 最短停留：`max(min_text_hold_s, 字数 / zh_chars_per_s)`。校验脚本会算。
- 所有文字必须在 `safe_area` 内（9:16 平台的顶部标题栏、底部文案与右侧按钮会遮挡）。

## 4. 运动
- 默认 `easeOutCubic` 入场、`easeInCubic` 出场；弹簧最多 6% 过冲；**文字不用弹跳缓动**。
- 相机永不完全静止：每个场景有缓慢推/移（1–3% 缩放即可）。
- 入场错峰 `stagger_s`，避免所有元素同时动（"twinning"）。
- 切点尽量落拍（有 `bpm` 时由 `validate_spec.py` 检查）。

## 5. 转场
- 每个接缝都要有转场，开头和结尾也要（淡入/淡出也算）。
- 优先有叙事动机的转场：match cut、cut on action、元素变形（morph）。

## 6. 禁用清单
见 JSON 的 `banned`。这些是"模板味"的主要来源（总结自 zero @twoclipping 等作者公开模板中的禁用列表，改写，非原文）。

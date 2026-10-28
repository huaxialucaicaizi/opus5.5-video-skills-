# 成片验收清单

`auto` = 由 `scripts/validate/qa_report.py` 自动判定；`manual` = 审片者（人或 Agent 看关键帧）判定并写入报告的 `manual_checks`。**P0 任何一项失败 = 不可交付。**

| ID | 级别 | 方式 | 检查项 | 通过标准 |
|---|---|---|---|---|
| T1 | P0 | auto | 时长 | 与规格 `duration_s` 相差 ≤ 1 帧 + 0.05 s |
| T2 | P0 | auto | 分辨率 / 帧率 | 与规格完全一致 |
| T3 | P0 | auto | 编码 | H.264、yuv420p、`+faststart`；有音频时 AAC |
| T4 | P0 | auto | 确定性 | 同一 t 渲染两次像素哈希一致 |
| T5 | P1 | auto | 黑帧 | 除首尾 ≤ 0.5 s 的淡入淡出外，无 ≥ 0.3 s 的全黑段 |
| T6 | P1 | auto | 冻帧 | 无 ≥ 1.0 s 的完全静止段（"活着"原则） |
| A1 | P1 | auto | 响度 | 综合响度在目标 ±2 LU 内（默认 -14 LUFS），真峰值 ≤ -1 dBTP |
| S1 | P0 | auto | 分镜结构 | Schema 通过；场景首尾相接无缝隙；总长=规格时长 |
| S2 | P1 | auto | reads | 每个 read 在所属场景内、互不重叠、≥ `min_read_s` |
| S3 | P1 | auto | 阅读速度 | 每段文字停留 ≥ `max(min_text_hold_s, 字数/zh_chars_per_s)` |
| S4 | P2 | auto | 卡点 | 有 bpm 时场景切点距最近拍 ≤ 1 帧 |
| S5 | P1 | auto | 转场 | 每个场景都有 `transition_in`（`none` 需写 note 说明理由） |
| L1 | P0 | auto | 素材许可 | 所有 `assets` 有作者与许可，许可不为 `unknown` |
| V1 | P0 | auto | 安全区 | 渲染期上报的文字框全部在安全区内 |
| V2 | P1 | auto | 字号 | 所有文字 ≥ `min_px`（按分辨率缩放后） |
| V3 | P1 | auto | 文字重叠 | 同一帧内文字框互不重叠 |
| M1 | P0 | manual | 信息正确 | 科普内容无事实错误，数字/术语准确 |
| M2 | P1 | manual | 每镜有事件 | 首帧与末帧之间有可见变化，且与 `event` 描述一致 |
| M3 | P1 | manual | 焦点清晰 | 关键帧里一眼能看出该看哪 |
| M4 | P1 | manual | 风格一致 | 未出现禁用清单中的效果；配色/字体全片一致 |
| M5 | P2 | manual | 首尾呼应 | 结尾回扣开头的母题 |

# QA 报告 · ai-explainer-landscape

**结论：PASS**　·　生成时间 2026-10-28T19:15:14+08:00　·　制作 Agent：claude-opus-5.5　·　审片：claude-opus-5.5 (same session as the builder — not an independent review)

| 项 | 值 |
|---|---|
| 文件 | `out/ai-explainer-landscape.mp4` |
| 时长 / 分辨率 / 帧率 | 15.0 s / 1920×1080 / 30.0 fps |
| 体积 / 码率 | 3.21 MB / 1714 kbps |
| 自动检查 | 通过 24 · 失败 0（P0 0） · 警告 0 · 跳过 1 |
| 人工检查待办 | 0 |

## 分镜与规格

| 状态 | 级别 | ID | 检查 | 说明 |
|---|---|---|---|---|
| ✅ | P0 | S1.schema | storyboard matches schema |  |
| ✅ | P0 | S1.task | task.json matches schema |  |
| ✅ | P0 | S1.match | storyboard format matches task |  |
| ✅ | P0 | S1.contiguous | scenes are contiguous and cover the duration |  |
| ✅ | P1 | S1.scene_len | every scene ≥ 1.0 s |  |
| ✅ | P0 | S1.ids | scene ids unique |  |
| ✅ | P1 | S2.reads | reads inside scene, ≥0.6s, non-overlapping |  |
| ✅ | P1 | S3.reading | every on-screen text is held long enough to read |  |
| ✅ | P2 | S4.beats | scene cuts land on the beat grid |  |
| ✅ | P1 | S5.transitions | every seam (incl. open/close) has a transition |  |
| ✅ | P0 | S6.components | all scene components are registered |  |
| ✅ | P0 | S7.style_fit | style 'explainer-dark-landscape' fits 1920x1080 |  |
| ✅ | P0 | L1.licences | every asset has author + known licence |  |

## 版式（渲染期文字框）

| 状态 | 级别 | ID | 检查 | 说明 |
|---|---|---|---|---|
| ✅ | P0 | V1.safe_area | text inside safe area (126/150 settled samples) |  |
| ✅ | P1 | V2.min_px | font size ≥ 28px |  |
| ➖ | P0 | V4.reserved | text stays out of reserved regions | none declared |
| ✅ | P1 | V3.overlap | no overlapping text boxes |  |
| ✅ | P1 | V5.contained | text stays inside its container (123 samples declare containers) |  |

## 成片技术参数

| 状态 | 级别 | ID | 检查 | 说明 |
|---|---|---|---|---|
| ✅ | P0 | T1.duration | duration 15.000s (expected 15s) |  |
| ✅ | P0 | T2.format | 1920x1080 @30fps (expected 1920x1080 @30) |  |
| ✅ | P0 | T3.codec | H.264 yuv420p, faststart, AAC audio |  |
| ✅ | P1 | T5.black | no black segments ≥0.3s (except head/tail fades) |  |
| ✅ | P1 | T6.frozen | no frozen segments ≥1.0s |  |
| ✅ | P1 | A1.loudness | integrated -14.0 LUFS (target -14±2), true peak -1.5 dBTP (≤ -1) |  |

## 确定性

| 状态 | 级别 | ID | 检查 | 说明 |
|---|---|---|---|---|
| ✅ | P0 | T4.determinism | same t → identical pixels (8 times × 3 renders, 2 pages) |  |

## 人工 / 审片 Agent

| 状态 | 级别 | ID | 检查 | 说明 |
|---|---|---|---|---|
| ✅ | P0 | M1 | 信息正确：无事实错误，示意数据已标注 | 与竖屏版内容相同；示意数据均有标注。 |
| ✅ | P1 | M2 | 每镜有事件：首末帧有可见变化且与 event 一致 | 5 个场景都有可见事件。 |
| ✅ | P1 | M3 | 焦点清晰：关键帧里一眼看出该看哪 | s3 横屏改为左右分栏，概率条占满右栏高度，可读性正常。其余场景在 16:9 中偏居中、留白较多，但焦点清楚。 |
| ✅ | P1 | M4 | 风格一致：无禁用效果，配色字体一致 | 与竖屏版同一配色与字体；无禁用效果。 |
| ✅ | P2 | M5 | 首尾呼应：结尾回扣开头母题 | 结尾回扣「说话」。 |

## 联系表

![contact sheet](contact_sheet.jpg)

## 关键帧

| t (s) | 场景 | 文件 |
|---|---|---|
| 0.17 | s1_hook | `t0_17.png` |
| 1.27 | s1_hook | `t1_27.png` |
| 2.37 | s1_hook | `t2_37.png` |
| 2.67 | s2_tokens | `t2_67.png` |
| 4.00 | s2_tokens | `t4_00.png` |
| 5.37 | s2_tokens | `t5_37.png` |
| 5.67 | s3_probs | `t5_67.png` |
| 7.50 | s3_probs | `t7_50.png` |
| 8.20 | s3_probs | `t8_20.png` |
| 9.37 | s3_probs | `t9_37.png` |
| 9.67 | s4_loop | `t9_67.png` |
| 11.00 | s4_loop | `t11_00.png` |
| 12.37 | s4_loop | `t12_37.png` |
| 12.67 | s5_takeaway | `t12_67.png` |
| 13.77 | s5_takeaway | `t13_77.png` |
| 14.87 | s5_takeaway | `t14_87.png` |

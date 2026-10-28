`sparkle-title.js` 现在是确定性的：`check_determinism.mjs --project=projects/e5-sparkle` 通过（同一时刻渲染 3 次、8 个时刻、2 个页面，像素都一致）。MP4 已渲染，QA 报告结论是 `PASS_WITH_WARNINGS`。

**不稳定的原因有三处：**
- 星点用 `Math.random()` 生成。
- 闪烁相位用 `Date.now()`。
- 星点的 `y` 每帧累减，状态带到下一帧。

**修复方式：**
- 星点的位置和大小改用引擎自带的 `hash()`，按星点序号取值。
- 闪烁和漂移都改成由场景内时间 `lt` 计算。
- 漂移速度是 12·u/秒，等于原来 30fps 下每帧 0.4·u，视觉速度没变。
- 星点数量、颜色、闪烁频率和标题入场动画都保持原样。

**手动检查（我看了 `out/contact_sheet.jpg` 和 `keyframes/t3_00.png`，据此写了 `projects/e5-sparkle/review.json`）：**
- M1–M4 通过：开头近乎空白，3 秒时标题和副标题已升起、星点可见，白色标题居中，星点不抢焦点。
- M5 记为警告：只有一个场景，结尾标题淡出、星点仍在，呼应了开头的星点，但没有专门的收束画面。

**文件位置：**
- MP4：`projects/e5-sparkle/out/e5-sparkle.mp4`
- QA 报告：`projects/e5-sparkle/out/qa_report.md` 和 `qa_report.json`

我没有跟原版渲染的帧逐帧对比，因为原版本身每次都不同，没有可比的基准。
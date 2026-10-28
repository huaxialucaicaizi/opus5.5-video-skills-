场景已修好，确定性检查通过，MP4 和 QA 报告也已生成。但 QA 里还有一项 P1 失败没有解决（见下）。

**修复内容**

文件：`/home/claude/ai-video-skills/evals/cross-agent/runs/claude-claude-haiku-5-5-E5-20261028-182357/workspace/components/html-canvas/scenes/sparkle-title.js`

原来的不确定性来自三处，都已改成 `t` 的纯函数：
- 星点位置和大小：`Math.random()` 改为 `hash('sp:x:i')` 等稳定哈希。
- 闪烁：`Date.now()` 改为帧时间 `t`。
- 漂移：每帧修改 `s.y` 的状态，改为 `y = wrap(y0 − 12·u·t)`。

视觉上保留了 60 颗星、同样的闪烁频率、同样的漂移速度（原来每帧 0.4u，30 fps 下约等于每秒 12u），以及标题和副标题的入场动画。一处小改动：星点漂出顶部后会从底部绕回来，原来则是消失。6 秒内只有最靠上的几颗星会受影响。我没有参考 `evals/cross-agent/fixtures/golden/` 里的答案文件，修复是按引擎契约写的。

**验证**
- `check_determinism.mjs --project=projects/e5-sparkle`：从失败变为通过。
- `build.sh --agent=claude` 完整跑通：spec 12/12，版式 3 项通过，响度 −14.0 LUFS，确定性通过。
- 我看了 `contact_sheet.jpg` 和 0.6 s 关键帧，标题入场、副标题出现、星点闪烁都正常。

**产出**
- MP4：`/home/claude/ai-video-skills/evals/cross-agent/runs/claude-claude-haiku-5-5-E5-20261028-182357/workspace/projects/e5-sparkle/out/e5-sparkle.mp4`（已作为文件发送给你）
- QA 报告：`/home/claude/ai-video-skills/evals/cross-agent/runs/claude-claude-haiku-5-5-E5-20261028-182357/workspace/projects/e5-sparkle/out/qa_report.md`
- 人工审片：`/home/claude/ai-video-skills/evals/cross-agent/runs/claude-claude-haiku-5-5-E5-20261028-182357/workspace/projects/e5-sparkle/review.json`，M1–M4 通过，M5 为 warn。M5 是 P2 项：这个视频只有一个镜头，没有单独的结尾回扣。

**未解决的问题：T6.frozen（P1，失败）**

`freezedetect` 报告 1.5 s 起有 4.2 s 冻结。原因是只有星点在动：相邻帧平均亮度差约 0.025%，低于检测器的 −60 dB 阈值。这种运动幅度与原来的效果一致，原版大概率也会触发。

报告的结论显示 PASS_WITH_WARNINGS，但它把这一项计为失败而非警告，所以“警告 0”的统计并不完整。要解决它，需要改变视觉效果，例如加大闪烁幅度或漂移速度，这与“保持原来视觉效果”相冲突。我没有擅自改动，请你决定：接受这个结果，还是调整星点的闪烁幅度。
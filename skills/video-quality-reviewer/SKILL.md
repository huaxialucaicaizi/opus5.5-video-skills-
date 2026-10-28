---
name: video-quality-reviewer
description: Review a rendered code-made video against its storyboard and the acceptance checklist. Runs the automatic checks (spec, layout, ffprobe, black/frozen frames, loudness, determinism), then actually looks at the contact sheet, seam strips and keyframes to judge accuracy, events, focus, style and ending, writes review.json and a QA report with a prioritised fix list. Use when asked to review, QA, check, critique or sign off a video or its frames.
---

# video-quality-reviewer

只审，不改代码。产出：`review.json`（人工项结论）+ `out/qa_report.md`（自动项 + 人工项合并）+ 按优先级排序的修改清单。

工具包根目录（下文记作 `$AVS`）：本 Skill 目录里若有 `.avs-root` 文件，其内容就是 `$AVS`（由 `scripts/install-skills.sh` 写入）；否则为本 SKILL.md **真实路径**向上两级（`realpath SKILL.md` 后取 `../..`）。可用：`AVS=$(cat <skill_dir>/.avs-root 2>/dev/null || (cd "$(dirname "$(realpath <skill_dir>/SKILL.md)")/../.." && pwd))`。

**独立性**：最好由没参与制作的 Agent 或人来审。同一个会话自审时，在 `review.json.reviewer` 里注明"same session as builder"。

## 触发条件
- "审一下 / 检查 / 验收 / QA / 这条片子行不行"
- code-video-builder 完成整片后
- 跨模型对照测试的评分环节（见 `$AVS/evals/cross-agent/`）

## 输入
- `<project>/` 目录：`storyboard.json`、`task.json`、`out/<task_id>.mp4`
- 若缺 `out/contact_sheet.jpg`、`out/keyframes/`、`out/layout.json`、`out/determinism.json`，按下面步骤生成
- 参照：`$AVS/spec/ACCEPTANCE_CHECKLIST.md`、风格文件的 `banned` 列表

## 执行步骤
1. **自动检查**（任何一项不能跑就记为 skip 并写原因，不要假装通过）：
   ```bash
   python3 $AVS/scripts/validate/validate_spec.py <p>
   node    $AVS/scripts/render/render.mjs --project=<p> --sheet --keyframes --layout
   python3 $AVS/scripts/validate/layout_check.py <p>
   python3 $AVS/scripts/validate/probe_video.py <p>/out/<task_id>.mp4 --project <p>
   node    $AVS/scripts/validate/check_determinism.mjs --project=<p>
   ```
2. **看联系表**：打开 `out/contact_sheet.jpg`。对照每个场景的 `event` 和 `reads`：首/中/末帧是否体现了事件？焦点是否一眼可见？
3. **看接缝**：对每个场景起点 `s`，渲染 `s-0.05, s+0.05, s+0.15, s+0.25`（`--sheet=... --outfile=out/review_seams.jpg`）。找：空帧、双重曝光、跳帧、元素突然出现。
4. **看成片本身**（不只看预览）：从 MP4 抽 4–6 帧（`ffmpeg -i x.mp4 -vf "select='eq(n,N1)+eq(n,N2)',scale=270:-1,tile=6x1" -frames:v 1 out/review_mp4.jpg`），确认编码后的画面与预览一致、文字清晰。
5. **逐项判定 M1–M5**（定义见验收清单）。M1 信息正确需要领域知识：对科普内容逐条核对说法；示意数据必须在画面上标注；不确定的说法写进 note，状态给 `warn`。
6. **写 `review.json`**：
   ```json
   {"reviewer": "<agent/人 + 是否独立>", "reviewed_at": "YYYY-MM-DD", "method": "<看了什么>",
    "checks": [{"id": "M1", "status": "pass|fail|warn", "note": "<具体到时间点和元素>", "evidence": ["out/keyframes/t5_37.png"]}]}
   ```
7. **出报告**：`python3 $AVS/scripts/validate/qa_report.py <p> --agent=<制作者>`。
8. **给修改清单**：按 P0 → P1 → P2 排，每条写"时间点 / 现象 / 建议改法 / 归属（planner 还是 builder）"。

## 输出
- `<p>/review.json`、`<p>/out/qa_report.md`、`<p>/out/qa_report.json`
- 回复里：结论（verdict）+ 不超过 10 条的修改清单

## 判定规则
- 任一 P0 失败 → `FAIL`，不可交付。
- 人工 P0/P1 有未审项 → `NEEDS_REVIEW`。
- 其余有警告 → `PASS_WITH_WARNINGS`；全绿 → `PASS`。
- **只看文件做判断**：没有打开图片就不能给 M2–M5 `pass`。

## 失败处理
| 情况 | 处理 |
|---|---|
| 无法打开图片（Agent 没有看图能力） | M2–M5 记为 `pending`，在回复中说明需要人或有视觉能力的 Agent 复核；自动项照常 |
| 没有浏览器，无法出联系表 | 用 FFmpeg 从 MP4 直接抽帧代替（步骤 4 的命令） |
| 视频与 storyboard 不符（场景数、时长不同） | 直接 S1/T1 失败，退回 builder |
| 发现事实错误 | M1 `fail`（P0），写清正确说法与来源 |

## 验收标准（对审片本身）
- [ ] 自动检查全部执行或注明 skip 原因
- [ ] 每个人工项都有具体证据（文件或时间点）
- [ ] 修改清单可执行（时间点 + 改法），不是泛泛的"更好看一点"

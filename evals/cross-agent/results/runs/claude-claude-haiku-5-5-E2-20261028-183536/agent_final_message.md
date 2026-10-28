The video is built and the QA report is at `PASS_WITH_WARNINGS`. The one warning is a simplification I chose to leave in.

**Outputs** (under `projects/e2-hallucination/`, which I created at the workspace root):
- Video: `/home/claude/ai-video-skills/evals/cross-agent/runs/claude-claude-haiku-5-5-E2-20261028-183536/workspace/projects/e2-hallucination/out/e2-hallucination.mp4`. It is 15.0 s, 1080×1920, 30 fps, H.264 with AAC at -14 LUFS.
- QA report: `.../projects/e2-hallucination/out/qa_report.md` (and `qa_report.json`).
- Spec and review: `task.json`, `storyboard.json`, `review.json` in the same folder.

**Structure** (5 scenes, cut on the beat grid):

| Time | Scene | Content |
|---|---|---|
| 0–2.5 s | Hook | "AI 为什么会一本正经地胡说？" |
| 2.5–5.5 s | Mechanism 1 | Probability bars pick the next word (a labelled, fictional example) |
| 5.5–9.0 s | Mechanism 2 | Words are appended one at a time, and the sentence gets more fluent |
| 9.0–12.5 s | Takeaway | "通顺，不等于真实" / "接得顺，不代表说得对" / term badge "AI 幻觉" |
| 12.5–15 s | Close | "人名、数字、出处都要核实" |

**Checks:** The spec validator passes 12/12. The layout check passes. All 22 automatic QA checks pass, covering T4 determinism and the loudness target. The manual checks M2–M5 pass with frame evidence. The self-test passes 8/8.

**Choices I made without asking:**
- Defaults: 15 s, 1080×1920, 30 fps, Douyin, no narration, synthesised music at 120 BPM.
- All probabilities and names are fictional and labelled "示意", and the sample sentence is labelled "示例句与概率均为虚构示意".
- I reused the existing components, with one backward-compatible change: `append-loop` gained an optional `note` param. I documented it in the component README. The example project's output is unaffected.

**Things to know:**
- **M1 is `warn`.** The visual shows the model always picking the highest-probability word. Real decoding often samples instead. This is a common simplification for a short explainer, but a later version could note it.
- **The review is not independent.** I built and reviewed the video in the same session, so `review.json` says so. A human or a different agent should look at it before publishing.
- **Nothing is committed or published.** The project is not attached to the "自媒体" Project's docs.
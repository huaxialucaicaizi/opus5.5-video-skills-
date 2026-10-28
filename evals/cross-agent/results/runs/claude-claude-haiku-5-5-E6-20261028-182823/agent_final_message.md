已生成 `projects/e6-pip/out/final.mp4`，原始三个输入文件没有改动（校验和前后一致）。

**做法**
- 主画面：broll.mp4（1080×1920 竖屏）。
- 画中画：talk.mp4 裁成中心正方形，缩放为宽度 32% 的圆形，放在右下角，底部留出 30% 高度，避开字幕区域。
- 声音：只用口播原声（AAC，单声道）。B-roll 本身没有音轨。
- 字幕：subs.srt 作为 mov_text 字幕轨嵌入，语言标记为 zho，可在播放器里开关，没有烧录进画面。
- 时长：以口播为准，6.4s。B-roll 原长 8s，已在合成时截到 6.4s。

**核对结果**
- 流信息：视频 1080×1920 H.264 30fps；音频 AAC；字幕轨 1 条（mov_text）。
- 视频流时长 6.37s，与 6.4s 相差不到一帧。
- 抽帧（1.5s、4.0s）：圆形画中画位置正确，字幕没有画在画面上。
- 音频可以完整解码。

**需要说明的几点**
- 我没有验证字幕文字在播放器里显示正常，只确认了字幕轨存在且语言标记正确。
- 没有运行 `probe_video.py` 或 `qa_report.py`，也没有生成完整的 contact sheet 审查；这一步只做了抽帧检查。
- 输入是 ffmpeg 生成的测试源，LICENSES.txt 写明无第三方许可，所以没有许可问题。
- 中间文件 `pip.mp4` 在 scratchpad 目录：`/tmp/claude-0/-home-claude-ai-video-skills-evals-cross-agent-runs-claude-claude-haiku-5-5-E6-20261028-182823-workspace/735f03d2-76cf-5c13-a6a6-4f0e5bf11689/scratchpad/pip.mp4`

未向 git 提交任何内容。
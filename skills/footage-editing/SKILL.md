---
name: footage-editing
description: Edit existing video footage with FFmpeg — probe, trim, concatenate, picture-in-picture (e.g. talking head shrunk to a corner circle over animated B-roll), burn or attach subtitles, replace or mix audio, export frames for code-drawn overlays, and normalise loudness. Keeps original audio, subtitles and timing unless told otherwise, and records the licence of every input. Use when the user supplies .mp4/.mov clips to cut, combine, overlay or re-format.
---

# footage-editing

处理**已有素材**。代码生成的画面（B-roll、字幕条、标题卡）由 code-video-builder 渲染成 MP4 后，在这里与真实素材合成。

工具包根目录（下文记作 `$AVS`）：本 Skill 目录里若有 `.avs-root` 文件，其内容就是 `$AVS`（由 `scripts/install-skills.sh` 写入）；否则为本 SKILL.md **真实路径**向上两级（`realpath SKILL.md` 后取 `../..`）。可用：`AVS=$(cat <skill_dir>/.avs-root 2>/dev/null || (cd "$(dirname "$(realpath <skill_dir>/SKILL.md)")/../.." && pwd))`。

所有操作封装在 `$AVS/scripts/render/footage.py`（只依赖 FFmpeg/ffprobe）。

## 触发条件
- 用户给了视频文件，要剪、拼、叠画中画、加字幕、换配乐、改画幅（横转竖）。
- "把口播缩成右下角圆形，主画面换成动画"这类合成任务。

## 输入
- 素材文件（只读：**永远不改原文件**，结果写到新文件）
- 每个素材的来源与许可（自有 / 授权 / 未知）。未知许可的素材只能用于本地草稿，交付前必须确认。
- 目标：时长、画幅、是否保留原声 / 原字幕

## 执行步骤
1. **登记与探测**：`python3 $AVS/scripts/render/footage.py probe <file>`，记录分辨率、帧率、时长、音轨、字幕轨。素材写入 `task.json.assets[]`。
2. **定剪辑表**：在 `<project>/edl.json` 写清每段 `{src, in, out}`、叠加层、字幕；先给用户看（文字表即可）。
3. **执行**（按需组合）：
   ```bash
   F=$AVS/scripts/render/footage.py
   python3 $F trim   in.mp4 --start 3.2 --end 9.8 -o a.mp4           # 精确裁切（重编码，帧精确）
   python3 $F concat a.mp4 b.mp4 c.mp4 -o joined.mp4                  # 拼接（自动统一分辨率/帧率/音频）
   python3 $F pip    broll.mp4 talk.mp4 -o out.mp4 --corner br --size 0.32 --circle --audio fg   # 画中画
   python3 $F subs   out.mp4 subs.srt -o out_sub.mp4 [--burn]          # 内嵌字幕轨或烧录
   python3 $F audio  out.mp4 music.wav -o mixed.mp4 --mode mix --music-db -18   # 换/混音轨
   python3 $F frames in.mp4 --fps 30 -o frames/                        # 导出帧，供代码逐帧描绘
   python3 $F loudnorm in.mp4 -o norm.mp4 --lufs -14
   ```
   - **代码 B-roll + 画中画**：先算出画中画会占的区域 `python3 $F pip-region 1080x1920 --corner br`，把输出加进 B-roll 项目 storyboard 的 `reserved_regions`，再让 code-video-builder 渲染。`layout_check.py` 的 V4 会保证没有文字被画中画挡住。默认画中画位置（`--bottom-safe 0.30`）已避开底部字幕带。
4. **核对**：`python3 $AVS/scripts/validate/probe_video.py <out.mp4>`；用 ffmpeg 抽帧看合成位置（画中画不挡字幕、不出安全区）。
5. **保持不变的东西要验证**：要求"原声、原字幕、时长不变"时，比较输入输出的时长（差 ≤ 1 帧）和音轨。

## 输出
- 新的 MP4（原文件不动）、`edl.json`、素材许可登记、probe 结果

## 失败处理
| 情况 | 处理 |
|---|---|
| 可变帧率（VFR）素材 | `trim/concat` 会统一为恒定帧率；在报告中注明 |
| 拼接素材分辨率/帧率不同 | `concat` 自动缩放+补边到第一段的规格，或用 `--size WxH --fps N` 指定 |
| 字幕编码乱码 | 先转为 UTF-8 的 .srt；烧录时用 `--font "Noto Sans CJK SC"` |
| 素材许可未知 | 不交付；告诉用户需要哪份授权，或用代码生成画面替代 |

## 验收标准
- [ ] 原文件未被修改
- [ ] 输出通过 `probe_video.py` 的 T3（编码）与 T5/T6（黑帧/冻帧）
- [ ] 用户要求保持不变的属性（时长/原声/字幕）已比对验证
- [ ] 每个输入素材都有许可记录

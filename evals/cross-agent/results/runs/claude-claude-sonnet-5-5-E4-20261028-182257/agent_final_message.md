`python3 scripts/validate/validate_spec.py projects/e4-broken` 现在是 12 项全过,0 失败,0 警告。5 个场景都还在,总时长 15 秒、1080×1920、30fps 都没变。我没有渲染视频。

改动都在 `projects/e4-broken/` 的 `storyboard.json` 和 `task.json` 里:

- **场景衔接:** `s3_probs` 的开始时间从 5.8 改成 5.5,和 `s2_tokens` 的结束对上。这也让它落在 120 BPM 的拍点上,节拍警告随之消失。
- **组件名:** `s3_probs` 的组件 `fancy-bars` 没有注册,我改成了已注册的 `prob-bars`。它的参数本来就是按 `prob-bars` 写的,所以没动参数。
- **阅读时长:** `s2_tokens` 里「它被切成了几块」那条阅读提示只有 0.3 秒,我把它延长到 0.65 秒,后一条从 3.9 秒开始,不重叠。
- **屏幕文字:** `s4_loop` 的「一遍又一遍」只显示 0.5 秒,不够读完。我把它的开始时间提前到 10.7 秒,显示 1.8 秒。渲染代码里这个标签本来就在这个时间点出现(`append-loop.js` 里是第一步起点加 1.5 个步长),所以storyboard 和实际画面是一致的。
- **结尾转场:** 最后一个场景 `s5_takeaway` 的 `transition_out` 从 `none` 改成 0.4 秒的 `fade`。
- **背景音乐:** `bgm` 的许可是 unknown,而且 `assets/bgm.mp3` 文件也不存在,所以没有使用。我把 `task.json` 的音乐改成程序合成(`synth`,120 BPM),并清空 `assets`。这和参考示例 `ai-explainer-15s` 的做法一样,`notes` 里也本来就写着声音由 `synth_music.py` 合成。

JSON 是用脚本重新写出的,所以格式会和原文件略有不同,内容只改了上面这些。
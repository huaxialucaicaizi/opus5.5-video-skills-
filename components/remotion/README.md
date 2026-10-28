# components/remotion

Remotion 包装层：用 `useCurrentFrame()` 驱动**同一套** `components/html-canvas` 引擎和场景，所以一份 storyboard 在 HTML-Canvas 路线和 Remotion 路线上画出同样的像素。

## 许可（先读）
Remotion 使用 [Remotion License](https://www.remotion.dev/docs/license)（源码可见，非 OSI）：个人、≤3 名员工的营利组织、非营利组织可免费使用；更大规模的营利组织需要购买 Company License。本目录只包含我们自己写的包装代码，不包含 Remotion 源码；依赖由你自行安装。

## 用法
```bash
cd components/remotion
npm install                                  # remotion, @remotion/cli, react, react-dom
mkdir -p public && cp ../../examples/ai-explainer-15s/out/audio.wav public/   # 可选：配乐，然后在 Root.tsx 的 defaultProps 里打开 audio
npm run studio                               # Remotion Studio 预览、拖动时间轴
npm run render                               # 输出 out/ai-explainer-15s.mp4
```
新增视频：在 `src/Root.tsx` 里 import 新的 storyboard，再加一个 `<Composition>`。

## 验证状态（如实说明）
| 项 | 状态 |
|---|---|
| 包装组件 + 真实 React 19，在 Chromium 中逐帧对比 HTML 播放器 | ✅ 5/5 帧像素完全一致（`npm run smoke` / `node test/smoke.mjs`） |
| 在真实 Remotion（Studio / `remotion render`）中运行 | ⚠️ **未验证**：开发环境的 npm 仓库被网络策略拦截，无法安装 Remotion。首次使用请先跑 `npm run render`，并用 `scripts/validate/probe_video.py` 检查输出 |

`test/fake-remotion.js` 只模拟了本组件用到的 6 个 API（`useCurrentFrame`、`useVideoConfig`、`delayRender`、`continueRender`、`staticFile`、`AbsoluteFill`），仅供测试。

## 实现要点
- `delayRender()` 一直持有到**字体加载完成并画完第一帧**，否则 Remotion 可能截到字体回退的帧。
- 画在 `useLayoutEffect` 中同步完成，Remotion 截图前帧已就绪。
- 构图尺寸必须等于 storyboard 的 `width/height`，否则抛错（防止静默缩放导致安全区计算失真）。

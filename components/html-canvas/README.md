# components/html-canvas

零依赖的确定性 2D 视频引擎（Canvas 2D）。HTML 播放器和 Remotion 包装层共用它。

```
engine.js          数学/缓动/闭式弹簧/hash、文字排版（中文逐字换行、标点避头）、帧 API、composition（背景+转场）
player.html        浏览器端：读取 ?project=<dir> 的 storyboard.json，暴露 window.__video 给渲染/校验脚本
scenes/index.js    组件注册表（storyboard 的 component 名 → 函数）
scenes/*.js        可复用场景组件
```

## 渲染契约 `window.__video`
| 成员 | 说明 |
|---|---|
| `ready` / `error` | 字体加载完、composition 构建完后 `ready=true`；失败时 `error` 为堆栈 |
| `meta` | `{width, height, fps, duration, frames}` |
| `frame(t, type, q)` | 画 t 时刻并返回 dataURL |
| `frameBlur(t, n, type, q)` | n 个子帧平均（180° 快门）的运动模糊帧 |
| `layout(t)` | t 时刻所有文字框 `[{id, text, role, scene, x, y, w, h, px, alpha, layer}]`，屏幕坐标 |
| `sceneAt(t)` / `inTransition(t)` | 当前场景 id / 是否处于转场中 |
| `sheet(times, cols, w)` | 联系表 dataURL |

预览：`python3 -m http.server` 在仓库根目录启动后打开 `/components/html-canvas/player.html?project=examples/ai-explainer-15s`。

## 写场景组件
```js
// scenes/my-scene.js
import { ease, seg, springTo } from '../engine.js';
import { chip, stepCaption, rise } from './_ui.js';
export default function myScene(f, p) {       // f = 帧 API, p = storyboard 里的 params
  f.camera({ push: 0.03 });                    // 相机永不静止
  const r = rise(f, 0.2, 30);                  // 0.2 s 时开始上升入场
  f.text(p.title, f.W / 2, f.H * 0.45 + r.dy, { role: 'headline', align: 'center', alpha: r.a * f.exit, maxWidth: f.safe.w, fit: true });
}
```
然后在 `scenes/index.js` 注册。帧 API `f`：`ctx, t, lt（场景内时间）, dur, W, H, u（按风格 reference_width 的缩放）, style, pal, safe{ x,y,w,h }, exit, bpm, text(), box(), measure(), font(), camera(), env()`。

**方框里有字时**（卡片、流程节点、标签）：先 `const id = f.box('my:box', x, y, w, h, alpha)`，再 `f.text(str, ..., { parent: id })`。这样 V5 能检查文字是否溢出方框；`chip()` 已自动这样做。

**规则**：只从 `t`/`lt` 计算；随机用 `hash()`；文字只用 `f.text()`；不要自己做退场淡出（用 `f.exit`）；不画背景；**靠近安全区边缘的内容留 ≥ 3% 余量**（相机推近会放大到中心的距离）；需要支持横屏时按 `W > H` 切换布局（参考 `prob-bars`）。

## 组件目录（params）
| 组件 | 用途 | params |
|---|---|---|
| `kinetic-title` | 开场标题：标签 + 1–3 行遮罩上升 + 高亮词下划线 + 光标 | `kicker?`, `lines: string[]`, `highlight?: {line, text}`, `cursor?: bool`, `sub?` |
| `token-split` | 一句话裂成若干块（token/词/步骤），下方可出编号 | `caption`, `tokens: string[]`, `ids?: string[]`, `splitAt?=0.9`, `idsAt?=1.7`, `note?` |
| `prob-bars` | 上下文 + 问题 + 横向概率条，选中最高项填入问号（横屏自动左右分栏） | `caption`, `context: string[]`, `question`, `options: [{label, p}]`, `pick`, `pickAt?=2.6`, `note?` |
| `append-loop` | 自回归/迭代：一行块不断追加，每步先问号再落下 | `caption`, `start: string[]`, `steps: [{token, p}]`, `stepDur?=0.62`, `firstAt?=0.5`, `loopLabel?` |
| `takeaway` | 结论卡：回顾行 + 结论 + 副句 + 术语徽章 | `recap?: string[]`, `kicker?`, `headline`, `sub?`, `term?`, `termAt?=1.2` |

时间参数都是**场景内时间**（秒）。

## 转场（storyboard 的 `transition_in.type`）
`fade`（经背景色分段淡出淡入）、`push`（旧场景上移淡出 → 新场景自下进入，分段，不重叠）、`wipe`（强调色擦除线）、`iris`（圆形展开）、`cut-on-action` / `smash-cut` / `none`（硬切）。`morph` / `match-cut` / `whip` 目前按 `fade` 处理——真正的形变/匹配剪辑需要在组件里自己做。最后一个场景的 `transition_out: fade` 淡到背景色。

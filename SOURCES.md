# 来源与许可（Provenance & Licensing）

核查日期：2026-10-28。方法：浅克隆各仓库，检查根目录 `LICENSE*` 文件与 `package.json` 的 `license` 字段；Remotion 许可读取 npm 包内 `LICENSE.md`。**本工具包不默认任何内容可再分发。**

## 分类原则

| 类别 | 含义 | 本仓库的处理 |
|---|---|---|
| **A. 可直接复用** | 有明确 OSI 许可（MIT / Apache-2.0 等） | 可复制/改编，须保留版权声明与许可文本 |
| **B. 需适配 / 有条件使用** | 可作为依赖使用，但许可附带条件，或需要用户自行安装 | 只写接入代码，不 vendored，不打包其源码 |
| **C. 仅供参考** | 无许可文件、许可不明确、或为他人创作的提示词 | 只链接原文、记录作者；方法论用**自己的话**重写，不复制原文 |

## 逐项核查

| 来源 | 作者 | 许可核查结果 | 类别 | 本仓库如何使用 |
|---|---|---|---|---|
| [joeseesun/opus-video-prompts](https://github.com/joeseesun/opus-video-prompts) | 向阳乔木 (joeseesun)，整理 2026-09-27 | **无 LICENSE 文件**；README 声明"所有提示词和视频作品的版权归原作者所有，本仓库只做索引" | C | 作为调研入口；案例分析见 `docs/research.md`，不复制任何提示词原文 |
| 该仓库收录的 18 份提示词 | Deedy、Stephan Livera、WY、宝玉、Alex Prompter、Rory Flynn、Axton、Winter、Danny Stuart、zero (@twoclipping)、Majid Manzarpour、Vib3Coded 等 | 版权归各作者，未授予再分发许可 | C | 仅提炼写法原则（先分镜、禁用清单、`seek(t)` 等），每条附作者与原帖 |
| [JohnHeibel/ClaudeAnimationBase](https://github.com/JohnHeibel/ClaudeAnimationBase) | John Heibel | **MIT**（`LICENSE` 文件 + package.json 一致），© 2026 John Heibel | A（代码）| 本仓库**未复制其代码**；借鉴了"reads 时间表"、联系表/帧条/局部裁切三级自检、常见失败清单等方法。注意：其中的 Clawd 角色形象属于 Anthropic 的品牌形象，MIT 只覆盖代码，**不覆盖角色商标/形象**，商业内容不要使用 |
| [JohnHeibel/PDoomVideo](https://github.com/JohnHeibel/PDoomVideo) | John Heibel（内容由模型生成）| package.json 写 `"license": "ISC"`，但**无 LICENSE 文件**；歌曲来源作者自述不确定 | C | 仅参考其 `render.mjs` 的并行可续渲、`ANIMATION_GUIDE.md` 的子代理分工方式；**歌曲绝不可复用** |
| [WinterArc21/Battle-of-Austerlitz-Film](https://github.com/WinterArc21/Battle-of-Austerlitz-Film) | Winter | **无 LICENSE** | C | 仅参考：旁白驱动时间轴（script.js 节拍）、从画面推导音效事件、分块可续渲 |
| [opusvideo/awesome-claude-video](https://github.com/opusvideo/awesome-claude-video) | opusvideo | **无 LICENSE** | C | 仅参考 `IMPLEMENTATION_GUIDES.md` 的案例归纳 |
| [heygen-com/hyperframes](https://github.com/heygen-com/hyperframes) | HeyGen | **Apache-2.0** | A/B | 作为可选外部渲染器在 `docs/research.md` 中说明；未 vendored |
| [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | Remotion AG | **Remotion License（源码可见，非 OSI）**：个人、≤3 名员工的营利组织、非营利组织免费；更大规模的营利组织需购买 Company License；不得复制/修改 Remotion 用于出售或再许可衍生品 | B | `components/remotion/` 只包含**我们自己写的**包装组件，由使用者自行 `npm install remotion`，并自行判断是否需要公司许可 |
| [remotion-dev/skills](https://github.com/remotion-dev/remotion/tree/main/packages/skills)（Remotion 官方 Agent Skills） | Remotion | 位于 Remotion monorepo，适用 Remotion License | B | 推荐使用者另行安装，未复制 |
| p5.js / p5.brush | Processing Foundation / A. Campos Uribe | p5.js 为 LGPL-2.1；p5.brush 为 MIT（以各自仓库为准） | B | 本工具包未使用；列为可选风格扩展 |
| Noto Sans CJK | Google / Adobe | SIL OFL 1.1 | A | 渲染时使用系统已安装字体，**不打包字体文件** |
| 案例配乐 | 本仓库 `scripts/render/synth_music.py` 程序化生成 | 原创，随本仓库许可 | A | 示例 MP4 的全部声音来源 |

## 本仓库自己的许可

本仓库原创代码与文档建议以 MIT 发布（见 `LICENSE`）。上表 B/C 类内容均未包含在内，只有链接。

## 给使用者的规则

1. 引入任何新素材/代码前，在 `assets.manifest.json`（任务规格里的 `assets` 字段）登记：来源 URL、作者、许可、是否允许商用、是否允许修改。
2. 许可字段为空或为 `unknown` 的素材，`validate_spec.py` 会直接判失败。
3. 音乐与音效必须是：原创合成、自有版权，或许可明确允许商用的曲库（并保留许可凭证）。

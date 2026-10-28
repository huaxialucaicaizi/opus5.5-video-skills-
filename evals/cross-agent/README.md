# 跨 Agent / 跨模型对照测试集

目的：用**同一份工具包、同一组提示词**，比较不同 Agent（Claude Code、Codex、Grok…）和不同模型做代码视频的能力，并且结果可复现、可审计。

## 任务（`tasks.json`）
| ID | 类型 | 考什么 | 评分方式 |
|---|---|---|---|
| E1 | build · 基线 | 按流程复现 15 s AI 科普 | 规格 20 · 版式 15 · 成片 20 · 确定性 15 · 音频 5 · 任务 25 |
| E2 | build · 迁移 | 新主题（AI 幻觉），只用现有组件 | 同上 |
| E3 | build · 扩展 | 横屏 RAG 流程图，**必须新建组件** | 同上（任务分含"新组件已注册并被使用"） |
| E4 | repair | 修 6 处预埋的规格缺陷，不改内容 | 修复率 70 · 意图保留 30（乘修复率，不做事不得分） |
| E5 | determinism | 修非确定性组件（`Math.random`/`Date.now`/跨帧状态） | 确定性 40 · 禁用模式清除 15 · 成片 20 · QA 5 · 版式 10 · 规格 10 |
| E6 | footage | 画中画 + 可开关字幕轨，时长与口播一致 | 技术 40 · 需求 60（时长/画幅/音轨/字幕轨/原文件未改） |
| E7 | review | 找出 4 个预埋缺陷（概率和 121%、-24 LUFS、出安全区、阅读时间不足） | 召回 70 · 产物 30 |

任何 P0 失败总分封顶 40；篡改校验脚本/Schema/默认风格 → 0 分。

## 公平性设计
- **全新工作区**：每次运行复制工具包（不含 .git、历史输出），再由 `fixtures/setup.py` 布置初始状态。
- **评分不信任自述**：`score_run.py` 用**测评端**的校验器，对工作区代码重新采集版式、重新跑确定性，直接 probe 工作区的 MP4。
- **完整性闸门**：校验脚本、Schema、默认风格文件的哈希必须与测评端一致。
- **校准**：`calibrate.sh` 对每个任务比较"什么都不做"和"标准答案"的得分，确认评分能区分两者（结果见 `results/calibration.md`）。
- **无人值守**：提示词要求不提问；人工介入次数记为 0 以外时需在结果中注明。

## 运行
```bash
bash evals/cross-agent/calibrate.sh                                    # 先校准评分器
bash evals/cross-agent/run_agent.sh --agent=claude --task=E1           # Claude Code（默认模型）
bash evals/cross-agent/run_agent.sh --agent=claude --model=claude-opus-5-5 --task=E1
bash evals/cross-agent/run_agent.sh --agent=codex  --task=E1           # 需本机安装 Codex CLI；flag 以 `codex exec --help` 为准
GROK_CMD="<你的 Grok 无头命令>" bash evals/cross-agent/run_agent.sh --agent=grok --task=E1
bash evals/cross-agent/run_agent.sh --agent=manual --task=E1           # 任意 Agent：只准备工作区并打印提示词，跑完后手动评分
python3 evals/cross-agent/summarize.py                                 # 汇总到 results/summary.md、runs.csv
```
每次运行目录：`runs/<agent>-<model>-<task>-<时间>/`，含 `prompt.txt`、`agent_output.txt`、`score.json`、`run.json`（用时、成本、轮数、实际使用的模型）、`workspace/`。

## 人工盲评（可选，补充自动分）
自动分衡量"是否按规范交付"，**不衡量好不好看**。建议对 E1–E3 的成片做盲评：去掉文件名中的 Agent 信息，3 名评审各自按 `rubric.md` 打分，取中位数，写入 `results/blind_ratings.csv`。

## 已知局限
- E7 召回用关键词匹配，Agent 可能提到关键词但没有真正诊断出问题；对 `FIXES.md` 需人工抽查。
- E1/E2 的关键词覆盖只检查 storyboard 文本，无法判断讲解是否真正清楚。
- 单次运行方差大：每个格子建议 ≥3 次运行再比较均值。
- 本仓库当前只在 Claude Code 上实测（Codex、Grok 的 CLI 不在开发环境中）。

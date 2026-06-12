# Day 12 — Prompt Engineering 核心技巧：Zero/Few-shot、Chain of Thought

> **阶段**：Phase 2 · Prompt Engineering 与 LLM API 开发
> **主题**：Zero-shot vs Few-shot、示例选择、Chain of Thought（CoT）"让我们一步步想"为何有效、demonstration 设计
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：Prompt 就是发给模型的"请求体"。Zero-shot 是只带配置不带样例的裸请求，Few-shot 是顺手塞几条示例数据，CoT 是打开"打印中间日志"开关——结果不仅更准，还能让你看清它怎么推。三种都是"组装 prompt"，`practice.py` 会真连本地 ollama（qwen2.5:3b）各跑一次，对比真实回答。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器，无需安装）。三栏并排把 Zero-shot / Few-shot / CoT 的 prompt 拼装方式同屏对比：左两栏看示例条数怎么堆进上下文，右栏点一下"让我们一步步想"，CoT 的推理步骤会**逐步展开动画**，一步步推到最终答案。先玩出"加示例 / 加推理"的直觉，再读理论与跑代码。

---

## 📖 学习内容（约 25 分钟）

### 1. Zero-shot vs Few-shot：要不要塞示例

| | Zero-shot 零样本 | Few-shot 少样本 |
|---|---|---|
| 给不给示例 | 不给，直接问 | 先给 N 条「问→答」示范再问 |
| 后端类比 | 裸请求，只带配置 | 请求里附带几条 mock 数据 |
| 成本 | token 少、便宜 | 示例占上下文，更贵更慢 |
| 适合 | 简单/通用任务 | 要固定格式、要对齐口味、领域术语 |

一句话：**先 Zero-shot 试，不达标再加 Few-shot**。示例不是越多越好——2~5 条往往就够，多了只是涨成本。

### 2. Few-shot 示例怎么选（demonstration 设计）

示例（demonstration）质量 > 数量，三条原则：
- **多样**：覆盖不同情况，别全是同一类，否则模型只学会一个套路。
- **同构**：示例格式 = 你想要的输出格式。想要 JSON，示例就给 JSON；想要"只回数字"，示例就只回数字。模型是"照葫芦画瓢"。
- **难度贴近**：示例难度接近真题，太简单带不动，太偏会跑题。

格式别错：示例的"答"放进 assistant 回合，"问"放进 user 回合——这正是 `practice.py` 里 ★2 干的事。

### 3. CoT「让我们一步步想」为何有效

对多步算术/逻辑题，直接问容易蒙错；加一句"让我们一步步思考"，模型会**先写推理步骤再给答案**，准确率明显提升。原因：自回归模型逐 token 生成，写出中间步骤等于把推理"外化"成上下文，后面每一步都能基于前面已写出的步骤，相当于给思考腾出"草稿纸"。Zero-shot 也能用：题尾直接拼触发语即可（★3）。代价是输出变长、变贵。

### 4. 三者一句话总结

> **Zero-shot** 裸问 → 不够就 **Few-shot** 塞示例对齐格式 → 多步推理题就上 **CoT** 让它先想后答。三招按"成本由低到高"叠加用。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Chain-of-Thought 原论文**（Wei et al., 2022，CoT 的出处，必看）— https://arxiv.org/abs/2201.11903 — 看一眼"让我们一步步想"在 GSM8K 上准确率怎么跳起来。
2. **Anthropic Prompt Engineering 概览**（官方，对 Claude/claude-opus-4-8 最对口）— https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview — 重点看 multishot（few-shot）和 let-Claude-think 两节。
3. **Brown et al., 2020「Language Models are Few-Shot Learners」**（GPT-3，few-shot 概念出处）— https://arxiv.org/abs/2005.14165 — 理解"零样本/少样本"术语从哪来。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，同一道算术题分别组装成 Zero-shot / Few-shot / CoT 三种 prompt，**真连本地 ollama（qwen2.5:3b）** 各跑一次，打印三种真实回答做对比。完成 3 个 ★ 即可看清差异。

```bash
# 前置：本地装好 ollama 并拉模型（默认 qwen2.5:3b，跑在 http://localhost:11434）
ollama serve
ollama pull qwen2.5:3b

# 在项目根目录跑（环境用 uv 管理，仅用标准库 urllib 连 ollama）：
uv run day-12/practice.py
# 换模型：OLLAMA_MODEL=qwen2.5:7b uv run day-12/practice.py
```

预期：Zero-shot 容易答错或只回数字，Few-shot 对齐成"只回最终答案"，CoT 先逐步推理再给答案——同一模型、同一道题，三种 prompt 真实回答的差异就是今天的核心。

### 🎨 配合可视化

跑通后回到 `visualize.html`，把代码里 zero/few/cot 三个函数和页面三栏一一对上号，点 CoT 那栏看推理步骤逐步展开——这就是"让模型先想后答"的物理动作。

---

## 🤔 思考题（边做边想）

1. Few-shot 加到 5 条还不达标，再加到 10 条通常收益很小甚至变差，为什么？跟你给单测加 case 的边际收益像不像？
2. CoT 让输出变长、变贵，哪些任务值得（多步算术）、哪些不值得（情感分类）？怎么权衡？
3. 把 Few-shot 示例的输出格式从"只回数字"换成 JSON，模型会跟着变吗？这对你做 Structured Output（Day 15）有什么启发？

> 把答案记在 `notes.md`，明天 Day 13 我们上 Self-Consistency / ReAct，正是 CoT 的进阶。

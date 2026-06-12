# Day 36 — 🤖 Agent 概念与架构模式：ReAct / Plan-and-Execute / Reflection

> **阶段**：Phase 4 · AI Agent 开发（开篇 · Day 36）
> **主题**：什么是 Agent，凭什么比裸 prompt 强；三种主流架构模式 ReAct、Plan-and-Execute、Reflection 怎么选
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：前 35 天你学的 RAG/Prompt/API 都是"一问一答"的纯函数。Agent 是把它升级成一个 **while 循环 + 工具路由器 + 终止条件** 的有状态服务——LLM 当大脑，工具当胳膊，循环让它能"想一步、做一步、看结果、再纠错"。今天你会亲手写一个 ReAct loop，真调本机 ollama 调工具。

---

## 📖 学习内容（约 25 分钟）

### 0. 从"一问一答"到 Agent：循环让它长出胳膊
裸 LLM 是个纯函数：`answer = f(prompt)`，问一次答一次，不会算账、查不到私有数据、错了不会改。**Agent** 给它加四样东西，本质就是你天天写的服务结构：

| Agent 部件 | 后端类比 | 干什么 |
|---|---|---|
| LLM | CPU / 大脑 | 推理、决策"下一步做啥" |
| Tools 工具 | 路由表 + 函数 | calculator/search/API，把脏活外包给确定性代码 |
| Loop 循环 | `while` + 终止条件 | 多步反复，做不完不退出 |
| Memory 记忆 | 上下文/会话状态 | 把每步结果回灌，下一步能看到 |

一句话：**Agent = LLM + 工具 + 循环 + 记忆**。RAG 在这里降级成 Agent 的"一个工具"（search）。

### 1. ReAct：边想边做，每步一工具（今天动手写的）
ReAct = **Rea**soning + **Act**ing，交错进行。每轮模型只产出一步：
```
Thought:  我得算 23×47          ← 推理：下一步干啥
Action:   calculator(23*47)     ← 调一个工具
Observation: 1081               ← 拿到真实结果，回灌
Thought:  够了                  ← 再想
Final:    1081
```
后端视角：一个 `while` 循环，每轮调模型拿 `Action: tool(arg)`，路由到工具执行，把 `Observation` 塞回上下文喂下一轮，直到模型给 `Final` 或到达 MAX_STEPS。优点：错了下一轮就能纠；缺点：每步都调一次模型，慢、贵、可能绕路。**绝大多数生产 Agent 都是 ReAct 变体。**

### 2. Plan-and-Execute：先拆全计划，再逐步执行
ReAct 走一步看一步；Plan-and-Execute 先让模型 **一次性拆出完整步骤列表**，再用便宜方式逐步执行：
```
Plan: 1.查论文编号  2.取数字  3.乘以0  4.汇报
Execute: 步骤1→步骤2→步骤3→步骤4（不再每步都问大模型该干啥）
```
类比：ReAct 像走一步问一次路；Plan-and-Execute 像先做完 sprint 规划再照单施工。**省模型调用、整体可控、适合长任务**；代价是计划僵，中途环境变了不灵活（所以常加"重规划 replan"）。

### 3. Reflection：做完自评，不满意就重做
做一版 → 自己当审稿人挑毛病 → 按意见重做，循环到够好：`draft → critique → revise`。后端类比：CI 里的 lint + 重跑。**多花算力换质量**，适合写代码、写文案这类对一次成型要求高的任务。三者常组合：ReAct 跑主循环、出方案、Reflection 把关。

| 模式 | 何时用 | 调模型次数 | 代价 |
|---|---|---|---|
| ReAct | 默认；要中途纠错、调工具 | 每步一次（多） | 慢、可能绕路 |
| Plan-and-Execute | 步骤清晰的长任务 | 规划1次+执行少量 | 计划僵需 replan |
| Reflection | 质量优先（写码/文案） | 翻倍 | 慢、贵 |

### 4. 工具与终止条件：别让循环转飞
两条命脉：**工具注册表**（`{"calculator": fn, "search": fn}`，就是路由表，模型只决定调谁、传啥）；**终止条件**（命中 `Final` 或撞 `MAX_STEPS`）。没有 MAX_STEPS，小模型容易绕圈烧钱——和任何 `while` 一样，先把出口写好。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **ReAct 原论文**（今天的循环就出自这里）— https://arxiv.org/abs/2210.03629
2. **Lilian Weng — LLM Powered Autonomous Agents**（Agent 体系最佳综述）— https://lilianweng.github.io/posts/2023-06-23-agent/
3. **Reflexion 论文**（Reflection 模式的源头）— https://arxiv.org/abs/2303.11366
4. **Anthropic — Building Effective Agents**（生产 Agent 设计原则，含何时别上 Agent）— https://www.anthropic.com/research/building-effective-agents
5. **Ollama Chat API 文档**（练习用的 /api/chat）— https://github.com/ollama/ollama/blob/main/docs/api.md

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：手写一个 ReAct agent loop，带 calculator（真算）和 search（mock 知识库）两个工具。问题会触发 Thought→Action→Observation 多轮循环。先补 5 个 `★` 行，再对照文末答案。HTTP 只用 `urllib`，无第三方库、不依赖 LangChain。

```bash
ollama serve                          # 默认 http://localhost:11434
ollama pull qwen2.5:3b                # 默认模型
export OLLAMA_MODEL=qwen2.5:7b        # 可选：想更聪明就换 7b
uv run day-36/practice.py
```
预期：算术题走 `calculator`、概念题走 `search`，每题打印 step 1/2 的 Thought/Action/Observation，最后给 Final——三题都收敛即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击打开 `visualize.html`（纯浏览器、零依赖、深色 canvas）。把 ReAct 循环画成转圈：选个问题，逐帧亮起 Thought→Action→Observation→…→Final，看大脑、工具、记忆怎么轮转；右侧切到 Plan-and-Execute / Reflection 对比三种模式的形状差异。

---

## 🤔 思考题（边做边想）

1. ReAct 每步都调一次模型很慢。哪类任务改用 Plan-and-Execute 更划算？计划僵硬的风险怎么补（关键词：replan）？
2. 为什么必须有 `MAX_STEPS`？没有它，小模型会怎样烧钱？类比你写过的任何 `while` 循环的退出条件。
3. 把 search 工具换成 Day35 的 RAG 检索，整个 Agent 就成了"会查私有知识库的助手"。再加一个工具，你最想加哪个？它的 Observation 该长什么样？

> 把答案记在 `notes.md`。明天 Day 37 起把这个 ReAct loop 接上真实工具/RAG，搭出能干活的 Agent。

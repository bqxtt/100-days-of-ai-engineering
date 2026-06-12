# Day 55 — 🏗️ 实践日：Agent 系统回顾与优化（Phase 4 收官）

> **阶段**：Phase 4 · AI Agent（Day 55，收官实践日，回顾 Day36-54）
> **主题**：把 Phase 4 的零件——ReAct / 工具 / 记忆 / 多 Agent / MCP / 可观测 / 安全 / 评估 / 生产化——组装成一个相对完整的 Agent，作为毕业作品
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：Agent 不是黑魔法，是一个 **while 循环 + 几个函数 + 一份会话状态 + 一摞日志**。和你写的后台任务调度器（拉任务→执行→记结果→重试→出报表）同构——只不过"决定下一步做什么"从 if/else 换成了 LLM。今天把前 19 天的零件焊成整机，就毕业。

---

## 📖 学习内容（约 25 分钟）

### 0. Phase 4 知识地图：一个 Agent 的 9 个零件（Day36-54）
| 零件 | 中文 | 来自 | 后端类比 |
|---|---|---|---|
| ReAct loop | 推理-行动循环 | Day36 | 任务调度主循环 while |
| Tool | 工具 | Day40 | 注册的 handler / RPC |
| Memory | 记忆 | Day41 | 缓存 + 数据库 + 归档 |
| Multi-Agent | 多智能体 | Day44/52 | 微服务拆分 + 委托 |
| MCP | 模型上下文协议 | Day46-47 | 工具的"USB 标准"接口 |
| Observability | 可观测性 | Day48 | 日志 / trace / 监控 |
| Security | 安全 | Day49 | 输入校验 + 权限边界 |
| Eval | 评估 | Day50 | 单测 + 回归基准 |
| Production | 生产化 | Day54 | 容错 / 扩缩 / 成本 |
LangChain/LangGraph（Day37-39）是把这些零件标准化的框架；CrewAI/AutoGen（Day45）是多 Agent 的工厂。**你手写一遍，框架就不再是黑盒。**

### 1. ReAct 是 Agent 的骨架（reasoning + acting）
一个 while：模型**想**(Thought)→**做**(Action=调工具)→**看**(Observation=工具结果回填)→再想，直到给 Final。本质就是"让 LLM 在循环里反复决策"。护栏 `max_steps` 防它一直调工具不收手——和你给重试加最大次数一个道理。

### 2. 工具 + 安全：模型只"决定"，代码才"执行"
工具定义 = 名字+描述+入参 schema 交给模型；模型回 `tool_calls` 只是**说**要调谁，真正算的是你本地的函数（Day49 安全边界在此）。今天还学一招：**工具出错不要 raise，把错误当 Observation 返回**，模型能据此自纠——这是生产 Agent 鲁棒的关键。

### 3. 记忆 + trace：状态与可观测
`messages` 列表就是短期记忆（Day41）——工具结果回填后下一轮模型看得见。每步落一行 trace（Day48）= 最朴素可观测性，出错能复盘是哪步。

### 4. 评估：给 Agent 打分（Day50）
几个有标准答案的任务，跑完做包含式断言算命中率。没有评估，"优化"就是瞎调；有了分，才知道改完是好是坏——和后端回归测试一样。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic — Building Effective Agents**（少即是多：先一个循环+工具，别堆框架）— https://www.anthropic.com/research/building-effective-agents
2. **Lilian Weng — LLM Powered Autonomous Agents**（Agent=Planning+Memory+Tools 经典总览）— https://lilianweng.github.io/posts/2023-06-23-agent/
3. **ReAct 论文**（推理+行动交错的范式起点）— https://arxiv.org/abs/2210.03629
4. **Ollama API**（本机 chat + tool_calls 接口）— https://github.com/ollama/ollama/blob/main/docs/api.md

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**stdlib urllib + 真连 Ollama**：把 Phase 4 零件焊成一个毕业作品 Agent——ReAct 循环 + 3 个工具 + 短期记忆 + trace 日志 + 重试，真调模型多步完成任务，再跑评估打分。补 5 个 `★` 行再对答案。

```bash
ollama serve                         # 默认 http://localhost:11434
ollama pull qwen2.5:3b               # 生成 + tool_calls（约 1.9GB）
uv run day-55/practice.py
```
预期：多步任务 trace 逐步可见，评估 3/3 出 100% 分——即毕业达标。

### 🎨 可视化（先玩再读理论更直观）
双击 `visualize.html`（纯 canvas、深色 #0e1117、零依赖）。逐步看 ReAct 循环转：Thought→Action(调工具)→Observation 回填→再想，trace 一行行落账，工具出错走自纠分支——一台 Agent 整机怎么跑一目了然。

---

## 🤔 思考题（边做边想）

1. 小模型把工具结果"忘了"，下一步又重查——靠什么纠：加 trace 提示、缩短步数、还是换记忆策略？
2. 工具出错该 raise 还是返回错误字符串？两种做法对 Agent 鲁棒性各有什么影响？
3. 评估只测了 3 题就 100%，能说 Agent 好用吗？要可信，评估集还该补哪些维度（多步、对抗、成本）？

> 答案记到 `notes.md`。**Phase 4 收官！** 明天 Day 56 进 **Phase 5（模型微调）**：通用模型搞不定的场景，就该自己微调——从 LoRA 原理到端到端训练部署。

---

> 🎓 **Phase 4 毕业**：从 Day36 的 ReAct 概念到今天的整机，你手写过 loop/tool/memory/multi-agent/MCP/trace/安全/评估。框架不再是黑盒，下一步换模型本身。

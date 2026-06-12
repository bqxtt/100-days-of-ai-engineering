# Day 38 — 🕸️ LangGraph 入门：图状态机、节点与边、条件路由

> **阶段**：Phase 4 · Agent 与编排（Day36-50）
> **主题**：用「图（Graph）」组织 Agent —— 状态机式编排，State / Node / Edge / 条件路由（conditional edge）
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：你写过 RAG 链路就知道——链（chain）是直线流水线，一段接一段、走完就结束。但 Agent 要"想一步、查一步、不够再查一步"，这是**循环 + 分支**，直线表达不了。LangGraph 把编排建成一张**有向图**：节点（node）是函数、边（edge）是跳转、共享 State 是 dict——这就是你早写过一百遍的**状态机 / 工作流引擎（workflow engine）**，只不过这次状态里跑的是 LLM。

---

## 📖 学习内容（约 25 分钟）

### 0. 从链到图：为什么 Agent 需要"图"
Phase 3 的 RAG 是一条**链（chain）**：`检索 → 重排 → 生成`，单向走完即终。但 Agent 不一样——它要 `想 → 决定要不要调工具 → 调 → 看结果不够再想 → 再调`，这是**循环（loop）**与**分支（branch）**。链没有回边、没有岔路，表达不了。所以要升级成**图（graph）**：节点可以指回前面（循环），可以根据条件去不同下家（分支）。

> 一句话：**图 > 线性链**，因为图**可循环、可分支**，而链只能一条道走到黑。

### 1. 四个核心概念（对照后端状态机看）
| LangGraph | 是什么 | 后端类比 |
|---|---|---|
| **State**（状态） | 一个共享 dict，每个节点读它、改它 | 状态机的"当前上下文" / 请求 context |
| **Node**（节点） | 一个函数 `state -> state`，干一件事 | 状态机的一个 handler / 一个 task |
| **Edge**（边） | A 干完去 B 的固定跳转 | 工作流里写死的"下一步" |
| **Conditional Edge**（条件边） | 看 state 决定下一站去哪 | `switch(state)` 路由 / if-else 转移 |
| **END** | 终止节点，图停在这 | 状态机的终态 |

把它们拼起来就是一台**状态机（state machine）**：State 是状态、Node 是状态里干的活、条件边是转移函数。后端工程师写过的订单状态流转（待支付→已支付→已发货）、审批工作流、Step Functions / Temporal——一模一样，只是节点里现在调的是 LLM。

### 2. 经典回路：agent → router → tool/end
今天手写的核心图就一个环：
```
        ┌─────────────────────────┐
        │                         │（不够，再来一轮）
   START ▶ agent ─▶ router ──┬──▶ tool ─┘
                            │
                            └──▶ END （够了，结束）
   ```
- **agent**：让 LLM 看 state 里的问题+已查资料，决定"还要不要查"。
- **router**（条件路由）：读 LLM 的决定——要查就去 `tool`，够了就去 `END`。
- **tool**：执行查询，把结果写回 state，**回边**指回 agent 再想一轮。
这就是循环+分支：直线链做不到的"按需多查几次"，图天然支持。

### 3. 守门人：步数上限防死循环
图能循环，就可能**转不停**。状态机的老规矩：加一个 `step` 计数，超上限强制走 END（LangGraph 里叫 `recursion_limit`）。后端写重试/轮询都设过 max-retries——同一招。

### 4. State 是单一真相源
所有节点不直接互相调用，只读写同一个 State dict——解耦、可重放、可观测。这正是后端"无状态 handler + 显式 context"的设计：任意节点崩了，拿着 State 就能从断点续跑。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）
1. **LangGraph 官方站**（今天的主角，先看首页定位）— https://langchain-ai.github.io/langgraph/
2. **LangGraph 核心概念**（State/Node/Edge/条件路由权威解释）— https://langchain-ai.github.io/langgraph/concepts/
3. **AWS Step Functions**（后端版状态机，对照理解"图编排"）— https://aws.amazon.com/step-functions/
4. **状态机（Finite-State Machine）维基**（万变不离其宗的底座）— https://en.wikipedia.org/wiki/Finite-state_machine
5. **Ollama Chat API**（练习真连本机模型，无需付费 key）— https://github.com/ollama/ollama/blob/main/docs/api.md

---

## 💻 动手练习（约 20 分钟）
**不装 LangGraph**，用标准库手写一台迷你状态图，把它的内核摸透：State=dict、节点=函数、条件边决定下一站，跑一个 `agent→router→tool/end` 的循环图，真连本机 Ollama。

```bash
# 前置：Ollama 已启动并拉过模型
ollama serve
ollama pull qwen2.5:3b
# 跑通即达标
cd ~/projects/daily-learn && uv run day-38/practice.py
# 想换模型：OLLAMA_MODEL=qwen2.5:7b uv run day-38/practice.py
```
先把标 ★ 的 5 行自己补一遍（条件路由是核心），再对照文末「参考答案」。

---

## 🤔 思考题
1. **链 vs 图**：同样一句话查一次就答的任务，链就够了。请举一个**必须用图**才能干的 Agent 任务，说清"必须"在哪。
2. **条件路由**：`router` 凭什么决定去 tool 还是 END？如果让 LLM 自己输出 `DONE/SEARCH`，相比代码硬判断"答案够不够"，各自风险是什么？
3. **死循环**：去掉步数上限，最坏会怎样？除了计数，还有什么信号能让图安全收尾？（提示：tool 结果重复、置信度）

> 答案写到 `notes.md`，跑通 `practice.py`，打开 `visualize.html` 点几遍看图怎么转。

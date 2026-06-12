# Day 45 — CrewAI vs AutoGen：两大多 Agent 框架对比与实践

> **阶段**：Phase 4 · AI Agent 开发（Multi-Agent 框架对比日）
> **主题**：搞懂两大多 Agent 框架的根本差异——**CrewAI = 角色+任务+流程**（流水线写死）、**AutoGen = 对话式群聊**（流程涌现自来回），用纯标准库各手写一个迷你版对比，真连本机 Ollama 跑通
> **预计耗时**：约 1 小时（25 分读 + 15 分资源 + 20 分动手）
> **给后端工程师的一句话**：两者都把「多个 LLM 协作」落地，区别只在**谁定流程**。CrewAI 像你写的 **pipeline/DAG**（ETL：抽取→清洗→入库，步骤你排死，role/task/crew）；AutoGen 像一群**微服务互相 RPC 聊到一致**（conversational，没总指挥，靠你来我往收敛）。今天不装框架（避免依赖），用 ~60 行 stdlib 各还原一遍内核，亲手跑就懂。

---

## 📖 学习内容（约 25 分钟）

### 1. 多 Agent（Multi-Agent）= 让几个 LLM 分工协作
单 Agent（Day42-43）一个模型边想边用工具。**多 Agent** 把活拆给几个有不同人设的模型：研究员只调研、作者只写、审稿只把关——分工降复杂度。问题来了：**谁决定下一步谁说话？** 两大框架给了相反答案。

### 2. CrewAI = 角色 + 任务 + 流程（role / task / crew）
术语对照：**Role（角色）**=一段固定人设、**Task（任务）**=一条指令、**Crew（队伍）**=把角色和任务排成清单顺序跑。流程是**你写死的**（sequential），上一任务产物喂给下一任务，无自由发言。后端类比：**这就是流水线 / DAG**——`研究员→作者→审稿`，等于 `抽取→清洗→入库`，步数固定、可预测。优点：稳、可控；缺点：不灵活。

### 3. AutoGen = 对话式多 Agent 群聊（conversational group chat）
术语对照：几个 Agent 共享一段**对话历史**，轮流发言（round-robin），聊到出现收敛信号（如 `DONE`）才停。流程**不写死、涌现自对话**——提议者出方案、挑刺者挑毛病、改进、再挑……来回到满意。后端类比：**没有总指挥的微服务互相 RPC**，靠协商收敛。优点：灵活、适合开放问题；缺点：可能跑偏、步数不定、要护栏。

### 4. 一图看清差异（同样是「多个 LLM」，调度方式相反）
| 维度 | CrewAI（流水线） | AutoGen（群聊） |
|---|---|---|
| 核心概念 | role / task / crew | conversational agents |
| 谁定流程 | 你写死（sequential） | 涌现自对话来回 |
| 步数 | 固定、可预测 | 不定，靠 DONE/护栏停 |
| 后端类比 | ETL pipeline / DAG | 微服务 RPC 协商收敛 |
| 收尾 | 任务清单跑完 | 收敛信号 or 最大轮数 |
| 适合 | 流程明确的活 | 开放讨论/反复打磨 |

产物：**一个 `mini_crew`（顺序流水线）+ 一个 `mini_groupchat`（聊到 DONE）**，同主题各跑一遍，对比手感。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **CrewAI 官方文档**（role/task/crew/process，框架版的 mini_crew）— https://docs.crewai.com/
2. **AutoGen 官方文档**（GroupChat/对话式多 agent，框架版的 mini_groupchat）— https://microsoft.github.io/autogen/
3. **Anthropic — Building Effective Agents**（何时该用工作流、何时该多 agent，圣经级取舍）— https://www.anthropic.com/engineering/building-effective-agents
4. **Ollama API 文档**（今天 chat helper 的 /api/chat 标准）— https://github.com/ollama/ollama/blob/main/docs/api.md

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：一份文件里两套架构——`mini_crew` 角色顺序流水线、`mini_groupchat` 两 agent 聊到 DONE，同主题对比。**不装 CrewAI/AutoGen**（避免依赖），用 `urllib` 直连。先补 5 个 `★` 行，再对照文末答案。

```bash
ollama serve                       # 默认 http://localhost:11434
ollama pull qwen2.5:3b             # 1.9GB 小模型；OLLAMA_MODEL 可覆盖
uv run day-45/practice.py          # 同主题各跑 crew + groupchat
OLLAMA_MODEL=qwen2.5:7b uv run day-45/practice.py   # 换大模型试收敛质量
```
预期：🧩 行是 Crew 顺序跑研究员→作者→审稿（步数固定）；💬 行是群聊提议者↔挑刺者来回到 DONE（步数不定）——即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击打开 `visualize.html`（纯 canvas、零依赖、深色 `#0e1117`）。左侧 Crew 流水线一格格点亮（固定 3 步）；右侧 GroupChat 两 agent 来回冒泡直到 DONE（步数不定）。并排看「写死流程 vs 涌现流程」。

---

## 🤔 思考题（边做边想）

1. 同一个主题，Crew 步数永远 3、GroupChat 可能 2 也可能 4——哪个更可控、哪个上限更高？你的业务该选谁？
2. GroupChat 若没人说 DONE 会怎样？`max_turns` 护栏对应 CrewAI 的什么（提示：CrewAI 为何天然不需要这护栏）？
3. 把 Crew 改成「研究员的产物分别喂作者和审稿、再合并」就成了 DAG（非线性）；这对应 LangGraph 的什么？

> 把答案记在 `notes.md`。下一步把工具（Day40）塞进多 Agent，每个角色配自己的工具——就是真实生产多 Agent 系统。

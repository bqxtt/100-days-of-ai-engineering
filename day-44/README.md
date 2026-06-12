# Day 44 — Multi-Agent 架构：协作模式 / 委托模式 / 竞争模式

> **阶段**：Phase 4 · AI Agent 开发（Day36-43 单 Agent → Day44 多 Agent）
> **主题**：把「一个会用工具的 Agent」（Day42-43 内核）变成「一支会协作的团队」。今天讲三种多 Agent 协作模式——**协作**（各司其职流水线）、**委托**（supervisor 分派）、**竞争**（多方案投票）——并真连 Ollama 把三种都跑一遍。
> **预计耗时**：约 1 小时（跑通 + 读懂三模式 + 想清何时该上多 Agent）
> **给后端工程师的一句话**：多 Agent（Multi-Agent System，多智能体系统）就是你早就会的**服务编排**：把一个大任务拆给多个角色，每个角色（agent）= 一个微服务，messages = 你的消息队列。协作=订单/库存/支付流水线编排；委托=dispatcher 主从路由；竞争=负载均衡多副本 + 仲裁。别一上来就上团队——单 Agent 能干就别拉团队，**人多了协调成本也涨**。

---

## 📖 学习内容（约 25 分钟）

### 0. 从单 Agent 到多 Agent：什么时候才该拉团队
单 Agent（Day42-43）= 一个 ReAct 循环，自己想自己做。够用就别复杂化。当任务**步骤多到一个角色塞不下上下文**、**需要不同专长**、或**要并行试多条路**时，拆成多个 agent。每个 agent 仍是单 Agent 内核，只是分工 + 互相传消息。**多 Agent = 多个单 Agent + 一套协作协议。**

| 概念 | 中文 / 英文 | 后端类比 | 一句话 |
|---|---|---|---|
| 协作模式 | Collaboration | 微服务编排 orchestration | 各司其职，串成流水线 |
| 委托模式 | Delegation/Supervisor | 主从 master-worker / 路由 routing | 主管分派，专家干活 |
| 竞争模式 | Competition/Voting | 负载均衡多副本 + 仲裁 | 多方案择优，投票定胜 |

### 1. 协作模式（Collaboration）= 各司其职流水线
三个角色 planner→coder→reviewer，上一个的产出喂给下一个，串成流水线。**后端类比：微服务编排**——下单服务→库存服务→支付服务，每个只管一段，消息往下传。优点是分工清晰、单角色上下文小；代价是串行慢、一环错全错。
```
需求 ─▶ planner(拆步骤) ─▶ coder(按步写码) ─▶ reviewer(验收+建议) ─▶ 成品
```

### 2. 委托模式（Delegation / Supervisor）= 主管分派
一个 supervisor（主管）自己不干活，只判断任务归属，把活分给对口专家（math/code/write）。**后端类比：主从 + dispatcher 路由**——网关看请求类型，路由到对应微服务。supervisor 是大脑，worker 是手脚。任务多样、专长不同时最划算。

### 3. 竞争模式（Competition / Voting）= 多方案投票
同一任务让 n 个 worker 各出一版（高 temperature 求多样），judge 投票选最优。**后端类比：负载均衡多副本 + 仲裁**——多副本算同件事，取最好结果。换准确率换算力，关键任务用得起；琐碎任务太贵。

### 4. 三模式不是互斥，可嵌套
真实系统常组合：supervisor 委托一个子团队**协作**完成，关键步骤再用**竞争**多采样投票。今天三个 demo 单独跑，看清各自骨架即可。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic — Building Effective Agents**（单 Agent vs 多 Agent vs 工作流，何时该上团队的圣经）— https://www.anthropic.com/engineering/building-effective-agents
2. **Anthropic — Multi-Agent Research System**（真实多 Agent 研究系统：orchestrator + 子 agent 并行，竞争/委托工程细节）— https://www.anthropic.com/engineering/multi-agent-research-system
3. **Ollama API 文档**（/api/chat 标准写法，今天 chat helper 的依据）— https://github.com/ollama/ollama/blob/main/docs/api.md
4. **CrewAI 概念**（框架版的角色/任务/流水线，对照看你 demo 缺什么，接 Day45）— https://docs.crewai.com/

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：一个 `chat` helper（标准 ollama 写法）+ 三模式各一个函数——协作 planner/coder/reviewer 流水线、委托 supervisor 分派、竞争多方案投票。先补 5 个 `★` 行，再对照文末答案。HTTP 只用 `urllib`，不装任何框架。

```bash
ollama serve                       # 默认 http://localhost:11434
ollama pull qwen2.5:3b             # 1.9GB 小模型；OLLAMA_MODEL 可覆盖
uv run day-44/practice.py
OLLAMA_MODEL=qwen2.5:7b uv run day-44/practice.py   # 想要更强协调可换 7b
```
预期：协作段三角色依次产出（步骤/代码/评审）；委托段「阶乘」派给 math、「广告语」派给 write；竞争段 3 方案 + 评委选号——三段都真出结果即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击打开 `visualize.html`（纯 canvas、零依赖、深色 `#0e1117`）。三种模式一屏对照，可点单步：协作是直线流水线、委托是主管放射分派、竞争是多副本汇聚投票。亲眼看清三种 topology 的不同。

---

## 🤔 思考题（边做边想）

1. 协作模式串行慢、一环错全环错。哪些环节能并行？reviewer 不通过该回退到 planner 还是 coder？（接微服务的补偿/回滚）
2. 委托模式里 supervisor 选错处理者怎么办？给它加「可回收重派」是变成哪种后端模式？
3. 竞争模式 n=3 要 3 倍算力。什么任务值这个价、什么任务纯浪费？投票用 judge 模型 vs 用规则（多数表决），各适合啥？

> 把答案记在 `notes.md`。下一步 Day45 用 CrewAI/AutoGen 框架把今天手写的三模式工程化——框架只是包了今天这套协作协议。

# Day 39 — 🤖 LangGraph 进阶：Human-in-the-loop、持久化状态

> **阶段**：Phase 4 · AI Agent（Day36-50）
> **主题**：让 Agent **能暂停等人审批**（human-in-the-loop）+ **state 存盘可恢复**（checkpoint 持久化）
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：你写过审批工作流（提单→挂起→人工 approve→继续）和可恢复任务（断点续传、消息重投）。今天 Agent 加的两个能力——**interrupt（人在回路）**= 审批挂起，**checkpoint（持久化）**= 任务存盘续跑——本质就是你那两套，只是状态机里跑的是 LLM 决策。

---

## 📖 学习内容（约 25 分钟）

### 1. 为什么 Agent 要"暂停"和"存盘"
Day36-38 的 Agent 是一口气跑完的：决策→调工具→再决策……但生产里两件事让它不能一口气跑：
- **有些动作不可逆**（删库、转账、发邮件）。不能让模型自己拍板，要**停下来等人批**。
- **进程会崩**（超时、OOM、重启）。跑到第 5 步崩了，不能从头再来，要**从断点续**。

LangGraph 把这两件事做成一等公民：**checkpoint** 每步存 state，**interrupt** 在节点处暂停。后端类比：前者=任务持久化（state 落库），后者=审批工作流（暂停等 approve）。

### 2. Checkpoint 持久化（state 存盘可恢复）
| 概念 | 术语 | 后端类比 |
|---|---|---|
| 每步保存图的状态 | checkpoint | 每步 commit 任务进度到 DB |
| 一次对话/任务的线程 | thread_id | 工单 ID / session |
| 崩溃后从最后一步继续 | resume / replay | 断点续传、消息重投 |

state 就是个可序列化字典：`{goal, log, step, pending, approved}`。存哪都行——LangGraph 用 SQLite/Postgres，今天用 **`.checkpoint.json`**。崩了 → `load()` 读回 → 接着跑。

### 3. Human-in-the-loop（人在回路 · interrupt/approve）
执行高危工具前 `interrupt`：把 state 落盘、退出，控制权交人。人 review → 改成 `approved=True` → 从断点 `resume`，那一步才真执行。
```
decide → 选到 delete_db → 挂起 pending → 存盘退出（⏸ INTERRUPT）
                                          └─人工 approve→ resume → 才真删
```
后端类比：和你的审批流一模一样——金额超阈值就转人工，批了才落库。

### 4. 中英术语速记
checkpoint 检查点/存盘 · interrupt 中断挂起 · resume 续跑 · human-in-the-loop 人在回路 · approve 审批通过 · thread_id 线程/工单ID · serialize 序列化 · breakpoint 断点

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **LangGraph · Persistence（checkpoint 官方概念）** — https://langchain-ai.github.io/langgraph/concepts/persistence/
2. **LangGraph · Human-in-the-loop（interrupt/approve 官方概念）** — https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/
3. **LangGraph · Low-level（State/Checkpointer/thread 全貌）** — https://langchain-ai.github.io/langgraph/concepts/low_level/
4. **Ollama API（本机 /api/chat，今天真调它做决策）** — https://github.com/ollama/ollama/blob/main/docs/api.md

---

## 💻 动手练习（约 20 分钟）

`practice.py`：**纯标准库**手写复刻 LangGraph 两机制——agent loop 在执行高危工具前 `interrupt`，把 state 序列化到 `.checkpoint.json`，模拟"人工 approve 后从断点恢复"。**真连本机 Ollama qwen2.5:3b 做决策**，不 mock。

```bash
ollama serve                # 默认 http://localhost:11434
ollama pull qwen2.5:3b      # 生成模型，约 1.9GB
uv run day-39/practice.py   # 仅 stdlib，无需装包
```
预期：先跑一两步 → **⏸ INTERRUPT** 落盘等审批 → 自动 APPROVE → 从 checkpoint 恢复执行 `delete_db`。先补 5 个 `★` 行，再对照文末答案。

### 🎨 可视化（先玩这个再读理论，更直观）
双击 `visualize.html`（纯 canvas、零依赖、深色）：点"下一步"看 Agent 走到 delete_db 时**暂停亮红**，state 写进右侧 checkpoint，点"approve"才放行——亲眼看 interrupt + 持久化怎么咬合。

---

## 🤔 思考题（边做边想）

1. checkpoint 为什么要"每步"存，而不是跑完存一次？崩在第 5 步会怎样？
2. interrupt 只拦 `delete_db`，query/archive 直接放行——审批阈值该按什么定？（类比金额阈值）
3. state 现在落 json 文件。多用户并发时 thread_id 起什么作用？换成 Postgres 要注意什么？

> 答案记到 `notes.md`。明天 Day 40：多 Agent 协作。

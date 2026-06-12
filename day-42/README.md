# Day 42-43 — 单 Agent 系统实战：构建一个代码分析 Agent

> **阶段**：Phase 4 · AI Agent 开发（**2 天合并实战** · Day36-41 总整合）
> **主题**：把前几天的零件焊成一个能自主多步干活的 Agent——工具操作真实文件系统，ReAct 循环让模型自己决定读哪些文件、统计行数/函数数、写出分析报告
> **预计耗时**：约 2 天 × 1 小时（Day42 跑通+读懂循环，Day43 改工具/换目标+复盘）
> **给后端工程师的一句话**：Agent（智能体）= 一个**会用工具的自动化脚本**，区别只在「下一步」由 LLM 决策、不是你写死的 `if/else`。你把工具表（tools）交给模型，模型边想（Thought）边点工具（Action），你本地真跑、把结果（Observation）塞回去，循环到它收手出报告。今天就用 `read_file`/`list_files`/`count_lines` 操作真实文件系统，造一个分析自身项目目录的 mini「Claude Code 内核」。

---

## 📖 学习内容（约 25 分钟）

### 0. Phase 4 脉络回顾：6 天，一个会自己干活的循环
今天不引入新概念，把 Day36-41 的零件归位：

| 知识点 | 在系统里的角色 | 一句话 |
|---|---|---|
| Day36 ReAct（思考-行动） | Agent 主循环 | 想→做→观察→再想 |
| Day37 LangChain Tool/Agent | 工具+决策器 | 框架只是包了这个循环 |
| Day40 工具设计（Tool） | name+描述+schema | 描述写好坏 = 模型调对不对 |
| Day41 短期记忆（Memory） | `messages` 列表 | 把每步追加进去就是记忆 |
| 今天 实战 | 焊成代码分析 Agent | 真读真统计真报告 |

产物：**一个 ReAct Agent**，自主 `list_files → count_lines → 出报告`，统计来自真实文件。

### 1. 系统骨架：ReAct 就是一个 while 循环
```
目标(goal) ──▶ ┌─[调模型] 想下一步 ───┐
               │   有 tool_call? ──是─▶ 本地真跑工具 → Observation → 塞回 messages ─┐
               │   否 ──▶ 直接吐报告 收尾                                            │
               └──────────────────◀───────────── 再想（最多 8 步护栏）───────────────┘
```
后端类比：和你写的任何「轮询 + 分发」服务一样——`while` 里拿一个指令、`dispatch` 到对应函数、回写状态。Agent 只是把「下一条指令」从队列换成了模型输出。**Action（行动 / agentic loop）= 调度，Observation（观察）= 函数返回值。**

### 2. Tool（工具）= name + 描述 + 入参 schema
模型自己不会读文件，它只「说」要调 `read_file(path="day-1/practice.py")`，真正干活的是你的 Python（安全边界在此：只读、锁死项目根、`../` 越权直接拒）。工具的**描述（description）**就是说明书——写清「想知道有哪些文件时调用」，模型才点对。这是 Day40 的核心：好工具 = 好描述 + 严校验。

### 3. Memory（记忆）= 不断追加的 messages
没有数据库——短期记忆就是那个 `messages` 列表。模型每条回复、每个工具的 Observation 都 `append` 进去，下一轮整包重发，模型才知道「上一步看到了 4 个文件」。**记忆 = 上下文累积**，超长再上摘要（summary memory，Day41）。

### 4. 为什么是「单 Agent」：自主多步、不收手才停
不是一问一答——模型要先 ls、再逐个 count、必要时 read，**自己决定步数**。护栏（max 8 步）防打转。这一步把「自动化脚本」升级成「Agent」：流程不写死，由模型据观察临场决策。换成真 read/grep/git，就是 Claude Code / Cursor 的最小内核。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **ReAct 原始论文（Reasoning+Acting）**—— 今天循环的理论源头 — https://arxiv.org/abs/2210.03629
2. **Anthropic — Building Effective Agents**（单 Agent vs 工作流，工具/循环设计圣经）— https://www.anthropic.com/engineering/building-effective-agents
3. **Ollama API 文档**（tool_calls 标准写法）— https://github.com/ollama/ollama/blob/main/docs/api.md
4. **LangChain Agents 概念**（框架版的同一个循环，对照看你 demo 缺什么）— https://python.langchain.com/docs/concepts/agents/

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：一个完整代码分析 Agent——3 个工具（list_files/read_file/count_lines）操作真实文件系统，ReAct 循环让 qwen2.5:3b 自主分析 `day-1/`。先补 5 个 `★` 行，再对照文末答案。HTTP 只用 `urllib`，无需装包。

```bash
ollama serve                       # 默认 http://localhost:11434
ollama pull qwen2.5:3b             # 支持 tool_calls 的 1.9GB 小模型
uv run day-42/practice.py          # 默认分析 day-1/
ANALYZE_DIR=day-20 uv run day-42/practice.py   # Day43：换目录练手
```
预期：🔧 行显示 Agent 自主调用 list_files→count_lines（多步），末尾报告含文件清单/行数/函数数——即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击打开 `visualize.html`（纯 canvas、零依赖、深色 `#0e1117`）。把 ReAct 循环做成可点单步：每点一下走一格——Thought→Action(选工具)→Observation(文件系统真实回值)→塞回记忆→再 Thought，直到收尾出报告。亲眼看 Agent 怎么自己决定先 ls 再 count，记忆条逐步变长。

---

## 🤔 思考题（边做边想）

1. 把 8 步护栏去掉、工具描述写模糊，Agent 会怎样？「不收手」和「调错工具」各对应哪一行的脆弱？
2. `read_file` 只许读、`_safe` 锁死项目根——若给 Agent 加 `write_file`，安全边界要加什么？（接 Day49 权限控制）
3. 现在记忆是无限追加的 `messages`，分析大仓库会爆 token。换成 Day41 的摘要记忆，该在循环哪一步压缩？

> 把答案记在 `notes.md`，并写 Phase 4 前半段复盘。下一步 Day44 进入 Multi-Agent——今天的单 Agent 会成为团队里的一员。

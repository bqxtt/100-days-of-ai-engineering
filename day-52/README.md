# Day 52-53 — Multi-Agent 实战：构建一个开发团队模拟系统

> **阶段**：Phase 4 · AI Agent 开发（**2 天合并实战** · Day42 单 Agent → 多 Agent 升级）
> **主题**：把「一个会用工具的 Agent」升级成「一支会协作的 AI 团队」——PM 拆需求 → Coder 写代码 → QA 真 exec 跑测试 → Reviewer 评审，supervisor 编排循环，红了打回重写，全程模型自决，端到端完成一个真编程任务
> **预计耗时**：约 2 天 × 1 小时（Day52 跑通+读懂编排，Day53 改任务/加角色+复盘）
> **给后端工程师的一句话**：Multi-Agent（多智能体）= 你早就会的**微服务编排**——supervisor 是调度器（orchestrator），每个 agent 是各管一段的 worker，QA 的 `exec` 是集成测试关卡，跑红就回滚重来。区别只在每个 worker 的「下一步」由 LLM 决策，不是写死的 `if/else`。今天就把一个编程需求丢给「团队」，看它们自己拆活、写码、测、审、打回，直到交付。

---

## 📖 学习内容（约 25 分钟）

### 0. 从单 Agent 到多 Agent：一个人变一支队
Day42 是一个 Agent 揽所有活；今天分工——每个 agent 一个**独立角色 prompt（独立上下文窗口）**，各司其职：

| 角色 | 后端类比 | 一句话 |
|---|---|---|
| Supervisor（主管 / orchestrator） | 调度器 dispatcher | 拆活、派单、卡关、汇总、决定停 |
| PM（产品 / product manager） | 把工单写成规格 | 口语需求 → 一句话规格 |
| Coder（开发 / developer） | worker | 按规格写函数 |
| QA（质检 / exec 真跑） | 集成测试关卡 | 真 exec 跑断言，红即打回 |
| Reviewer（评审 / code review） | MR 评审人 | 不满足规格就给一条修改意见 |

产物：**一支跑得通的 AI 开发团队**，把 `is_prime` 从需求做到交付，QA 反馈来自真实执行。

### 1. 系统骨架：orchestrator-worker 编排（Action 调度循环）
```
任务 ─▶ PM 拆规格 ─▶ ┌─ Coder 写码 ─▶ QA exec 真跑 ─▶ Reviewer 评审 ─┐
                     │      双绿(测试过+评审OK)? ──是─▶ 交付收尾          │
                     └──◀── 否：打回 + 反馈回灌，重写（最多3轮护栏）────────┘
```
后端类比：和 CI/CD 流水线一模一样——提交→构建→测试→评审，红灯回滚重提。Supervisor = 流水线编排器；**Action（行动）= 派单调度，Observation（观察）= QA 的 exec 结果 + 评审意见**。

### 2. 分工 = 独立 prompt = 独立上下文（worker 不互相污染）
Anthropic multi-agent 研究系统的核心：lead 给每个 worker「目标+输出格式+边界」，worker 各开独立窗口并行探索。本 demo 串行简化，但分工同理——PM 只管规格、Coder 只看规格+反馈、Reviewer 只判合不合。**角色清晰才不重复劳动、不留空白**。

### 3. QA = 真 exec：硬反馈是闭环的钥匙
Coder 写完不算数，QA `exec(code)` + `exec(assert...)` 本地真跑测试——这是模拟里唯一不靠模型嘴说的「ground truth」。红了 supervisor 把异常回灌 Coder 重写。**没有真测试，团队就在互相吹捧；有了 exec，就有客观卡关。**

### 4. 为什么是「多 Agent」：分工 + 双绿放行 + 护栏停
不是一问一答——supervisor 循环派单，**测试过且评审 OK 才放行**，否则带反馈重来；3 轮护栏防死磕。换 worker 为 Claude、QA 为真 pytest、编排为 LangGraph，就是生产级 multi-agent 开发团队。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic — Multi-agent Research System**（supervisor 拆活/派 worker/汇总，本实战的蓝本，多 worker 省 90% 时间）— https://www.anthropic.com/engineering/multi-agent-research-system
2. **Anthropic — Building Effective Agents**（orchestrator-worker vs workflow，何时该上多 agent 的圣经）— https://www.anthropic.com/engineering/building-effective-agents
3. **Ollama API 文档**（/api/chat 标准写法，chat helper 同款）— https://github.com/ollama/ollama/blob/main/docs/api.md
4. **LangGraph Multi-Agent 概念**（supervisor 模式的框架版，对照看 demo 缺什么）— https://langchain-ai.github.io/langgraph/concepts/multi_agent/

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：5 个角色（PM/Coder/QA/Reviewer/Supervisor）协作做 `is_prime`，QA 用 `exec` 真跑断言、红了打回重写，端到端到交付。先补 5 个 `★` 行，再对照文末答案。HTTP 只用 `urllib`，不装任何框架。

```bash
ollama serve                       # 默认 http://localhost:11434
ollama pull qwen2.5:3b             # 1.9GB 小模型；OLLAMA_MODEL 可覆盖
cd ~/projects/daily-learn && uv run day-52/practice.py
TASK="写一个 reverse_str(s) 反转字符串" uv run day-52/practice.py   # 换任务再跑
```
看输出：📋PM 规格 → 💻Coder 各轮代码 → 🧪QA exec 红/绿 → 👀Reviewer 意见 → 📦交付。把 `is_prime` 故意改一行让 QA 红，观察打回重写。
打开 `visualize.html`（双击即可，纯 canvas 无依赖）看流水线动起来。

## 🤔 思考题（写进 notes.md，Day53 复盘）
1. QA 双绿才放行：去掉 QA、只靠 Reviewer 评审会怎样？哪行是闭环的「ground truth」？
2. 现在是串行；Anthropic 的 multi-agent 强调并行 worker——demo 哪一步能并行、收益是什么？
3. 给团队加 write_file 真落盘，安全边界要加什么（接 Day49 权限 / 沙箱）？

# Day 20 — 🏗️ 实践日：构建一个带 Tool Use 的智能命令行助手

> **阶段**：Phase 2 · Prompt Engineering 与 LLM API 开发（收官实践日）
> **主题**：把 Day 11-19 的技能拼成一个可跑的 CLI 助手——真连 Ollama + tool use 循环 + 流式打印 + 重试
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：前 9 天你学了一堆"零件"——API 参数、prompt、tool use、结构化、重试……今天不学新概念，只干一件事：**把它们拧成一台机器**。一个智能命令行助手的骨架，本质就是个 `while` 循环——"调模型 → 模型说要用工具 → 你执行工具 → 把结果塞回去再调模型"，转到模型说"我答完了"为止。今天**真连本地 Ollama**（qwen2.5:3b，免费离线、无需付费 key），让模型真去决定调哪个工具；接真实 Claude 只是把一个函数换成 SDK 调用。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器，零依赖，深色）。它把一台"带工具的助手"在你眼前跑一遍：① 用户提问 → ② 助手（mock LLM）逐字**流式**吐字 → ③ 决定调用工具（calc / time / search）→ ④ 工具返回结果 → ⑤ 助手拿结果**接着流式**回答。还能看到一次模拟"超时 → 自动重试"。看完你就懂了：**Agent 不神秘，就是"对话 + 工具调用"的循环**。先玩后读。

---

## 📖 学习内容（约 30 分钟）

### 0. 回顾：Phase 2 的脉络（Day 11→19 怎么串起来）

今天是把这条线拼成一个东西，先把脉络捋一遍：

| Day | 技能 | 在今天的助手里扮演什么 |
|---|---|---|
| 11 | **API 参数**（temperature/top_p/max_tokens） | 配置模型怎么吐字 |
| 12 | **Prompt 核心**（Zero/Few-shot、CoT） | system prompt 定人设、教它"先想再答" |
| 13 | **高级技巧**（ReAct） | tool use 循环本身就是 ReAct：Reason → Act → Observe |
| 14 | **Tool Use** | 助手的双手——能调 calc/time/search |
| 15 | **结构化输出**（JSON/Schema） | 工具入参就是一份 schema，模型按 schema 填参数 |
| 16 | **多模态** | 可扩展：同一条 messages 还能塞图（今天先不接） |
| 17 | **流式输出**（SSE） | 助手逐字打印，体验不卡顿 |
| 18 | **Prompt 模板管理** | system/tool 定义抽成模板，方便换版本 |
| 19 | **生产化**（成本/限流/重试） | 重试 + 退避，把超时/限流挡在外面 |

一句话：**Day 11-13 教它"怎么想"，Day 14-15 给它"手"，Day 16-18 管"输入输出与版本"，Day 19 让它"扛得住生产"。今天=把这些拼成一个 CLI 助手。**

### 1. 智能助手的骨架 = 一个 agent loop

去掉所有花哨，一个带工具的助手就是这个循环：

```
messages = [系统提示, 用户问题]
while True:
    回复 = 调LLM(messages, tools)          # 1) 问模型
    if 回复.要用工具:
        结果 = 执行工具(回复.工具名, 回复.参数)  # 2) 你的代码干活
        messages += [回复, 工具结果]           # 3) 把结果塞回对话
        continue                              #    再问一轮
    else:
        return 回复.文本                       # 4) 模型答完，收工
```

后端类比：这就是一台**状态机**。模型不会自己执行工具——它只**说**"我想调 calc，参数 {a:2,b:3}"，真正算的是**你的代码**。安全边界、权限、审计全在你手里。这正是 Day 13 的 ReAct（Reason→Act→Observe）落到代码上的样子。

### 2. 工具 = 名字 + 描述 + 入参 schema（接 Day 14/15）

模型靠 `description` 决定**何时**用，靠 `input_schema` 知道**怎么填参数**：

```json
{
  "name": "calc",
  "description": "做四则运算。需要算数时调用。",
  "input_schema": {
    "type": "object",
    "properties": {"a": {"type": "number"}, "op": {"type": "string"}, "b": {"type": "number"}},
    "required": ["a", "op", "b"]
  }
}
```

模型返回的 tool_use 里 `input` 就是按这份 schema 填好的 JSON——所以"结构化输出"和"tool use"本是一家。

### 3. 流式 + 重试：体验与稳健（接 Day 17/19）

- **流式**：不等整段生成完，逐 token 打印，用户看到光标在动就不焦虑。今天 `stream=True` 读 Ollama 真吐的增量。
- **重试**：网络抖动/限流/超时是常态。包一层"失败→等待→再试"，本练习连不上时自动重试一次。SDK 自带重试，但理解原理你才会调。

```
for attempt in range(max_retries):
    try: return call()
    except 可重试错误: sleep(base * 2**attempt); 继续
raise  # 试到顶还不行才放弃
```

### 4. 从 Ollama 到真实 Claude：只换一个函数

`practice.py` 里所有 LLM 调用走本地 **Ollama**（qwen2.5:3b，免费离线）。接真实模型时，把 `ollama_call()` 换成 Anthropic SDK 的 `client.messages.create(...)`，工具循环、流式、重试**一行不用改**。这就是好骨架的价值：**核心逻辑与具体模型解耦**。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic Python SDK（今天接真实模型用它，必看）** — https://github.com/anthropics/anthropic-sdk-python — `practice.py` 文末注释给了对应改法，看 README 的 tool use / streaming 段。
2. **Anthropic 官方 Tool Use 文档** — https://docs.anthropic.com/en/docs/build-with-claude/tool-use — agent loop、tool_use/tool_result 结构、stop_reason 的权威说明，呼应模块 1/2。
3. **Anthropic Cookbook · 工具与 Agent 示例** — https://github.com/anthropics/anthropic-cookbook — 真实可跑的 tool use / 多工具编排范例，是今天骨架的"进阶版"。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯 Python 标准库（无需 numpy、无需付费 API key），真连本地 Ollama**。这是一个完整的命令行助手骨架：真 agent loop + tool use 循环 + 流式打印 + 重试，把 Phase 2 全部技能串成一个东西。补齐多个 `★`，再对照文末答案。

```bash
# 先备好 Ollama（已装可跳过前两步）：
ollama serve            # 启动服务（默认 http://localhost:11434）
ollama pull qwen2.5:3b  # 拉模型（约 1.9GB）
# 真跑：
uv run day-20/practice.py
```

预期：助手依次处理 3 个问题——"3 加 5"（模型决定调 calc）、"几点了"（调 time）、"查一下 RAG"（调 search），每次都能看到模型真去调工具 → 本地执行 → 拿结果流式续答。看到完整对话跑完即达标。

### 🎨 可视化

`visualize.html` 把这台机器的"对话 + tool 调用流程"画成深色动画，先玩它最直观。

---

## 🤔 思考题（边做边想）

1. 工具不是模型自己执行的，是**你的代码**执行的——这对安全/权限/审计意味着什么？哪些工具你绝不会让它自动跑？
2. agent loop 里若模型一直要调工具不收手，会怎样？该加什么护栏（最大轮数、预算上限）？这和你给后台任务设超时像不像？
3. 流式输出让"首字延迟"变短，但总耗时没变——为什么用户体验还是好很多？
4. 把 mock 换成真实 Claude，循环/流式/重试都不用动——这种"核心逻辑与模型解耦"的设计，在你现有后端里还有哪些地方该这么做？

> 把答案记进 `notes.md`，里面还有 **Phase 2 复盘模板**。明天进入 Phase 3：RAG 系统，从 Embedding 原理开始。

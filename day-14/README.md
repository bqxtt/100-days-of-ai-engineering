# Day 14 — Function Calling / Tool Use：让模型调用外部工具

> **阶段**：Phase 2 · Prompt Engineering 与 LLM API 开发
> **主题**：用 tools 参数把模型变成"会调函数的大脑"，外部能力（天气/计算/查库）接进来
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：模型本身不会查天气、不会精确算术、连不上你的数据库。Function Calling（Tool Use）的本质是——模型不直接执行函数，它只**申请**调用（输出一段 `tool_use` JSON），活儿还是你后端干完再把结果回填。说白了就是模型当"调度器"，你当"执行器"，中间走一个 RPC 回路。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器，零依赖）。这是一个 **Tool Use 回路动画**：用户提问 → 模型决定是否调用工具（输出 tool_use 卡片）→ 工具被本地执行 → tool_result 回填 → 模型给最终答案。可一步步单击推进，右侧实时显示这一轮在传的 JSON（tool schema / tool_use / tool_result），并能切换"并行两工具"看一次 tool_use 里发出多个调用。先看清楚"模型↔工具"是怎么来回的，再读理论。

---

## 📖 学习内容（约 25 分钟）

核心心智模型一句话：**模型不执行工具，只输出"该调谁、传什么参数"；执行和回填都在你这边**。下面四块拼出完整回路。

### 1. Tool Schema 定义：把函数说明书喂给模型

你在请求里带一个 `tools` 数组，每个工具用 **JSON Schema** 描述。`practice.py` 这次真连本地 **Ollama**，用的是 Ollama/OpenAI 风格 `{"type":"function","function":{name/description/parameters}}`；Claude 字段名略不同（`input_schema`），概念一致：

```json
{"type": "function", "function": {
  "name": "get_weather",
  "description": "查某城市当前气温",
  "parameters": {
    "type": "object",
    "properties": {"city": {"type": "string", "description": "城市名"}},
    "required": ["city"]
  }
}}
```

这就是给模型看的"接口文档"。后端类比：等于你把一份 OpenAPI/接口注释发过去，模型据此决定调哪个、怎么填参数。**description 写得越清楚，调用准确率越高**——它是 prompt 的一部分，不是摆设。

### 2. 模型如何决定调用：它输出意图，不执行

带上 tools 发请求后，模型自己判断"这题要不要用工具"。Ollama 要用就在 `message.tool_calls` 里给出调用（Claude 是 content 里的 `tool_use` 块，意思一样）：

```json
{"function": {"name": "get_weather", "arguments": {"city": "北京"}}}
```

关键点：**模型到此就停了，函数一行都没跑**。`arguments` 是它按你的 schema 凑出来的参数（Ollama 直接给 dict，可 `fn(**args)` 调）。你的后端按 `name` 路由到真函数执行——和收到一个 RPC 请求一模一样。

### 3. tool_use / tool_result 回路：必须把结果还回去

执行完，把结果包成消息追加进对话，再请求一次。Ollama 用 **role=tool**（Claude 是 user 角色 + `tool_result` 块，要 `tool_use_id` 对上 id）：

```json
{"role":"tool","name":"get_weather","content":"{\"temp_c\":26}"}
```

模型拿到结果才能继续。**没回填，对话就断了**。这一来一回（user→assistant tool_calls→tool 结果→assistant）就是 agent loop 的最小单元——只要还有 `tool_calls` 就循环，没了才收尾。Day 13 的 ReAct（推理+行动）正是把这个回路套多轮。

### 4. 并行工具调用（Parallel Tool Use）：一轮发多个

模型可在**同一个 tool_calls 回合**里发多个调用（如同时查天气+算汇率），后端并发执行后一次性回填。也可能像 `practice.py` 里那样分两轮：先查天气、看结果再调计算器——回路本身能撑这两种模式，循环到没有 tool_calls 才停。后端类比：一次 fan-out 调多个下游再聚合，比串行省一个来回。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic — Tool use (function calling) 官方文档**（必读，今天所有字段以它为准）— https://docs.anthropic.com/en/docs/build-with-claude/tool-use — 看清 `tools` / `tool_use` / `tool_result` / `tool_choice` / 并行调用。
2. **Anthropic — Tool use 速览与示例 Notebook** — https://github.com/anthropics/anthropic-cookbook/tree/main/tool_use — 端到端可跑的调用循环，对照 `practice.py` 看真实 API 版长啥样。
3. **OpenAI — Function calling 指南**（横向对比）— https://platform.openai.com/docs/guides/function-calling — 字段叫 `tools`/`tool_calls`，概念一致；理解"两家协议差异不大"。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯 stdlib，真连本地 Ollama**（不需要 API Key）。它跑一次完整回路：真模型发 tool_calls → 本地执行天气/计算器 → 以 role=tool 回填 → 模型收尾。完成 3 个 ★ 即可。

前置（必须，否则连不上）：

```bash
# 1) 装并启动 Ollama，监听 http://localhost:11434
# 2) 拉一个支持原生 tools 的模型（约 1.9 GB）：
ollama pull qwen2.5:3b
# 想换模型：export OLLAMA_MODEL=qwen2.5:7b

# 3) 在项目根目录跑（环境用 uv 管理）：
uv run day-14/practice.py
```

预期：看到 tools 定义打印 → 模型真发 tool_calls 调 get_weather → 本地执行 → 再调 calculator 换算 → 模型给出 78.8°F 的最终回答。能跑通这条真回路，今天就达标。

### 🎨 配合可视化

跑通后回 `visualize.html`，把代码里 `chat()发tool_calls → TOOLS[name](**args) → role=tool 回填` 三步在动画里逐帧对上号；右侧 JSON 就是 `practice.py` 在 messages 里来回追加的内容。

---

## 🤔 思考题（边做边想）

1. 模型只输出 tool_use 不执行——为什么这反而是"特性"不是"缺陷"？（提示：权限、审计、安全谁说了算）
2. 如果你不把 tool_result 回填就再问，会发生什么？为什么 `tool_use_id` 必须对上？
3. 并行调用省的是哪种成本：API 轮次还是单工具耗时？什么情况下并行反而不安全（提示：有依赖、有副作用）？
4. `practice.py` 的 calculator 用了 eval——这在生产是个口子。你会怎么约束模型能调的工具与参数范围？

> 把答案记在 `notes.md`。明天 Day 15 — Structured Output：把今天的 schema 约束用到"逼模型只吐 JSON"。

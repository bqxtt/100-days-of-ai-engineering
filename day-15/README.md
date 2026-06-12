# Day 15 — Structured Output：JSON Mode、Schema 约束、输出格式控制

> **阶段**：Phase 2 · Prompt Engineering 与 LLM API 开发
> **主题**：让模型稳定吐出"机器可直接消费"的 JSON——JSON Mode、tool use 强制 schema、Pydantic 校验、容错解析与重试
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：上游接口返回的不是英文段落，而是要进数据库、进下游 RPC 的结构体。结构化输出就是把 LLM 从"会聊天的人"变成"返回 `200 OK + JSON body` 的可靠接口"——而你要做的，是给它加上 schema 契约和容错解析这两道闸门。

---

## 📖 学习内容（约 25 分钟）

### 1. 为什么要结构化输出（Why structured output）

你不会接受一个下游服务"大概率返回 JSON，偶尔夹一段废话"。但纯 prompt 让模型输出 JSON 正是这种"大概率"——它会贴心地加上 ` ```json ` 围栏、写句"当然可以！"、漏个字段、留个尾逗号。后端拿到就 `json.loads` 崩了。结构化输出解决三件事：**(1) 字段稳定**（下游不用兜底空值）、**(2) 类型/枚举可控**（`plan` 只能是 free/pro/enterprise）、**(3) 免去脆弱的正则清洗**。从"约束强度"由弱到强有四档：

| 手段 | 约束力 | 用在哪 |
|---|---|---|
| Prompt 里写"只返回 JSON" | 弱（仍可能脏） | 快速试，配容错解析 |
| **JSON Mode**（`output_config.format` + json_schema） | 强（保证合法 JSON 且贴合 schema） | 抽取/分类，要可直接入库 |
| **Tool use + strict schema** | 强（参数即结构体） | 模型要"调一个动作"，参数本身就是结构化数据 |
| Pydantic `messages.parse` | 强 + 自动校验成对象 | 业务代码里最省事，直接拿到 typed 对象 |

### 2. JSON Mode：用 schema 约束响应格式

Claude 通过 `output_config.format` 接一个 JSON Schema，直接保证响应体是符合该 schema 的合法 JSON（默认模型用 `claude-opus-4-8`）：

```python
import anthropic, json
client = anthropic.Anthropic()
resp = client.messages.create(
    model="claude-opus-4-8", max_tokens=16000,
    messages=[{"role": "user", "content": "提取：Jane Doe 30岁 想要 pro 套餐"}],
    output_config={"format": {"type": "json_schema", "schema": {
        "type": "object",
        "properties": {"name": {"type": "string"}, "age": {"type": "integer"},
                       "plan": {"type": "string"}},
        "required": ["name", "age", "plan"], "additionalProperties": False,
    }}})
data = json.loads(next(b.text for b in resp.content if b.type == "text"))
```
注意：旧的顶层 `output_format` 已废弃，统一用 `output_config.format`。schema 不支持递归、`minLength`/`maximum` 等数值约束（这些要客户端补校验，正是练习里做的）。

### 3. Tool use 强制 schema：参数就是结构体

模型"要调一个工具"时，工具的 `input_schema` 就是它必须填满的结构。加 `"strict": True` 让参数严格匹配 schema，比"求模型返回 JSON"更自然——动作和数据一次到位：

```python
tools=[{"name":"book_flight","strict":True,"input_schema":{
    "type":"object","properties":{
        "dest":{"type":"string"},"pax":{"type":"integer","enum":[1,2,3,4]}},
    "required":["dest","pax"],"additionalProperties":False}}]
```

### 4. Pydantic 校验 + 容错解析（生产闭环）

最省事是 `client.messages.parse(..., output_format=PydanticModel)`，直接拿到校验过的对象。但**任何手段都不是 100%**——max_tokens 截断、refusal、边角逻辑约束失败仍会发生。生产闭环 = **抽取 JSON → schema 校验 → 不过就回带错误重试**。这正是今天 `practice.py` 跑的：真连本地 Ollama（`qwen2.5:3b` + `format="json"`）抽 JSON、修尾逗号、按最小 jsonschema 子集校验、违规把错误回带模型重试一次自愈。校验/重试逻辑纯标准库、HTTP 仅用 `urllib`，看懂这条链才能在 SDK 黑盒外做兜底。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic — Structured outputs**（必读，JSON Mode + strict 工具）— https://platform.claude.com/docs/en/build-with-claude/structured-outputs
2. **Anthropic — Tool use overview**（input_schema 即契约）— https://platform.claude.com/docs/en/agents-and-tools/tool-use/overview
3. **Pydantic — 官方文档**（后端做数据校验的事实标准）— https://docs.pydantic.dev/latest/
4. **JSON Schema — 入门**（type/required/enum/range 全在这）— https://json-schema.org/learn/getting-started-step-by-step

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本地 Ollama**手写结构化输出闭环：让模型把一段自由文本抽成 JSON（`format="json"` 走 JSON Mode），用 jsonschema 子集校验，违规就把错误回带给模型重试一次自愈。先补 3 个 `★` 行，再对照文末答案。三个校验/重试函数仍是纯标准库，HTTP 用 `urllib`、无需装包。

```bash
# 前置：装好 Ollama 并起服务、拉模型（练习用 qwen2.5:3b，支持 format="json"）
ollama serve            # 默认 http://localhost:11434
ollama pull qwen2.5:3b
# 然后直接跑（仅 stdlib，无需额外依赖）：
uv run day-15/practice.py
```
预期：Ollama 抽出 `name/age/plan/tags` 四字段；若 plan 越枚举或 age 越界，把错误回带重试一次自愈，最终打印 `✅ 校验通过`，即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击打开 `visualize.html`（纯浏览器、零依赖、深色）。逐句把自由文本喂进去，看它流经 **抽取 → schema 约束 → 校验** 三道闸门变成结构化 JSON：切换 plan/age 看红绿校验灯实时变化，故意写脏文本看尾逗号被修、缺字段被拦。

---

## 🤔 思考题（边做边想）

1. JSON Mode 已保证合法 JSON，为什么生产代码还必须自己再 schema 校验一次？（提示：max_tokens 截断、`minimum`/`maximum` 不被原生支持）
2. 同样要"结构化数据"，什么时候用 JSON Mode、什么时候用 strict tool use？这和你设计 REST 返回体 vs RPC 入参的取舍像不像？
3. 校验失败时"回带错误重试"会增加成本和延迟，你会重试几次、什么时候放弃转人工？（Day 19 错误处理/重试策略会呼应）

> 把答案随手记在 `notes.md`，Day 16 我们从结构化输出走向多模态 API。

# Day 11 — LLM API 基础：Chat Completions API

> **阶段**：Phase 2 · Prompt Engineering 与 LLM API 开发（开篇日）
> **主题**：messages 结构、采样参数（temperature/top_p/max_tokens/stop）、流式 vs 非流式、token 计费
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：一次 LLM 调用，本质就是一个 `POST /v1/messages`——你传一段对话历史和几个超参，它流式吐回 token。今天把这个"超级 RPC"的请求体、参数、计费全部拆清楚，下个 10 天就能把它接进任何后端服务。

---

## 📖 学习内容（约 25 分钟）

### 1. messages 结构：对话就是一个数组（system/user/assistant）

LLM API 是**无状态的**——服务端不记得你上一句说了什么。每次请求你都要把**完整对话历史**当数组传过去。这跟无 session 的 REST 接口一模一样：状态在客户端，每次自带上下文。

三种角色（role）：

| role | 谁说的 | 干啥用 |
|---|---|---|
| `system` | 你（开发者） | 设定人设/规则，整段对话只设一次（Anthropic 单独放 `system` 字段，不放 messages 里） |
| `user` | 终端用户 | 用户的输入 |
| `assistant` | 模型 | 模型上一轮的回复，回传给它当记忆 |

多轮对话 = 自己维护一个 messages 列表，每轮 append 进去：

```python
# Anthropic Claude（model id: claude-opus-4-8）
import anthropic
client = anthropic.Anthropic()  # 读环境变量 ANTHROPIC_API_KEY
msgs = [{"role": "user", "content": "我叫 Alice"}]
r1 = client.messages.create(model="claude-opus-4-8", max_tokens=1024,
        system="你是简洁的后端助手", messages=msgs)
msgs.append({"role": "assistant", "content": r1.content[0].text})
msgs.append({"role": "user", "content": "我叫啥？"})   # 模型记得是因为历史传回去了
```

工程类比：**REST 无 session，状态全在客户端。** 你不传历史，它就"失忆"。

### 2. 四个采样参数：控制"吐字"的随机性与边界

模型每步输出的不是一个词，而是**整个词表的概率分布（logits→softmax）**。这四个参数就是在调这个分布：

| 参数 | 默认/范围 | 直觉 | 工程类比 |
|---|---|---|---|
| `temperature` | 0~1（Claude） | 温度↑分布变平→更随机；温度↓变尖→更确定。0 ≈ 贪心 | 限流"激进系数"：调高更野，调低更稳 |
| `top_p` | 0~1 | 只在累计概率达 p 的最小词集里采样（核采样），砍掉长尾 | 白名单：只保留头部候选 |
| `max_tokens` | 必填 | 最多生成几个 token，到了硬截断 | 响应体大小上限/超时熔断 |
| `stop` | 字符串/列表 | 命中即停，结果不含 stop 串 | 分隔符：读到 `\n\n` 就 break |

记两条：**temperature 和 top_p 别同时狂调**（一个变平一个砍尾，互相打架，通常二选一）；**max_tokens 太小会半句截断**，要给够余量。

> ⚠️ 注意：本课用 claude-opus-4-8 讲"参数概念"，但**真实 Claude Opus 4.8/4.7 已移除 temperature/top_p**，确定性靠 prompt 控制；temperature/top_p 在很多模型（含 sonnet-4-6 之前）仍可用。概念通用，落地查文档。

### 3. 流式 vs 非流式：要不要边吐边收

- **非流式**：一次拿完整回复。代码简单，但 `max_tokens` 大时连接会挂很久、易超时。
- **流式（streaming）**：SSE 逐 token 推回，首字延迟低、可随时取消。聊天 UI、长输出必用。

```python
with client.messages.stream(model="claude-opus-4-8", max_tokens=1024,
        messages=[{"role":"user","content":"写首诗"}]) as s:
    for t in s.text_stream: print(t, end="", flush=True)
```

类比：非流式=`return resp.json()`；流式=Server-Sent Events 边收边渲染。

### 4. token 计费：按"字"收钱，输入输出不同价

token≈词的碎片，1 token≈0.75 英文词。**输入 + 输出分开按量计费**，输出通常贵 5 倍。
账单 = 输入 token×输入价 + 输出 token×输出价（每百万 token 计价）：

| 模型 | 输入 $/1M | 输出 $/1M |
|---|---|---|
| claude-opus-4-8 | 5 | 25 |
| claude-sonnet-4-6 | 3 | 15 |
| claude-haiku-4-5 | 1 | 5 |

省钱三招：选对模型（简单任务用 haiku）、控 `max_tokens`、对固定长前缀开 prompt caching（缓存命中约 0.1×）。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic Messages API 文档**（默认就看这个）— https://docs.anthropic.com/en/api/messages — 请求体、role、参数、stream 字段全在这。
2. **OpenAI Chat Completions 文档**（对照另一家命名）— https://platform.openai.com/docs/api-reference/chat — 同样的 messages/temperature/top_p/stop，名字略不同。
3. **Anthropic 定价页 / models 总览** — https://www.anthropic.com/pricing 与 https://docs.anthropic.com/en/docs/about-claude/models/overview — 实时单价与上下文窗口。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**真连本地 ollama**：对同一个 prompt，分别用 `temperature=0.2` 和 `1.2` 各跑多次，亲眼对比低温复读稳定 / 高温每次发散。纯 stdlib（urllib），无第三方依赖。

```bash
# 前置：先开本地 ollama 并有 qwen2.5:3b
ollama serve            # 另开一个终端
ollama pull qwen2.5:3b  # 首次需拉模型
# 项目用 uv 管理环境，依赖已装好，直接跑：
cd /Users/zqr/projects/daily-learn && uv run day-11/practice.py
# 想换大模型：OLLAMA_MODEL=qwen2.5:7b uv run day-11/practice.py
```

预期：temperature=0.2 几次输出几乎一模一样，=1.2 每次都不同。看到 ★ 两行自己写对、低温稳/高温散，今天就达标。报"连接拒绝"=没开 ollama。

### 🎨 可视化（先玩这个再读理论，更直观）

双击打开 `visualize.html`（纯浏览器，无需安装）。拖 `temperature` 看概率柱状图变尖/变平，拖 `top_p` 看长尾被砍掉，点采样看 1000 次落点分布——亲眼看清两个旋钮怎么塑形输出。

---

## 🤔 思考题（边做边想）

1. temperature=0 和 temperature=2 各适合什么后端场景？（提示：抽取 JSON vs 写营销文案）
2. top_p 砍掉长尾，为啥能既保多样性又防"胡言乱语"？和你给接口加候选白名单像不像？
3. 把 stop 设成 `["\n\n"]` 会怎样？如果输出里本来就该有空行，会踩什么坑？
4. 同样一段长 system prompt 调 1000 次，怎么用 prompt caching 把账单从输入价 5×降到约 0.1×？

> 把答案随手记在 `notes.md`，明天 Day 12 接着讲 Prompt Engineering 与结构化输出。

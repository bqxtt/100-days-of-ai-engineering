# Day 17 — 流式输出与实时交互：SSE、WebSocket 集成模式

> **阶段**：Phase 2 · Prompt Engineering 与 LLM API 开发
> **主题**：为什么要流式、SSE 协议、`stream=true` 怎么解析、WebSocket vs SSE 选型、后端中转模式
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：模型生成一段长回答要好几秒——如果非流式，用户就盯着空白屏幕干等到全文返回。**流式（streaming）** 就是把回答**边生成边发**，一个 token 一个 token 推给前端，打字机效果立刻拉满。技术上它不是黑魔法，就是一条 **HTTP 长连接 + 一行一行 `data:` 事件**（即 SSE）。会读你现有的分块响应，你就会接 LLM 流式。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器，零依赖）。一句回答在非流式里是"等几秒，整段蹦出来"；在流式里是"立刻开始，逐字流出"。页面演示：① 切换 非流式/流式 对比首字延迟 → ② 看 token 逐字打字机吐出 → ③ 右侧实时显示底层 SSE 事件流（`message_start` → 一串 `content_block_delta` → `message_stop`）。看完你就懂：**流式 = 把一坨 response 拆成一连串小 `data:` 事件，逐条解析、逐条上屏**。先玩后读，效果最好。

---

## 📖 学习内容（约 30 分钟）

### 1. 为什么要流式：首字延迟（核心直觉）

非流式：请求发出 → 模型憋完整段 → 一次性返回。一段 500 token 的回答可能憋 6 秒，用户这 6 秒全在等。
流式：请求发出 → 模型生成第一个 token 就推一个 → 用户 ~0.5 秒就看到字在动。

```
非流式：[----------等 6s----------] 整段
流式：  [0.5s] 你 好 ，我 来 帮 你 ...（边生成边到，6s 内陆续填满）
```

衡量两个指标：**TTFT（Time To First Token，首字延迟）** 和 **总时长**。流式不改总时长，但把 TTFT 砍到极低——这是体验质变。后端类比：就是大文件别等全部读完再返回，改成 **chunked / 边读边 flush**，老技术，新用途。

> 还有一个隐藏好处：长输出别等 timeout。一次性等 64K token 的整段返回，连接很容易超时断掉；流式持续有数据流，连接活着，所以 SDK 对大 `max_tokens` 默认就建议流式。

### 2. SSE 协议：流式的底层就这几行

**SSE（Server-Sent Events，服务器推送事件）** 是浏览器原生支持的"服务器单向往客户端推消息"协议。本质是一条不关闭的 HTTP 响应，`Content-Type: text/event-stream`，内容是一行行纯文本：

```
event: content_block_delta
data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"你"}}

event: content_block_delta
data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"好"}}

event: message_stop
data: {"type":"message_stop"}
```

规则就三条：① 一行 `data:` 是一个事件，② 空行表示一个事件结束，③ 客户端逐行读、剥掉 `data: ` 前缀、`json.loads` 解析。浏览器用 `EventSource`，后端只需把 `data:` 拼好往 socket 里写。**没有握手、没有二进制帧，就是文本流**，这是它简单的原因。

### 3. `stream=true` 怎么解析：拼 token

调 Claude（默认示例用 Claude streaming）时加 `stream=true`，返回的不是一个 JSON 而是一串事件。关心的就一种：`content_block_delta` 里的 `text_delta.text`，把它们顺序拼起来 = 完整回答。

```
message_start            → 开场，含元信息
content_block_start      → 一个内容块开始
content_block_delta * N  → 每个就是一小段文本，拼接它们 ← 你只盯这个
content_block_stop       → 块结束
message_delta            → 收尾，含 stop_reason / usage
message_stop             → 全部结束
```

SDK 帮你省事：`client.messages.stream(...)` 直接给 `text_stream` 逐 token 迭代，要全文就 `.get_final_message()`。但今天我们**手撕解析**一遍，看清"剥前缀 → 解析 JSON → 取 delta → 拼接"，这样换任何语言/框架都不慌。本地实战用 ollama（`/api/chat` 每行一个 JSON、`message.content` 是增量），事件形态略有差异，但「逐行读→取增量→拼接」是完全一致的套路。

### 4. WebSocket vs SSE：选型

| 维度 | SSE | WebSocket |
|---|---|---|
| 方向 | 单向（服务器→客户端） | 双向 |
| 协议 | 普通 HTTP，原生 `EventSource` | 独立 `ws://` 握手升级 |
| 复杂度 | 低，重连自动 | 高，要管心跳/重连 |
| 适合 | **LLM 流式回答、通知、进度** | 聊天室、协同编辑、双向实时 |

记一条：**单向把 token 推给前端，SSE 就够，是 LLM 流式的默认选择**；只有需要客户端持续往服务器推（多人协同、语音双工）才上 WebSocket。别为了"实时"就无脑 WebSocket，徒增运维。

### 5. 后端中转模式：API Key 永远别上前端

前端别直连 Claude——Key 会暴露。标准架构是**后端中转（proxy）**：前端连你的后端（SSE），你的后端连 Claude（streaming），把上游每个 delta 转发下来。

```
前端 ──SSE──▶ 你的后端 ──Claude streaming──▶ Claude
  ◀──逐token── (转发上游 delta) ◀──delta 流──
```

中转层顺手干三件事：① 藏 Key、② 鉴权/限流/计费、③ 落库与审计。前端只看到你的 `/chat/stream`，看不到 Claude。这就是 Day 19 生产化要展开的雏形。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic Streaming 官方文档**（今天主线，必读）— https://docs.anthropic.com/en/docs/build-with-claude/streaming — 看 `stream=true` 的事件类型表（`message_start` / `content_block_delta` / `message_stop`）和 SDK `messages.stream()` 用法。
2. **MDN — Server-sent events / Using SSE** — https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events — 弄清 `data:`/`event:` 行格式、`EventSource` 浏览器端、自动重连。
3. **MDN — WebSocket API** — https://developer.mozilla.org/en-US/docs/Web/API/WebSockets_API — 对照看双向协议，理解模块 4 的选型分界。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**真连本地 ollama**（仅标准库，不依赖任何 SDK）：向 `http://localhost:11434/api/chat` POST 一个 `stream=True` 的请求，逐行读响应流，每行 JSON 含一段 `message.content` 增量——手撕一遍流式解析。① body 设 `stream=True` 让模型逐 token 回吐；② 逐行 `json.loads` 拿 `message.content`；③ 边收边上屏 + 顺序拼接出完整回答。完成 3 个 `★` 即达标。

**前置**：本地需启动 ollama 并拉好 `qwen2.5:3b`：

```bash
ollama serve            # 默认监听 http://localhost:11434
ollama pull qwen2.5:3b  # 拉模型（约 1.9 GB）
```

```bash
# 跑：
uv run day-17/practice.py
```

预期：看到 qwen 的回答 token 一个个真"流"出来（打字机效果，每行是 ollama 推的一个增量分片），增量顺序拼接成完整句子，分片数=片段数、长度对得上即一致。这就是 LLM 流式的真实拆解，换 Claude/OpenAI 也是同一套「逐行读 → 取增量 → 拼接」。

---

## 🤔 思考题（边做边想）

1. 流式不缩短总生成时长，只砍 TTFT——为什么用户体验却像"快了一倍"？这和你给慢接口加 loading 占位是不是同一招？
2. SSE 单向就够 LLM 流式，什么场景非 WebSocket 不可？无脑上 WebSocket 的代价是什么？
3. 后端中转转发上游 delta 时，如果前端断了你该不该继续烧 Claude 的 token？怎么优雅取消？
4. 流式回答中途出错（限流/超时）该怎么收尾？已经吐了一半的内容要不要保留？

> 把答案记进 `notes.md`，Day 18 我们讲 Prompt 模板管理（版本控制、A/B 测试、评估框架）。

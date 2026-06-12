# Day 46 — MCP（Model Context Protocol）：理解 MCP 协议

> **阶段**：Phase 4 · AI Agent 开发
> **主题**：MCP = AI 的「USB-C 接口」标准——一套统一协议，让任何宿主接任何工具源，告别 N×M 私有对接
> **预计耗时**：约 1 小时（30 分钟读懂三角 + 三类能力，20 分钟手写 JSON-RPC 握手，10 分钟思考）
> **给后端工程师的一句话**：MCP（模型上下文协议 / Model Context Protocol）就是给 LLM 工具世界定的**统一接口协议**——Day40 你为单个模型写工具，那是私有插头；MCP 把它标准化，让 Claude Desktop / Cursor / 你的 Agent 任意接「任意人写的工具 Server」。一份固定消息格式（`initialize`/`tools/list`/`tools/call`，跑在 JSON-RPC 上）就是全部精髓，跟 OpenAPI 之于微服务、LSP 之于编辑器是同一招。

---

## 📖 学习内容（约 30 分钟）

### 0. 一句话：MCP = AI 工具的「USB-C」
没 USB-C 之前，每个设备一种插头（N 个 Host × M 个工具 = N×M 套私有对接）。MCP 出一个标准口：工具方写一次 **Server**，宿主方写一次 **Client**，谁都能插谁——N+M 取代 N×M。所以它叫**协议（protocol）**，不是框架、不是库，就是「报文长什么样」的约定。

### 1. Host / Client / Server 三角（Host=宿主 Client=客户端 Server=服务端）
```
 Host(宿主)  Claude Desktop / Cursor / 你的 Agent —— 装着 LLM，决定调谁
   │  每个外部源开一个↓
 Client(客户端) 由 Host 内置 —— 1 对 1 连一个 Server，负责握手+收发报文
   │  ↓ JSON-RPC
 Server(服务端) 暴露能力的进程 —— GitHub / Postgres / 文件系统 / 你写的工具
```
后端类比：**Host=网关进程，Client=每个上游的连接客户端，Server=各微服务**。Client↔Server 一对一，Host 管所有 Client——和你的网关连多个后端是一回事。

### 2. 三类能力：tools / resources / prompts
| 能力 | 是什么 | 谁控制 | 后端类比 |
|---|---|---|---|
| **tools**（工具） | 可执行函数，模型点名调用 | 模型决定调 | POST 接口 / RPC 方法 |
| **resources**（资源） | 可读数据，按 URI 取（文件/表/文档） | 宿主/用户选 | GET 接口 / 只读视图 |
| **prompts**（提示词） | 预制提示模板，用户触发 | 用户选 | 存储过程 / 快捷命令 |
今天重点是 **tools**（占 90% 用途），`tools/list` 发现、`tools/call` 调用——和 Day40 的工具定义一模一样，只是套进了标准信封。

### 3. JSON-RPC over stdio / SSE：传输是 JSON-RPC 2.0
消息体永远是 `{"jsonrpc":"2.0","id":1,"method":...,"params":...}`，结果回 `result`、失败回 `error`。跑在两种管道上：本地 Server 用 **stdio**（标准输入输出，进程间管道）；远程用 **SSE/HTTP**（Server-Sent Events）。三步握手雷打不动：`initialize`（宣告版本+能力）→ `tools/list`（发现）→ `tools/call`（调用）。**协议=方法名+信封固定，传输=换根管子，能力=填工具——三层正交。**

### 4. 为什么是「协议」而非「库」：可组合性
你换 Host（Claude→Cursor）、换 Server（自写→官方 GitHub Server），代码一行不改，因为报文不变。这就是 LSP 让 VSCode 接任何语言的同款套路。背后是 Anthropic 2024-11 开放的标准，已成事实生态。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **MCP 官网**（最快入门，三角图+概念）— https://modelcontextprotocol.io/
2. **MCP 协议规范 spec**（initialize/tools/list/tools/call 报文逐字定义）— https://spec.modelcontextprotocol.io/
3. **Anthropic 发布公告**（为何造 MCP、N×M 问题）— https://www.anthropic.com/news/model-context-protocol
4. **Ollama API 文档**（今天 chat 用的 /api/chat 标准写法）— https://github.com/ollama/ollama/blob/main/docs/api.md

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：手写一个极简 MCP 风格的 JSON-RPC `Server`+`Client`，跑通三步握手（`initialize`→`tools/list`→`tools/call`），再把工具结果喂给 qwen2.5:3b 作答。先补 5 个 `★` 行，再对照文末答案。HTTP 只用 `urllib`，不装 mcp 包——重在看清协议消息格式。

```bash
ollama serve                       # 默认 http://localhost:11434
ollama pull qwen2.5:3b             # 1.9GB 小模型；OLLAMA_MODEL 可覆盖
uv run day-46/practice.py          # 进程内演示三步握手 + 喂模型
```
预期：`→/←` 行打印出真实 MCP 报文（带 `jsonrpc`/`method`/`result`），末尾 🤖 用工具真值答天气——即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击打开 `visualize.html`（纯 canvas、零依赖、深色 `#0e1117`）。把三步握手做成可单步：点一下走一格——Client 发 `initialize` → Server 回能力 → `tools/list` 发现 → `tools/call` 调用 → 结果回灌，左侧亮 Host/Client/Server 三角。亲眼看一条 JSON-RPC 报文怎么在三角里跑完一圈。

---

## 🤔 思考题（边做边想）

1. tools / resources / prompts 谁控制谁：哪类是「模型自己决定调」、哪类是「用户/宿主选」？映射到你后端的 POST/GET/存储过程，分别对应哪个？
2. 一个 Server 想挂上 Claude Desktop 和你自写 Agent 两个 Host，要改 Server 代码吗？为什么——协议保证了什么不变？
3. 把 stdio 换成 SSE/HTTP，`practice.py` 的 `MiniMCPClient.call` 要改哪一行？协议层（方法名+信封）会变吗？

> 把答案记在 `notes.md`。下一步把 mini Server 换成进程间 stdio，就是一个能挂进 Claude Desktop 的真 MCP Server。

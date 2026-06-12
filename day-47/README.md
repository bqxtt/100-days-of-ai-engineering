# Day 47 — MCP 实践：开发自定义 MCP Server

> **阶段**：Phase 4 · AI Agent 开发（Day46 懂协议 → 今天动手焊一个）
> **主题**：纯标准库手写一个完整 MCP Server（stdio + JSON-RPC 2.0），暴露 3 个真工具，Client subprocess 拉起跑通 initialize/tools/list/tools/call 完整握手，再把工具接到 Ollama agent loop。
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：MCP Server（Model Context Protocol，模型上下文协议）= 一个 **stdin 收请求 / stdout 回响应的微服务**，只不过传输是 stdio 而非 HTTP，协议是 JSON-RPC 2.0（`{id,method,params}` → `{id,result}`）。你写过的任何「读一行、路由 method、回一行」服务就是它。今天手写一遍看清协议本体，造出的 server 能**原样挂进 Claude Desktop / Code**。

---

## 📖 学习内容（约 25 分钟）

### 1. MCP Server = stdio 上的 JSON-RPC 微服务
没有框架时它就这么朴素：循环读 stdin 每一行 → 是一个 JSON-RPC 请求 `{"id":1,"method":"tools/call","params":{...}}` → 路由到对应处理 → 把 `{"id":1,"result":{...}}` 写回 stdout。后端类比：和你的 RPC handler 一模一样，**transport（传输）从 TCP/HTTP 换成 stdio 管道**，**method 路由表**就是 `if method=="..."`。Client 不用知道 server 是 Python 还是 Rust——协议解耦。

### 2. 三个必备 method：握手 → 发现 → 调用
| method | 角色 | 一句话 |
|---|---|---|
| `initialize` | 握手 | 交换 protocolVersion + serverInfo，确认能通话 |
| `tools/list` | 发现（discovery） | server 自报有哪些工具 + inputSchema |
| `tools/call` | 执行（invoke） | 带 name+arguments，server 真跑、回 content |
这三步就是 MCP 的心跳：先握手，再问"你有啥工具"，再"帮我调这个"。返回的 `content:[{type:"text",text}]` 是标准信封。

### 3. 工具的 inputSchema 就是 JSON Schema = function calling 同形
MCP 工具描述用 `inputSchema`（JSON Schema），和 OpenAI/Ollama 的 `function.parameters` **同一种结构**。所以 `tools/list` 拿到的清单**一行转换就能喂给模型**——这是 MCP 的杀手锏：写一次 server，任何支持 tool_call 的模型都能用。

### 4. 官方 python-sdk：省去手写 JSON-RPC
生产别手搓。`pip install mcp` 后用 `FastMCP`，`@mcp.tool()` 装饰一个函数即注册，stdio transport / 握手 / schema 全自动。手写一遍只为看清下层；明白后切 SDK 几行就起一个能被 Claude Desktop 复用的 server。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **官方 Python SDK**（FastMCP，生产首选）— https://github.com/modelcontextprotocol/python-sdk
2. **Build a Server 快速上手**（5 分钟起一个真 server）— https://modelcontextprotocol.io/quickstart/server
3. **MCP 规范**（JSON-RPC 信封、initialize/tools 全字段）— https://spec.modelcontextprotocol.io
4. **JSON-RPC 2.0 规范**（id/method/params/result 本体）— https://www.jsonrpc.org/specification

---

## 💻 动手练习（约 20 分钟）

`practice.py` **纯标准库**，双角色：默认跑 client，自己 `subprocess` 拉起自己当 server。补 5 个 `★` 行（serve 路由 + client 握手/调用 + agent 接线），再对照文末答案。

```bash
ollama serve                       # 默认 http://localhost:11434
ollama pull qwen2.5:3b             # 支持 tool_calls 的小模型
uv run day-47/practice.py          # client 拉起 server，跑完整握手 + agent loop
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | uv run day-47/practice.py --serve  # 裸调 server
```
预期：打印 `initialize -> day47-notes`、`tools/list -> [note_add,note_list,list_files]`、🔧 行是模型自主走 MCP 调的工具，末尾出报告——即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击 `visualize.html`（纯 canvas、零依赖、深色 `#0e1117`）。单步走 Client↔Server 的 JSON-RPC 往返：每点一下发一条请求、管道流过、server 路由、回 result，看 initialize→tools/list→tools/call 三步握手报文逐条点亮。

---

## 🤔 思考题（边做边想）

1. server 用 stdio 而非 HTTP，对「一个 Client 拉起多个 Server」有何好处？子进程崩了 client 怎么知道？
2. `tools/list` 的 inputSchema 能直接喂 Ollama——若 server 加个 `note_delete`，client/agent 哪几行需改？哪几行零改？
3. 手写版 vs 官方 SDK：换 `FastMCP` 后你这 3 个工具改几行？为什么说 server 能「原样挂 Claude Desktop」？

> 答案记进 `notes.md`。下一步把手写 server 换成官方 SDK，再写进 `claude_desktop_config.json` 真用起来。

# Day 47 笔记 · MCP 实践：开发自定义 MCP Server

## 思考题答案
1. stdio 而非 HTTP 的好处（多 server / 子进程崩了怎么知道）：

2. 加 note_delete 工具：client/agent 哪几行要改、哪几行零改（schema 自动转 function）：

3. 手写版换 FastMCP 改几行 / 为什么能「原样挂 Claude Desktop」：

## 协议三步握手（各记一条要点）
- initialize（握手）：交换 protocolVersion + serverInfo，
- tools/list（发现）：server 自报工具 + inputSchema，
- tools/call（调用）：name+arguments → content[{type:text}]，

## 关键认知
- MCP Server = stdio 上的 JSON-RPC 微服务（transport 换 stdio，路由还是 method 表）：
- inputSchema = JSON Schema = function calling 同形，一行转换喂模型：
- 手写一遍 vs 官方 python-sdk（FastMCP/@tool）的取舍：

## 实战观察（跑 uv run 看 🔧 行）
- 模型自主调了哪几个 MCP 工具、顺序对不对：
- 裸调 `--serve`（echo JSON | ...）回了什么：

## 今日卡点 / 疑问

## 一句话总结
自定义 MCP Server = stdin 收 JSON-RPC、stdout 回 result 的微服务：initialize 握手→tools/list 发现→tools/call 执行，工具 schema 直接喂模型，手写能跑、生产用 python-sdk，server 可复用进 Claude Desktop/Code。

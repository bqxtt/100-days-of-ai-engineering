# Day 46 笔记 · MCP（Model Context Protocol）理解 MCP 协议

## 思考题答案
1. tools/resources/prompts 谁控制谁，映射后端 POST/GET/存储过程：
   - tools=模型决定调（≈POST/RPC）；resources=用户/宿主选（≈GET/只读视图）；prompts=用户触发（≈存储过程/快捷命令）

2. 一个 Server 挂两个 Host 要不要改代码、协议保证了什么不变：

3. stdio 换 SSE/HTTP 改哪行、协议层会不会变：

## 核心要点（各记一条）
- MCP=AI 工具的「USB-C」：N+M 取代 N×M，是协议不是库：
- 三角 Host/Client/Server：Host 装 LLM，Client 1对1 连 Server，Server 暴露能力：
- 三类能力 tools/resources/prompts：
- 传输 JSON-RPC over stdio/SSE：信封 {jsonrpc,id,method,params/result} 固定：
- 三步握手 initialize → tools/list → tools/call：

## 实战观察（跑 uv run 看 →/← 报文）
- 三步握手报文格式、result 里 content 怎么取：
- 工具值喂给 qwen2.5:3b 后回答如何：

## 今日卡点 / 疑问

## 一句话总结
MCP = AI 工具的统一接口协议（USB-C），Host/Client/Server 三角靠 JSON-RPC 三步握手（initialize/tools/list/tools/call）解耦工具与宿主，跟 OpenAPI/LSP 同款套路。

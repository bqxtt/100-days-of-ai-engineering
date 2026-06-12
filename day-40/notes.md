# Day 40 笔记 — Tool 设计原则

## 核心：工具 = 给 LLM 用的 REST API
- 调用者从「人/前端」换成模型，文档烂的后果一样：传错参、循环、报错。
- 六要素：清晰 name + 好 description + JSON Schema + 友好 error + 幂等 + 粒度合适。

## practice 实测（qwen2.5:3b 真跑）
- 差工具 `do_stuff` 模糊 desc + 空 schema → 模型乱编参数名（`old_location`、order_id 当字符串）→ 校验失败。
- 好工具 `transfer_order` 严格 schema + 示例 desc → 模型一次调对。
- 同一模型，差别全在工具设计。**desc 和 schema 就是 prompt**。

## 三条带走
1. error 回报模型 ≠ 崩溃：返回 `{"ok":False,"error":...}` 让模型自纠（像 422+body）。
2. enum + required 是最便宜的护栏，等于 DB 外键/约束。
3. 幂等防重试翻车：超时重发同一 tool_call 不能扣两次款。

## 类比锚点
RESTful 命名→tool name；OpenAPI summary→description；request validation→JSON Schema；422→error 回报；PUT→幂等；单端点单职责→粒度。

## 资源
- Anthropic Writing tools for agents: https://www.anthropic.com/engineering/writing-tools-for-agents
- Ollama tool support: https://ollama.com/blog/tool-support

## ★ 答案：calc_tax 工具 desc 清晰 + amount/region(enum CN/US) required + 幂等同输入恒输出，见 practice.py 底部 ANSWER。

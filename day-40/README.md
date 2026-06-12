# Day 40 — Tool 设计原则：如何为 Agent 设计好用的工具

> Phase 4 · Day 40 · 后端工程师 · 1 小时/天
> **一句话**：给 Agent 设计工具（tool）就是给「调用者是 LLM」的 REST API —— 名字、说明书、参数契约、错误码一样不能少。

---

## 📖 模块一：概念

Agent 靠 **工具（tool / function calling）** 干实事。坏工具让模型瞎调、崩溃、循环；好工具让模型一次调对。好工具六要素：

1. **清晰 name** —— `transfer_order` 而非 `do_stuff`，像 RESTful 路由 `POST /orders/transfer`。
2. **好 description** —— 写清「何时用、怎么用、单位、示例」，像 OpenAPI summary。
3. **JSON Schema 参数** —— 必填/类型/枚举，像请求体校验（request validation）。
4. **友好 error** —— 把 `{"error": "..."}` 回报给模型让它自纠，而非抛异常崩掉，像返回 422+body 而非 500。
5. **幂等（idempotent）** —— 同输入多次调用结果一致、无副作用，像 PUT/GET。
6. **粒度合适（granularity）** —— 一个工具干一件事，别糊成 `/everything`。

**类比**：你设计的 REST API 给前端用，文档烂前端就乱传参；工具的「前端」是 LLM，desc 烂模型就猜错 → name/desc/schema 就是给模型的 API 文档。

## 🔗 模块二：资源

- Anthropic《Writing tools for agents》: https://www.anthropic.com/engineering/writing-tools-for-agents
- Ollama tool support: https://ollama.com/blog/tool-support

## 💻 模块三：实操

`practice.py`：同一任务给「差工具 vs 好工具」，真调本地 ollama qwen2.5:3b 对比成功率。

```bash
ollama pull qwen2.5:3b      # 需支持 tools 的模型
uv run practice.py
```

观察：差工具 desc 模糊+无 schema，模型乱起参数名（`old_location`/字符串 order_id）→ 失败；好工具 schema 严格 → 一次调对。校验把 error 回报模型，不崩。

## 🤔 模块四：思考

1. 为什么把 error 字符串回给模型比抛异常更好？模型能用错误信息做什么？
2. 幂等为何重要？Agent 可能因超时重试同一调用——非幂等工具会怎样？
3. 一个 `manage_order(action=...)` 大工具 vs 拆成 `create/cancel/transfer` 三个小工具，各自代价？
4. `enum` 限定仓库代码，比让模型自由填字符串好在哪？类比数据库外键。

**术语**：tool/工具，schema/参数契约，idempotent/幂等，granularity/粒度，affordance/可供性。

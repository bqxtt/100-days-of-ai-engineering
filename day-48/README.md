# Day 48 — Agent 的可观测性：日志、追踪、LangSmith

> **阶段**：Phase 4 · AI Agent 开发（Day 48）
> **主题**：让黑盒 Agent 变透明——给每一步 LLM/工具调用记一条 **Span**，串成 **Trace**，量化 token/延迟/成本（Metrics），亲手写一个追踪装饰器，真跑一遍 agent loop 打印结构化 trace 树。
> **预计耗时**：约 1 小时（25 分读 + 15 分资源 + 20 分手写追踪器）
> **给后端工程师的一句话**：Agent 可观测性 = **分布式追踪那套，原样搬到 LLM 上**。Trace=一次请求全链路、Span=链路里一段调用、Metrics=token/延迟/成本指标，对应你早就会的 OpenTelemetry / APM（Jaeger、SkyWalking）。LangSmith / Langfuse 就是「专给 LLM 的 Jaeger+Grafana」，今天先不依赖它们，自己手写一个 50 行的迷你版看清原理。

---

## 📖 学习内容（约 25 分钟）

### 0. 为什么 Agent 必须可观测：黑盒会咬人
单 Agent 一跑就是 5~8 步、每步一次 LLM + 几次工具，任何一步都可能慢、可能烧 token、可能调错工具。出问题只看最终报告等于**线上 500 却没装日志**。可观测性回答三问：慢在哪步、钱花哪、为什么调错。后端早有答案——把分布式追踪搬过来。

### 1. 三件套：Trace / Span / Metrics（中英术语 + 后端类比）
| 概念 | 英文 | 后端类比 | 在 Agent 里是什么 |
|---|---|---|---|
| 追踪 | **Trace** | 一次 HTTP 请求的全链路 | 一次 `run_agent(goal)` 从开始到出报告 |
| 跨度 | **Span** | 链路里一段调用（DB 查询、RPC） | 一次 LLM 调用 / 一次工具执行 |
| 指标 | **Metrics** | QPS、P99 延迟、CPU | 每步 token / 延迟 / 成本估算 |
| 父子 | **parent/child** | trace_id + span_id 串调用栈 | loop 是父，每步 LLM/工具是子 |
| 属性 | **attributes** | tag/label | model、tool 名、输入输出片段 |

**Trace = 一棵树**：根是整个 agent run，分支是每一步，叶子是 LLM 调用和工具调用。看树就知道全貌。

### 2. 每步要记什么：name / 输入 / 输出 / 耗时 / token
一个 span 至少抓五样：`name`（llm.call / tool.read_file）、`input`（messages 或参数）、`output`（回复或返回值）、`latency_ms`（结束-开始）、`tokens`（prompt+eval）。token×单价=**成本**。这正是 OpenTelemetry GenAI 语义约定里 `gen_ai.usage.input_tokens` / `gen_ai.request.model` 那批字段——业界已把它标准化，不是各家乱记。

### 3. 怎么记：包装器/装饰器，不污染业务逻辑
后端类比拦截器（interceptor）/ AOP：在「真调用」外裹一层，进时记开始、出时算耗时+token、塞进当前 trace。业务代码不动，包一层就有追踪。本机 Ollama 真回 `prompt_eval_count`/`eval_count`/`total_duration`——直接拿来当 token 与延迟，不用估。

### 4. LangSmith / Langfuse 替你做什么
手写够看原理，生产用平台：自动拦截每次调用、Web 看 trace 瀑布图、存历史、聚合成本/延迟仪表盘、回放 prompt、做数据集评测。**LangSmith**=LangChain 官方托管；**Langfuse**=开源可自托管。一行 `@traceable` 或 callback 就把今天的手写盘上云。**OpenTelemetry GenAI** 是中立标准，三家字段都向它对齐——学标准比学某家平台更值。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **LangSmith 文档**（LangChain 官方追踪/评测平台）— https://docs.smith.langchain.com/
2. **Langfuse 文档**（开源可自托管，trace/成本/评测）— https://langfuse.com/docs
3. **OpenTelemetry GenAI 语义约定**（中立标准字段，今天 span 就照它命名）— https://opentelemetry.io/docs/specs/semconv/gen-ai/
4. **OpenTelemetry 追踪概念**（Trace/Span 本体，后端通用）— https://opentelemetry.io/docs/concepts/signals/traces/

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：手写一个 `Span` 包装器 + 全局 trace，跑一个 mini agent loop（真调 qwen2.5:3b + 模拟工具），每步记 name/输入/输出/耗时/token，结束打印一棵带成本汇总的 **trace 树**。先补 5 个 `★`，再对照文末答案。HTTP 只用 `urllib`，无需装包，不依赖 LangSmith。

```bash
ollama serve                       # 默认 http://localhost:11434
ollama pull qwen2.5:3b             # 1.9GB 小模型；OLLAMA_MODEL 可覆盖
uv run day-48/practice.py          # 真跑一遍，看结构化 trace 树
```
预期：末尾打印一棵 trace 树，每个 span 有耗时(ms)/token/成本，根节点汇总总延迟+总 token+总成本——即达标。token/延迟来自 Ollama 真实返回字段，不是 mock。

### 🎨 可视化（先玩这个再读理论）
双击 `visualize.html`（纯 canvas、零依赖、深色 `#0e1117`）。单步展开一条 trace：根 span 出现 → 子 span（llm.call / tool.run）逐个落位成瀑布图，每条按耗时排长短、标 token，右侧成本累加。一眼看清「慢在哪步、钱花哪」——就是 LangSmith 那张瀑布图的极简版。

---

## 🤔 思考题（边做边想）

1. trace 树为什么要 trace_id + parent_span_id？换成只打一行行日志会丢什么？（对比你查 P99 时只有散日志的痛）
2. 成本=token×单价。本地 Ollama 免费，那 token 指标还有什么用？（接 Day50 上线后切云模型）
3. 给 span 加采样（10% trace 才记全量）——后端为何这么干？Agent 调试期该开还是关？
4. LangSmith/Langfuse 上传 input/output 含用户数据，自托管 vs 托管怎么选？合规边界在哪？

> 把答案记在 `notes.md`，写一条 Phase 4 可观测性复盘。下一步 Day49 权限/安全，Day50 部署——可观测是上线前必备底座。

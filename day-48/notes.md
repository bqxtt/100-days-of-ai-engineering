# Day 48 笔记 · Agent 可观测性（Trace / Span / Metrics / LangSmith）

## 思考题答案
1. trace 树为什么要 trace_id + parent_span_id？只打散日志会丢什么：

2. 本地 Ollama 免费，token 指标还有什么用（接 Day50 切云模型）：

3. trace 采样（10% 全量）后端为何这么干？调试期开还是关：

4. LangSmith/Langfuse 上传 input/output 含用户数据，自托管 vs 托管怎么选、合规边界：

## 三件套对照（后端 → Agent，各记一句）
- Trace（一次请求全链路 → 一次 run_agent）：
- Span（一段调用 → 一次 LLM/工具）：
- Metrics（QPS/P99 → token/延迟/成本）：
- OpenTelemetry GenAI 字段（gen_ai.usage.* / gen_ai.request.model）：
- LangSmith vs Langfuse（托管 vs 开源自托管）：

## 实战观察（跑 uv run 看 trace 树）
- 哪步耗时最长、占总延迟多少：
- 两次 llm.call 的 token 差多少、为什么：
- 工具 span 耗时 vs LLM span 耗时量级：

## 今日卡点 / 疑问

## 一句话总结
Agent 可观测性=分布式追踪搬上 LLM：每步包成 Span 串成 Trace，量化 token/延迟/成本；手写 50 行=LangSmith/Langfuse 内核。

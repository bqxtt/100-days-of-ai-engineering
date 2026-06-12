# Day 19 — 生产化考量：成本优化、速率限制、错误处理、重试策略

> **阶段**：Phase 2 · Prompt Engineering 与 LLM API 开发
> **主题**：prompt 缓存/模型分级降本、rate limit 应对、429 指数退避重试、超时熔断
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：这天没有新模型概念，全是你最熟的活——限流、重试、熔断、对账。区别只是把"调下游服务"换成"调 LLM API"。Token 就是钱、429 就是限流、5xx 就是过载。会扛流量峰值的后端，天生会做 LLM 生产化。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器、零依赖）。三块画布：① **令牌桶限流**——令牌按速率往桶里滴，请求来了拿一个，桶空就排队；② **重试退避时间线**——429 后等待越来越长（指数退避 + 抖动），看清"惊群"为什么要加 jitter；③ **成本累计**——每次调用按 token 计费，看缓存命中如何把曲线压平。先玩后读，限流和退避的"形状"一眼就懂。

---

## 📖 学习内容（约 30 分钟）

### 1. 成本优化：prompt 缓存 + 模型分级（省钱大头）

LLM 成本 = `input_token × 单价 + output_token × 单价`。两个最有效的杠杆：

- **Prompt 缓存**：重复的前缀（system、长文档、few-shot）缓存后**只收 ~0.1 倍**；写缓存 1.25 倍。一份 5 万 token 的文档反复问，缓存能省约 80%+。前缀必须**逐字节稳定**——别把 `now()`、UUID 塞进 system，否则缓存全失效。
- **模型分级**：简单分类/抽取用 Haiku（$1/$5），主力用 Opus 4.8（$5/$25），非实时批量走 Batch API 再砍 50%。别为省钱擅自降级——但该用小模型的活别用大模型。

| 模型 | 输入 $/1M | 输出 $/1M | 用在哪 |
|---|---|---|---|
| Opus 4.8 | $5 | $25 | 主力、难任务 |
| Haiku 4.5 | $1 | $5 | 分类/抽取/限速敏感 |
| 缓存读 | ~0.5 | — | 重复前缀，省 ~90% |

文档：Prompt caching — https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching ｜ Pricing — https://docs.anthropic.com/en/docs/about-claude/pricing

### 2. Rate Limit 应对：令牌桶 + 配额头

Anthropic 按 **RPM/ITPM/OTPM**（每分钟请求/输入 token/输出 token）限流，超了返回 **429** + `retry-after`。生产做法：客户端用**令牌桶**主动控速，别等 429 才慌；读响应头 `anthropic-ratelimit-*-remaining` 提前降速。这就是你给下游接口加限流的同一套——`practice.py` 里 50 行手写一个。

文档：Rate limits — https://docs.anthropic.com/en/api/rate-limits

### 3. 429 重试：指数退避 + 抖动

可重试的：**429 / 500 / 529(过载)**；不可重试：**400/401/403/404** 等 4xx——重试也白搭，直接抛。退避 `delay = min(cap, base·2^n) + jitter`：指数让压力指数下降，**抖动**避免所有客户端同时回来造成"惊群"。SDK 默认 `max_retries=2`，需要更多就改参数，别盲目造轮子。

文档：Errors — https://docs.anthropic.com/en/api/errors

### 4. 超时熔断：别让一个慢请求拖垮全局

设置请求 timeout；连续失败就**熔断**（短路一段时间不再打），把快失败留给降级路径（小模型/缓存/兜底文案）。流式输出能避免高 `max_tokens` 撞 HTTP 超时——长输出一定 stream。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic Rate Limits（必读）** — https://docs.anthropic.com/en/api/rate-limits — 看清 RPM/ITPM/OTPM 三类配额与响应头。
2. **Prompt Caching** — https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching — 降本第一杠杆，注意"前缀逐字节稳定"。
3. **Errors & 重试指南** — https://docs.anthropic.com/en/api/errors — 哪些码该退避、哪些直接放弃。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`：手写 ① 令牌桶限流 ② 指数退避重试 ③ 成本估算。令牌桶先控速、再真调本地 ollama `qwen2.5:3b`，用 ollama 真回吐的 `prompt_eval_count/eval_count` 算成本；429 退避用模拟状态码演示。先补 3 个 ★ 行再对答案。

```bash
ollama serve            # 默认监听 http://localhost:11434
ollama pull qwen2.5:3b  # 一次性拉模型
uv run day-19/practice.py
```

预期：4 个真请求被令牌桶放行后调通、429 退避两次后成功、用真实 token 估出成本与缓存省额。能跑出这三段就达标。

---

## 🤔 思考题（边做边想）

1. 令牌桶 vs 漏桶，应对突发流量哪个更友好？为什么 RPM 这种配额天然适合令牌桶？
2. 退避里的 jitter 删掉会怎样？和你线上重试风暴的经历像不像？
3. 哪些钱靠"缓存"省、哪些靠"换小模型"省？把 system prompt 里塞个时间戳，缓存为什么就失效了？

> 答案随手记 `notes.md`，明天 Day 20 用今天的限流+重试+成本控制，搭一个带 Tool Use 的命令行助手。

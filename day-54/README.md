# Day 54 — Agent 生产化部署：容错、扩展、成本控制

> **阶段**：Phase 4 · AI Agent 开发（Day44-53 已经把多 Agent / 协作 / 记忆焊起来，今天把它送上生产线）
> **主题**：能跑通 ≠ 能上线。生产化 = 把 Day42 那个裸 ReAct 循环包上三层护甲——**容错**（重试/超时/降级 fallback）、**扩展**（并发/队列/无状态）、**成本控制**（小模型路由/语义缓存/step 预算）
> **预计耗时**：约 1 小时（跑通 practice 看故障重试+缓存命中，读 4 模块，做思考题）
> **给后端工程师的一句话**：你给订单服务做的高可用、限流、熔断、缓存——**一模一样地搬给 Agent**。LLM 调用就是个慢、贵、还会偶发抽风的下游接口；retry/timeout/fallback 是熔断，并发/队列是水平扩展，缓存+小模型路由是省钱。今天手写一个带这全套护甲的 agent runner，真连 ollama，**亲眼看一次故障被重试救回、一次重复 query 被缓存零调用挡掉**。

---

## 📖 学习内容（约 25 分钟）

### 1. 容错（Fault Tolerance）= 重试 + 超时 + 降级 fallback
LLM 接口会超时、会 5xx、会偶发空回。生产 Agent 不能一抖就崩：
- **超时（timeout）**：每次调用卡死阈值，到点就掐——别让一个慢请求拖垮整条链。
- **重试（retry）**：失败按**指数退避**（1s→2s→4s）重试 N 次，避开瞬时抖动。
- **降级（fallback）**：N 次都挂，不抛错给用户——返回兜底答案 / 切小模型 / 给缓存旧值。
> 后端类比：**熔断 + 重试 + 降级**（Hystrix/Resilience4j）。下游挂了你不会 500 给前端，而是返回兜底页。Agent 同理。

### 2. 扩展（Scale）= 并发 + 队列 + 无状态
单条 ReAct 跑 30s，1000 个用户排队就是噩梦：
- **无状态（stateless）**：runner 本身不存状态，状态全在传入的 `messages`——才能随便加机器水平扩。
- **并发（concurrency）**：多请求用线程池/进程池同时打 LLM，吞吐量翻倍。
- **队列（queue）**：洪峰用队列削峰，worker 按容量消费，挡住打爆模型服务。
> 后端类比：**无状态服务 + Nginx 负载均衡 + Kafka 削峰**。状态进 messages/Redis，机器随便加。

### 3. 成本控制（Cost）= 小模型路由 + 缓存 + step 上限
每次调用都烧钱/烧算力，省钱三连：
- **小模型路由（routing）**：简单 query 走 3b，复杂的才升 7b——别拿大炮打蚊子。
- **语义缓存（cache）**：相同/相似问题直接返缓存，**零调用**。命中率高，账单腰斩。
- **step 预算（budget）**：ReAct 循环上限封死，防止打转烧穿预算（Day42 的 8 步护栏就是雏形）。
> 后端类比：**读多写少上 Redis 缓存 + 限流 + 慢查询熔断**。缓存命中 = 不查库；step 上限 = 单请求资源封顶。

### 4. 三件事是同一套工程思维
高可用从不是「写更聪明的核心」，而是「假设下游必挂、流量必爆、预算必紧」后加护栏。Agent 的核心循环 Day42 就写完了——生产化加的全是**外围护甲**，一行核心逻辑都不用动。这正是后端十年沉淀的可靠性工程，平移到 LLM 而已。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic — Building Effective Agents**（生产 Agent 圣经：简单优先、护栏/循环/成本设计）— https://www.anthropic.com/engineering/building-effective-agents
2. **Ollama API 文档**（`/api/chat` 标准、超时与参数）— https://github.com/ollama/ollama/blob/main/docs/api.md
3. **AWS — Exponential Backoff and Jitter**（重试退避算法，容错地基）— https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
4. **Martin Fowler — CircuitBreaker**（熔断/降级模式，平移到 LLM 调用）— https://martinfowler.com/bliki/CircuitBreaker.html

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：手写一个生产级 agent runner——**重试+超时**容错、**语义缓存**省调用、**step 预算**封顶，真调 qwen2.5:3b。脚本会故意制造一次故障演示重试救回，再发两个重复 query 演示缓存命中**零调用**。先补 5 个 `★` 行，再对照文末答案。HTTP 只用 `urllib`，无需装包。

```bash
ollama serve                       # 默认 http://localhost:11434
ollama pull qwen2.5:3b             # 1.9GB 小模型；OLLAMA_MODEL 可覆盖
uv run day-54/practice.py          # 看 🔁 重试、💾 缓存命中、💰 节省统计
```
预期：日志里有一次 `🔁 重试` 后成功、第二个重复问题打 `💾 命中`、末尾报告「N 次提问只真调了 M 次，省了 X 次」——即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击打开 `visualize.html`（纯 canvas、零依赖、深色 `#0e1117`）。单步看一条请求过三道护甲：缓存命中→直返；未命中→带超时调 LLM→失败就退避重试→重试耗尽就 fallback。右侧账单随缓存命中实时下降，亲眼看「容错救回一次崩」「缓存省下一次调用」。

---

## 🤔 思考题（边做边想）

1. 重试用**固定 1s** vs **指数退避**，对下游已经过载的模型服务有什么区别？（提示：雪崩）
2. 语义缓存现在按「问题完全相同」命中。要做到「相似问题也命中」，键该换成什么？会引入什么新风险？
3. fallback 返回兜底答案，用户体验是「降级」不是「报错」。但 fallback 也可能掩盖故障——监控上要补哪个指标才不被蒙在鼓里？

> 把答案记在 `notes.md`，并写 Day54 生产化复盘。下一步把无状态 runner 丢进队列+线程池，就是真正能扛流量的 Agent 服务。

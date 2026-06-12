"""
Day 48 实战：Agent 可观测性——手写 Trace/Span/Metrics（真连 Ollama，纯标准库）。
给黑盒 agent loop 装上「分布式追踪」：每步 LLM/工具调用记一条 Span，串成一棵 Trace，
每个 Span 抓 name/输入/输出/耗时/token，末尾打印结构化 trace 树并汇总总延迟+总 token+成本。

后端类比：这就是 OpenTelemetry / Jaeger 那一套——Trace=一次请求全链路，Span=链路里一段调用，
        Metrics=每步 token/延迟/成本。LangSmith/Langfuse 就是「专给 LLM 的 Jaeger+Grafana」，
        今天不依赖它们，手写 50 行迷你版看清原理。token/延迟用 Ollama 真实返回字段，非 mock。

⚠️ 需要 Ollama：本机启动且拉过 qwen2.5:3b。
    ollama serve               # 默认 http://localhost:11434
    ollama pull qwen2.5:3b     # OLLAMA_MODEL 可覆盖
跑通：cd ~/projects/daily-learn && uv run day-48/practice.py

练习：先写标 ★ 的 5 行，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import os, json, time, urllib.request

OLLAMA = "http://localhost:11434/api/chat"
MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
PRICE_PER_1K = 0.0002   # 假想云模型单价（$/1K token），本地免费，仅演示成本汇总

# ---------- 1) Span：一段调用的追踪记录。仿 OpenTelemetry gen_ai.* 语义约定 ----------
TRACE = []          # 全局 trace = span 列表（生产里挂在 trace_id 上，这里单 trace 够用）
def now(): return time.perf_counter()

class Span:
    """包装器：with Span(name) 进时记开始、出时算耗时，attrs 存 token/输入输出。"""
    def __init__(self, name, parent=0, **attrs):
        self.name, self.parent, self.attrs = name, parent, attrs
        self.tokens, self.cost, self.ms = 0, 0.0, 0
    def __enter__(self):
        self.t0 = now(); TRACE.append(self); return self
    def __exit__(self, *e):
        self.ms = int((now() - self.t0) * 1000)              # ★1 耗时(ms) = 结束 - 开始
    def set(self, tokens=0, **kv):
        self.tokens = tokens
        self.cost = tokens / 1000 * PRICE_PER_1K             # 成本 = token × 单价
        self.attrs.update(kv)

# ---------- 2) 被追踪的 LLM 调用：真调 Ollama，token/延迟直接拿真实返回字段 ----------
def llm(messages, sp):
    body = json.dumps({"model": MODEL, "messages": messages, "stream": False}).encode()
    req  = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    d = json.loads(urllib.request.urlopen(req, timeout=180).read())
    tin, tout = d.get("prompt_eval_count", 0), d.get("eval_count", 0)   # 真实输入/输出 token
    sp.set(tin + tout, model=MODEL, out=d["message"]["content"][:50])   # ★2 把 token 记进 span
    return d["message"]["content"]

# ---------- 3) 模拟工具：也是一个 span（工具调用要不要计入追踪？要——它也占延迟）----------
def tool_wordcount(text):
    return f"{len(text.split())} 词"

# ---------- 4) agent loop：每步用 Span 包起来，自动串成 trace 树 ----------
def run_agent(goal):
    with Span("agent.run", goal=goal) as root:               # 根 span = 整次 run
        msgs = [{"role": "user", "content": goal}]
        for step in range(2):                                # 简化：2 步演示追踪
            with Span("llm.call", parent=1) as s:            # ★3 子 span 包住 LLM 调用
                ans = llm(msgs, s)
            msgs.append({"role": "assistant", "content": ans})
            with Span("tool.wordcount", parent=1) as s:      # 子 span 包住工具
                s.set(0, out=tool_wordcount(ans))
            msgs.append({"role": "user", "content": "再补充一句。"})
        root.set(sum(x.tokens for x in TRACE), out="done")   # 根汇总：总 token
    return TRACE

# ---------- 5) 打印结构化 trace 树 + 成本汇总（手写版 LangSmith 瀑布图）----------
def print_trace():
    tot_ms = TRACE[0].ms; tot_tok = sum(s.tokens for s in TRACE); tot_cost = sum(s.cost for s in TRACE)
    print("📊 Trace 树（name | 耗时 | token | $成本 | 属性）")
    for s in TRACE:
        bar = "█" * max(1, s.ms * 24 // max(tot_ms, 1))      # 耗时占比条 = 瀑布图
        ind = "  " * s.parent + ("└ " if s.parent else "● ")
        a = s.attrs.get("out", ""); print(f"{ind}{s.name:<14} {s.ms:>5}ms {s.tokens:>4}tk ${s.cost:.5f} {bar} {a}")
    print(f"\n总计：{tot_ms}ms · {tot_tok} token · ${tot_cost:.5f}（成本=token×单价；本地免费，演示而已）")

if __name__ == "__main__":
    print(f"🔭 可观测 Agent | 模型={MODEL}\n")
    run_agent("用一句话解释什么是分布式追踪。")               # ★4 真跑 agent，每步自动记 span
    print_trace()                                            # ★5 打印 trace 树
    print("\n达标：上面是手写的结构化 trace；上 LangSmith/Langfuse 只需换成 @traceable，原理一模一样。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  self.ms = int((now() - self.t0) * 1000)
#   ★2  sp.set(tin + tout, model=MODEL, out=d["message"]["content"][:50])
#   ★3  with Span("llm.call", parent=1) as s:
#   ★4  run_agent("用一句话解释什么是分布式追踪。")
#   ★5  print_trace()
#
# 接生产：把 Span 换成 @traceable(LangSmith) / langfuse.trace()，字段对齐 OTel gen_ai.*，
# token/延迟/成本自动上报，Web 看瀑布图——今天手写的就是平台内核。

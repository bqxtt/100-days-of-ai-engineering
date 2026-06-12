"""
Day 54 生产化部署：给 Agent 加三层护甲——容错、扩展、成本控制（真连 Ollama，纯标准库）。
Day42 那个裸 ReAct 循环能跑通，但上不了线：LLM 调用慢、贵、还偶发抽风。今天把它包成生产 runner：
  容错 = 超时(timeout) + 指数退避重试(retry) + 降级(fallback)   —— 后端的熔断/重试/降级
  扩展 = runner 无状态(状态全在 messages)，天然可并发/进队列      —— 后端的无状态服务+负载均衡
  成本 = 语义缓存(命中=零调用) + step 预算上限                   —— 后端的 Redis 缓存+限流
核心循环 Day42 写完了，一行不动；今天加的全是外围护甲。本脚本会：
  ① 故意制造一次故障，演示重试把它救回   ② 发两次重复问题，演示缓存命中省一次真调用

⚠️ 需要 Ollama：本机装好并启动，且拉过 qwen2.5:3b。
    brew install ollama        # macOS（已装可跳过）
    ollama serve               # 启动服务（默认 http://localhost:11434）
    ollama pull qwen2.5:3b     # 拉模型（约 1.9GB）；OLLAMA_MODEL 可覆盖
跑通即达标：    cd ~/projects/daily-learn && uv run day-54/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import os, json, time, hashlib, urllib.request, urllib.error

OLLAMA  = "http://localhost:11434/api/chat"
MODEL   = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")   # 默认 3b，可用环境变量覆盖
TIMEOUT = 60          # 单次调用超时（秒）：到点掐断，别让慢请求拖垮链路
RETRIES = 3           # 容错：最多重试 3 次
BUDGET  = 4           # 成本：step 预算上限——封死 ReAct 循环步数，烧不穿

CACHE = {}            # 语义缓存：问题指纹 -> 回答。命中=零调用，账单腰斩
STATS = {"calls": 0, "hits": 0, "retries": 0}   # 监控指标：真调了几次/命中几次/重试几次

# ---------- 1) 调 Ollama：带超时+指数退避重试+降级，这就是 LLM 版的熔断 ----------
def llm(messages, fail_once=False):
    body = json.dumps({"model": MODEL, "messages": messages, "stream": False}).encode()
    for attempt in range(RETRIES):
        try:
            if fail_once and attempt == 0:               # 演示：第一次故意抛超时，看重试救回
                raise urllib.error.URLError("演示故障")
            req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
            r = urllib.request.urlopen(req, timeout=TIMEOUT)        # ★1 timeout= 到点掐断
            STATS["calls"] += 1
            return json.loads(r.read())["message"]["content"]
        except (urllib.error.URLError, TimeoutError) as e:
            STATS["retries"] += 1
            wait = 2 ** attempt                          # ★2 指数退避：1s→2s→4s，避开瞬时抖动
            print(f"  🔁 重试 {attempt+1}/{RETRIES}（{e}），退避 {wait}s")
            time.sleep(0.3)                              # 演示压缩等待（真线上用 time.sleep(wait)）
    return "[降级]服务暂不可用，已返回兜底答案"           # 降级 fallback：N 次全挂也不抛错给用户

# ---------- 2) 语义缓存：相同问题直接返缓存，零调用（成本控制核心） ----------
def cache_key(q):
    return hashlib.sha256(q.strip().lower().encode()).hexdigest()[:12]   # 指纹=问题的哈希

def ask(question, fail_once=False):
    k = cache_key(question)
    if k in CACHE:                                       # ★3 命中：不调模型，直接返历史答案
        STATS["hits"] += 1
        print(f"  💾 缓存命中：{question[:18]}… → 省一次真调用")
        return CACHE[k]
    ans = llm([{"role": "user", "content": question}], fail_once)
    CACHE[k] = ans                                       # ★4 存进缓存，下次同问题白嫖
    return ans

# ---------- 3) 无状态 runner：状态全在 messages，所以能并发/进队列水平扩展 ----------
def run(question, fail_once=False):
    for step in range(BUDGET):                           # step 预算上限：循环封顶，防打转烧穿
        ans = ask(question, fail_once)
        if not ans.startswith("[降级]") or step == BUDGET - 1:
            return ans                                   # 拿到答案/降级兜底就收尾
    return "[降级]超出 step 预算"

if __name__ == "__main__":
    print(f"🛡️  生产 Agent runner | 模型={MODEL} | 超时{TIMEOUT}s 重试{RETRIES} 预算{BUDGET}步\n")
    qs = ["用一句话解释什么是熔断", "用一句话解释什么是熔断", "用一句话解释什么是缓存"]  # 第2个重复→命中
    for i, q in enumerate(qs):
        first = (i == 0)                                 # 第1个故意触发一次故障，演示重试救回
        print(f"❓ Q{i+1}: {q}")
        print("   →", run(q, fail_once=first)[:70], "\n")
    saved = STATS["hits"]
    print(f"💰 统计：{len(qs)} 次提问，真调 {STATS['calls']} 次，缓存省 {saved} 次，重试 {STATS['retries']} 次")
    print("跑通即达标：🔁 是重试救回故障，💾 是缓存省调用——容错+成本控制全程未改核心循环。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  r = urllib.request.urlopen(req, timeout=TIMEOUT)
#   ★2  wait = 2 ** attempt
#   ★3  if k in CACHE: ... return CACHE[k]
#   ★4  CACHE[k] = ans
#   ★5  for step in range(BUDGET):   # step 预算封顶（见 run 函数）
#
# 接生产：retry/timeout/fallback=熔断，无状态 runner 丢线程池/队列=水平扩展，
# 语义缓存+小模型路由=省钱。换 Claude（tool_use 强）、缓存换 Redis、并发上 worker，逻辑不变。

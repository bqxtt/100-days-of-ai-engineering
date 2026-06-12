"""
Day 19 练习："生产化"四件套——令牌桶限流 + 指数退避重试 + 成本估算，真连本地 ollama。
把后端最熟的三件事放进真实 LLM 调用里跑一遍：
  1) TokenBucket   令牌桶限流：按 RPM 配额发放令牌，没令牌就排队，对应 Anthropic rate limit
  2) retry         429/5xx 才重试，指数退避 + 抖动(jitter)，4xx 直接抛——别盲目重试
  3) CostEstimator 成本估算：用 ollama 真实回吐的 prompt_eval_count/eval_count × 单价
真调 qwen2.5:3b 产生真实 token，再按官方价格估算成本；429 退避部分用模拟状态码演示。
纯 Python 标准库（urllib），不装第三方包。

⚠️ 前置：需本地启动 ollama 且已拉 qwen2.5:3b
    ollama serve           # 默认监听 http://localhost:11434
    ollama pull qwen2.5:3b # 拉模型
练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
    uv run day-19/practice.py
"""
import json
import random
import time
import urllib.request

random.seed(0)

API = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"

# Claude Opus 4.8 单价（美元 / 1M token），缓存读约 0.1x、缓存写约 1.25x —— 数字来自官方 pricing
PRICE = {"in": 5.0, "out": 25.0, "cache_read": 0.5, "cache_write": 6.25}  # 每百万 token


def ollama_chat(prompt: str):
    """真调本地 ollama，返回 (回答文本, 输入token, 输出token)。token 数是 ollama 真回吐的。"""
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "stream": False}).encode()
    req = urllib.request.Request(API, body, {"Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req))
    return d["message"]["content"], d["prompt_eval_count"], d["eval_count"]  # 真实 token 计数


# ---------- 1) 令牌桶限流（Token Bucket）：60 RPM = 每秒补 1 个令牌 ----------
class TokenBucket:
    def __init__(self, rpm: int):
        self.rate = rpm / 60.0          # 每秒补多少令牌
        self.cap = max(1, rpm // 30)    # 桶容量(允许短时突发,留小一点好看到排队)
        self.tokens = self.cap
        self.t = time.monotonic()

    def take(self) -> float:
        now = time.monotonic()
        self.tokens = min(self.cap, self.tokens + (now - self.t) * self.rate)  # 按时间补令牌
        self.t = now
        if self.tokens >= 1:
            self.tokens -= 1
            return 0.0
        wait = (1 - self.tokens) / self.rate                                   # ★1 缺多少令牌就等多久
        self.tokens = 0
        return wait


# ---------- 2) 指数退避重试：只对 429/5xx 退避，4xx 立刻放弃 ----------
def backoff(attempt: int, base=0.5, cap=8.0) -> float:
    return min(cap, base * (2 ** attempt)) + random.uniform(0, 0.3)  # ★2 2^n 指数 + 抖动防同步惊群

def call_with_retry(fake_status, max_retry=5):
    for attempt in range(max_retry):
        code = fake_status()
        if code == 200:
            return f"ok@attempt{attempt}"
        if code in (429, 500, 529):                # 可重试：限流/服务器错/过载
            d = backoff(attempt)
            print(f"   {code} 第{attempt}次重试，等 {d:.2f}s")
            time.sleep(min(d, 0.05))               # 演示用：把真实 sleep 压短，逻辑不变
            continue
        raise RuntimeError(f"{code} 不可重试，直接失败")  # 4xx 客户端错——重试也没用
    raise RuntimeError("重试用尽")


# ---------- 3) 成本估算器：token × 单价 ----------
def cost(n_in, n_out, n_cache_read=0):
    c = n_in / 1e6 * PRICE["in"] + n_out / 1e6 * PRICE["out"]
    c += n_cache_read / 1e6 * PRICE["cache_read"]      # ★3 缓存读只 0.1 倍单价，命中越多越省
    return c


if __name__ == "__main__":
    print("== 限流：4 个真请求挤 60RPM 桶，令牌桶先控速再真调 ollama ==")
    bucket = TokenBucket(rpm=60)
    prompts = ["一句话讲限流", "一句话讲重试", "一句话讲缓存", "一句话讲熔断"]
    tot_in = tot_out = 0
    for i, p in enumerate(prompts):
        time.sleep(0.2)
        wait = bucket.take()
        if wait:
            time.sleep(wait)
        ans, ti, to = ollama_chat(p)               # 被令牌桶放行后才真调，产生真实 token
        tot_in += ti; tot_out += to
        print(f"req{i} 等{wait:.2f}s | in={ti} out={to} | {ans.strip()[:40]}")

    print("\n== 重试：模拟 429 两次后成功（退避逻辑同样护着上面的真调用）==")
    seq = iter([429, 429, 200])
    print("  结果:", call_with_retry(lambda: next(seq)))

    print("\n== 成本：用真实 token 算这轮花了多少 ==")
    real = cost(tot_in, tot_out)
    print(f"  本轮 4 次真调：in={tot_in} out={tot_out} 合计 = ${real:.6f}")
    cached = cost(0, tot_out, n_cache_read=tot_in)
    print(f"  若 input 全命中缓存       ≈ ${cached:.6f}  省 {(1-cached/real)*100:.0f}%")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  wait = (1 - self.tokens) / self.rate
#   ★2  return min(cap, base * (2 ** attempt)) + random.uniform(0, 0.3)
#   ★3  c += n_cache_read / 1e6 * PRICE["cache_read"]
# 看到限流排队、429退避后成功、用真实 token 算出成本与缓存省额，这一天就串通了。

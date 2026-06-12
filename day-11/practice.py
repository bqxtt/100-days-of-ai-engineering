"""
Day 11 练习：真连本地 ollama，亲手调 temperature 看输出怎么从"稳"变"野"。
LLM 每步吐 logits -> softmax -> 采样，temperature 就是缩放 logits 的旋钮：
低温分布变尖 -> 几乎复读同一句；高温分布变平 -> 越答越发散。
今天不模拟，直接发 POST /api/chat 让真模型给你跑出这个对比。

前置条件：先 `ollama serve` 并拉好模型 qwen2.5:3b（默认）。
可用 OLLAMA_MODEL=qwen2.5:7b 切大模型。

练习方式：先把 2 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
跑通即达标（同一问题低温几乎一模一样、高温每次不同）：
    cd /Users/zqr/projects/daily-learn && uv run day-11/practice.py
"""
import json, os, urllib.request

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")

def chat(messages, **kw):
    # 纯 stdlib：把对话+options 打包成 JSON POST 给本地 ollama，非流式拿整条回复
    body = {"model": MODEL, "messages": messages, "stream": False, **kw}
    req = urllib.request.urlopen(
        "http://localhost:11434/api/chat", json.dumps(body).encode(), timeout=120
    )
    return json.load(req)["message"]["content"].strip()

PROMPT = "用一句话续写：天空很蓝，"

def run(temp, rounds=4):
    msgs = [{"role": "user", "content": PROMPT}]
    outs = []
    for _ in range(rounds):
        outs.append(chat(msgs, options={"temperature": temp}))   # ★1 同一 prompt、只改 temperature 重复跑
    return outs

uniq = lambda outs: len(set(outs))   # ★2 用去重数衡量发散度：低温≈1，高温更大
print(f"模型={MODEL}  问题={PROMPT}\n")

low = run(0.2)
print("--- 低温 temperature=0.2（应几乎复读、稳定）---")
for i, o in enumerate(low, 1):
    print(f"  [{i}] {o}")

high = run(1.2)
print("\n--- 高温 temperature=1.2（应各不相同、发散）---")
for i, o in enumerate(high, 1):
    print(f"  [{i}] {o}")

print(f"\n低温不同答案数={uniq(low)}  高温不同答案数={uniq(high)}")
print("低温几乎一模一样、高温每次都变，就说明 temperature 调对了。")

# ============ 参考答案（被你应当先自己写的 2 行）============
#   ★1  outs.append(chat(msgs, options={"temperature": temp}))
#   ★2  uniq = lambda outs: len(set(outs))
# 报错连接拒绝 = 没开 ollama：先 `ollama serve` 并 `ollama pull qwen2.5:3b`。

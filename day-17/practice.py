"""
Day 17 练习：真连本地 ollama，逐 token 流式打印 qwen 的回答（打字机效果）。
把"流式输出"串通三步：
  1) 服务端：向 ollama POST 请求，body 里 stream=True，它会逐行回吐 JSON
  2) 客户端逐行读响应：每行 json.loads，拿到本次的 message.content 增量
  3) 边收边上屏（打字机）+ 把增量顺序拼接 = 完整回答，再做一致性校验

⚠️ 前置：需本地启动 ollama 且已拉 qwen2.5:3b
    ollama serve           # 默认监听 http://localhost:11434
    ollama pull qwen2.5:3b # 拉模型
跑通即达标：
    uv run day-17/practice.py
"""
import json
import urllib.request

API = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"
msgs = [{"role": "user", "content": "用一句话解释什么是流式输出。"}]

# ---------- 1) 服务端：stream=True，逐行回吐 JSON ----------
body = json.dumps({"model": MODEL, "messages": msgs, "stream": True}).encode()
req = urllib.request.Request(API, body, {"Content-Type": "application/json"})

# ---------- 2)+3) 客户端：逐行解析 + 拼接 delta ----------
pieces, n_delta = [], 0
print("→ token 逐字流出：", end="", flush=True)
for line in urllib.request.urlopen(req):                  # 一行 = 一个增量事件
    if not line.strip():
        continue
    d = json.loads(line)                                  # ★1 每行就是一个 JSON 事件
    tok = d["message"]["content"]                         # ★2 取本次的 content 增量
    pieces.append(tok); n_delta += 1
    print(tok, end="", flush=True)                        # 边收边上屏（打字机）
    if d.get("done"):
        print()                                           # 流结束
        break

full = "".join(pieces)                                     # ★3 顺序拼接所有 delta = 完整回答
print(f"\n共收到 {n_delta} 个 delta，拼回：{full}")
# 校验：分片数应与片段数一致，且拼回长度=各片段长度之和（无丢字/重复）
ok = n_delta == len(pieces) and len(full) == sum(len(p) for p in pieces)
print("一致性校验:", "✅ 通过" if ok else "❌ 不一致")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  d = json.loads(line)
#   ★2  tok = d["message"]["content"]
#   ★3  full = "".join(pieces)
# 看到 token 逐字流出、delta 数=分片数、拼回与流出一致，就把真流式串通了。

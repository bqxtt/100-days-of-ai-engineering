"""
Day 20 练习：带 Tool Use 的智能命令行助手（真连 Ollama，纯标准库）。
不需要 numpy、不需要付费 API key——把 Phase 2 全部技能串成一个真跑的 agent loop：
  - Day11 API 参数  - Day12/13 prompt+ReAct  - Day14 tool use  - Day15 结构化
  - Day17 流式打印  - Day18 模板  - Day19 重试退避
核心就一个 while 循环：调模型 -> 模型要用工具 -> 本地执行工具 -> 塞回去 -> 再调，到无 tool_call 输出最终答。

⚠️ 需要 Ollama：本机要装好并启动 ollama，且拉过 qwen2.5:3b。
    brew install ollama        # macOS（已装可跳过）
    ollama serve               # 启动服务（默认 http://localhost:11434）
    ollama pull qwen2.5:3b     # 拉模型（约 1.9GB）
跑通即达标：    cd ~/projects/daily-learn && uv run day-20/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import sys, time, json, datetime, urllib.request, urllib.error

OLLAMA = "http://localhost:11434/api/chat"   # Day11：连真实推理后端
MODEL  = "qwen2.5:3b"                          # 小而支持 tool_calls 的开源模型

# ---------- 0) 工具：名字+描述+入参schema（接 Day14/15）。真正干活的是你的代码 ----------
def tool_calc(a, op, b):
    return {"+": a + b, "-": a - b, "*": a * b, "/": (a / b if b else "∞")}[op]
def tool_time():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
def tool_search(q):
    return f"[mock] 关于「{q}」：RAG=检索增强生成，先查资料再让模型作答。"  # 真项目里换成检索

# 本地执行函数表：模型只会"说"要调哪个工具，真正算的是你的代码（安全边界在此）
TOOLS = {
    "calc":   lambda i: tool_calc(i["a"], i["op"], i["b"]),
    "time":   lambda i: tool_time(),
    "search": lambda i: tool_search(i["q"]),
}

# 工具定义 = 名字+描述+入参 schema（Day15 结构化），交给模型决定何时/如何调用
TOOL_DEFS = [
    {"type": "function", "function": {"name": "calc", "description": "四则运算，需要算数时调用",
        "parameters": {"type": "object", "properties": {
            "a": {"type": "number"}, "op": {"type": "string"}, "b": {"type": "number"}},
            "required": ["a", "op", "b"]}}},
    {"type": "function", "function": {"name": "time", "description": "查当前时间，问几点时调用",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "search", "description": "查资料，问概念时调用",
        "parameters": {"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]}}},
]

SYSTEM = "你是简洁的命令行助手。需要算数/时间/查资料就调对应工具，否则直接答。"  # Day12 人设模板

# ---------- 1) 调 Ollama：stream=False 时一把拿完整回复（含 tool_calls 决策） ----------
def ollama_call(messages, tools, stream):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "tools": tools, "stream": stream}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=120)

# ---------- 2) 重试退避（Day19）：超时/连不上自动再试一次 ----------
def with_retry(fn):
    try:
        return fn()                                          # ★1 先试一次，失败才退避重试
    except (urllib.error.URLError, TimeoutError):
        print("   ⚠ 调用失败，0.5s 后重试一次"); time.sleep(0.5)
        return fn()

# ---------- 3) 流式打印（Day17）：把模型逐 token 吐字直接刷到终端 ----------
def stream_final(messages):
    resp = with_retry(lambda: ollama_call(messages, None, True))
    for line in resp:                                        # ndjson：每行一个增量
        chunk = json.loads(line).get("message", {}).get("content", "")
        sys.stdout.write(chunk); sys.stdout.flush()
    print()

# ---------- 4) agent loop：助手骨架 = 一个 while（调模型->要工具就本地跑->塞回->再调） ----------
def assistant(user_msg):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg}]
    print(f"👤 {user_msg}\n🤖 ", end="")
    for _ in range(5):  # 护栏：最多 5 轮，防止一直调工具不收手
        resp = with_retry(lambda: ollama_call(messages, TOOL_DEFS, False))
        msg = json.loads(resp.read())["message"]
        calls = msg.get("tool_calls")
        if calls:                                            # 有 tool_calls -> 本地执行回填
            messages.append(msg)
            for c in calls:
                name, args = c["function"]["name"], c["function"]["arguments"]
                result = TOOLS[name](args)                   # ★2 本地执行工具，拿结果
                print(f"[调用 {name}{args} -> {result}]  ", end="")
                messages.append({"role": "tool", "content": str(result)})  # ★3 结果塞回，再循环
            continue
        messages.append({"role": "assistant", "content": ""})
        return stream_final(messages)                        # 无 tool_call：流式吐最终答，收工

if __name__ == "__main__":
    for q in ["3 加 5 等于几？", "现在几点？", "帮我查一下 RAG 是什么"]:
        assistant(q); print()
    print("跑通即达标：3 题都看到 调工具->流式续答，全程真连 Ollama。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  return fn()                                        # try 里直接调，except 才重试
#   ★2  result = TOOLS[name](args)
#   ★3  messages.append({"role": "tool", "content": str(result)})
#
# 接真实 Claude：把 ollama_call 换成 Anthropic SDK，循环/流式/重试逻辑不变：
#   import anthropic
#   client = anthropic.Anthropic()                          # 读 ANTHROPIC_API_KEY
#   resp = client.messages.create(model="claude-opus-4-8", max_tokens=1024,
#            system=SYSTEM, tools=tool_defs, messages=messages)   # 工具按上面 schema 定义
#   # resp.stop_reason=="tool_use" -> 取 tool_use 块本地执行，塞回 tool_result，再 create
#   # 流式：client.messages.stream(...)；重试：SDK 自带 max_retries。while 循环一行不改。

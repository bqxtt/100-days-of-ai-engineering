"""
Day 36 实践：用标准库手写一个 ReAct 风格 Agent Loop（真连本机 Ollama，零第三方库）。
本质：Thought → Action → Observation 循环。LLM 不直接编答案，而是"想一步、调一个工具、看结果"，
循环若干轮直到给出 Final Answer。后端类比：这就是一个 while 循环 + 工具路由器（router/dispatch）+ 终止条件。

为什么不直接问模型？小模型不会算账、查不到私有数据。给它工具：calculator（真算）、search（mock 库），
模型只负责"决定调哪个、传什么参"，脏活外包给确定性代码——这就是 Agent 比裸 prompt 强的地方。

⚠️ 需要 Ollama：本机装好并启动，拉过生成模型。
    ollama serve                    # 默认 http://localhost:11434
    ollama pull qwen2.5:3b          # 默认模型；想换 7b：export OLLAMA_MODEL=qwen2.5:7b
跑通即达标：    cd ~/projects/daily-learn && uv run day-36/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑。
"""
import os, re, json, urllib.request

MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")   # 默认 3b，OLLAMA_MODEL 可覆盖
MAX_STEPS = 6                                       # 终止保险：再聪明也不让它无限转

# ---------- 0) chat helper：唯一的网络出口，真打 Ollama，纯 stdlib urllib ----------
def chat(msgs):
    return json.load(urllib.request.urlopen(
        "http://localhost:11434/api/chat",
        json.dumps({"model": MODEL, "messages": msgs, "stream": False}).encode(),
        timeout=120))["message"]   # 返回 {"role":..,"content":..}

# ---------- 1) 工具箱（Tools）：确定性代码，Agent 只负责决定调谁、传啥 ----------
def calculator(expr):                              # 真算，不让 LLM 猜数字
    return str(eval(expr, {"__builtins__": {}}, {}))   # 已封死内置，仅 demo 用

_KB = {                                            # search 的 mock 数据：当成你的私有库/检索接口
    "ollama": "Ollama 是本地运行大模型的工具，默认端口 11434。",
    "react":  "ReAct 把 Reasoning 和 Acting 交错：想一步、做一步、看结果。论文 2210.03629。",
    "agent":  "Agent = LLM 大脑 + 工具 + 循环 + 记忆，能自己拆任务、调工具、纠错。",
}
def search(q):
    for k, v in _KB.items():
        if k in q.lower(): return v
    return "未命中知识库。"

TOOLS = {"calculator": calculator, "search": search}   # 工具注册表 = 后端的路由表

# ---------- 2) 系统提示：约定 ReAct 协议，逼模型按 Thought/Action/Final 格式输出 ----------
SYSTEM = (
    "你是一个会用工具的 ReAct agent。可用工具：\n"
    "  calculator(算术表达式) 如 calculator(23*47)\n"
    "  search(关键词)        如 search(ollama)\n"
    "每轮严格用以下两种之一：\n"
    "  Thought: <推理>\\nAction: 工具名(参数)    # 需要调工具时\n"
    "  Thought: <推理>\\nFinal: <最终答案>        # 已能回答时\n"
    "规则：算术必须调 calculator；任何概念/事实问题先 search 取证再 Final，禁止凭记忆直接答。\n"
    "一次只一步，禁止自己编 Observation。"
)

ACT = re.compile(r"Action:\s*(\w+)\((.*?)\)", re.S)   # 解析 Action: tool(arg)
FIN = re.compile(r"Final:\s*(.+)", re.S)              # 解析 Final: answer

# ---------- 3) Agent Loop：Thought → Action → Observation 循环，真调 ollama ----------
def react(question):
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": question}]
    for step in range(1, MAX_STEPS + 1):
        out = chat(msgs)["content"]                  # ★1 调模型，拿这一步的 Thought/Action/Final
        print(f"\n── step {step} ──\n{out.strip()}")
        if (f := FIN.search(out)):                   # ★2 命中 Final 就终止，返回答案
            return f.group(1).strip()
        m = ACT.search(out)
        if not m:                                    # 没给 Action 也没给 Final：提醒一次再继续
            msgs.append({"role": "user", "content": "请用 Action: 工具(参数) 或 Final: 答案"}); continue
        tool, arg = m.group(1), m.group(2).strip().strip("'\"")
        obs = TOOLS.get(tool, lambda _: "未知工具")(arg)   # ★3 真执行工具，拿到 Observation
        print(f"Observation: {obs}")
        msgs.append({"role": "assistant", "content": out})     # ★4 把模型这步存回上下文（记忆）
        msgs.append({"role": "user", "content": f"Observation: {obs}"})  # ★5 回灌结果，喂下一轮
    return "(达到最大步数仍未收敛)"

if __name__ == "__main__":
    print(f"🤖 ReAct agent · model={MODEL} · 工具={list(TOOLS)}")
    for q in ["23 乘以 47 等于多少？", "什么是 ReAct？", "ReAct 论文编号乘以 0 是几？"]:
        print(f"\n❓ {q}")
        print(f"✅ 最终答案: {react(q)}")
    print("\n跑通即达标：算术题走 calculator、概念题走 search，多轮 Thought→Action→Observation 收敛。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  out = chat(msgs)["content"]
#   ★2  if (f := FIN.search(out)): return f.group(1).strip()
#   ★3  obs = TOOLS.get(tool, lambda _: "未知工具")(arg)
#   ★4  msgs.append({"role": "assistant", "content": out})
#   ★5  msgs.append({"role": "user", "content": f"Observation: {obs}"})
#
# 三种架构模式（README 详解）：
#   ReAct           = 边想边做，每步一工具，错了下一轮纠（本练习）
#   Plan-and-Execute= 先一次性拆出全计划，再逐步执行（少调模型、可控）
#   Reflection      = 做完自评、不满意就重做（多花算力换质量）
# 接生产：工具换真 API、search 换 RAG、循环换 LangGraph/Claude tool_use，协议一行不改。

"""
Day 50-51 实战：迷你 Agent 评估框架（eval harness，真连 Ollama，纯标准库）。
两天合并：Day42 焊好了 Agent，今天回头问一句——「它真的好用吗？」。靠跑一次看着对不算数，
Agent 走的是多步轨迹（用错工具 / 多绕几步 / 最后答案不靠谱都可能），得系统化测。
本框架=后端的「集成测试套件」：几个任务用例真跑 ReAct Agent，自动判定 成功率/步数效率/工具选对率，
再请第二个模型当裁判（LLM-as-judge）给最终答案打质量分，汇总成一份评估报告。

后端类比：这就是给 Agent 写 CI——测试集=用例表，断言=自动判定，质量分=人工评审的自动化代餐。
        4 指标 = 任务成功率(对不对) + 步数效率(快不快) + 工具选对率(走没走弯路) + 最终质量(写得好不好)。

⚠️ 需要 Ollama：启动并拉过 qwen2.5:3b。   ollama serve  &&  ollama pull qwen2.5:3b
跑通即达标：    cd ~/projects/daily-learn && uv run day-50/practice.py
练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import os, json, urllib.request

OLLAMA = "http://localhost:11434/api/chat"
MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")   # 被测 Agent 与裁判同款，3b 可覆盖

# ---------- 0) 被测对象：一个迷你计算 Agent（2 工具，ReAct 循环）。Day42 那套，缩到能测 ----------
def add(a, b): return a + b
def mul(a, b): return a * b
TOOLS = {"add": add, "mul": mul}
TOOL_DEFS = [
    {"type":"function","function":{"name":"add","description":"两数相加",
        "parameters":{"type":"object","properties":{"a":{"type":"number"},"b":{"type":"number"}},"required":["a","b"]}}},
    {"type":"function","function":{"name":"mul","description":"两数相乘",
        "parameters":{"type":"object","properties":{"a":{"type":"number"},"b":{"type":"number"}},"required":["a","b"]}}},
]
SYSTEM = "你是计算 Agent，只能用 add/mul 工具一步步算，禁止口算。算完直接给最终数字答案。"

def chat(messages, tools=None):  # 标准 chat helper：urllib POST /api/chat，stream=False
    body = json.dumps({"model": MODEL, "messages": messages, "tools": tools, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())["message"]

def run_agent(goal, maxstep=6):                       # 跑 Agent，返回(答案, 步数, 用过的工具序列)
    msgs = [{"role":"system","content":SYSTEM},{"role":"user","content":goal}]
    used = []
    for _ in range(maxstep):
        m = chat(msgs, TOOL_DEFS); msgs.append(m)
        calls = m.get("tool_calls")
        if not calls: return m["content"], len(used), used      # 不调工具=收尾出答案
        for c in calls:
            fn, a = c["function"]["name"], c["function"]["arguments"]
            if isinstance(a, str): a = json.loads(a)
            used.append(fn)
            msgs.append({"role":"tool","content":str(TOOLS[fn](**a))})
    return "(超步数)", len(used), used

# ---------- 1) 测试集：每条用例=目标+期望答案+期望工具(契约)。这就是 Agent 的「集成测试用例表」 ----------
CASES = [
    {"goal":"算 3 加 5 等于几", "expect":"8",  "want":["add"]},
    {"goal":"算 4 乘 6 等于几", "expect":"24", "want":["mul"]},
    {"goal":"算 2 乘 3 再加 1", "expect":"7",  "want":["mul","add"]},
]

# ---------- 2) 自动判定 3 个客观指标：成功率/步数效率/工具选对率（不花钱、毫秒级，先跑这个） ----------
def grade(case, ans, used):
    ok    = case["expect"] in ans.replace(",", "")            # ★1 成功率：期望数字出现在答案里
    tool  = set(used) >= set(case["want"])                    # ★2 工具选对率：调齐了该用的工具
    steps = len(used)
    eff   = max(0, 1 - (steps - len(case["want"])) * 0.3)     # 步数效率：每多绕一步扣 0.3
    return {"ok":ok, "tool":tool, "steps":steps, "eff":round(eff,2)}

# ---------- 3) LLM-as-judge：客观分测不了「写得好不好」，请第二个模型当裁判给 1-5 质量分 ----------
def judge(goal, ans):
    p = f"任务：{goal}\nAgent答案：{ans}\n只回一个 1-5 整数评质量（5=清楚正确，1=糟糕），别的不说。"
    txt = chat([{"role":"user","content":p}])["content"]      # ★3 裁判无工具，纯打分
    d = [c for c in txt if c.isdigit()]
    return int(d[0]) if d else 3

# ---------- 4) 跑全套 + 汇报告（轨迹检查就看 🔧 工具序列对不对） ----------
if __name__ == "__main__":
    print(f"🧪 Agent 评估框架 | 模型={MODEL} | 用例数={len(CASES)}\n")
    rows = []
    for c in CASES:
        ans, steps, used = run_agent(c["goal"])              # ★4 真跑 Agent
        g = grade(c, ans, used)
        q = judge(c["goal"], ans)                            # ★5 LLM 裁判打质量分
        rows.append({**g, "q":q})
        flag = "✅" if g["ok"] else "❌"
        print(f"{flag} {c['goal']:14s} 答={ans[:20]:20s} 工具={'>'.join(used) or '无'} 步={steps} 质量={q}/5")
    n = len(rows)
    print("\n📊 评估报告")
    print(f"  任务成功率 : {sum(r['ok'] for r in rows)}/{n} = {sum(r['ok'] for r in rows)/n:.0%}")
    print(f"  工具选对率 : {sum(r['tool'] for r in rows)}/{n} = {sum(r['tool'] for r in rows)/n:.0%}")
    print(f"  步数效率   : {sum(r['eff'] for r in rows)/n:.2f}（1=零绕路）")
    print(f"  平均质量分 : {sum(r['q'] for r in rows)/n:.1f}/5（LLM-judge）")
    print("\n跑通即达标：上面是 3 指标自动判定 + LLM 裁判，组合成一张可回归对比的成绩单。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  ok = case["expect"] in ans.replace(",", "")
#   ★2  tool = set(used) >= set(case["want"])
#   ★3  txt = chat([{"role":"user","content":p}])["content"]
#   ★4  ans, steps, used = run_agent(c["goal"])
#   ★5  q = judge(c["goal"], ans)
#
# 接生产：用例换 50+ 条真任务，judge 换 Claude（评分更稳）+ 多维 rubric，
# 每次改 prompt/工具就跑整套，成功率掉了就是回归——这就是 OpenAI evals / LangSmith 的内核。

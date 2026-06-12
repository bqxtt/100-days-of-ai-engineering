"""
Day 55 实践（Phase 4 收官·毕业作品）：把 Phase 4 全部零件组装成一个相对完整的 Agent，真连本机 Ollama。
零件来源（Day36-54）：
  - ReAct 循环（Day36）= 一个 while：Thought->Action->Observation->... 直到 Final（模型用 tool_calls 当 Action）
  - 多工具（Day40）   = calc / time / kv 存查 三件，本地执行，安全边界在你的代码（Day49）
  - 短期记忆（Day41） = messages 列表就是会话状态，工具结果回填后下一轮可见
  - trace 日志（Day48）= 每步 thought/action/obs 落 list，结束打印=最朴素的可观测性
  - 重试退避（Day54） = 连不上/超时自动再试，护栏 max_steps 防死循环
  - 评估打分（Day50） = 跑几个有标准答案的任务，做包含式断言算分，量化 Agent 能力
作为 Phase 4 毕业作品：一个 ReAct 多步 Agent 真调 ollama 完成多步任务，再跑评估打分。

纯标准库 urllib + json，真调 Ollama，无 mock、无付费 key。
⚠️ 需要 Ollama：本机装好并启动，且拉过 qwen2.5:3b（支持 tool_calls）。
    brew install ollama                 # macOS（已装可跳过）
    ollama serve                        # 启动服务（默认 http://localhost:11434）
    ollama pull qwen2.5:3b              # 拉模型（约 1.9GB，支持工具调用）
跑通即达标：    cd ~/projects/daily-learn && uv run day-55/practice.py
练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑。
"""
import time, json, datetime, urllib.request, urllib.error

OLLAMA = "http://localhost:11434/api/chat"   # 默认 /api/chat，连真实推理后端
MODEL  = "qwen2.5:3b"                          # 小而支持 tool_calls 的开源模型

# ---------- 0) 多工具（Day40）：名字+描述+入参schema。模型只"决定"调谁，真活由你代码干（Day49 安全边界） ----------
STORE = {}                                                # kv 内存表，模拟"短期外存"
def t_calc(a, op, b):
    try: a, b = float(a), float(b)                          # 模型常把数字传成字符串，先容错转换
    except (TypeError, ValueError): return f"err: a/b 需是数字，收到 {a!r},{b!r}"  # 错误当 Observation 让模型自纠
    r = {"+":a+b,"-":a-b,"*":a*b,"/":(a/b if b else "∞")}.get(op, "err: op 仅 + - * /")
    return int(r) if isinstance(r, float) and r == int(r) else r
def t_time():        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
def t_kv(action, key, value=None):
    if action == "set": STORE[key] = value; return f"已存 {key}={value}"
    return STORE.get(key, "(无)")
TOOLS = {  # 本地执行表：模型说调哪个，真正算的是这里
    "calc": lambda i: t_calc(i["a"], i["op"], i["b"]),
    "time": lambda i: t_time(),
    "kv":   lambda i: t_kv(i["action"], i["key"], i.get("value")),
}
TOOL_DEFS = [
    {"type":"function","function":{"name":"calc","description":"四则运算，需算数时调",
        "parameters":{"type":"object","properties":{"a":{"type":"number"},"op":{"type":"string"},"b":{"type":"number"}},"required":["a","op","b"]}}},
    {"type":"function","function":{"name":"time","description":"查当前时间","parameters":{"type":"object","properties":{}}}},
    {"type":"function","function":{"name":"kv","description":"存/取键值。action=set 存，get 取",
        "parameters":{"type":"object","properties":{"action":{"type":"string"},"key":{"type":"string"},"value":{"type":"string"}},"required":["action","key"]}}},
]
SYSTEM = "你是多步任务助手。需要算数/时间/暂存数据就调对应工具，分步完成，结果出来直接给最终答。"

# ---------- 1) 调 Ollama + 重试退避（Day54）：超时/连不上自动再试一次 ----------
def call(messages):
    body = json.dumps({"model":MODEL,"messages":messages,"tools":TOOL_DEFS,"stream":False}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type":"application/json"})
    return json.load(urllib.request.urlopen(req, timeout=120))["message"]
def with_retry(fn):
    try: return fn()                                       # ★1 先试一次，失败才退避重试
    except (urllib.error.URLError, TimeoutError):
        time.sleep(0.5); return fn()

# ---------- 2) ReAct Agent（Day36）：一个 while = Thought->Action(工具)->Observation->...->Final ----------
def agent(task, max_steps=6):
    msgs = [{"role":"system","content":SYSTEM},{"role":"user","content":task}]  # messages=短期记忆(Day41)
    trace = []                                             # trace 日志(Day48)：每步落账=可观测性
    for _ in range(max_steps):                             # 护栏：最多 N 步，防死循环
        msg = with_retry(lambda: call(msgs))
        calls = msg.get("tool_calls")
        if calls:                                          # 有 Action：本地执行工具→回填 Observation
            msgs.append(msg)
            for c in calls:
                name, args = c["function"]["name"], c["function"]["arguments"]
                obs = TOOLS[name](args)                     # ★2 本地执行工具，拿 Observation
                trace.append(f"Action {name}{args} -> {obs}")
                msgs.append({"role":"tool","content":str(obs)})  # ★3 结果塞回，下一轮模型可见
            continue
        trace.append(f"Final: {msg['content'][:60]}")
        return msg["content"], trace                       # 无工具调用 = Final，收工
    return "(超步数)", trace

# ---------- 3) 评估打分（Day50）：几个有标准答案的任务，包含式断言算分 ----------
CN = "零一二三四五六七八九十"; M = datetime.date.today().month
EVAL = [("3 乘以 8 再加 6 等于几？", ["30"]), ("把我的城市存成北京，然后取出来", ["北京"]),
        ("现在是几月？", [str(M), CN[M]])]                  # 答案可阿拉伯也可中文，断言放宽
def evaluate():
    hit = 0
    for task, ok_list in EVAL:
        ans, tr = agent(task)
        ok = any(e in ans for e in ok_list)                # ★4 包含式断言：答案含任一期望即算对
        expect = ok_list[0]
        print(f"  {'✅' if ok else '❌'} {task}\n     答:{ans[:50]} | 期望含:{expect} | 步:{len(tr)}")
        hit += ok
    print(f"  📊 评估得分 {hit}/{len(EVAL)} = {hit/len(EVAL)*100:.0f}%")  # ★5 命中率=Agent 能力分

if __name__ == "__main__":
    print("⏳ 连 Ollama，跑毕业作品 Agent ...\n— 多步任务演示 —")
    ans, trace = agent("先算 12 加 8，把结果存成 sum，再取出来告诉我")
    for s in trace: print("  ·", s)
    print(f"🤖 {ans}\n\n— 评估打分（Phase4 毕业测）—"); evaluate()
    print("跑通即达标：ReAct 循环真调 ollama 多步完成任务，trace 可见，评估出分。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  try: return fn()
#   ★2  obs = TOOLS[name](args)
#   ★3  msgs.append({"role":"tool","content":str(obs)})
#   ★4  ok = expect in ans
#   ★5  print(f"... {hit}/{len(EVAL)} = {hit/len(EVAL)*100:.0f}%")
#
# 接生产：工具加权限校验(Day49)、trace 上 LangSmith(Day48)、多 Agent 委托(Day44)、容错扩缩(Day54)。
# 接 Claude：call() 换 anthropic SDK，stop_reason=="tool_use" 取块本地执行回填，while/trace/重试一字不改。

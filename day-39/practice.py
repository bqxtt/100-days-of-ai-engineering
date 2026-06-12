"""
Day 39 实践：LangGraph 进阶——Human-in-the-loop（人在回路）+ 持久化状态（checkpoint）。
纯标准库手写一个 Agent，复刻 LangGraph 两个核心机制：
  1) checkpoint 持久化：每跑一步把 state 序列化到 .checkpoint.json，进程崩了能从断点 resume。
  2) interrupt 人在回路：执行"高危工具"（delete_db）前暂停，落盘等人工 approve，批准后从断点继续。
真连本机 Ollama（qwen2.5:3b）让模型决定"下一步调哪个工具"，不是 mock。
纯 stdlib + urllib，无 LangGraph、无 pip。后端类比：审批工作流（暂停等审批）+ 任务可恢复（断点续跑）。

⚠️ 需要 Ollama：本机装好并启动，且拉过生成模型。
    ollama serve                          # 默认 http://localhost:11434
    ollama pull qwen2.5:3b                # 约 1.9GB
跑通即达标：  cd ~/projects/daily-learn && uv run day-39/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍（看不到答案就照注释推），再对照文末「参考答案」。
下面已是完整版，直接跑：第一次会"中断"在审批点，自动批准后再跑一次，从 checkpoint 恢复。
"""
import json, os, sys, time, urllib.request, urllib.error

OLLAMA   = "http://localhost:11434"
MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")      # 默认 qwen2.5:3b，可用环境变量覆盖
CKPT     = os.path.join(os.path.dirname(__file__), ".checkpoint.json")  # state 存盘文件
RISKY    = {"delete_db"}                                # 高危工具：执行前必须人工审批

# ---------- 1) chat helper：真调 Ollama 决策，绝不 mock ----------
def chat(msgs):
    return json.load(urllib.request.urlopen(OLLAMA + "/api/chat",
        json.dumps({"model": MODEL, "messages": msgs, "stream": False}).encode(),
        timeout=120))["message"]                        # ★ 返回 {"role","content"}

# ---------- 2) 工具：Agent 能调的"动作"。delete_db 是高危的，要走人在回路 ----------
def query_db(arg):  return f"查询完成：用户 {arg} 共 3 条记录"
def archive(arg):   return f"归档完成：{arg} 已写入冷存储"
def delete_db(arg): return f"⚠️ 已物理删除 {arg}（不可逆！）"
TOOLS = {"query_db": query_db, "archive": archive, "delete_db": delete_db}

# ---------- 3) checkpoint 持久化：state 存盘 / 读盘，可中断可恢复 ----------
def save(state): json.dump(state, open(CKPT, "w"), ensure_ascii=False, indent=2)   # 序列化到磁盘
def load():      return json.load(open(CKPT)) if os.path.exists(CKPT) else None    # 断点读回
def clear():     os.path.exists(CKPT) and os.remove(CKPT)

# ---------- 4) 让 LLM 决定下一步：从工具表里选一个调用，真调 ollama ----------
def decide(state):
    done = {s["tool"] for s in state["log"]}                # 已做过的工具，避免重复
    todo = [t for t in ("query_db", "archive", "delete_db") if t not in done]
    if not todo: return {"tool": "done", "arg": ""}         # 三步都做完 -> 收尾
    sys_p = ("你是运维 Agent，按计划逐步执行。可用工具：query_db/archive/delete_db。"
             "只从【还没做】的工具里选一个，先查再归档最后才删。只回一行 JSON："
             "{\"tool\":\"工具名\",\"arg\":\"参数\",\"reason\":\"一句话\"}。")
    hist = "\n".join(f"已做：{s['tool']}({s['arg']})" for s in state["log"])
    msgs = [{"role": "system", "content": sys_p},
            {"role": "user", "content": f"任务：{state['goal']}\n已做：\n{hist or '(无)'}\n还没做：{todo}\n下一步？"}]
    txt = chat(msgs)["content"]
    try:    act = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])    # ★ 抠出 JSON
    except Exception: act = {}
    tool = next((t for t in todo if t in str(act.get("tool", ""))), todo[0])  # 钳到合法工具名
    arg  = {"query_db": "alice", "archive": "alice", "delete_db": "old_logs"}[tool]
    return {"tool": tool, "arg": arg, "reason": act.get("reason", "")}

# ---------- 5) Agent 主循环：interrupt（暂停等审批）+ checkpoint（每步落盘） ----------
def run(state):
    while state["step"] < 6:
        if state.get("pending"):                          # 有挂起的高危动作 → 等审批
            if not state.get("approved"):
                save(state)                               # ★ 落盘后退出，把控制权交人工
                print(f"\n⏸  INTERRUPT：高危操作 delete_db({state['pending']}) 待审批，state 已存盘 .checkpoint.json")
                print("   → 后端类比：审批工作流挂起，进程可退出/崩溃，人工 approve 后断点恢复\n")
                return False                              # 中断：未完成
            act = {"tool": "delete_db", "arg": state["pending"]}     # 已批准：直接执行，不再拦
            state["pending"] = None
        else:
            act = decide(state)                           # 真调 ollama 决策
            if act["tool"] == "done": break
            if act["tool"] in RISKY:                       # 高危：先挂起，下轮 interrupt
                state["pending"] = act["arg"]; continue
        result = TOOLS.get(act["tool"], lambda a: "未知工具")(act.get("arg", ""))
        state["log"].append({"tool": act["tool"], "arg": act.get("arg", ""), "result": result})
        state["step"] += 1; save(state)                   # 每步 checkpoint：崩了能续
        print(f"  step{state['step']}: {act['tool']}({act.get('arg','')}) -> {result}")
    return True                                           # 完成

def main():
    state = load() or {"goal": "归档用户 alice 的数据，再删除旧库 old_logs", "log": [], "step": 0,
                       "pending": None, "approved": False}
    print(f"模型 {MODEL} | checkpoint {'恢复' if state['log'] else '全新'}启动，目标：{state['goal']}")
    done = run(state)
    if not done:                                          # 命中 interrupt：模拟人工 approve 后恢复
        st = load(); st["approved"] = True; save(st)
        print("👤 人工已 APPROVE，从 checkpoint 恢复 …")
        run(load())
    print("\n✅ 任务结束。删掉 checkpoint，下次全新跑。"); clear()

if __name__ == "__main__":
    try: main()
    except urllib.error.URLError: sys.exit("连不上 Ollama：先 `ollama serve` 并 `ollama pull qwen2.5:3b`")

# ================= 参考答案（5 个 ★ 行）=================
# ★ chat 返回：  ["message"] 即 {"role":"assistant","content":...}
# ★ 抠 JSON：    json.loads(txt[txt.index("{"): txt.rindex("}")+1])
# ★ interrupt：  save(state) 落盘后 return False，把流程暂停交给人工
# ★ resume：     st["approved"]=True; save(st); run(load()) 从断点继续
# ★ 高危拦截：   decide 选到 RISKY -> state["pending"]=arg; continue 等下轮 interrupt

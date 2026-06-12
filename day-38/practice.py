"""
Day 38 · LangGraph 入门：手写一台迷你「图状态机」跑通 agent→router→tool/end 循环图。
不装 LangGraph，纯标准库还原它的内核：
  State = dict（共享上下文） | Node = 函数 state->state | Edge = 跳转 | 条件路由 = 看 state 决定下一站
为什么用图不用链：链是直线（检索→生成→结束），Agent 要"想→查→不够再查"——可循环可分支，只有图能表达。
一句话：agent 想，router 路由，tool 执行回边再想；够了去 END。真连本机 Ollama，不付费、不联外网。

⚠️ 需要 Ollama：本机装好并启动，且拉过 qwen2.5:3b（约 1.9GB）。
    ollama serve                  # 启动（默认 http://localhost:11434）
    ollama pull qwen2.5:3b        # 生成模型
跑通即达标：  cd ~/projects/daily-learn && uv run day-38/practice.py
换模型：      OLLAMA_MODEL=qwen2.5:7b uv run day-38/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍（条件路由是核心），再对照文末「参考答案」。下面已是完整版，直接跑。
"""
import os, json, urllib.request, urllib.error

# ---------- chat helper：真连 ollama /api/chat，禁 mock ----------
def chat(msgs):
    body = json.dumps({"model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
                       "messages": msgs, "stream": False}).encode()
    req = urllib.request.urlopen("http://localhost:11434/api/chat", body, timeout=120)
    return json.load(req)["message"]["content"].strip()

# ---------- 一个假"工具"：本地知识库查询（真项目里是 RAG / API / DB） ----------
KB = {
    "langgraph": "LangGraph 把 Agent 编排成有向图：State 是共享 dict、Node 是函数、Edge 是跳转，支持循环和分支。",
    "状态机": "状态机（FSM）= 一组状态 + 转移函数；图状态机就是它的多分支版，节点干活、条件边路由。",
    "条件路由": "条件路由（conditional edge）读 state 决定下一节点，等价于后端的 switch/if-else，是图能分支的关键。",
}
def search_tool(q):
    ql = q.lower()
    for k, v in KB.items():
        if k.lower() in ql: return v
    return "未命中：知识库里没有这条，建议结束。"

# ========= State：一个共享 dict，每个节点读它改它（单一真相源） =========
def new_state(question):
    return {"question": question, "facts": [], "step": 0, "answer": "", "next": ""}

# ========= Node 1 · agent：看已知资料，决定要继续查还是收尾作答 =========
def agent(s):
    facts = "\n".join(s["facts"]) or "（暂无）"
    out = chat([
        {"role": "system", "content": "你是状态机里的 agent。只输出一行：要继续查就写 SEARCH:<关键词>；资料够就写 DONE。"},
        {"role": "user", "content": f"问题：{s['question']}\n已知资料：{facts}\n你的决定："}])
    s["next"] = out                                    # 把决定写回 state，给 router 读
    return s

# ========= Node 2 · tool：执行查询，把结果写回 state，回边指回 agent =========
def tool(s):
    kw = s["next"].split("SEARCH:", 1)[-1].strip()[:20]
    s["facts"].append(f"[{kw}] {search_tool(kw)}")     # 工具结果进 State
    s["step"] += 1
    return s

# ========= Node 3 · finish：资料够，让 LLM 据资料作答，写进 state =========
def finish(s):
    facts = "\n".join(s["facts"]) or "（无）"
    s["answer"] = chat([{"role": "user",
        "content": f"只依据资料回答，简洁：\n资料：{facts}\n问题：{s['question']}"}])
    return s

# ========= 条件路由（conditional edge）：核心——看 state 决定下一站 =========
def router(s):
    if s["step"] >= 3:           return "finish"        # ★1 守门人：步数上限防死循环
    if "DONE" in s["next"]:      return "finish"        # ★2 agent 说够了 -> 收尾
    if "SEARCH" in s["next"]:    return "tool"          # ★3 要查 -> 去工具节点
    return "finish"                                     # 兜底：决定不清也收尾

# ========= 图引擎：节点表 + 边表，从 START 转到 END，纯字典驱动 =========
NODES = {"agent": agent, "tool": tool, "finish": finish}
def run_graph(question):
    s, cur = new_state(question), "agent"               # START -> agent
    while cur != "END":
        s = NODES[cur](s)                               # 执行当前节点
        ran = cur
        if cur == "agent":   cur = router(s)            # ★4 agent 后走条件路由
        elif cur == "tool":  cur = "agent"              # ★5 tool 回边 -> 再想一轮（循环！）
        else:                cur = "END"                # finish -> END
        print(f"  · 跑完 {ran:<7} -> {cur:<7} step={s['step']} next={s['next'][:24]}")
    return s

if __name__ == "__main__":
    for q in ["LangGraph 是什么？", "条件路由怎么决定下一节点？"]:
        print(f"\n❓ {q}")
        st = run_graph(q)
        print(f"🤖 {st['answer']}")
    print("\n跑通即达标：每问都经 agent→router→tool 多轮再 finish，循环图据资料作答。图>链，因为可循环可分支。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  if s["step"] >= 3:        return "finish"
#   ★2  if "DONE" in s["next"]:   return "finish"
#   ★3  if "SEARCH" in s["next"]: return "tool"
#   ★4  cur = router(s)
#   ★5  cur = "agent"
#
# 接 LangGraph：StateGraph(State) + add_node/add_edge/add_conditional_edges，本练习的 router 就是
# add_conditional_edges 的判定函数，回边=循环、step 上限=recursion_limit，概念一字不改，只换 API。

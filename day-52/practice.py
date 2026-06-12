"""
Day 52-53 实战：多 Agent 开发团队模拟系统（真连 Ollama，纯标准库）。
两天合并的 Multi-Agent 收官实战：把一个编程任务交给一支「AI 开发团队」自动完成。
角色分工（各司其职，独立 prompt = 独立上下文窗口）：
  Supervisor（主管/orchestrator） 拆活、定调、决定停 ; PM（产品） 把口语需求变规格 ;
  Coder（开发） 写函数 ; Reviewer（评审） 挑刺打回 ; QA = 本地真 exec 跑测试给硬反馈。
核心是一个 Coder→exec→Reviewer 循环：测试不过或评审不过就打回重写，过了才收手。
这正是 Anthropic「orchestrator-worker」模式的最小可跑版：lead 拆任务派给 worker，再汇总。

后端类比：和你写的「微服务编排」一样——主管=调度器，各 agent=各自负责一段的 worker，
        QA exec=集成测试关卡，跑红就回滚重来。区别只是每个 worker 的「下一步」由 LLM 决策。

⚠️ 需要 Ollama：本机装好并启动，且拉过 qwen2.5:3b（小模型，禁 mock，真连）。
    brew install ollama        # macOS（已装可跳过）
    ollama serve               # 启动服务（默认 http://localhost:11434）
    ollama pull qwen2.5:3b     # 拉模型（约 1.9GB）；OLLAMA_MODEL 可覆盖
任务默认：写一个 is_prime(n) 判断素数；QA 用真 exec 跑断言测它，红了打回 Coder。
跑通即达标：    cd ~/projects/daily-learn && uv run day-52/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import os, re, json, urllib.request, urllib.error

OLLAMA = "http://localhost:11434/api/chat"
MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")    # 默认 3b，OLLAMA_MODEL 可覆盖
TASK   = os.environ.get("TASK", "写一个 is_prime(n) 函数：判断整数 n 是否为素数，返回 True/False")
MAX_ROUNDS = 3                                           # 护栏：评审-重写最多 3 轮，防打转

# ---------- chat helper：把 messages POST 给 /api/chat，标准写法，全队共用 ----------
def chat(system, user, temperature=0.3):
    body = json.dumps({"model": MODEL, "stream": False, "options": {"temperature": temperature},
                       "messages": [{"role": "system", "content": system},
                                    {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())["message"]["content"]  # ★1

# ---------- 各 agent = 一个独立角色 prompt（独立上下文，各司其职）----------
def pm(task):                                            # 产品经理：口语需求 -> 一句话规格
    return chat("你是 PM，把需求压成一句中文规格（函数名/入参/返回/1个边界），不写代码。", task)

def coder(spec, feedback=""):                            # 开发：按规格+评审反馈写 Python
    extra = f"\n上轮被打回，必须修复：{feedback}" if feedback else ""
    code = chat("你是 Python 工程师。只输出一个函数的纯代码，无解释无 markdown 围栏。",
                spec + extra, temperature=0.2)
    m = re.search(r"```(?:python)?\n(.*?)```", code, re.S)  # 模型常带围栏，剥掉
    return (m.group(1) if m else code).strip()

def reviewer(spec, code):                                # 评审：通过则首字 OK，否则给一条修改意见
    return chat("你是评审。代码满足规格回 'OK'，否则只回一条最关键的中文修改意见。", f"规格:{spec}\n代码:\n{code}")

TESTS = {  # 测试集随任务函数名走（默认 is_prime），换 TASK 时也有真断言可跑
    "is_prime":    "assert is_prime(7) and not is_prime(8) and not is_prime(1) and is_prime(2)",
    "add":         "assert add(2,3)==5 and add(-1,1)==0",
    "reverse_str": "assert reverse_str('abc')=='cba'",
}
def qa_run(code):                                        # ★2 QA = 本地真 exec 跑测试，给硬反馈
    fn = (re.search(r"def (\w+)", code) or [None, ""])[1] # 从代码里抠出函数名，挑对应测试集
    tests = TESTS.get(fn, f"assert callable({fn})")      # 没专属断言时至少验函数可调用
    try:
        ns = {}; exec(code, ns); exec(tests, ns)         # 真跑：编译+执行+断言
        return True, "全部测试通过"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"

# ---------- supervisor：orchestrator-worker 编排——拆活、循环派单、QA 卡关、汇总 ----------
def supervisor(task):
    print(f"🧑‍💼 Supervisor 接活：{task}\n")
    spec = pm(task);                       print(f"📋 PM 规格：{spec}\n")          # 拆需求
    feedback = ""
    for r in range(1, MAX_ROUNDS + 1):
        code = coder(spec, feedback);      print(f"💻 Coder 第{r}轮产出：\n{code}\n")  # ★3 写代码
        ok, msg = qa_run(code);            print(f"🧪 QA exec：{'✅' if ok else '❌'} {msg}")
        rev = reviewer(spec, code);        print(f"👀 Reviewer：{rev[:50]}\n")
        passed = ok and rev.strip().upper().startswith("OK")   # ★4 测试+评审双绿才放行
        if passed:
            return f"✅ 第{r}轮交付通过\n{code}"
        feedback = msg if not ok else rev                      # QA 红优先回灌，否则回灌评审意见
    return f"⚠️ {MAX_ROUNDS}轮未通过，最后版本：\n{code}"

if __name__ == "__main__":
    print(f"🏭 多 Agent 开发团队启动 | 模型={MODEL}\n" + "─"*48)
    print("\n📦 最终交付：\n" + supervisor(TASK))                # ★5 放手，让团队自己跑到交付
    print("\n跑通即达标：PM→Coder→QA(真exec)→Reviewer 循环，QA 红就打回重写，全程模型自决。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  return json.loads(urllib.request.urlopen(req, timeout=180).read())["message"]["content"]
#   ★2  ns={}; exec(code, ns); exec(tests, ns)  # 真 exec 跑断言（测试集按函数名挑），红即反馈
#   ★3  code = coder(spec, feedback)
#   ★4  passed = ok and rev.strip().upper().startswith("OK")
#   ★5  supervisor(TASK)
#
# 接生产：worker 换 Claude（多 worker 并行探索可省 90% 时间）、QA 换真 pytest/CI，
# supervisor 换 LangGraph 状态机——编排逻辑一行不改，这就是 multi-agent 开发团队的最小内核。

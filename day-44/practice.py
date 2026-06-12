"""
Day 44 — Multi-Agent 架构：协作 / 委托 / 竞争 三模式（真连 Ollama，纯标准库）。
单 Agent 已会（Day42-43 的 ReAct 内核）。今天把「一个 Agent」变成「一支团队」：
  · 协作模式：planner → coder → reviewer 三个角色各司其职、轮流真调 qwen，流水线产出。
  · 委托模式：supervisor（主管）读任务，判它属于哪类，分派给对应专家 Agent（主从/路由）。
  · 竞争模式：3 个 worker 各出一版方案，judge 投票挑最优（多方案择优）。

后端类比：
  协作=微服务编排（订单→库存→支付，各服务各管一段）  委托=主从/任务路由（dispatcher 分发）
  竞争=负载均衡里的多副本 + 仲裁取最优。Agent 只是把「函数」换成「会推理的角色」。

⚠️ 需要 Ollama：本机装好并启动，且拉过 qwen2.5:3b。
    brew install ollama && ollama serve              # 默认 http://localhost:11434
    ollama pull qwen2.5:3b                            # 1.9GB；OLLAMA_MODEL 可覆盖
跑通即达标：    cd ~/projects/daily-learn && uv run day-44/practice.py
练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import os, json, urllib.request

OLLAMA = "http://localhost:11434/api/chat"
MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")           # 默认 3b，可用环境变量覆盖

# ---------- chat helper：标准 ollama 写法，把 system+user 拼好 POST 给 /api/chat ----------
def chat(system, user, temperature=0.4):
    body = json.dumps({"model": MODEL, "stream": False, "temperature": temperature,
                       "messages": [{"role": "system", "content": system},          # ★1 角色靠 system 塑形
                                    {"role": "user", "content": user}]}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())["message"]["content"].strip()

# ========== 模式一：协作（各司其职，流水线）—— 类比微服务编排 ==========
# 三个角色，每个只干一件事，上一个的产出是下一个的输入。串成一条流水线。
ROLES = {
    "planner":  "你是规划师。把需求拆成 3 条简短实现步骤，只列要点，别写代码。",
    "coder":    "你是程序员。按给定步骤写一个简短 Python 函数，只输出代码，别解释。",
    "reviewer": "你是评审。检查代码是否实现需求，给一句通过/不通过结论 + 一条改进建议。",
}
def collaborate(task):
    plan = chat(ROLES["planner"],  f"需求：{task}")                                  # ★2 planner 先出步骤
    code = chat(ROLES["coder"],    f"需求：{task}\n步骤：{plan}")                     # coder 按步骤写
    review = chat(ROLES["reviewer"], f"需求：{task}\n代码：{code}")                   # reviewer 验收
    return plan, code, review

# ========== 模式二：委托（supervisor 分派）—— 类比主从 / 任务路由 ==========
# 主管自己不干活，只判断任务归属，把活分给对口专家，是「dispatcher」。
WORKERS = {"math": "你是数学专家，只算结果", "code": "你是程序员，只给代码", "write": "你是文案，只写文案"}
def supervise(task):
    pick = chat("你是主管。从 math/code/write 里选最合适处理者，只回一个词。", task).lower()
    worker = next((k for k in WORKERS if k in pick), "write")                        # ★3 解析主管的分派结果
    return worker, chat(WORKERS[worker], task)

# ========== 模式三：竞争（多方案投票）—— 类比负载均衡多副本 + 仲裁 ==========
def compete(task, n=3):
    cands = [chat("用一句话回答，要有亮点", task, temperature=0.9) for _ in range(n)] # ★4 n 个 worker 各出一版
    menu = "\n".join(f"{i+1}. {c}" for i, c in enumerate(cands))
    win  = chat("你是评委，从下列方案选最好的一个，只回编号数字。", menu)               # judge 投票
    return cands, win

if __name__ == "__main__":
    print(f"🤖 Multi-Agent 团队启动 | 模型={MODEL}\n" + "="*50)

    print("\n【协作模式】planner→coder→reviewer 流水线，各司其职：")
    p, c, r = collaborate("写一个函数判断字符串是否回文")
    print(f"  📐 planner:\n{p}\n  💻 coder:\n{c}\n  ✅ reviewer:\n{r}")

    print("\n" + "="*50 + "\n【委托模式】supervisor 看任务、分派给对口专家：")
    for t in ["12 的阶乘是多少", "写一句产品广告语"]:
        w, ans = supervise(t)
        print(f"  🧭 「{t}」→ 派给 [{w}] → {ans[:60]}")

    print("\n" + "="*50 + "\n【竞争模式】3 个 worker 各出方案，judge 投票挑最优：")
    cands, win = compete("给学编程的人一句鼓励")                                       # ★5 跑竞争+投票
    for i, c in enumerate(cands): print(f"  {i+1}. {c}")
    print(f"  🏆 评委选了：{win}")

    print("\n" + "="*50 + "\n三模式 = 微服务编排 / 主从路由 / 负载均衡多副本，团队 > 单兵。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  {"role": "system", "content": system}, {"role": "user", "content": user}
#   ★2  plan = chat(ROLES["planner"], f"需求：{task}")
#   ★3  worker = next((k for k in WORKERS if k in pick), "write")
#   ★4  cands = [chat("用一句话回答，要有亮点", task, temperature=0.9) for _ in range(n)]
#   ★5  cands, win = compete("给学编程的人一句鼓励")
#
# 接生产：每个角色换成带工具的完整 Agent（Day42 内核），协作=LangGraph 多节点、
# 委托=supervisor 路由、竞争=多采样投票。Claude 上等价能力更强、可并行跑团队。

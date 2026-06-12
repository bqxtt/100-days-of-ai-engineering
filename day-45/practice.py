"""
Day 45 实战：CrewAI vs AutoGen —— 用纯标准库手写两种多 Agent 架构，对比差异（真连 Ollama）。
不装任何框架（避免依赖地狱），但把两家的「设计哲学」用 ~60 行各还原一遍，亲手跑通就懂差异。

  CrewAI   = 角色 + 任务 + 流程（role / task / crew）：你定一队角色、排好任务清单，按顺序流水跑。
  AutoGen  = 对话式多 Agent 群聊（conversational group chat）：两三个 Agent 互相说话，聊到收敛才停。
  一句话差异：CrewAI 像「项目排期表」（你写死流程），AutoGen 像「拉群讨论」（流程涌现自对话）。

后端类比：CrewAI = 你写死的 pipeline / DAG（ETL：抽取→清洗→入库，步骤固定）；
        AutoGen = 微服务互相 RPC 聊到达成一致（没有总指挥，靠你来我往收敛）。两者都真调本机 LLM。

⚠️ 需要 Ollama：本机装好并启动，且拉过 qwen2.5:3b。
    ollama serve               # 启动服务（默认 http://localhost:11434）
    ollama pull qwen2.5:3b     # 拉模型（约 1.9GB）；OLLAMA_MODEL 可覆盖
跑通即达标：    cd ~/projects/daily-learn && uv run day-45/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import os, json, urllib.request

OLLAMA = "http://localhost:11434/api/chat"
MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")        # 默认 3b，可用环境变量覆盖

# ---------- 0) 标准 chat helper：把 messages POST 给 /api/chat，拿一段纯文本回复 ----------
def chat(messages, temperature=0.4):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "stream": False, "options": {"temperature": temperature}}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())["message"]["content"].strip()

def ask(system, user):                                       # 单角色一问一答：给人设+任务，拿结果
    return chat([{"role": "system", "content": system}, {"role": "user", "content": user}])

# ====================== 一、迷你 CrewAI：角色 + 任务 + 顺序流程 ======================
# 哲学：先定义角色（role）→ 排任务清单（task）→ crew 按序执行，上一任务产物喂给下一任务。
# 流程是你写死的（sequential），没有自由发言，像流水线。
def mini_crew(topic):
    roles = {                                                # 角色表：每个角色一段固定人设（system）
        "研究员": "你是研究员，只列要点，3 条以内，简洁。",
        "作者":   "你是技术作者，把要点写成一段 60 字内的科普话。",
        "审稿":   "你是审稿，只输出最终成品，必要时润色，别加废话。",
    }
    tasks = [("研究员", f"调研主题：{topic}，给 3 个要点"),     # 任务清单：顺序执行
             ("作者",   "把上面的要点写成科普段落"),
             ("审稿",   "给出最终定稿")]
    out = topic
    for role, task in tasks:                                  # ★1 crew = for 循环顺序跑任务
        out = ask(roles[role], f"{task}\n\n上游产物：{out}")    # 上一步产物当下一步输入（流水线）
        print(f"  🧩 [{role}] {out[:50]}…")
    return out

# ====================== 二、迷你 AutoGen：对话式多 Agent 群聊 ======================
# 哲学：2-3 个 Agent 共享一段对话，轮流发言，聊到出现「DONE」收敛才停。流程涌现自对话，没人排期。
def mini_groupchat(topic, max_turns=4):
    agents = {"提议者": "你提一个简短方案。看到对方意见就改进，满意了在结尾写 DONE。",
              "挑刺者": "你只挑方案的一个毛病并给建议；方案够好了就回复 DONE。"}
    history = [{"role": "user", "content": f"群聊主题：{topic}"}]   # 共享对话历史 = 群聊记忆
    speakers = ["提议者", "挑刺者"]
    for turn in range(max_turns):
        who = speakers[turn % 2]                                    # 轮流发言（round-robin 选下一个）
        sys = agents[who]
        reply = chat([{"role": "system", "content": sys}] + history)
        history.append({"role": "assistant", "content": f"[{who}] {reply}"})  # ★2 发言回灌进共享历史
        print(f"  💬 [{who}] {reply[:50]}…")
        if "DONE" in reply.upper():                                 # ★3 出现 DONE = 收敛，提前停
            break
    return history[-1]["content"]

if __name__ == "__main__":
    topic = "为什么数据库要加索引"
    print(f"🤖 模型={MODEL} | 主题：{topic}\n")
    print("一、CrewAI 风格（角色+任务+顺序流水线，流程写死）：")
    crew_out = mini_crew(topic)                                     # ★4 跑流水线
    print(f"\n📋 Crew 定稿：{crew_out}\n" + "-"*60)
    print("\n二、AutoGen 风格（对话式群聊，流程涌现自来回）：")
    chat_out = mini_groupchat(topic)                               # ★5 跑群聊
    print(f"\n📋 群聊收敛：{chat_out}\n" + "-"*60)
    print("\n差异：Crew=你排好的流水线（步数固定）；GroupChat=聊到 DONE 才停（步数不定）。两者都真调 ollama。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  for role, task in tasks: out = ask(roles[role], ...)
#   ★2  history.append({"role": "assistant", "content": f"[{who}] {reply}"})
#   ★3  if "DONE" in reply.upper(): break
#   ★4  crew_out = mini_crew(topic)
#   ★5  chat_out = mini_groupchat(topic)
#
# 接生产：装 CrewAI 就把 mini_crew 换成 Crew(agents,tasks,process=sequential)；
# 装 AutoGen 就把 mini_groupchat 换成 GroupChatManager。内核就是这两段——角色流水线 vs 对话收敛。

"""
Day 37 · LangChain 核心概念：Chain / Memory / Tool / Agent 四大模块。
本课不装 LangChain，而是用 stdlib 手写一个迷你版，让你看清这四个抽象其实就是后端老熟人：
  · Chain  = 函数串联流水线   prompt模板 -> ollama -> 解析（LCEL 的 a | b | c 就是 compose）
  · Memory = 一个对话历史 list（有状态会话，跟你 session/上下文一样）
  · Tool   = 一个函数注册表（dict 名字->callable，跟你 dispatch table 一样）
  · Agent  = ReAct 循环：模型读问题选工具、执行、看结果、再决策（while + if/else）
一句话：LangChain 没有黑魔法，它替你把"模板/历史/工具/循环"这些后端模式封装好。
纯标准库 + 真连本机 Ollama，无需 pip / 付费 key。

⚠️ 需要 Ollama：本机装好并启动，且拉过生成模型。
    brew install ollama                  # macOS（已装可跳过）
    ollama serve                         # 启动服务（默认 http://localhost:11434）
    ollama pull qwen2.5:3b               # 生成模型（约 1.9GB），OLLAMA_MODEL 可覆盖
跑通即达标：    cd ~/projects/daily-learn && uv run day-37/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑。
"""
import json, os, re, urllib.request

OLLAMA = "http://localhost:11434"
MODEL  = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")   # 默认 qwen2.5:3b，环境变量可覆盖

# ============ 0) chat helper：唯一一处真连 Ollama，往下全是纯函数 ============
def chat(msgs):
    """msgs=[{'role':..,'content':..}] -> {'role','content'}。LangChain 的 ChatOllama 底层也是这个。"""
    return json.load(urllib.request.urlopen(OLLAMA + "/api/chat",
        json.dumps({"model": MODEL, "messages": msgs, "stream": False}).encode(),
        timeout=120))["message"]

# ============ 1) Chain：prompt模板 -> 模型 -> 解析，三个函数串成一条流水线 ============
# LangChain 的 LCEL：prompt | model | parser  —— 那个 | 就是函数 compose，仅此而已。
def prompt_tmpl(topic):                     # ① 模板：填变量
    return [{"role": "user", "content": f"用一句话解释「{topic}」，给后端工程师听，不超30字。"}]
def call_model(msgs):                        # ② 调模型
    return chat(msgs)["content"]
def parse_out(text):                         # ③ 解析：去空白
    return text.strip().replace("\n", " ")
def chain(topic):
    return parse_out(call_model(prompt_tmpl(topic)))   # ★1 串联：模板→模型→解析（就是 LCEL）

# ============ 2) Memory：一个 list 装对话历史，让无状态模型变成有状态会话 ============
# 模型本身无记忆，每次都现拉。Memory = 把历史拼进 messages 一起发，跟你 session 存上下文一样。
class Memory:
    def __init__(self, system): self.msgs = [{"role": "system", "content": system}]
    def say(self, text):
        self.msgs.append({"role": "user", "content": text})       # 追加用户轮
        reply = chat(self.msgs)["content"]                        # ★2 带全部历史去调模型
        self.msgs.append({"role": "assistant", "content": reply}) # 追加 AI 轮，下次接着记
        return reply

# ============ 3) Tool：一个 {名字: 函数} 注册表，就是后端的 dispatch table ============
TOOLS = {}
def tool(fn): TOOLS[fn.__name__] = fn; return fn   # 装饰器=注册。LangChain 的 @tool 一样
@tool
def add(args):    return sum(float(x) for x in re.findall(r"-?\d+\.?\d*", args))  # 抠出数字求和
@tool
def upper(args):  return args.upper()                              # 文本工具
@tool
def length(args): return len(args.strip())                        # 数长度

# ============ 4) Agent：ReAct 循环 = while + 让模型选工具 + 执行 + 反馈，直到给答案 ============
# 这就是 Day36 的 ReAct 落地：模型每步输出 ACT:工具|参数 或 ANSWER:终值；我们执行后喂回。
def agent(question, max_steps=4):
    tnames = ", ".join(TOOLS)
    sys = (f"你是带工具的助手。工具：{tnames}（add求和/upper转大写/length数长度）。"
           f"每步只回一行：要用工具回 ACT:工具|参数；能答了回 ANSWER:结果。")
    msgs = [{"role": "system", "content": sys}, {"role": "user", "content": question}]
    for _ in range(max_steps):
        line = chat(msgs)["content"].strip().splitlines()[0]
        if line.upper().startswith("ANSWER"):
            return line.split(":", 1)[1].strip()
        m = re.match(r"ACT:\s*(\w+)\s*\|\s*(.*)", line, re.I)
        if not m: return line
        name, arg = m.group(1), m.group(2)
        obs = TOOLS[name](arg) if name in TOOLS else f"无此工具:{name}"  # ★3 查注册表执行
        msgs += [{"role": "assistant", "content": line},
                 {"role": "user", "content": f"OBS:{obs}。继续。"}]      # ★4 观测喂回循环
    return "(超步数)"

# ============ 演示：四个模块各跑一遍，看清它们就是四种后端模式 ============
if __name__ == "__main__":
    print(f"模型: {MODEL}  ({OLLAMA})")
    print("\n[1] Chain  prompt→model→parser:")
    print("  ", chain("缓存"))

    print("\n[2] Memory 对话有记忆:")
    m = Memory("你是简洁助手，只用一句话答。")
    m.say("我叫小后端，记住。")
    print("   →", m.say("我叫什么？"))                              # ★5 第二轮应记得名字

    print("\n[3] Tool   注册表+直调:")
    print("   add('2 3')=", TOOLS["add"]("2 3"), " upper('rag')=", TOOLS["upper"]("rag"))

    print("\n[4] Agent  ReAct 选工具:")
    print("   →", agent("把 7 加 5 的和算出来"))
    print("\n四件套都跑通：Chain=串联 Memory=历史list Tool=注册表 Agent=循环。LangChain 替你封装这些。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  return parse_out(call_model(prompt_tmpl(topic)))
#   ★2  reply = chat(self.msgs)["content"]
#   ★3  obs = TOOLS[name](arg) if name in TOOLS else f"无此工具:{name}"
#   ★4  {"role":"user","content":f"OBS:{obs}。继续。"}
#   ★5  m.say("我叫什么？")  上一轮存进 self.msgs，本轮带历史发出，模型才记得
#
# 接真实 LangChain：chain 换 prompt|ChatOllama|StrOutputParser，Memory 换 ConversationBufferMemory，
# tool 换 @tool 装饰器，agent 换 create_react_agent + AgentExecutor —— 概念一行不改，只换实现。

"""
Day 42-43 实战：构建一个「代码分析 Agent」（真连 Ollama，纯标准库）。
两天合并的收官实战：把 Phase 4 前几天学的零件焊成一个能自主多步干活的 Agent。
  Day36 ReAct 架构  Day37 工具/记忆概念  Day40 工具设计  Day41 短期记忆 = messages
核心是一个 while 循环（ReAct）：模型想(Thought)->要工具(Action)->本地真跑(Observation)->塞回去->再想，
循环到模型不再要工具、直接吐出分析报告为止。工具操作的是真实文件系统（list_files/read_file/count_lines）。

后端类比：这就是「一个会用工具的自动化脚本」——只不过下一步由 LLM 决策，不是你写死的 if/else。
        模型自己决定先 ls 哪个目录、再 read 哪个文件、统计哪个、最后总结，全程你不插手。

⚠️ 需要 Ollama：本机装好并启动，且拉过 qwen2.5:3b（支持 tool_calls 的小模型）。
    brew install ollama        # macOS（已装可跳过）
    ollama serve               # 启动服务（默认 http://localhost:11434）
    ollama pull qwen2.5:3b     # 拉模型（约 1.9GB）；OLLAMA_MODEL 可覆盖
分析目标默认是本项目的 day-1/ 目录（真实文件，自己分析自己）。
跑通即达标：    cd ~/projects/daily-learn && uv run day-42/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import os, re, json, urllib.request, urllib.error

OLLAMA = "http://localhost:11434/api/chat"
MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")           # 默认 3b，可用环境变量覆盖
ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # daily-learn/ 根
TARGET = os.environ.get("ANALYZE_DIR", "day-1")                 # 要分析的目录（项目内相对）

# ---------- 0) 工具实现：真操作文件系统。安全边界——只许读、且锁死在项目根内 ----------
def _safe(rel):  # 把相对路径关进 ROOT，挡住 ../ 越权
    p = os.path.realpath(os.path.join(ROOT, rel))
    if not p.startswith(ROOT):
        raise ValueError("越界访问被拒绝")
    return p

def list_files(path="."):                       # 工具1：列目录里的文件
    files = sorted(f for f in os.listdir(_safe(path)) if not f.startswith("."))
    return ", ".join(files) or "(空目录)"

def read_file(path):                            # 工具2：读文件内容（截断防爆 token）
    return open(_safe(path), encoding="utf-8", errors="ignore").read()[:1200]

def count_lines(path):                          # 工具3：统计行数 + 函数数（粗略 def 计数）
    txt = open(_safe(path), encoding="utf-8", errors="ignore").read()
    return f"行数={len(txt.splitlines())} 函数数={len(re.findall(r'^def ', txt, re.M))}"

TOOLS = {"list_files": list_files, "read_file": read_file, "count_lines": count_lines}

# 工具定义（Day40：名字+描述+入参 schema 要写清，模型靠这个决定调谁）
TOOL_DEFS = [
    {"type": "function", "function": {"name": "list_files", "description": "列出目录下的文件，想知道有哪些文件时调用",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "读取一个文件的内容",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "count_lines", "description": "统计文件的行数与函数数",
        "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}}},
]

SYSTEM = (f"你是代码分析 Agent。逐步用工具分析目录 {TARGET}/：先 list_files 看有哪些文件，"
          "再对每个 .py 文件 count_lines，必要时 read_file 看内容；调够工具后停止调用，"
          "直接输出一份中文分析报告（文件清单/总行数/函数数/一句话评价）。")

# ---------- 1) 调 Ollama：把 messages+工具表 POST 给 /api/chat，拿模型的下一步决策 ----------
def ollama_call(messages):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "tools": TOOL_DEFS, "stream": False}).encode()                 # ★1 带 tools 才能触发工具调用
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())["message"]

# ---------- 2) ReAct 循环：Thought->Action(模型)->Observation(本地真跑)->回灌->再循环 ----------
def run_agent(goal):
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": goal}]
    for step in range(8):                                  # 护栏：最多 8 步，防止打转不收手
        msg = ollama_call(messages)                        # 模型决定：调工具 or 出报告
        messages.append(msg)                               # ★2 把模型回复存进短期记忆(messages)
        calls = msg.get("tool_calls")
        if not calls:                                      # 没要工具 = 推理完了，吐最终报告
            return msg["content"]
        for c in calls:                                    # Action：执行模型点名的每个工具
            fn = c["function"]["name"]
            args = c["function"]["arguments"]
            if isinstance(args, str): args = json.loads(args)
            obs = TOOLS[fn](**args)                         # ★3 本地真跑工具，拿 Observation
            print(f"  🔧 {fn}({args}) -> {str(obs)[:60]}")
            messages.append({"role": "tool", "content": str(obs)})   # ★4 观察结果回灌给模型
    return "(达到步数上限，未收尾)"

if __name__ == "__main__":
    print(f"🤖 代码分析 Agent 启动 | 模型={MODEL} | 目标目录={TARGET}/\n")
    report = run_agent(f"分析 {TARGET}/ 这个目录，告诉我有哪些文件、总共多少行、多少个函数。")  # ★5 给目标，放手让它跑
    print("\n📋 分析报告：\n" + report)
    print("\n跑通即达标：上面 🔧 是 Agent 自主决定的多步工具调用，报告由模型据真实统计写成。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  "tools": TOOL_DEFS, "stream": False
#   ★2  messages.append(msg)
#   ★3  obs = TOOLS[fn](**args)
#   ★4  messages.append({"role": "tool", "content": str(obs)})
#   ★5  report = run_agent(f"分析 {TARGET}/ 这个目录，...")
#
# 接生产：工具换成真 read/grep/git，模型换 Claude（tool_use/agentic 强），
# 循环逻辑一行不改——这就是 Claude Code / Cursor 这类编码 Agent 的最小内核。

"""
Day 47 实战：手写一个完整的 MCP Server（纯标准库，stdio + JSON-RPC 2.0）+ 真连 Ollama Agent。
你已懂 MCP 协议（Day46），今天动手把它焊出来：一个进程当 Server，暴露 3 个真工具；
Client 用 subprocess 拉起它、走 stdio 管道收发 JSON-RPC，跑通 initialize -> tools/list -> tools/call，
最后把这堆工具接到 ollama agent loop——模型自己决定调哪个 MCP 工具。

后端类比：MCP Server 就是一个「stdin 收请求 / stdout 回响应」的微服务，只不过传输是 stdio 不是 HTTP，
        协议是 JSON-RPC 2.0（{id,method,params} -> {id,result}）。Client 就是网关：subprocess 拉起、
        管道转发、把模型的 tool_call 翻译成 tools/call。这个 server 能被 Claude Desktop/Code 原样复用。

⚠️ Agent 部分真连 Ollama（禁 mock）：本机装好并启动，拉过 qwen2.5:3b（支持 tool_calls 的小模型）。
    brew install ollama && ollama serve            # 默认 http://localhost:11434
    ollama pull qwen2.5:3b                          # 约 1.9GB；OLLAMA_MODEL 可覆盖
本文件双角色：默认跑 client（拉起自己当 server）。子进程模式 `python practice.py --serve` = 纯 server。
跑通即达标：    cd ~/projects/daily-learn && uv run day-47/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import os, re, sys, json, subprocess, urllib.request

OLLAMA = "http://localhost:11434/api/chat"
MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")
ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # daily-learn/ 根

# ================== 第一部分：MCP SERVER（被子进程拉起，纯 stdin/stdout JSON-RPC）==================
NOTES = {}   # 内存笔记库：id -> text（真 CRUD，可换成 sqlite/文件）

def _safe(rel):                                  # 安全边界：把路径锁死在项目根内，挡 ../ 越权
    p = os.path.realpath(os.path.join(ROOT, rel))
    if not p.startswith(ROOT): raise ValueError("越界访问被拒绝")
    return p

def t_note_add(text):  NOTES[len(NOTES)+1] = text; return f"已存为 #{len(NOTES)}: {text}"   # 工具1 写
def t_note_list():     return "; ".join(f"#{i}:{t}" for i, t in NOTES.items()) or "(空)"      # 工具2 读全部
def t_list_files(path="."): return ", ".join(sorted(f for f in os.listdir(_safe(path)) if not f.startswith(".")))  # 工具3 查文件

TOOLS = {"note_add": t_note_add, "note_list": t_note_list, "list_files": t_list_files}
# 工具表：MCP 的 inputSchema = JSON Schema，和 OpenAI/Ollama 的 function schema 同形，能直接喂给模型
SCHEMAS = [
    {"name": "note_add",   "description": "新增一条笔记并存档", "inputSchema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
    {"name": "note_list",  "description": "列出已存的全部笔记", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "list_files", "description": "列出项目某目录下的文件", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
]

def serve():  # JSON-RPC 路由：一行一个请求，回一行响应（stdio transport）。这套能直接挂进 Claude Desktop。
    for line in sys.stdin:
        if not line.strip(): continue
        req = json.loads(line); m, p, rid = req.get("method"), req.get("params", {}), req.get("id")
        if m == "initialize":      r = {"protocolVersion": "2024-11-05", "serverInfo": {"name": "day47-notes", "version": "1.0"}}
        elif m == "tools/list":    r = {"tools": SCHEMAS}                                        # ★1 暴露工具清单
        elif m == "tools/call":    out = TOOLS[p["name"]](**p.get("arguments", {})); r = {"content": [{"type": "text", "text": str(out)}]}  # ★2 真跑工具
        else:                      r = {}
        sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": rid, "result": r}) + "\n"); sys.stdout.flush()

# ================== 第二部分：MCP CLIENT（subprocess 拉起 server，走管道发 JSON-RPC）==================
class MCPClient:
    def __init__(self):
        self.p = subprocess.Popen([sys.executable, __file__, "--serve"],            # ★3 把自己当 server 拉起
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.n = 0
    def call(self, method, **params):                  # 发一条 JSON-RPC，读一行结果（id 配对）
        self.n += 1
        self.p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": self.n, "method": method, "params": params}) + "\n")
        self.p.stdin.flush()
        return json.loads(self.p.stdout.readline())["result"]
    def close(self): self.p.terminate()

# ================== 第三部分：把 MCP 工具接到 Ollama Agent ==================
def ollama(messages, tools):
    body = json.dumps({"model": MODEL, "messages": messages, "tools": tools, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())["message"]

if __name__ == "__main__":
    if "--serve" in sys.argv: serve(); sys.exit()                                    # 子进程入口=纯 server

    print(f"🤖 MCP Client 启动 | server=本进程 --serve | 模型={MODEL}\n")
    mcp = MCPClient()
    print("握手 initialize ->", mcp.call("initialize")["serverInfo"]["name"])
    schemas = mcp.call("tools/list")["tools"]                                         # ★4 拿工具清单
    print("tools/list ->", [t["name"] for t in schemas])
    print("tools/call note_add ->", mcp.call("tools/call", name="note_add", arguments={"text": "Day47 手写了 MCP"})["content"][0]["text"])

    # MCP 的 inputSchema 直接转成 Ollama function schema，喂给模型自己决定调谁
    odefs = [{"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["inputSchema"]}} for t in schemas]
    msgs = [{"role": "user", "content": "用 list_files 看 day-1 有哪些文件，再 note_add 一条总结，最后 note_list 给我看。"}]
    for _ in range(6):
        m = ollama(msgs, odefs); msgs.append(m)
        if not m.get("tool_calls"): print("\n📋 报告:\n" + m["content"]); break
        for c in m["tool_calls"]:
            a = c["function"]["arguments"]; a = json.loads(a) if isinstance(a, str) else a
            obs = mcp.call("tools/call", name=c["function"]["name"], arguments=a)["content"][0]["text"]  # ★5 走 MCP 执行
            print(f"  🔧 {c['function']['name']}({a}) -> {obs[:60]}")
            msgs.append({"role": "tool", "content": obs})
    mcp.close()
    print("\n跑通即达标：上面是真 JSON-RPC 握手+调用，工具走 MCP 协议跑——这个 server 可原样接 Claude Desktop。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  r = {"tools": SCHEMAS}
#   ★2  out = TOOLS[p["name"]](**p.get("arguments", {})); r = {"content": [{"type":"text","text":str(out)}]}
#   ★3  subprocess.Popen([sys.executable, __file__, "--serve"], stdin=PIPE, stdout=PIPE, text=True)
#   ★4  schemas = mcp.call("tools/list")["tools"]
#   ★5  obs = mcp.call("tools/call", name=..., arguments=a)["content"][0]["text"]
#
# 官方 SDK：pip install mcp，@server.list_tools()/@server.call_tool() 装饰器 + FastMCP 省去手写 JSON-RPC；
# 本文件手写一遍是为看清协议本体——生产用 SDK，stdio transport 一样，能直接挂 Claude Desktop/Code。

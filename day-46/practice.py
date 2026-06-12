"""
Day 46 实战：纯标准库手写一个「极简 MCP 风格」JSON-RPC 服务端+客户端（真连 Ollama）。
MCP = AI 的「USB-C 接口」：一套统一协议，让任何 Host(宿主) 接任何 Server(工具源)，不用一对一对接。
今天不装 mcp 包、不开子进程，进程内演示协议本体——你会亲手敲出真实 MCP 的三步握手报文：
    initialize  ->  tools/list  ->  tools/call    全部走 JSON-RPC 2.0（MCP 的传输层就是它）。
拿到工具结果后，把它当 Observation 喂给本机 ollama，让 qwen2.5:3b 据真实工具值写答案。

后端类比：MCP 之于 AI 工具 = OpenAPI/gRPC 之于微服务，= LSP 之于编辑器。
        Server 暴露能力，Client 握手发现+调用，全靠一份固定的消息格式——今天看的就是这份格式。

⚠️ 需要 Ollama：本机装好并启动，且拉过 qwen2.5:3b。
    ollama serve               # 默认 http://localhost:11434
    ollama pull qwen2.5:3b     # 约 1.9GB；OLLAMA_MODEL 可覆盖
跑通即达标：    cd ~/projects/daily-learn && uv run day-46/practice.py
练习方式：先把 5 个 ★ 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import os, json, urllib.request

OLLAMA = "http://localhost:11434/api/chat"
MODEL  = os.environ.get("OLLAMA_MODEL", "qwen2.5:3b")

# ====================== MCP Server 端：暴露 3 类能力，全靠固定消息格式 ======================
# 能力1: tools（可执行函数，模型点名调用）  本 demo 实现 2 个 tool
def get_weather(city): return f"{city} 今天 24°C，多云转晴"
def add(a, b):         return str(a + b)
TOOLS = {
    "get_weather": (get_weather, {"city": "城市名"}),
    "add":         (add,         {"a": "加数", "b": "被加数"}),
}

class MiniMCPServer:
    """极简 MCP 服务端：只认 JSON-RPC 2.0 报文，方法名按 MCP spec 命名。"""
    def handle(self, req):                                           # 收一条请求，回一条响应
        m, rid, params = req["method"], req.get("id"), req.get("params", {})
        if m == "initialize":                                       # ① 握手：宣告协议版本+能力
            return self._ok(rid, {"protocolVersion": "2024-11-05",
                                  "capabilities": {"tools": {}},
                                  "serverInfo": {"name": "mini-mcp", "version": "0.1"}})
        if m == "tools/list":                                       # ② 发现：报出工具清单+schema
            return self._ok(rid, {"tools": [
                {"name": n, "description": f"调用 {n}",
                 "inputSchema": {"type": "object", "properties": {k: {"type": "string"} for k in p}}}
                for n, (_, p) in TOOLS.items()]})
        if m == "tools/call":                                       # ③ 调用：跑工具，回结果
            fn = TOOLS[params["name"]][0]
            out = fn(**params["arguments"])
            return self._ok(rid, {"content": [{"type": "text", "text": out}]})
        return {"jsonrpc": "2.0", "id": rid, "error": {"code": -32601, "message": "method not found"}}
    def _ok(self, rid, result):                                     # JSON-RPC 2.0 成功响应骨架
        return {"jsonrpc": "2.0", "id": rid, "result": result}     # ★1 result 包成功，error 包失败

# ====================== MCP Client 端：握手 -> 发现 -> 调用，全程只发 JSON-RPC ======================
class MiniMCPClient:
    def __init__(self, server): self.s, self.n = server, 0
    def call(self, method, params=None):                            # 发一条带自增 id 的请求
        self.n += 1
        req = {"jsonrpc": "2.0", "id": self.n, "method": method, "params": params or {}}  # ★2 标准信封
        print(f"  → {json.dumps(req, ensure_ascii=False)}")
        resp = self.s.handle(req)
        print(f"  ← {json.dumps(resp, ensure_ascii=False)}")
        return resp["result"]

# ====================== 把工具结果喂给 ollama，让模型据真实值答题 ======================
def chat(messages):                                                 # 标准 chat helper：stdlib urllib
    body = json.dumps({"model": MODEL, "messages": messages, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=180).read())["message"]["content"]

if __name__ == "__main__":
    srv = MiniMCPServer(); cli = MiniMCPClient(srv)
    print("① initialize 握手"); cli.call("initialize", {"protocolVersion": "2024-11-05"})
    print("② tools/list 发现能力")
    tools = cli.call("tools/list")["tools"]; print(f"    发现工具：{[t['name'] for t in tools]}")
    print("③ tools/call 调用 get_weather")
    res = cli.call("tools/call", {"name": "get_weather", "arguments": {"city": "上海"}})  # ★3 调用报文
    obs = res["content"][0]["text"]                                # ★4 从 content 取文本结果

    print("\n④ 把 MCP 工具结果喂给 ollama 让它据此回答")
    ans = chat([{"role": "user", "content": f"工具说：{obs}。请用一句话回答上海今天适合穿什么。"}])  # ★5
    print("🤖 " + ans.strip())
    print("\n跑通即达标：上面 →/← 就是真实 MCP 三步握手报文，模型据工具真值作答，零外部依赖。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  return {"jsonrpc": "2.0", "id": rid, "result": result}
#   ★2  req = {"jsonrpc":"2.0","id":self.n,"method":method,"params":params or {}}
#   ★3  res = cli.call("tools/call", {"name":"get_weather","arguments":{"city":"上海"}})
#   ★4  obs = res["content"][0]["text"]
#   ★5  ans = chat([{"role":"user","content":f"工具说：{obs}。..."}])
# 接生产：Host=Claude Desktop/Code，Client/Server 跨进程走 stdio 或 SSE，方法名一字不差。
# 真实只是把 srv.handle 换成进程通信，协议格式（initialize/tools/list/tools/call）完全相同。

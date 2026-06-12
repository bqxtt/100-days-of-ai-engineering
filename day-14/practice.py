"""
Day 14 练习：真连本地 Ollama，跑一次完整的 Tool Use / Function Calling 循环。
不再是 mock 模型——真让模型自己决定调哪个工具、传什么参数；本地执行后把结果回填，模型再说话：
    模型输出 tool_calls  ->  本地真正执行函数  ->  把结果以 role=tool 回填  ->  模型再调一次给最终答。

前置依赖（必须）：
  1. 装好并启动 Ollama，监听 http://localhost:11434
  2. 拉一个支持原生 tools 的模型：  ollama pull qwen2.5:3b
  （可用环境变量 OLLAMA_MODEL 覆盖，默认 qwen2.5:3b）

练习方式：先把 3 个标了 ★ 的地方自己写一遍，再对照文末「参考答案」。下面已是可直接运行的完整版：
    uv run day-14/practice.py
"""
import json, os, re, urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"

def chat(messages, **kw):
    """一次 /api/chat 调用，返回 message 对象（含 content / tool_calls）。纯 stdlib。"""
    body = {"model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"),
            "messages": messages, "stream": False, **kw}
    return json.load(urllib.request.urlopen(
        OLLAMA_URL, json.dumps(body).encode(), timeout=120))["message"]

# ============================================================
# 1) 本地真实可执行的工具（后端最熟：就是普通函数）
#    模型不会自己算/查天气，它只会"申请"调用，活儿在你这边干。
# ============================================================
def get_weather(city: str) -> dict:
    mock = {"北京": 26, "上海": 30, "深圳": 33, "Tokyo": 22}   # mock 数据，假装查了气象 API
    return {"city": city, "temp_c": mock.get(city, 20), "unit": "C"}

def calculator(expr: str) -> dict:
    expr = str(expr).translate(str.maketrans("（）", "()"))  # 容错：小模型偶尔给全角括号
    if not re.fullmatch(r"[\d\s+\-*/.()]+", expr):           # 只允许算术字符，挡掉乱输入
        return {"expr": expr, "error": "表达式含非法字符"}
    return {"expr": expr, "result": eval(expr, {"__builtins__": {}})}  # 仅供练习；生产别用 eval

# 函数名 -> 函数对象 的注册表（后端的路由表）
TOOLS = {"get_weather": get_weather, "calculator": calculator}

# 发给 Ollama 的 tools 参数：Ollama/OpenAI 风格 —— {"type":"function","function":{...JSON Schema...}}
TOOL_SCHEMA = [
    {"type": "function", "function": {
        "name": "get_weather", "description": "查某城市当前气温（摄氏）",
        "parameters": {"type": "object",
                       "properties": {"city": {"type": "string", "description": "城市名"}},
                       "required": ["city"]}}},
    {"type": "function", "function": {
        "name": "calculator", "description": "做一次算术运算，expr 是 Python 表达式字符串",
        "parameters": {"type": "object",
                       "properties": {"expr": {"type": "string", "description": "如 26*9/5+32"}},
                       "required": ["expr"]}}},
]

# ============================================================
# 2) Tool Use 回路：真调 Ollama，直到模型不再申请工具才停（agent loop 的雏形）
# ============================================================
def run(user_text):
    messages = [{"role": "user", "content": user_text}]
    while True:
        reply = chat(messages, tools=TOOL_SCHEMA)
        messages.append(reply)                     # 把模型这轮回复整段塞回历史
        if reply.get("content"):
            print("🤖", reply["content"])

        calls = reply.get("tool_calls")
        if not calls:                              # ★1 模型不再申请工具 -> 结束回路
            break

        for c in calls:
            name = c["function"]["name"]
            args = c["function"]["arguments"]       # Ollama 直接给 dict
            fn = TOOLS[name]                         # ★2 用注册表按名字找到真函数
            try:
                out = fn(**args)                      #     本地真正执行，喂模型给的参数
            except Exception as e:                    #     工具出错绝不能崩回路，把错误回报给模型
                out = {"error": str(e)}
            print(f"   🛠 {name}({args}) -> {out}")
            # ★3 工具结果以 role=tool 回填，模型才能接着说话
            messages.append({"role": "tool", "name": name,
                             "content": json.dumps(out, ensure_ascii=False)})

if __name__ == "__main__":
    print("需先启动 Ollama 并 `ollama pull qwen2.5:3b`")
    print("发给模型的 tools 定义：", json.dumps(TOOL_SCHEMA, ensure_ascii=False)[:80], "...\n")
    run("北京现在多少度？把它换算成华氏（公式 c*9/5+32），用计算器算。")

# ============ 参考答案（先自己写的 3 处）============
#   ★1  if not calls: break
#   ★2  fn = TOOLS[name]
#   ★3  messages.append({"role": "tool", "name": name, "content": json.dumps(out, ...)})
# 看到模型真发 tool_calls、工具被本地执行、再拿结果给出最终华氏回答，即跑通。

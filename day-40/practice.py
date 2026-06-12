# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Day 40 — Tool 设计原则：如何为 Agent 设计好用的工具
====================================================

后端类比：给 Agent 设计工具 = 设计一套好用的 REST API。
一个好工具要满足：
  1. name        清晰命名     —— 像 RESTful 路由：GET /weather 不叫 GET /do_stuff
  2. description 说明书       —— 像 OpenAPI summary：告诉调用方何时用、用法、单位
  3. JSON Schema 参数契约     —— 像请求体校验：必填/类型/枚举，缺一不可
  4. friendly error 友好报错  —— 像 422 带 body：把 error 回报给模型，而非 500 崩溃
  5. idempotent  幂等         —— 像 PUT：同样输入多次调用结果一致、无副作用
  6. granularity 粒度合适     —— 一个端点干一件事，别糊成 GET /everything

本练习：同一任务，分别给「差工具」和「好工具」，真调 ollama 的 tools 能力，
对比模型调用成功率。差工具 = 模糊 desc、没 schema、出错就崩。
好工具 = 清晰 desc + 示例 + 严格 schema + 校验 + error 回报模型。

运行：uv run practice.py
依赖：本地 ollama (http://localhost:11434) + qwen2.5:3b（支持 tools）。
  ollama pull qwen2.5:3b
模型可用 OLLAMA_MODEL 覆盖。无网络/无 ollama 时给出明确提示，不 mock。
"""
import json
import os
import urllib.request
import urllib.error

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


def chat(msgs, tools):
    """带 tools 的最小 chat helper：真连 ollama /api/chat。返回 message 对象。"""
    body = json.dumps({
        "model": MODEL,
        "messages": msgs,
        "tools": tools,
        "stream": False,
    }).encode()
    req = urllib.request.urlopen(OLLAMA_URL, body, timeout=120)
    return json.load(req)["message"]


# ---------------------------------------------------------------------------
#  同一只「工具」，两套设计。任务：把订单从仓库 A 转到仓库 B。
# ---------------------------------------------------------------------------

# 差工具：名字含糊、desc 一句废话、没参数 schema。模型很难猜对何时/如何调。
BAD_TOOLS = [{
    "type": "function",
    "function": {
        "name": "do_stuff",
        "description": "处理订单相关的事情",   # 模糊：处理什么？怎么调？
        "parameters": {"type": "object", "properties": {}},  # 没 schema，无约束
    },
}]

# 好工具：动词+名词命名、desc 写清用途/单位/示例、schema 必填+枚举+类型。
GOOD_TOOLS = [{
    "type": "function",
    "function": {
        "name": "transfer_order",
        "description": (
            "把一个订单从源仓库转移到目标仓库。用于库存调拨场景。"
            "示例：把订单 1024 从 BJ 转到 SH，调用 "
            "transfer_order(order_id=1024, from_wh='BJ', to_wh='SH')。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "integer", "description": "订单号，正整数"},
                "from_wh": {"type": "string", "enum": ["BJ", "SH", "GZ"],
                            "description": "源仓库代码"},
                "to_wh": {"type": "string", "enum": ["BJ", "SH", "GZ"],
                          "description": "目标仓库代码"},
            },
            "required": ["order_id", "from_wh", "to_wh"],
        },
    },
}]

WAREHOUSES = {"BJ", "SH", "GZ"}


def run_transfer(args):
    """工具真实实现：参数校验 + 幂等 + 友好 error 回报（不 raise，不崩）。"""
    oid, src, dst = args.get("order_id"), args.get("from_wh"), args.get("to_wh")
    if not isinstance(oid, int) or oid <= 0:
        return {"ok": False, "error": f"order_id 必须是正整数，收到 {oid!r}"}
    if src not in WAREHOUSES or dst not in WAREHOUSES:
        return {"ok": False, "error": f"仓库必须是 {sorted(WAREHOUSES)}，收到 {src!r}->{dst!r}"}
    if src == dst:
        return {"ok": True, "msg": "源=目标，幂等无操作"}  # 幂等：同输入安全
    return {"ok": True, "msg": f"订单 {oid} 已从 {src} 转到 {dst}"}


def trial(tools, label):
    """跑一次：发同样任务，看模型能否成功发出可用 tool_call。"""
    msgs = [{"role": "user", "content": "请把订单 1024 从北京(BJ)仓转到上海(SH)仓"}]
    try:
        m = chat(msgs, tools)
    except (urllib.error.URLError, ConnectionError) as e:
        print(f"  [{label}] ollama 连接失败：{e}. 请先 `ollama serve` 并 pull {MODEL}")
        return None
    calls = m.get("tool_calls") or []
    if not calls:
        print(f"  [{label}] 模型没调工具，直接回答：{m.get('content','')[:60]}…  → 设计失败")
        return False
    fn = calls[0]["function"]
    args = fn["arguments"]
    if isinstance(args, str):
        args = json.loads(args)
    result = run_transfer(args)
    ok = bool(args) and result.get("ok")
    print(f"  [{label}] 调用 {fn['name']}({args}) → {result}  → {'成功' if ok else '失败'}")
    return ok


if __name__ == "__main__":
    print(f"模型：{MODEL}（差工具 vs 好工具，对比 tool_call 成功率）\n")
    print("差工具（模糊 desc + 无 schema）：")
    trial(BAD_TOOLS, "BAD")
    print("好工具（清晰 desc + schema + 校验 + 友好 error）：")
    trial(GOOD_TOOLS, "GOOD")
    print("\n校验 + 友好 error 演示（不崩）：")
    for a in [{"order_id": -1, "from_wh": "BJ", "to_wh": "SH"},
              {"order_id": 5, "from_wh": "BJ", "to_wh": "X"},
              {"order_id": 5, "from_wh": "SH", "to_wh": "SH"}]:
        print("  ", a, "->", run_transfer(a))

    # ★ 挑战：补全这个「报税额」工具，使其 desc 清晰、schema 带 enum+required、
    #   并幂等。提示：region 限 ['CN','US']，amount 正数。完成后 trial 它。
    # 答案见底部 ANSWER。

# ===================== ANSWER（先想再看）=====================
ANSWER = {
    "type": "function",
    "function": {
        "name": "calc_tax",
        "description": "按地区税率计算应缴税额。示例：calc_tax(amount=100, region='CN') 返回 13。",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "税前金额，正数"},
                "region": {"type": "string", "enum": ["CN", "US"], "description": "纳税地区"},
            },
            "required": ["amount", "region"],
        },
    },
}
def calc_tax(amount, region):  # 幂等：同输入恒定输出，无副作用
    if not isinstance(amount, (int, float)) or amount <= 0:
        return {"ok": False, "error": "amount 必须为正数"}
    rate = {"CN": 0.13, "US": 0.10}.get(region)
    if rate is None:
        return {"ok": False, "error": "region 仅支持 CN/US"}
    return {"ok": True, "tax": round(amount * rate, 2)}

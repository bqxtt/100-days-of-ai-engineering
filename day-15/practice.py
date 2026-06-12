"""
Day 15 练习：结构化输出（Structured Output）的「JSON Mode 真抽取 + Schema 校验 + 自愈重试」三板斧。
真连本地 Ollama，让模型把一段自由文本抽成 JSON，再用纯标准库 jsonschema 子集校验，违规就把
错误回带给模型重试一次自愈——把生产里的「脏文本→干净结构体」闭环亲手跑通。

★ 需要先装好 Ollama 并起服务：
    ollama serve            # 默认 http://localhost:11434
    ollama pull qwen2.5:3b  # 本练习用的模型，支持 format="json"
跑通即达标：
    uv run day-15/practice.py
预期：模型抽出 name/age/plan/tags 四字段，若 plan 越枚举/age 越界则带错误重试一次自愈，校验通过。
实战对应：JSON Mode/工具强制 -> 仍可能脏 -> 抽 JSON -> schema 校验 -> 不通过就回带错误重试。
我们用最小 jsonschema 子集（type/required/enum/range/array）自己实现校验，看清模型在做什么。
"""
import json
import re
import urllib.request

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:3b"

# ---- 要约束的目标 schema（jsonschema 子集，类似真实 tool 的 input_schema）----
USER_SCHEMA = {
    "type": "object",
    "required": ["name", "age", "plan", "tags"],
    "properties": {
        "name": {"type": "string"},
        "age":  {"type": "integer", "minimum": 0, "maximum": 150},
        "plan": {"type": "string", "enum": ["free", "pro", "enterprise"]},
        "tags": {"type": "array", "items": {"type": "string"}},
    },
}

# ---- 要抽取的自由文本：一句客服记录，字段藏在自然语言里 ----
SOURCE_TEXT = (
    "客户 Alice 今年 30 岁，目前用的是 pro 套餐，常用 api 和 sdk 这两个能力，"
    "希望下个季度保留 pro。"
)


def ollama_chat(system: str, user: str) -> str:
    """stdlib 直连 Ollama 的 chat 接口，format=json 强制合法 JSON。返回模型文本。"""
    payload = {
        "model": MODEL,
        "format": "json",                      # ★ JSON Mode：保证返回合法 JSON
        "stream": False,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["message"]["content"]


def extract_json(text: str):
    """从模型文本里抠出第一个 JSON 对象，并修掉常见尾逗号。抠不出返回 None。"""
    m = re.search(r"\{.*\}", text, re.DOTALL)          # ★1 贪婪匹配到最后一个 }，配 DOTALL 跨行
    if not m:
        return None
    blob = re.sub(r",\s*([}\]])", r"\1", m.group(0))   # 去掉 } 或 ] 前的尾逗号
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        return None


def validate(obj, schema):
    """最小 jsonschema 校验：返回错误列表，空列表=通过。"""
    errs = []
    if schema["type"] == "object":
        for key in schema.get("required", []):          # ★2 required：缺字段就是硬错误
            if key not in obj:
                errs.append(f"缺少必填字段 '{key}'")
        for key, spec in schema.get("properties", {}).items():
            if key not in obj:
                continue
            v, t = obj[key], spec["type"]
            if t == "integer" and not isinstance(v, int):
                errs.append(f"'{key}' 应为 integer")
            elif t == "string" and not isinstance(v, str):
                errs.append(f"'{key}' 应为 string")
            elif t == "array" and not isinstance(v, list):
                errs.append(f"'{key}' 应为 array")
            if "enum" in spec and v not in spec["enum"]:
                errs.append(f"'{key}'={v!r} 不在允许值 {spec['enum']}")
            if "minimum" in spec and isinstance(v, int) and v < spec["minimum"]:
                errs.append(f"'{key}'={v} 小于下限 {spec['minimum']}")
            if "maximum" in spec and isinstance(v, int) and v > spec["maximum"]:
                errs.append(f"'{key}'={v} 大于上限 {spec['maximum']}")
    return errs


def extract_user(text: str):
    """让 Ollama 把文本抽成符合 schema 的 JSON；不过校验就回带错误重试一次自愈。"""
    schema_hint = json.dumps(USER_SCHEMA, ensure_ascii=False)
    system = (
        "你是数据抽取器。把文本抽成 JSON，必须符合这个 schema："
        + schema_hint
        + " 只输出 JSON，不要解释。plan 只能是 free/pro/enterprise，age 是 0-150 整数。"
    )

    raw = ollama_chat(system, text)
    obj = extract_json(raw) or {}
    errs = validate(obj, USER_SCHEMA)
    if not errs:
        return obj, errs, False

    # ★3 把校验错误回带给模型，要求自己改正——真实里就是再发一轮带 errors 的 prompt
    fix_user = (
        f"原文：{text}\n你刚才的 JSON：{json.dumps(obj, ensure_ascii=False)}\n"
        f"违反 schema：{errs}\n请修正后重新只输出合规 JSON。"
    )
    raw2 = ollama_chat(system, fix_user)
    obj2 = extract_json(raw2) or {}
    return obj2, validate(obj2, USER_SCHEMA), True


def main():
    print(f"源文本：{SOURCE_TEXT}\n连接 Ollama {MODEL} 抽取中…\n")
    obj, errs, retried = extract_user(SOURCE_TEXT)
    tag = "（重试自愈后）" if retried else "（一次过）"
    if not errs:
        print(f"✅ 校验通过{tag}  {obj}")
    else:
        print(f"⚠️ 仍不合规{tag}  {obj}  错误：{errs}")


if __name__ == "__main__":
    main()

# ============ 参考答案（你应当先自己写的 3 处）============
#   ★1  re.search(r"\{.*\}", text, re.DOTALL)        # 贪婪匹配到最后一个 }，配 DOTALL 跨行
#   ★2  for key in schema.get("required", []): if key not in obj: errs.append(...)
#   ★3  把 validate 返回的 errs 拼进 prompt 再调一次 ollama_chat，缺/越界字段交给模型自己改
# 看到 "✅ 校验通过" 即成功——抽取 + schema 校验 + 回带错误重试三件套打通了。

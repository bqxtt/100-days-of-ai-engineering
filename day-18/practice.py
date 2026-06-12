"""
Day 18 练习：「Prompt 模板系统 + A/B 评估」，真连本地 Ollama 跑。
需 Ollama：先 `ollama serve`，模型 qwen2.5:3b（`ollama pull qwen2.5:3b`），端口 11434。
零三方依赖，纯标准库 urllib 调 Ollama。串通三件事：
  1) 模板引擎：变量插值 {{name}} + 版本号 + 内容指纹 -> Prompt 即代码、可版本化
  2) 注册表：v1/v2 两版 prompt 入册，能查历史、能回滚
  3) 真 A/B：两版 prompt 各对几道测试题真调 Ollama，再用 Ollama 当裁判
     (LLM-as-judge) 打分对比选胜者

练习方式：先把 3 个标了 ★ 的行/块自己写一遍，再对照文末「参考答案」。
题量被刻意压到很小，整段 < 60s：
    uv run day-18/practice.py
"""
import re
import json
import time
import hashlib
import urllib.request
from dataclasses import dataclass, field

OLLAMA = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:3b"

# ============ 1) 模板引擎：变量插值 + 版本号 ============
# Prompt 不是写死的字符串，而是「模板 + 变量」。模板入册带版本号，像代码提交。
VAR = re.compile(r"\{\{\s*(\w+)\s*\}\}")          # 匹配 {{var}} / {{ var }}

@dataclass
class PromptTemplate:
    name: str
    version: int
    body: str                                      # 含 {{占位符}} 的模板正文
    fingerprint: str = field(default="", init=False)

    def __post_init__(self):
        # 内容指纹：正文变一个字，哈希就变 -> A/B 才有意义、缓存才会失效（呼应 Day13）
        self.fingerprint = hashlib.sha256(self.body.encode()).hexdigest()[:8]

    def render(self, **vars) -> str:
        # ★1 用变量替换 {{占位符}}；缺变量直接报错，别让模板带洞上线
        return VAR.sub(lambda m: str(vars[m.group(1)]), self.body)

    def required_vars(self) -> set[str]:
        return set(VAR.findall(self.body))

# ---- 注册表：同名 prompt 的多个版本，存一处，可查可回滚 ----
class Registry:
    def __init__(self): self.store: dict[str, list[PromptTemplate]] = {}
    def add(self, t: PromptTemplate): self.store.setdefault(t.name, []).append(t)
    def get(self, name, version): return next(p for p in self.store[name] if p.version == version)
    def latest(self, name): return max(self.store[name], key=lambda p: p.version)
    def history(self, name): return [(p.version, p.fingerprint) for p in self.store[name]]

reg = Registry()
reg.add(PromptTemplate("classify", 1, "把工单分类：{{text}}。直接给类别。"))
reg.add(PromptTemplate("classify", 2,
    "你是客服分类助手。仅从[退款,物流,投诉,其他]里选一个，只输出类别名。\n工单：{{text}}"))

print("== classify 版本历史(版本, 指纹) ==", reg.history("classify"))
print("v2 需要变量:", reg.get("classify", 2).required_vars())
print("v2 渲染示例:", reg.get("classify", 2).render(text="我要退钱"))

# ============ 2) 真连 Ollama（被评估的"模型"）============
# 离线 mock 退役：每道题都把渲染后的 prompt 发给本地 qwen2.5:3b，拿真实输出来评估。
def ollama(prompt: str, num_predict: int = 24) -> str:
    body = json.dumps({"model": MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0, "num_predict": num_predict}}).encode()
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=55) as r:
        return json.load(r)["response"].strip()

# 题量刻意小：2 版 × 3 题 = 6 次生成 + 1 次裁判，总共 7 次调用，整段 < 60s
CASES = [  # (输入, 期望类别)
    ("我要退款", "退款"), ("快递三天没动", "物流"), ("态度太差了", "投诉"),
]

def evaluate(t: PromptTemplate) -> dict:
    hit, outs = 0, []
    for text, want in CASES:
        out = ollama(t.render(text=text))
        outs.append(f"{text}->{out}")
        hit += (want in out)                       # ★2 期望类别出现在真实输出里即命中
    return {"ver": t.version, "fp": t.fingerprint, "acc": hit / len(CASES), "outs": outs}

# ============ 3) 真 A/B：两版对跑 + LLM-as-judge 裁判 ============
t0 = time.time()
a = evaluate(reg.get("classify", 1))
b = evaluate(reg.get("classify", 2))
print("\n== A/B 评估（真调 Ollama）==")
for r in (a, b):
    print(f"v{r['ver']}({r['fp']})  acc={r['acc']:.0%}  样例: {r['outs']}")

# 用 Ollama 当裁判：把两版表现给它，让它按 rubric 选更可靠的那版（开放式任务靠这个）
judge_prompt = (
    "你是 Prompt 评审。两版分类 prompt 各跑同一批工单，输出如下。\n"
    f"A 版准确率 {a['acc']:.0%}，样例 {a['outs']}\n"
    f"B 版准确率 {b['acc']:.0%}，样例 {b['outs']}\n"
    "哪版分类更准、更只输出类别名？只回 A 或 B，单个字母。"
)
verdict = ollama(judge_prompt, num_predict=4)
winner = b if b["acc"] >= a["acc"] else a          # ★3 准确率高者胜（持平偏向新版）
print(f"\n裁判(LLM-as-judge)倾向: {verdict!r}")
print(f"-> 按准确率胜出: v{winner['ver']}  应灰度上线该版（其余进回滚池）")
print(f"总耗时 {time.time()-t0:.1f}s（7 次 Ollama 调用）")

print("\n直觉：Prompt = 代码 -> 入册带版本/指纹 -> 真调模型跑 A/B -> 让模型当裁判 -> 用数据决定上哪版。")

# ============ 参考答案（应先自己写的 3 处）============
#   ★1  return VAR.sub(lambda m: str(vars[m.group(1)]), self.body)
#   ★2  hit += (want in out)
#   ★3  winner = b if b["acc"] >= a["acc"] else a
# 看到 v2 真实准确率 >= v1、裁判也倾向 B，就把"版本控制+真A/B+LLM裁判"串通了。

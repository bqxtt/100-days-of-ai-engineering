"""
Day 32 练习：用 qwen2.5:3b 当裁判（LLM-as-Judge），给 RAG 答案打三个分。
不需要 numpy、不需要付费 key——纯标准库 + 本机 Ollama，亲手把 RAGAS 三指标算出来：
  - Faithfulness 忠实度：答案的每句话能否由 context 支持（治幻觉/编造）
  - Answer Relevancy 答案相关度：答案切不切问题的题（治跑题）
  - Context Relevancy 上下文相关度：检索回的料对问题有不有用（治检索拉胯）
核心就一句：拆句 -> 逐句问裁判 yes/no -> 求平均。RAGAS 库也是这么干的。

⚠️ 需要 Ollama：本机要装好并启动 ollama，且拉过 qwen2.5:3b。
    brew install ollama        # macOS（已装可跳过）
    ollama serve               # 启动服务（默认 http://localhost:11434）
    ollama pull qwen2.5:3b     # 拉裁判模型（约 1.9GB）
跑通即达标：    cd ~/projects/daily-learn && uv run day-32/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, urllib.request, urllib.error

OLLAMA = "http://localhost:11434/api/chat"
MODEL  = "qwen2.5:3b"

# ---------- 裁判一律 temperature=0，钉死随机性，让分数可复现 ----------
def ask_judge(prompt):
    body = json.dumps({"model": MODEL, "stream": False, "options": {"temperature": 0},
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["message"]["content"].strip()

def is_yes(text):  # 容错：模型可能回「Yes.」「是」「yes，因为…」
    return text.strip().lower().lstrip("「\"'").startswith(("yes", "是", "y", "1"))

# ---------- 1) Faithfulness 忠实度：答案每句能否由 context 推出 ----------
def faithfulness(context, answer):
    claims = [s.strip() for s in answer.replace("。", "。|").split("|") if s.strip()]
    supported = 0
    for c in claims:
        verdict = ask_judge(f"上下文：{context}\n陈述：{c}\n这条陈述能由上下文支持吗？只回 yes 或 no。")
        if is_yes(verdict): supported += 1                 # ★1 被支持就计数
    return supported / max(1, len(claims))                  # 支持句 / 总句数

# ---------- 2) Answer Relevancy 答案相关度：RAGAS 同款「反推问题」法 ----------
# 让裁判从答案猜原问题，再比对：跑题答案猜出的问题对不上，相关度就低
def answer_relevancy(question, answer):
    guessed = ask_judge(f"阅读这段答案，写出它最可能在回答的那个问题，只输出问题：{answer}")
    v = ask_judge(f"问题A：{question}\n问题B：{guessed}\n两个问题问的是同一件事吗？只回 yes 或 no。")
    return 1.0 if is_yes(v) else 0.0                         # ★2 反推问题对得上才算切题

# ---------- 3) Context Relevancy 上下文相关度：料里有没有回答问题所需的信息 ----------
def context_relevancy(question, context):
    v = ask_judge(f"资料：{context}\n陈述：这份资料能回答问题「{question}」。\n这条陈述对吗？只回 yes 或 no。")
    return 1.0 if is_yes(v) else 0.0

def evaluate(name, q, ctx, ans):
    print(f"\n【{name}】问：{q}\n  答：{ans}")
    f = faithfulness(ctx, ans); ar = answer_relevancy(q, ans); cr = context_relevancy(q, ctx)
    print(f"  Faithfulness 忠实度       {f:.2f}  (答案有没有编)")
    print(f"  Answer Relevancy 答案相关  {ar:.2f}  (切不切题)")
    print(f"  Context Relevancy 上下文相关{cr:.2f}  (料对不对路)")
    return f, ar, cr

if __name__ == "__main__":
    CTX = "Acme 公司成立于 2021 年，总部在杭州，主营 RAG 检索增强生成的 SaaS。"
    # 第一组：好答案——照料、切题，应三项都高
    evaluate("好答案", "Acme 成立于哪一年？", CTX, "Acme 成立于 2021 年。")
    # 第二组：掺编造(员工500=料里没有)+末句跑题，Faithfulness 与 Answer Relevancy 应明显低
    evaluate("编造+跑题答案", "Acme 成立于哪一年？", CTX,
             "Acme 成立于 2021 年。它有 500 名员工。我建议你今天多喝水。")  # ★3 故意编+跑题
    print("\n跑通即达标：第一组三项均高、第二组忠实度/相关度明显塌——RAGAS 三指标真跑了一遍。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  if is_yes(verdict): supported += 1
#   ★2  return 1.0 if is_yes(v) else 0.0
#   ★3  "Acme 成立于 2021 年。它有 500 名员工。我建议你今天多喝水。"
#
# 接真实 RAGAS：装 `uv add ragas`，把三个手搓函数换成官方指标即可，逻辑同源：
#   from ragas import evaluate
#   from ragas.metrics import faithfulness, answer_relevancy, context_relevancy
#   evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_relevancy])
# 换更强裁判更稳：把 ask_judge 指向 claude-opus-4-8（Anthropic SDK），prompt 不用改。

"""
Day 28 练习：完整可问答的基础 RAG Pipeline（下）——检索→拼prompt→生成→引用。
纯 Python 标准库（无需 numpy、无需付费 API key），真连本地 Ollama 跑两问。
  - 嵌入（embedding）：nomic-embed-text  - 生成（generation）：qwen2.5:3b
四步骨架：① top-k 检索 retrieve  ② 拼 context 装 prompt  ③ 带引用生成  ④ 防幻觉兜底
Day 27 是「上」（加载/分块/嵌入/建库），今天是「下」：把库用起来，真答问。

⚠️ 需要 Ollama：本机要装好并启动 ollama，且拉过两个模型。
    brew install ollama                # macOS（已装可跳过）
    ollama serve                       # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text       # 嵌入模型（约 274MB）
    ollama pull qwen2.5:3b             # 生成模型（约 1.9GB）
跑通即达标：    cd ~/projects/daily-learn && uv run day-28/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, math, urllib.request

OLLAMA = "http://localhost:11434"
EMB_MODEL = "nomic-embed-text"   # 嵌入：把文本变向量
GEN_MODEL = "qwen2.5:3b"          # 生成：拿到 context 写答案

# ---------- 小知识库：5 条「公司内部文档」片段（真项目里来自分块后的文档） ----------
KB = [
    "门禁卡丢失后，请在 24 小时内到一楼前台挂失，并缴纳 20 元补办工本费。",
    "公司年假为每年 15 天，入职满一年可休，未休年假不结转到下一年。",
    "报销流程：登录 OA → 财务 → 新建报销单，发票需在消费后 30 天内提交。",
    "VPN 账号由 IT 部统一分配，远程办公必须连 VPN，密码每 90 天强制更换。",
    "食堂午餐时间为 11:30 至 13:00，员工每餐补贴 8 元，刷工牌结算。",
]

def post(path, body):
    req = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

def embed(text, kind="document"):
    # nomic 用任务前缀区分「被检索的文档」和「检索用的问题」，检索更准
    p = f"search_{kind}: {text}"
    return post("/api/embeddings", {"model": EMB_MODEL, "prompt": p})["embedding"]

def cosine(a, b):  # 语义相似度：方向越一致越接近 1
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)) + 1e-9)

# 建库一次：每条文档先嵌入好，省得每次重算（真项目里存向量库）
KB_VECS = [embed(d, "document") for d in KB]

# ---------- ① 检索 retrieve：问题嵌入 → 和库逐条算相似度 → 取 top-k ----------
def retrieve(question, k=2):
    qv = embed(question, "query")
    scored = [(cosine(qv, v), d) for v, d in zip(KB_VECS, KB)]   # ★1 每条文档算分
    scored.sort(reverse=True)                                    # 分高在前
    return scored[:k]                                            # 取最相关的 k 条

# ---------- ② 拼 context：把 top-k 编号塞进 prompt，让模型只看资料作答 ----------
def build_prompt(question, hits):
    ctx = "\n".join(f"[{i+1}] {d}" for i, (_, d) in enumerate(hits))
    return (f"只根据下面资料回答，引用编号如 [1]；资料里没有就答「资料中未提及」。\n\n"
            f"资料：\n{ctx}\n\n问题：{question}")                # ★2 context 拼进 prompt

# ---------- ③ 生成 generate：把拼好的 prompt 交给 qwen2.5:3b 写带引用的答案 ----------
def generate(prompt):
    return post("/api/generate", {"model": GEN_MODEL, "prompt": prompt,
                                  "stream": False, "options": {"temperature": 0}})["response"]

# ---------- ④ 防幻觉两道闸：a) 检索分太低直接兜底  b) prompt 限定「没有就答未提及」 ----------
def ask(question, k=2, min_score=0.50):
    hits = retrieve(question, k)
    print(f"👤 {question}")
    for s, d in hits:
        print(f"   检索 score={s:.3f}  {d[:24]}…")
    if hits[0][0] < min_score:                                  # ★3 最相关都不够像→不答
        print("🤖 资料中未提及（防幻觉第一道：检索分过低，不硬编）\n"); return
    ans = generate(build_prompt(question, hits))
    print(f"🤖 {ans.strip()}\n")

if __name__ == "__main__":
    ask("食堂几点开饭？")            # 库里有 → 应带引用作答
    ask("报销的发票要几天内交？")    # 库里有 → 应带引用作答
    ask("公司养了几只猫？")          # 库里没有 → 靠 prompt 兜底，不瞎编
    print("跑通即达标：前两问带 [编号] 引用、第三问兜底不幻觉，全程真连 Ollama。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  scored = [(cosine(qv, v), d) for v, d in zip(KB_VECS, KB)]
#   ★2  context 用 "[1] 文档…\n[2] 文档…" 编号，prompt 里要求按编号引用
#   ★3  if hits[0][0] < min_score:  # 最相关一条都低于阈值就兜底
#
# 接真实 Claude：把 generate 换成 Anthropic SDK，检索/拼prompt/引用逻辑不变：
#   import anthropic; client = anthropic.Anthropic()
#   r = client.messages.create(model="claude-opus-4-8", max_tokens=512,
#         messages=[{"role":"user","content": build_prompt(q, hits)}])
#   ans = r.content[0].text   # 同一份 context+引用约束，只换生成后端

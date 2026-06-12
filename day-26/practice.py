"""
Day 26 练习：两阶段检索 = 向量召回 + LLM 重排（真连 Ollama，纯标准库）。
不需要 numpy、不需要付费 API key。一句话流程：
  query --nomic-embed-text 召回 top-N--> 候选 --qwen2.5:3b 当 reranker 逐个打相关分--> 重排 top-K
重点：故意放一个"字面像但答非所问"的注水文档，看它被召回排前，rerank 后沉底。

⚠️ 需要 Ollama：本机要装好并启动 ollama，且拉过这两个模型。
    brew install ollama              # macOS（已装可跳过）
    ollama serve                     # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text     # 嵌入模型，做召回（约 274MB）
    ollama pull qwen2.5:3b           # 生成模型，当 reranker 打分（约 1.9GB）
跑通即达标：    cd ~/projects/daily-learn && uv run day-26/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, math, urllib.request

OLLAMA = "http://localhost:11434/api"
EMB_MODEL  = "nomic-embed-text"   # bi-encoder：doc 向量可离线预算，召回快但有损
RANK_MODEL = "qwen2.5:3b"         # 当 LLM-reranker：query+doc 拼一起出 1 个相关分

QUERY = "怎么给 RAG 加重排提升准确率？"
DOCS = [
    "Cohere Rerank 把 query 和每个候选拼一起逐对打分，是托管的 cross-encoder 重排服务。",
    "重排能把召回里排第6的正确文档提到第1，用1%算力买大半准度，是 RAG 性价比最高的一层。",
    "RAG 准确率不行通常先加 reranker：召回 top-N 后用 cross-encoder 精排出 top-K 再喂模型。",
    "今天天气不错，重排了一下书架，把准确的菜谱放前面，提升了找菜效率。",  # 注水：字面像，答非所问
    "向量数据库支持百万级近似检索，写入快、查询快，但召回有损，常需后接重排。",
]

# ---------- 调 Ollama ----------
def post(path, body):
    req = urllib.request.Request(f"{OLLAMA}/{path}", json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

def embed(text):
    return post("embeddings", {"model": EMB_MODEL, "prompt": text})["embedding"]

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x*x for x in a)), math.sqrt(sum(y*y for y in b))
    return dot / (na*nb + 1e-9)

# ---------- 阶段1：bi-encoder 向量召回 top-N（宽进、快、有损） ----------
def recall(query, docs):
    qv = embed(query)
    scored = [(cosine(qv, embed(d)), d) for d in docs]      # ★1 query 与每个 doc 各自编码再比余弦
    return sorted(scored, key=lambda x: -x[0])              # 相似度从高到低

# ---------- 阶段2：LLM-as-reranker 逐个打分精排（严出、慢、准） ----------
def rerank_score(query, doc):
    prompt = (f"问题：{query}\n文档：{doc}\n"
              "这个文档对回答问题的相关性，0到10打一个整数，只输出数字：")
    out = post("generate", {"model": RANK_MODEL, "prompt": prompt, "stream": False})["response"]
    return float("".join(c for c in out if c.isdigit()) or 0)  # 抠出数字当相关分

def rerank(query, docs, top_k=3):
    scored = [(rerank_score(query, d), d) for d in docs]    # ★2 query+doc 拼一起，逐对打分
    return sorted(scored, key=lambda x: -x[0])[:top_k]      # ★3 取重排后 top-K

def show(title, ranked):
    print(f"\n{title}")
    for i, (s, d) in enumerate(ranked, 1):
        print(f"  {i}. [{s:5.2f}] {d}")

if __name__ == "__main__":
    print(f"query：{QUERY}\n注水文档（字面像、答非所问）：第4条")
    rec = recall(QUERY, DOCS)
    show("① 召回（nomic 向量相似度，top-N）：", rec)
    rk = rerank(QUERY, [d for _, d in rec], top_k=3)
    show("② 重排（qwen2.5:3b 打相关分，top-K=3）：", rk)
    print("\n对比：召回常把注水文档排进前列；rerank 后正确文档顶上、注水沉底即达标。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  scored = [(cosine(qv, embed(d)), d) for d in docs]
#   ★2  scored = [(rerank_score(query, d), d) for d in docs]
#   ★3  return sorted(scored, key=lambda x: -x[0])[:top_k]
#
# 换托管 cross-encoder（Cohere Rerank）：把 rerank() 换成一行 API，召回/生成不动：
#   import cohere; co = cohere.Client(KEY)
#   r = co.rerank(model="rerank-3.5", query=QUERY, documents=DOCS, top_n=3)  # 直接回 relevance score
# 换开源本地 cross-encoder（bge-reranker-v2-m3）：FlagEmbedding 的 FlagReranker 逐对算分，免费离线。

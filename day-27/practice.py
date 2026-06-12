"""
Day 27 练习：基础 RAG Pipeline 上半场 —— 搭好「索引侧」（indexing）。
今天只做一件事：把一堆文档变成可被语义检索的向量库。完整链路：
    加载文档 → 分块(chunk) → nomic-embed-text 嵌入(embed) → 存进 numpy 向量库 → 验证一次检索
下半天(Day28)用这个库做问答(retrieve + generate)，今天先把"地基"夯实。

⚠️ 需要 Ollama：本机装好并启动 ollama，且拉过 nomic-embed-text。
    brew install ollama              # macOS（已装可跳过）
    ollama serve                     # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text     # 拉嵌入模型（约 274MB，768 维）
跑通即达标：    cd ~/projects/daily-learn && uv run day-27/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, urllib.request
import numpy as np

OLLAMA = "http://localhost:11434/api/embeddings"   # 本地嵌入后端
EMB_MODEL = "nomic-embed-text"                      # 768 维，索引和查询必须同一个模型

# ---------- 0) 加载文档：真项目里来自 PDF/网页/Notion，这里用几段内置文本代表 ----------
DOCS = [
    "RAG 全称 Retrieval-Augmented Generation，检索增强生成。先从知识库检索相关片段，再喂给大模型作答，缓解幻觉。",
    "向量数据库存的是 embedding 向量，靠余弦相似度做近邻搜索，常见有 Chroma、Milvus、Pinecone。",
    "文本分块 chunking 把长文档切成小片，块太大噪声多、块太小丢上下文，常用 200-500 字加重叠 overlap。",
    "nomic-embed-text 是开源嵌入模型，输出 768 维向量，可本地用 Ollama 跑，无需付费 API。",
    "今天午饭吃了红烧牛肉面，加了一个卤蛋，店里 WiFi 很慢但面挺香。",  # 噪声：用来验证检索能排开无关内容
]

# ---------- 1) 分块：长文档先切片再嵌入。这里文档已短，按句号粗切+保留来源 ----------
def chunk(text, doc_id, size=80):
    parts, buf = [], ""
    for s in text.replace("。", "。\n").split("\n"):
        s = s.strip()
        if not s: continue
        buf += s
        if len(buf) >= size:
            parts.append(buf); buf = ""
    if buf: parts.append(buf)
    return [{"doc": doc_id, "text": p} for p in parts]

# ---------- 2) 嵌入：调 nomic-embed-text 把文字 → 768 维向量（索引/查询同模型同维） ----------
def embed(text):
    body = json.dumps({"model": EMB_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    vec = json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"]  # ★1 取 embedding 字段
    return np.array(vec, dtype="float32")

# ---------- 3) 入库：把所有块嵌成矩阵 + 归一化（归一后点积=余弦相似度，检索更快） ----------
def build_index(docs):
    chunks = [c for i, d in enumerate(docs) for c in chunk(d, i)]
    M = np.stack([embed(c["text"]) for c in chunks])
    M /= np.linalg.norm(M, axis=1, keepdims=True)            # ★2 行归一化：点积即余弦相似度
    return chunks, M

# ---------- 4) 检索：query 同样嵌入 → 与库矩阵点积 → 取 Top-k（下半天问答的入口）----------
def search(query, chunks, M, k=2):
    q = embed(query); q /= np.linalg.norm(q)
    scores = M @ q                                           # ★3 一次矩阵乘=对全库算相似度
    top = scores.argsort()[::-1][:k]
    return [(chunks[i]["text"], float(scores[i])) for i in top]

if __name__ == "__main__":
    print("→ 建索引中（首调会下载/加载嵌入模型，稍候）...")
    chunks, M = build_index(DOCS)
    print(f"✓ 入库统计：文档 {len(DOCS)} 篇 → 块 {len(chunks)} 个 → 向量库 shape={M.shape}（块数×维度）")
    print(f"  单块平均字数≈{sum(len(c['text']) for c in chunks)//len(chunks)}，维度={M.shape[1]}\n")

    q = "本地嵌入模型 nomic-embed-text 输出多少维向量？"
    print(f"🔍 检索：{q}")
    for txt, sc in search(q, chunks, M):
        print(f"  [{sc:.3f}] {txt}")
    print("\n跑通即达标：看到向量库 shape=(N, 768)，且检索命中嵌入模型那段、把牛肉面排在后面。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  vec = json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"]
#   ★2  M /= np.linalg.norm(M, axis=1, keepdims=True)
#   ★3  scores = M @ q
# 索引侧做完=今天达标；Day28 拿 search() 的命中片段拼进 prompt 调模型 = retrieve+generate。
# 换生产：numpy 库 → Chroma/Milvus；nomic-embed-text → text-embedding-3 等，链路一行不改。

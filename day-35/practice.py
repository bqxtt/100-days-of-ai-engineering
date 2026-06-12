"""
Day 35 实践日：构建一个可用的"个人知识库问答系统"（mini-RAG，完整链路）。
把 Phase 3（Day21-34）的全部技能拼成一个真跑通的 CLI：
  Day21 嵌入 -> Day22 向量库 -> Day23/24 分块 -> Day25 混合检索(向量+关键词)
  -> Day26 rerank 重排 -> Day27/28 pipeline -> Day29-31 高级RAG -> Day32 引用兜底 -> Day34 缓存
一句话：加载文档 -> 分块 -> nomic 嵌入入库 -> 混合检索 -> rerank -> qwen2.5:3b 带引用回答。
纯标准库 + 真连本机 Ollama，无需 numpy / pip / 付费 key。

⚠️ 需要 Ollama：本机要装好并启动，且拉过两个模型（一个嵌入、一个生成）。
    brew install ollama                  # macOS（已装可跳过）
    ollama serve                         # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text         # 嵌入模型（约 274MB，输出 768 维）
    ollama pull qwen2.5:3b               # 生成模型（约 1.9GB）
跑通即达标：    cd ~/projects/daily-learn && uv run day-35/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑。
"""
import json, math, re, hashlib, urllib.request, urllib.error

OLLAMA = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"   # Day21：句向量，768 维
GEN_MODEL   = "qwen2.5:3b"          # Day27：小而能答的生成模型

# ---------- 0) 知识库（KB）：一份本地"文档"。真项目里换成 md/pdf/wiki ----------
DOCS = {
    "rag.md": "RAG 即检索增强生成（Retrieval-Augmented Generation），先从知识库检索相关片段，"
              "再把片段塞进 prompt 让大模型作答，能减少幻觉、引入私有知识。核心三步：嵌入、检索、生成。",
    "chunk.md": "文本分块（chunking）把长文档切成小块再嵌入。常见策略：固定大小、递归分块、语义分块。"
                "块太大检索不精、太小丢上下文，常用 200-500 字并设重叠（overlap）保留边界语义。",
    "vec.md": "向量数据库存定长向量并做近似最近邻（ANN）检索，靠 HNSW/IVF 索引加速。"
              "检索就是把 query 嵌成向量、按余弦相似度 ORDER BY 取 Top-K，是 RAG 的召回层。",
    "rerank.md": "重排（rerank）用 Cross-Encoder 把 query 与候选片段一起打分，比向量召回更准但更慢，"
                 "所以先用向量召回 Top-N、再 rerank 精排 Top-K，是召回与精度的折中。",
    "hybrid.md": "混合检索（hybrid search）= 向量检索 + 关键词检索（BM25），向量擅长语义、关键词擅长术语/缩写，"
                 "两路结果融合再排序，召回更全。是生产 RAG 的默认配置。",
    "eval.md": "RAG 评估看忠实度（faithfulness，答案是否有据）和相关性（relevancy），RAGAS 是常用框架。"
               "生产化还要缓存、增量更新与监控告警，避免知识过期与重复嵌入开销。",
    "weather.md": "今天天气晴，适合散步。",  # 干扰项：和问答主题无关，检验检索能否排除噪声
}

# ---------- 1) Ollama 客户端：嵌入 + 生成。Day34 给嵌入加内存缓存（同句不重复算） ----------
_emb_cache = {}
def _post(path, payload):
    req = urllib.request.Request(OLLAMA + path, json.dumps(payload).encode(),
                                 {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

def embed(text):  # Day21：一句话 -> 768 维向量；缓存命中直接返回
    key = hashlib.md5(text.encode()).hexdigest()
    if key not in _emb_cache:
        _emb_cache[key] = _post("/api/embeddings", {"model": EMBED_MODEL, "prompt": text})["embedding"]
    return _emb_cache[key]

def generate(prompt):  # Day27：把检索片段 + 问题交给生成模型
    return _post("/api/chat", {"model": GEN_MODEL, "stream": False,
        "messages": [{"role": "user", "content": prompt}]})["message"]["content"]

# ---------- 2) 分块（Day23/24）：按句切，再聚成带重叠的小块，保留来源 ----------
def chunk(name, text, size=80, overlap=20):
    sents = [s for s in re.split(r"(?<=[。.!?])", text) if s.strip()]
    blocks, buf = [], ""
    for s in sents:
        buf += s
        if len(buf) >= size:
            blocks.append(buf); buf = buf[-overlap:]  # 留尾巴做重叠，保边界语义
    if buf.strip():
        blocks.append(buf)
    return [{"src": name, "text": b} for b in blocks]

# ---------- 3) 入库（Day22）：每块嵌成向量，存成简易"向量库"（内存 list 即可） ----------
def build_index(docs):
    idx = []
    for name, text in docs.items():
        for c in chunk(name, text):
            c["vec"] = embed(c["text"])  # ★1 给每个块算嵌入向量后入库
            idx.append(c)
    return idx

# ---------- 4) 检索（Day25 hybrid）：向量召回 + 关键词召回，分数融合 ----------
def cos(a, b):
    d = sum(x*y for x, y in zip(a, b))
    return d / (math.sqrt(sum(x*x for x in a)) * math.sqrt(sum(y*y for y in b)) + 1e-9)

def keyword_score(q, text):  # 简版 BM25：query 词在块里命中越多分越高
    qs = set(re.findall(r"\w+", q.lower()))
    return sum(1 for w in qs if w in text.lower()) / (len(qs) or 1)

def retrieve(idx, query, n=4):
    qv = embed(query)
    for c in idx:
        c["v"] = cos(qv, c["vec"])                     # 语义分
        c["k"] = keyword_score(query, c["text"])       # 关键词分
        c["score"] = 0.6 * c["v"] + 0.4 * c["k"]       # ★2 融合两路：语义为主、关键词补术语
    return sorted(idx, key=lambda c: c["score"], reverse=True)[:n]

# ---------- 5) Rerank（Day26）：用生成模型当 Cross-Encoder 给每候选 0-9 打分精排 ----------
def rerank(query, cands, k=3):
    for c in cands:
        ask = f"问题：{query}\n片段：{c['text']}\n这段对回答问题的相关性打分0-9，只输出数字："
        m = re.search(r"\d", generate(ask))
        c["rr"] = int(m.group()) if m else 0           # ★3 取模型相关性分，做二次精排
    # 用召回分做并列时的稳压器，避免小模型打分抖动把对的块挤掉
    return sorted(cands, key=lambda c: (c["rr"], c["score"]), reverse=True)[:k]

# ---------- 6) 生成（Day27/28）：拼带编号引用的 prompt，强制据库作答、给出引用 ----------
def answer(query, top):
    ctx = "\n".join(f"[{i+1}] {c['text']}（来源:{c['src']}）" for i, c in enumerate(top))
    prompt = (f"只依据下面资料回答，并在句末用[编号]标注引用；资料没有就说不知道。\n"
              f"资料：\n{ctx}\n\n问题：{query}\n答案：")
    return generate(prompt), top                       # ★4 把检索片段 + 问题给模型，要带引用

# ---------- 7) 完整 pipeline：把上面所有 Phase3 步骤串起来 ----------
def ask(idx, query):
    cands = retrieve(idx, query, n=5)                  # 混合检索召回
    top = rerank(query, cands, k=3)                    # ★5 召回后再 rerank 精排
    ans, cites = answer(query, top)
    print(f"\n❓ {query}\n🤖 {ans.strip()}")
    print("   引用:", " ".join(f"[{i+1}]{c['src']}" for i, c in enumerate(cites)))

if __name__ == "__main__":
    print("⏳ 加载文档 -> 分块 -> nomic 嵌入入库 ...")
    index = build_index(DOCS)
    print(f"✅ 知识库就绪：{len(DOCS)} 篇文档 -> {len(index)} 个块，每块 {len(index[0]['vec'])} 维")
    for q in ["什么是 RAG？", "分块为什么要重叠？", "rerank 和向量检索差别？"]:
        ask(index, q)
    print("\n跑通即达标：3 问都据库作答且带 [来源] 引用，天气干扰块不被选中。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  c["vec"] = embed(c["text"])
#   ★2  c["score"] = 0.6 * c["v"] + 0.4 * c["k"]
#   ★3  c["rr"] = int(m.group()) if m else 0
#   ★4  return generate(prompt), top
#   ★5  top = rerank(query, cands, k=3)
#
# 接真实云端：嵌入换 OpenAI/Cohere embeddings、向量库换 Chroma/Pinecone、
# rerank 换 Cohere Rerank、生成换 Claude——pipeline 的 7 步顺序一行不改，只换实现。

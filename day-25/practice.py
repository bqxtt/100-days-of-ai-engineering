"""
Day 25 练习：三种检索召回对比——向量检索 + 简易 BM25 + RRF 融合。
纯 Python 标准库 + numpy，真连本地 Ollama 用 nomic-embed-text 给一组文档嵌入。
一句话目标：同一个查询，三套排序摆在一起看差别——
  - 稠密向量检索（dense）：懂语义/近义词，但短查询、专有名词容易漏
  - BM25 关键词检索：抓精确词命中（缩写、ID、人名），但不懂同义
  - Hybrid + RRF：把两路名次融合，互补取长，多数场景最稳

⚠️ 需要 Ollama：本机要装好并启动 ollama，且拉过 nomic-embed-text（约 274MB）。
    brew install ollama                 # macOS（已装可跳过）
    ollama serve                        # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text        # 拉嵌入模型
跑通即达标：    cd ~/projects/daily-learn && uv run day-25/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, math, re, urllib.request
from collections import Counter
import numpy as np

OLLAMA = "http://localhost:11434/api/embeddings"
EMBED  = "nomic-embed-text"

# ---------- 文档库：故意混入「语义近但用词不同」和「关键词精确命中」两类，好对比三种召回 ----------
DOCS = [
    "猫是一种常见的家养宠物，喜欢睡觉和抓老鼠。",            # 0 语义≈狗（宠物），无关键词 BM25
    "狗是人类忠实的伙伴，会看家护院。",                       # 1 语义≈猫
    "RAG 是检索增强生成，先检索资料再让大模型作答。",         # 2 含关键词 RAG
    "向量数据库用 cosine 相似度做近邻搜索。",                  # 3 含关键词 cosine
    "BM25 是经典的关键词检索算法，靠词频和逆文档频率打分。",   # 4 含关键词 BM25
    "Python 是一门简洁的编程语言，适合做后端和脚本。",         # 5 干扰项
    "混合检索把向量召回和关键词召回融合，用 RRF 取长补短。",   # 6 含关键词 RRF/向量/关键词
    "番茄炒蛋是一道家常菜，先炒蛋再下番茄。",                  # 7 强干扰项
]
QUERY = "宠物动物"   # 故意不含库中任何精确词：考验向量懂语义、BM25 抓不到

# ---------- 1) 稠密向量检索：真连 Ollama 嵌入 + 余弦相似度 ----------
def embed(text):
    body = json.dumps({"model": EMBED, "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return np.array(json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"])

def cosine(a, b):
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))   # ★1 余弦=点积/模长积

def vector_search(query):
    qv = embed(query)
    dvs = [embed(d) for d in DOCS]
    scored = [(i, cosine(qv, dv)) for i, dv in enumerate(dvs)]
    return sorted(scored, key=lambda x: -x[1])   # 高相似度在前

# ---------- 2) 简易 BM25 关键词检索：词频 TF + 逆文档频率 IDF ----------
def tok(s):  # 极简分词：中文按字 + 英文按词（真项目用 jieba/分词器）
    return re.findall(r"[a-zA-Z0-9]+|[一-鿿]", s.lower())

def bm25_search(query, k1=1.5, b=0.75):
    docs = [tok(d) for d in DOCS]
    N = len(docs); avgdl = sum(len(d) for d in docs) / N
    df = Counter(t for d in set(map(tuple, docs)) for t in set(d))  # 每词出现在几篇
    scores = []
    for i, d in enumerate(docs):
        tf = Counter(d); s = 0.0
        for t in set(tok(query)):
            if t not in tf: continue
            idf = math.log((N - df[t] + 0.5) / (df[t] + 0.5) + 1)
            s += idf * tf[t]*(k1+1) / (tf[t] + k1*(1 - b + b*len(d)/avgdl))  # ★2 BM25 打分
        scores.append((i, s))
    return sorted(scores, key=lambda x: -x[1])

# ---------- 3) RRF 融合：只看「名次」不看分数，1/(k+rank) 相加，天然跨量纲 ----------
def rrf(rank_a, rank_b, k=60):
    pos = lambda rl: {i: r for r, (i, _) in enumerate(rl, 1)}  # 文档->名次(从1起)
    pa, pb = pos(rank_a), pos(rank_b)
    fused = [(i, 1/(k+pa[i]) + 1/(k+pb[i])) for i in pos(rank_a)]   # ★3 RRF=两路 1/(k+名次) 相加
    return sorted(fused, key=lambda x: -x[1])

def show(title, ranked, n=4):
    print(f"\n=== {title} ===")
    for r, (i, sc) in enumerate(ranked[:n], 1):
        print(f"  {r}. (#{i} {sc:.4f}) {DOCS[i]}")

if __name__ == "__main__":
    print(f"查询：「{QUERY}」  (库中无此精确词，看谁能召回 猫/狗)")
    vec = vector_search(QUERY)
    kw  = bm25_search(QUERY)
    hy  = rrf(vec, kw)
    show("① 稠密向量检索 dense", vec)   # 应召回 猫(0)/狗(1)：懂语义
    show("② BM25 关键词检索",   kw)     # 大概率全 0 分：无精确词命中
    show("③ Hybrid + RRF",      hy)     # 融合：稳住语义召回，又能在有关键词时抢回精确命中
    print("\n跑通即达标：向量召回到宠物、BM25 抓不到、Hybrid 综合最稳——三路一目了然。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b)))
#   ★2  s += idf * tf[t]*(k1+1) / (tf[t] + k1*(1 - b + b*len(d)/avgdl))
#   ★3  fused = [(i, 1/(k+pa[i]) + 1/(k+pb[i])) for i in pos(rank_a)]
# 把 QUERY 换成 "BM25" 试试：此时 BM25 精确命中第4篇，Hybrid 也会把它顶上去。

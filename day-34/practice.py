"""
Day 34 练习：RAG 生产化四件套 —— 把后端最熟的"缓存 + 增量更新 + 监控"搬进向量库。
真用 nomic-embed-text 跑通，全程纯标准库（urllib），不装 numpy/不装 LangChain：
  1) 嵌入缓存（embedding cache）：同一段文本只算一次向量，二次命中走内存，省调用、提速
  2) 增量索引（incremental add/delete）：新增/删除文档只动几行，绝不重建整库
  3) 语义缓存（semantic cache）：问题语义相近就复用旧答案，不重复检索+生成
  4) 监控指标（metrics）：缓存命中率、库规模、平均延迟，一行打印就能接 Prometheus

核心一句话：RAG 上线后 80% 的工作不是检索，而是"别每次都重算"。缓存命中、增量更新、
指标告警——这正是后端做 OLTP 服务那一套，换个数据是向量而已。

⚠️ 需要 Ollama：本机装好并启动 ollama，且拉过 nomic-embed-text。
    brew install ollama              # macOS（已装可跳过）
    ollama serve                     # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text     # 拉嵌入模型（约 274MB，768 维）
跑通即达标：    cd ~/projects/daily-learn && uv run day-34/practice.py
（没装 ollama 也能跑：脚本自带离线随机向量兜底，缓存/增量/语义命中逻辑照样演示）

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import hashlib
import json
import math
import time
import urllib.request

OLLAMA = "http://localhost:11434/api/embeddings"   # 本地嵌入后端
EMB_MODEL = "nomic-embed-text"                      # 768 维，索引和查询必须同一个模型


# ---------- 真嵌入：nomic-embed-text 把文本 → 768 维向量；离线时用确定性随机向量兜底 ----------
def _raw_embed(text):
    body = json.dumps({"model": EMB_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"]

def _fallback_embed(text):
    # 没装 ollama 也能跑：拿文本 hash 当种子造确定性向量，相同文本→相同向量，逻辑不变
    import random
    rng = random.Random(int(hashlib.md5(text.encode()).hexdigest(), 16))
    return [rng.gauss(0, 1) for _ in range(64)]


# ---------- 1) 嵌入缓存：同文本只算一次。key 用文本 hash，二次命中直接返回 ----------
class EmbeddingCache:
    def __init__(self):
        self.store, self.hits, self.miss = {}, 0, 0

    def embed(self, text):
        key = hashlib.md5(text.encode()).hexdigest()
        if key in self.store:
            self.hits += 1                                   # ★1 命中：跳过昂贵的模型调用
            return self.store[key]
        self.miss += 1
        try:
            vec = _raw_embed(text)
        except Exception:
            vec = _fallback_embed(text)
        self.store[key] = vec
        return vec

    def rate(self):
        n = self.hits + self.miss
        return self.hits / n if n else 0.0


def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


# ---------- 2) 增量向量库：add/delete 只动一行，永不重建；嵌入走缓存 ----------
class VectorStore:
    def __init__(self, cache):
        self.cache = cache
        self.items = {}                                      # doc_id -> {"text":..., "vec":...}

    def add(self, doc_id, text):
        self.items[doc_id] = {"text": text, "vec": self.cache.embed(text)}  # 新增=插一条

    def delete(self, doc_id):
        self.items.pop(doc_id, None)                         # ★2 删除=弹一条，不碰其余文档

    def search(self, query, k=2):
        qv = self.cache.embed(query)
        scored = [(cos(qv, it["vec"]), did, it["text"]) for did, it in self.items.items()]
        return sorted(scored, reverse=True)[:k]


# ---------- 3) 语义缓存：问题语义相近就复用旧答案，省一次检索+生成 ----------
class SemanticCache:
    def __init__(self, cache, threshold=0.92):
        self.cache, self.threshold = cache, threshold
        self.qa = []                                         # [(query_vec, answer)]
        self.hits, self.miss = 0, 0

    def get(self, query):
        qv = self.cache.embed(query)
        for vec, ans in self.qa:
            if cos(qv, vec) >= self.threshold:               # ★3 相似度过阈→直接复用旧答
                self.hits += 1
                return ans
        self.miss += 1
        return None

    def put(self, query, answer):
        self.qa.append((self.cache.embed(query), answer))

    def rate(self):
        n = self.hits + self.miss
        return self.hits / n if n else 0.0


# ---------- 4) 一个简化的 RAG：检索 top1 文档当答案，叠加语义缓存 + 计时监控 ----------
def ask(store, scache, q):
    t0 = time.perf_counter()
    cached = scache.get(q)
    if cached is not None:
        return cached, (time.perf_counter() - t0) * 1000, "语义缓存命中"
    top = store.search(q, k=1)[0]
    ans = top[2]
    scache.put(q, ans)
    return ans, (time.perf_counter() - t0) * 1000, "走检索"


if __name__ == "__main__":
    cache = EmbeddingCache()
    store = VectorStore(cache)
    scache = SemanticCache(cache)

    print("== 1) 嵌入缓存 + 增量 add：建库 4 篇文档 ==")
    DOCS = {
        "d1": "RAG 全称检索增强生成，先检索相关片段再喂给大模型作答，缓解幻觉。",
        "d2": "向量数据库靠余弦相似度做近邻搜索，常见有 Chroma、Milvus、Pinecone。",
        "d3": "嵌入缓存让同一段文本只算一次向量，二次直接命中内存，省调用提速。",
        "d4": "今天午饭吃了红烧牛肉面加卤蛋，店里 WiFi 很慢但面挺香。",  # 噪声
    }
    for did, t in DOCS.items():
        store.add(did, t)
    print(f"   库规模={len(store.items)}  嵌入命中率={cache.rate():.0%}（全 miss，首次都得算）")

    print("\n== 2) 重复同文 + 删除：嵌入缓存命中 / 增量 delete 不重建 ==")
    store.add("d1", DOCS["d1"])                # 同文重入 → 嵌入缓存命中，不再调模型
    store.delete("d4")                         # 删噪声文档，其余 3 篇纹丝不动
    print(f"   库规模={len(store.items)}  嵌入命中率={cache.rate():.0%}（d1 复用命中一次）")

    print("\n== 3) 语义缓存：第一次走检索，相近问题第二次直接复用 ==")
    a1, ms1, why1 = ask(store, scache, "什么是 RAG？")
    a2, ms2, why2 = ask(store, scache, "RAG 是啥意思")      # 措辞不同、语义相同
    print(f"   Q1[{why1:8s}] {ms1:6.1f}ms  -> {a1[:24]}…")
    print(f"   Q2[{why2:8s}] {ms2:6.1f}ms  -> {a2[:24]}…")

    print("\n== 4) 监控指标：一行打印，可直接接 Prometheus ==")
    print(json.dumps({
        "embed_cache_rate": round(cache.rate(), 3),
        "semantic_cache_rate": round(scache.rate(), 3),
        "vectors": len(store.items),
        "embed_calls": cache.miss,
    }, ensure_ascii=False))

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  self.hits += 1
#   ★2  self.items.pop(doc_id, None)
#   ★3  if cos(qv, vec) >= self.threshold:
# 看到：建库全 miss → 重入命中 → 删除后库不重建 → 相近问题语义缓存提速，四件套就串通了。

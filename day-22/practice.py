"""
Day 22 练习：纯 NumPy 手写一个 mini 向量库（Vector DB），真连 Ollama 嵌入+检索+生成。
内核就三件事：add（嵌入入库）、query topk（余弦相似度暴力检索）、相似度排序。
把 6 句话入库，查一条问题取 Top-K，再让 qwen2.5:3b 拿检索结果生成一句答 —— 这就是 RAG 的雏形。

⚠️ 需要 Ollama：本机装好并启动 ollama，且拉过两个模型：
    ollama serve                    # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text    # 嵌入模型（约 270MB，768 维）
    ollama pull qwen2.5:3b          # 生成模型（约 1.9GB）
跑通即达标：   cd ~/projects/daily-learn && uv run day-22/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, urllib.request
import numpy as np

OLLAMA = "http://localhost:11434"
EMBED_MODEL = "nomic-embed-text"   # 嵌入：句子 -> 768 维向量
GEN_MODEL   = "qwen2.5:3b"          # 生成：拿检索结果作答


def embed(text, prefix="search_document"):
    """调 Ollama 把一句话嵌成向量（768 维）。nomic 建议入库用 search_document、查询用 search_query 前缀。"""
    body = json.dumps({"model": EMBED_MODEL, "prompt": f"{prefix}: {text}"}).encode()
    req = urllib.request.Request(OLLAMA + "/api/embeddings", body, {"Content-Type": "application/json"})
    return np.array(json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"], dtype=float)


def generate(prompt):
    """调 qwen2.5:3b 一把生成（演示 RAG 的"生成"那一步）。"""
    body = json.dumps({"model": GEN_MODEL, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA + "/api/generate", body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["response"].strip()


class MiniVectorDB:
    """纯 NumPy 的 mini 向量库：add 入库、query 暴力检索 Top-K（余弦相似度）。"""
    def __init__(self):
        self.texts, self.vecs = [], []          # 原文 + 向量，平行存（等于一张两列表）

    def add(self, text):
        v = embed(text)
        self.texts.append(text)
        self.vecs.append(v / (np.linalg.norm(v) + 1e-8))   # 入库即归一化，余弦=点积

    def query(self, q, k=3):
        qv = embed(q, prefix="search_query"); qv = qv / (np.linalg.norm(qv) + 1e-8)
        M = np.stack(self.vecs)                  # [N,768]
        sims = M @ qv                            # ★1 归一化后，余弦相似度=矩阵乘向量（暴力O(N)）
        top = np.argsort(-sims)[:k]              # ★2 相似度从高到低取前 k 个下标
        return [(self.texts[i], float(sims[i])) for i in top]


DOCS = [
    "用户下单后超过 3 天仍未发货，会自动触发提醒。",
    "物流轨迹在仓库分拣后两天内更新到运输中。",
    "退款一般在 1-3 个工作日原路返回到付款账户。",
    "新用户注册即送 50 元优惠券，限首单使用。",
    "今天天气晴朗，适合户外跑步和骑行。",
    "猫是夜行动物，瞳孔在暗处会放大成圆形。",
]

if __name__ == "__main__":
    db = MiniVectorDB()
    print("入库 6 句话（真嵌入）…")
    for d in DOCS:
        db.add(d)

    q = "下单后很久不发货怎么办"
    print(f"\n查询：{q}\nTop-3 最近邻：")
    hits = db.query(q, k=3)
    for t, s in hits:
        print(f"  {s:.3f}  {t}")

    context = "\n".join(t for t, _ in hits)
    prompt = f"只根据下面资料用一句话回答问题。\n资料：\n{context}\n问题：{q}\n答："  # ★3 拼上下文喂模型=RAG
    print("\n用 Top-3 当上下文，qwen2.5:3b 生成：")
    print("  " + generate(prompt))
    print("\n跑通即达标：Top-3 命中订单/物流相关、相似度明显高于天气/猫两句。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  sims = M @ qv                 # 向量已归一化，点积就是余弦相似度
#   ★2  top = np.argsort(-sims)[:k]   # 负号=降序，取前 k
#   ★3  prompt = f"...资料：\n{context}\n问题：{q}\n答："   # 检索结果当上下文喂 LLM
#
# 上生产：把 MiniVectorDB 换成 Chroma —— add/query 心智一模一样，只是它带 HNSW 索引扛百万级：
#   import chromadb; c = chromadb.Client(); col = c.create_collection("docs")
#   col.add(documents=DOCS, ids=[str(i) for i in range(len(DOCS))])   # 自动嵌入+入库
#   col.query(query_texts=[q], n_results=3)                            # 自动嵌入+Top-K

"""
Day 21 练习：Embedding 原理「真嵌入 + 手写余弦 + 语义排序」三板斧。
真连本机 Ollama，把一组中英文句子用 nomic-embed-text 嵌成 768 维向量，纯手写余弦相似度，
给定 query 排序找语义最近的句子——把"语义=坐标距离"的检索内核亲手跑通。

★ 需要先装好 Ollama 并起服务、拉嵌入模型：
    ollama serve                    # 默认 http://localhost:11434
    ollama pull nomic-embed-text    # 768 维句向量模型
可选：ollama pull qwen2.5:3b       # 文末用它把意图改写成检索 query
跑通即达标：
    uv run day-21/practice.py
预期：每句维度=768；query「怎样让接口更快」语义最近的是 API/优化类句子，"今天天气真好"垫底。
实战对应：query 嵌成向量 -> 和库里每条算余弦 -> sorted 取 Top-K，就是向量库检索的概念内核。
余弦只看方向不看长短：cos=A·B/(|A||B|)，1=同义 0=无关；近义≠近字面，零字面重叠也能命中。
"""
import json
import math
import urllib.request

# ---- 待检索的句子库：故意混中英、混话题，看跨语言/跨字面能否靠语义聚到一起 ----
CORPUS = [
    "加缓存能显著降低 API 接口的响应时间",
    "给后端接口接上 Redis 缓存来降低耗时",
    "优化数据库查询的 SQL 让响应更快",
    "今天天气真好，适合出去散步",
    "周末打算去爬山看日出",
    "晚饭想吃一碗热腾腾的牛肉面",
]
QUERY = "怎样让接口更快"


def embed(t):
    return json.load(urllib.request.urlopen(
        "http://localhost:11434/api/embeddings",
        json.dumps({"model": "nomic-embed-text", "prompt": t}).encode(),
        timeout=60))["embedding"]


def cosine(a, b):
    """手写余弦相似度：只比方向不比长短，落在 [-1,1]，越大越像。"""
    dot = sum(x * y for x, y in zip(a, b))                 # ★1 点积 A·B：对应维相乘再相加
    na = math.sqrt(sum(x * x for x in a))                   # 模长 |A|
    nb = math.sqrt(sum(y * y for y in b))                   # 模长 |B|
    return dot / (na * nb)                                  # ★2 余弦 = 点积 / (|A|·|B|)


def search(query, corpus):
    """query 嵌成向量，和库里每条算余弦，按相似度降序——这就是检索内核。"""
    qv = embed(query)
    scored = [(cosine(qv, embed(s)), s) for s in corpus]
    scored.sort(reverse=True)                              # ★3 余弦越大越靠前，取 Top-K
    return scored


def main():
    print(f"嵌入模型：nomic-embed-text  库内 {len(CORPUS)} 句，开始嵌入…\n")
    dim = len(embed(CORPUS[0]))
    print(f"每句被编码成 {dim} 维向量（768 维 = 768 个浮点的'语义身份证'）\n")
    print(f"query：{QUERY}\n按语义相似度排序（零字面重叠也能命中）：")
    for i, (score, s) in enumerate(search(QUERY, CORPUS), 1):
        bar = "█" * round(score * 30)
        print(f"  {i}. {score:.3f} {bar:<30} {s}")
    print("\n看到 API/数据库/Redis 类挤上前排、'天气/爬山'垫底，即说明语义检索打通了。")


if __name__ == "__main__":
    main()

# ============ 参考答案（你应当先自己写的 3 处）============
#   ★1  dot = sum(x*y for x,y in zip(a,b))           # 点积：对应维相乘再累加
#   ★2  return dot / (na*nb)                          # 余弦=点积/(模长·模长)，归一化掉长短
#   ★3  scored.sort(reverse=True)                     # 余弦降序，最像的排最前
# 看到 query「怎样让接口更快」前排全是 API/延迟/缓存、爬山天气垫底，即成功——
# 嵌入 + 手写余弦 + 语义排序三件套打通，正是向量数据库检索的 1% 概念内核。

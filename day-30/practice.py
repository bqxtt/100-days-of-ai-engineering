"""
Day 30 练习：CRAG 简版（Corrective RAG / 纠错检索增强生成）——真连 Ollama，纯标准库。
不需要 numpy、不需要付费 API key。核心思路一句话：
  检索 -> 用 qwen2.5:3b 给每篇文档「相关性」打分 -> 不够好就「改写 query」重检 -> 再答。
对照 Day 21-29 的「检索->塞进 prompt->作答」固定流程，今天给它加了「自我评估 + 自我纠错」的回路：
  检索回来不一定对，先让模型当评委（grade），低于阈值就纠错（rewrite + retrieve 再来一遍）。

⚠️ 需要 Ollama：本机要装好并启动 ollama，且拉过这两个模型。
    brew install ollama                    # macOS（已装可跳过）
    ollama serve                           # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text           # 嵌入模型（检索打分用，约 274MB）
    ollama pull qwen2.5:3b                 # 生成+相关性评委（约 1.9GB）
跑通即达标：    cd ~/projects/daily-learn && uv run day-30/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, math, urllib.request

OLLAMA = "http://localhost:11434"
EMB_MODEL, GEN_MODEL = "nomic-embed-text", "qwen2.5:3b"   # 嵌入 vs 生成，分工不同
GRADE_THRESHOLD = 0.55          # 相关性阈值：低于它 = 检索质量不够，触发纠错重检
MAX_RETRIES = 2                 # 纠错回路最多重试几次，防止一直改写不收手（agent 护栏思想）

# ---------- 0) 假知识库：真项目里这是向量库里几万条 chunk，这里手搓 5 条 ----------
DOCS = [
    "Self-RAG 让模型自己发 reflection token，决定要不要检索、检索回来好不好、有没有支撑。",
    "CRAG（Corrective RAG）用一个评估器给检索结果打分，差就改写 query 去网络重检后纠正。",
    "Adaptive RAG 按问题难度路由：简单题直接答，中等走单次检索，难题走多步迭代检索。",
    "猫是一种常见宠物，喜欢睡觉和抓老鼠，和高级 RAG 没什么关系。",
    "向量数据库用近似最近邻（ANN）做相似度检索，是 RAG 的检索底座。",
]

# ---------- 1) 嵌入 + 余弦相似度：检索的底座（接 Day 21-22） ----------
def embed(text):
    body = json.dumps({"model": EMB_MODEL, "prompt": text}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/embeddings", body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["embedding"]

def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)

def retrieve(query, doc_vecs, k=2):
    qv = embed(query)
    ranked = sorted(DOCS, key=lambda d: cos(qv, doc_vecs[d]), reverse=True)
    return ranked[:k]                                       # 取最相似的 k 条

# ---------- 2) 调 qwen2.5:3b 生成（评委 + 最终作答都走它） ----------
def chat(prompt):
    body = json.dumps({"model": GEN_MODEL, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0}}).encode()
    req = urllib.request.Request(f"{OLLAMA}/api/generate", body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["response"].strip()

# ---------- 3) CRAG 核心：让模型当评委给文档相关性打 0~1 分（Self-RAG 的「评分」思想） ----------
def grade(query, doc):
    p = (f"问题：{query}\n文档：{doc}\n"
         "这篇文档和问题相关吗？只回一个 0 到 1 的小数（1=高度相关，0=无关），别的不要：")
    raw = chat(p)
    try:
        return max(0.0, min(1.0, float(raw.split()[0].strip(":：。"))))  # ★1 解析评委分数，夹到 0~1
    except ValueError:
        return 0.0

# ---------- 4) 纠错：相关性不够就改写 query，换个说法重检（CRAG 的 corrective） ----------
def rewrite(query):
    return chat(f"原问题检索效果不好，把它改写得更适合检索（更具体/换关键词），只回改写后的问句：\n{query}")

def crag(query, doc_vecs):
    for attempt in range(MAX_RETRIES + 1):
        docs = retrieve(query, doc_vecs)
        scores = [grade(query, d) for d in docs]            # ★2 给每篇召回文档打相关性分
        best = max(scores)
        print(f"  第{attempt+1}轮 query=「{query}」  相关性={[round(s,2) for s in scores]} 最高={best:.2f}")
        if best >= GRADE_THRESHOLD or attempt == MAX_RETRIES:
            good = [d for d, s in zip(docs, scores) if s >= GRADE_THRESHOLD] or docs
            return good, best, attempt + 1
        query = rewrite(query)                              # ★3 没过阈值：改写后重检，再来一轮
    return docs, best, MAX_RETRIES + 1

def answer(query, docs):
    ctx = "\n".join(f"- {d}" for d in docs)
    return chat(f"只根据以下资料用一句话回答，没有就说不知道：\n{ctx}\n问题：{query}")

if __name__ == "__main__":
    doc_vecs = {d: embed(d) for d in DOCS}                  # 离线建索引：每条 chunk 先嵌入
    for q in ["CRAG 是怎么纠错的？", "今天天气怎么样？"]:
        print(f"\n👤 {q}")
        docs, best, rounds = crag(q, doc_vecs)
        print(f"🤖 {answer(q, docs)}  （评分{best:.2f}，用了{rounds}轮检索）")
    print("\n跑通即达标：第1题一次过、第2题低分触发改写重检，全程真连 Ollama。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  return max(0.0, min(1.0, float(raw.split()[0].strip(":：。"))))
#   ★2  scores = [grade(query, d) for d in docs]
#   ★3  query = rewrite(query)
#
# 真实 CRAG（arxiv 2401.15884）：评估器判 correct/ambiguous/incorrect，incorrect 时走网络搜索重检；
# 这里用「分数阈值 + 改写本地重检」做最小可跑骨架。把 chat() 换成 Anthropic SDK、retrieve() 接真向量库即生产版。

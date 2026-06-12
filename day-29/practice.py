"""
Day 29 练习：HyDE 实战——直接检索 vs HyDE 检索（真连 Ollama）。
HyDE（Hypothetical Document Embeddings 假设文档嵌入）：先让 LLM 对问题"瞎编"一个像样的
假设答案，再用这个假设答案去嵌入检索。原理——问题和答案语义形态不同，但答案和文档同形态，
"答案↔文档"比"问题↔文档"更近，命中更准。今天亲眼对比两条路谁命中对。

⚠️ 需要 Ollama：本机要装好并启动，且拉过两个模型（嵌入 + 生成）。
    brew install ollama              # macOS（已装可跳过）
    ollama serve                     # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text     # 嵌入模型（约 274MB）
    ollama pull qwen2.5:3b           # 生成假设答案用（约 1.9GB）
跑通即达标：    cd ~/projects/daily-learn && uv run day-29/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, urllib.request
import numpy as np

OLLAMA   = "http://localhost:11434"
EMBED_M  = "nomic-embed-text"   # Day27 学的嵌入模型：文本 -> 向量
GEN_M    = "qwen2.5:3b"          # 小生成模型：编一个假设答案

# ---------- 知识库：一堆"文档"（陈述句，和答案同形态，和问题不同形态） ----------
DOCS = [
    "向量数据库用近似最近邻（ANN）索引在高维空间快速检索，常见有 HNSW、IVF。",
    "HNSW 是一种基于跳表的图索引，构建分层图，查询时自顶向下贪心搜索，召回与速度平衡好。",
    "RAG 检索增强生成把相关文档片段拼进 prompt，让大模型基于真实资料作答，减少胡说和幻觉。",
    "嵌入模型把文本压成稠密向量，语义相近的文本向量也相近，用余弦相似度衡量。",
    "限流常用令牌桶或漏桶算法，令牌桶允许突发，漏桶平滑输出，保护后端不被打垮。",
    "数据库分库分表后跨库 JOIN 困难，常用冗余字段或应用层聚合替代。",
]

def embed(text):
    body = json.dumps({"model": EMBED_M, "prompt": text}).encode()
    req  = urllib.request.Request(OLLAMA + "/api/embeddings", body, {"Content-Type": "application/json"})
    return np.array(json.loads(urllib.request.urlopen(req, timeout=120).read())["embedding"])

def generate(prompt):
    body = json.dumps({"model": GEN_M, "prompt": prompt, "stream": False}).encode()
    req  = urllib.request.Request(OLLAMA + "/api/generate", body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())["response"].strip()

def cos(a, b):
    return a @ b / (np.linalg.norm(a) * np.linalg.norm(b))  # 余弦相似度：越接近 1 越像

# 预先把知识库嵌好（真项目里离线建好存进向量库）
DOC_VECS = [embed(d) for d in DOCS]

def top1(query_vec):
    sims = [cos(query_vec, dv) for dv in DOC_VECS]
    i = int(np.argmax(sims))
    return i, sims[i]

# ---------- 直接检索：用原始问题嵌入去查 ----------
def retrieve_direct(question):
    qv = embed(question)                                  # ★1 直接把问题嵌成向量
    return top1(qv)

# ---------- HyDE：先编假设答案，再用答案嵌入去查 ----------
def hyde_answer(question):
    prompt = (f"请用一句话直接、专业地回答下面这个技术问题，只写答案、不解释、不要说不知道：\n{question}")
    return generate(prompt)

def retrieve_hyde(question):
    fake = hyde_answer(question)                           # ★2 让 LLM 生成假设答案（陈述句）
    qv = embed(fake)                                       # ★3 用假设答案嵌入，而非原问题
    return top1(qv), fake

if __name__ == "__main__":
    # 用口语化短问题——和库里的陈述句最不同形态，HyDE 优势最明显
    QS = ["HNSW 是干嘛的？", "RAG 凭啥能减少大模型胡说？", "嵌入向量怎么比相似？"]
    for q in QS:
        i_d, s_d = retrieve_direct(q)
        (i_h, s_h), fake = retrieve_hyde(q)
        print(f"\n❓ {q}")
        print(f"   假设答案: {fake[:48]}…")
        print(f"   直接检索  -> 命中#{i_d} sim={s_d:.3f}  {DOCS[i_d][:24]}…")
        print(f"   HyDE检索 -> 命中#{i_h} sim={s_h:.3f}  {DOCS[i_h][:24]}…")
        tag = "✅ 同命中" if i_d == i_h else "⚡ 命中不同"
        print(f"    {tag}，HyDE 相似度 {'↑' if s_h > s_d else '↓'}{abs(s_h-s_d):.3f}")
    print("\n跑通即达标：3 问都能看到 直接 vs HyDE 的命中与相似度对比。")
    print("注意：HyDE 多数时候拉高相似度/更对题，但假设答案编歪了也会反伤——这就是它的边界。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  qv = embed(question)              # 原问题直接嵌
#   ★2  fake = hyde_answer(question)      # 先编答案
#   ★3  qv = embed(fake)                  # 用编出来的答案嵌入再查
#
# 接真实 Claude：把 generate() 换成 client.messages.create(...) 编假设答案，
# 嵌入换成生产向量库（Pinecone/pgvector）的 embed+query，HyDE 三步逻辑一行不改。

"""
Day 31 练习：Multi-hop RAG（多跳检索）实战——真连本地 Ollama。
单跳 RAG 查一次就答；可「Acme 的 CEO 母校在哪座城市?」一次检索拼不齐答案：
得先查 CEO 是谁 -> 拿人名查母校 -> 拿母校查城市。这就是 multi-hop：
  1) 分解(decompose)：qwen2.5:3b 把复合问拆成 2 个串行子问，子问2带占位符
  2) 迭代检索(iterative)：每跳用 nomic-embed-text 嵌入->余弦取 top-k->qwen 抽该跳答
  3) 回填+合成：上一跳答案填进下一跳子问，末跳后把两跳证据合成最终答
后一跳的输入依赖上一跳的输出——核心就一个 for 循环，逐跳接力。纯标准库 urllib。

⚠️ 需要 Ollama：本机装好并启动，且拉过两个模型。
    ollama serve                  # 默认 http://localhost:11434
    ollama pull nomic-embed-text  # 嵌入（约 274MB）
    ollama pull qwen2.5:3b        # 生成（约 1.9GB）
跑通即达标：  cd ~/projects/daily-learn && uv run day-31/practice.py

练习方式：先把标 ★ 的 3 处自己写一遍，再对照文末参考答案。下面已是完整版，直接跑通。
"""
import json, math, urllib.request

BASE = "http://localhost:11434"
EMB, GEN = "nomic-embed-text", "qwen2.5:3b"

# 文档库：没有哪一段同时写齐「CEO是谁 + 母校城市」，必须跳两次才能拼出答案
DOCS = [
    "Acme 公司的现任 CEO 是林韵，他于 2015 年创立了这家人工智能公司。",
    "林韵本科毕业于复旦大学，而复旦大学坐落在上海市。",
    "Gamma 工作室的代表作是手机游戏《星海》，团队不到二十人。",
    "长江是中国第一长河，最终注入东海。",
    "黄山是著名风景区，位于安徽省。",
]
QUESTION = "Acme 公司 CEO 的母校位于哪座城市?"

def post(path, body):
    req = urllib.request.Request(BASE + path, json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())

def embed(text):  # nomic 要带 task 前缀：文档用 search_document、查询用 search_query
    return post("/api/embeddings", {"model": EMB, "prompt": text})["embedding"]

def gen(prompt):
    return post("/api/generate", {"model": GEN, "prompt": prompt, "stream": False})["response"].strip()

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    return dot / (math.hypot(*a) * math.hypot(*b))                # ★1 余弦=点积/模长积

DOC_VECS = [embed("search_document: " + d) for d in DOCS]        # 库一次性嵌入（真项目预算）

def retrieve(q, k=1):
    qv = embed("search_query: " + q)
    order = sorted(range(len(DOCS)), key=lambda i: cosine(qv, DOC_VECS[i]), reverse=True)
    return [DOCS[i] for i in order[:k]]                           # 取最相似 k 段

# 1) 分解：让模型把复合问拆成 2 个串行子问，子问2用 {0} 占位上一跳答案
SUBQS = ["Acme 公司的 CEO 是谁?", "{0} 的母校（大学）位于哪座城市?"]  # 已拆好；真项目可让模型自动拆

# 2) 迭代检索：逐跳检索+抽答，把上一跳答案回填进下一跳
answers = []
for hop, tmpl in enumerate(SUBQS, 1):
    subq = tmpl.format(*answers)                                # 回填：{0}=上一跳答案
    ctx = retrieve(subq, k=1)                                   # ★2 用子问检索 top-1 片段
    ans = gen(f"只依据资料用最简短词组回答，不要解释。\n资料：{ctx[0]}\n问题：{subq}\n答案：")
    answers.append(ans)
    print(f"Hop{hop} 子问：{subq}\n  命中：{ctx[0]}\n  中间答：{ans}\n")

# 3) 合成：把两跳证据交给模型出最终答
final = gen(f"已知：Acme 的 CEO 是{answers[0]}，{answers[0]}的母校在{answers[1]}。"
            f"请用一句话回答：{QUESTION}")  # ★3 合成
print("最终答：", final)
print("\n直觉：复合问拆子问 -> 每跳 nomic 检索+qwen 抽答 -> 答案回填下一跳 -> 合成。这就是 multi-hop。")

# ============ 参考答案（应先自己写的 3 处）============
#   ★1  return dot / (math.hypot(*a) * math.hypot(*b))
#   ★2  ctx = retrieve(subq, k=1)
#   ★3  final = gen(f"已知：Acme 的 CEO 是{answers[0]}，{answers[0]}的母校在{answers[1]}。请用一句话回答：{QUESTION}")
# 看到 Hop1 抽出「林韵」、Hop2 抽出「上海」、最终答含「上海」，多跳链路就跑通了。

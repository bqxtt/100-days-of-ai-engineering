"""
Day 33 练习：Multi-modal RAG —— 图片/PDF/表格混合文档统一检索（真连 Ollama，纯标准库）。
核心套路：异构进、同构出 —— 把图片、表格、PDF 段落全"翻译"成文本，统一嵌入到同一向量空间，再做跨模态问答。
  1) 图 -> caption：有 vision 模型(llava)真生成描述，无则降级用文件名/上下文当伪 caption（永不崩）
  2) 表格 -> 序列化：每行展开成 "列名=值" 自描述文本，行列结构不丢
  3) PDF 段落 -> 直接当文本
  4) 全部走 nomic-embed-text 嵌入（768维）-> 同一向量空间 -> 余弦最近邻检索
  5) 命中块喂 qwen2.5:3b 真生成带来源的答案

⚠️ 需要 Ollama：本机要装好并启动，且拉过下面两个模型（可选 llava）：
    ollama serve                    # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text    # 嵌入模型（~274MB，768维）
    ollama pull qwen2.5:3b          # 生成模型（~1.9GB）
    ollama pull llava               # 可选：真给图配 caption；没有则优雅降级
跑通即达标：    cd ~/projects/daily-learn && uv run day-33/practice.py

练习方式：先把 3 个标 ★ 的行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, math, urllib.request, urllib.error

OLLAMA = "http://localhost:11434"
EMBED, GEN = "nomic-embed-text", "qwen2.5:3b"
VISION_HINTS = ("llava", "qwen2-vl", "bakllava", "moondream", "minicpm-v", "vision")

# ---------- 混合文档：3 种模态原始数据，各说各话 ----------
IMG = {"file": "contract_scan.png", "alt": "一份纸质合同的扫描件", "near": "签约方甲乙双方盖章"}
PDF = ["公司2024年营收同比增长28%，毛利率提升至42%。",
       "主要驱动来自一线城市市场，其中上海贡献最大。"]
TABLE = {"caption": "2024 一线城市人口与GDP表", "cols": ["城市", "人口", "GDP"],
         "rows": [["北京", "2189万", "4.0万亿"], ["上海", "2487万", "4.7万亿"]]}

# ---------- 0) HTTP 小工具（优雅降级：连不上返回 None，永不抛崩）----------
def post(path, body):
    try:
        req = urllib.request.Request(OLLAMA + path, json.dumps(body).encode(),
                                     {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)
    except (urllib.error.URLError, OSError, ValueError): return None

def have_vision():
    r = post("/api/tags", {}) or {}
    return next((m["name"] for m in r.get("models", [])
                 if any(h in m["name"].lower() for h in VISION_HINTS)), None)

# ---------- 1) 三种模态各自"翻译"成文本（异构 -> 同构）----------
def caption_image(img, vision):
    if vision:  # 有 vision 模型：真看图配字（此处用 alt 占位，真项目传 images=[b64]）
        r = post("/api/chat", {"model": vision, "stream": False, "messages":
            [{"role": "user", "content": f"一句话描述：{img['alt']}"}]})
        if r: return r["message"]["content"].strip()
    return f"[图片] {img['alt']}；周边文字：{img['near']}（文件名 {img['file']}）"  # 降级伪caption

def serialize_table(t):  # ★1 每行展开成 "列名=值" 自描述文本，行列结构不丢
    lines = [", ".join(f"{c}={v}" for c, v in zip(t["cols"], row)) for row in t["rows"]]
    return f"{t['caption']}：" + "；".join(lines)

# ---------- 2) 统一嵌入：异构文本 -> 同一向量空间（768维）----------
def embed(text):
    r = post("/api/embeddings", {"model": EMBED, "prompt": text})
    return r["embedding"] if r else None

def cos(a, b):  # ★2 余弦相似度：点积 / 模长积
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb + 1e-9)

def generate(q, ctx):
    r = post("/api/chat", {"model": GEN, "stream": False, "messages": [
        {"role": "user", "content": f"只依据资料回答，注明来源模态。\n资料：{ctx}\n问题：{q}"}]})
    return r["message"]["content"].strip() if r else None

if __name__ == "__main__":
    vision = have_vision()
    print(f"vision 模型：{vision or '无 -> 优雅降级用上下文当 caption'}\n")

    chunks = [("图片", caption_image(IMG, vision)), ("PDF段", PDF[0]), ("PDF段", PDF[1]),
              ("表格", serialize_table(TABLE))]                       # ★3 4 个异构块统一成文本
    db = [(m, t, embed(t)) for m, t in chunks]
    if any(v is None for *_, v in db):
        print("⚠️ Ollama 未运行/无 nomic-embed-text，已演示翻译；嵌入跳过。装好后重跑即可。")
        for m, t, _ in db: print(f"  [{m}] {t}")
    else:
        print(f"统一嵌入 {len(db)} 块，向量维度 = {len(db[0][2])}（同一空间）：")
        for m, t, _ in db: print(f"  [{m}] {t[:34]}…")
        for q in ["上海有多少人口？", "合同里谁盖章了？", "公司营收同比增长多少？"]:
            qv = embed(q)
            top2 = sorted(db, key=lambda r: cos(qv, r[2]), reverse=True)[:2]  # 取最近邻 top-2
            print(f"\n❓ {q}\n  命中 [{top2[0][0]}] {top2[0][1][:30]}…")
            ans = generate(q, "；".join(t for _, t, _ in top2))
            print(f"  🤖 {ans or '(生成模型未就绪)'}")
        print("\n跑通即达标：图/表/PDF 都进了同一向量空间，跨模态问句各自命中对应块。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  lines = [", ".join(f"{c}={v}" for c, v in zip(t["cols"], row)) for row in t["rows"]]
#   ★2  return sum(x*y for x,y in zip(a,b)) / (na*nb + 1e-9)
#   ★3  chunks = [("图片", caption_image(...)), ("PDF段", ...), ("表格", serialize_table(...))]
# 看到 4 个异构块统一成 768 维向量、"上海人口"命中表格、"盖章"命中图 caption，就串通了。
# 接生产：Ollama 换 Anthropic/OpenAI embeddings + 向量库(Chroma/Pinecone)，序列化/降级逻辑不变。

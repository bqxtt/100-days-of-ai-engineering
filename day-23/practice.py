"""
Day 23 练习：纯 Python 手写三种文本分块器，并用真实 embedding 验证相邻 chunk 相似度。
不需要 numpy、不需要 LangChain，三种 chunker 共约 40 行——RAG 的"切菜刀"今天自己造一把：
  - 固定大小（fixed）：按字符数硬切，最简单、最暴力
  - 重叠固定（overlap）：固定切 + 相邻 chunk 留 overlap 接缝，少切断句子
  - 递归（recursive）：按"段落→句号→逗号→字符"优先级切，尽量沿自然边界

核心一句话：分块=把长文切成"够小能进上下文、够大保完整语义"的片段，是 RAG 召回质量的天花板。

⚠️ 需要 Ollama：本机要装好并启动 ollama，且拉过 nomic-embed-text（向量验证用）。
    brew install ollama          # macOS（已装可跳过）
    ollama serve                 # 启动服务（默认 http://localhost:11434）
    ollama pull nomic-embed-text # 拉嵌入模型（约 274MB）
跑通即达标：    cd ~/projects/daily-learn && uv run day-23/practice.py
（没装 ollama 也能跑：三种分块器照常打印对比，只有最后一段相似度验证会跳过）

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑通。
"""
import json, math, urllib.request, urllib.error

OLLAMA = "http://localhost:11434/api/embeddings"
EMBED  = "nomic-embed-text"

# 一段长文：3 个主题段落（猫/咖啡/RAG），故意写满分隔符方便观察"边界"
TEXT = (
    "猫是独立的小动物，喜欢睡觉和晒太阳。它们一天能睡十六小时，醒着时大多在梳理毛发。"
    "猫不像狗那样依赖主人，但也会用蹭腿表达亲近。\n\n"
    "咖啡因是一种兴奋剂，能暂时驱散困意。早晨一杯咖啡让人清醒，但下午喝太多会影响睡眠。"
    "不同烘焙度的豆子风味差别很大，浅烘酸、深烘苦。\n\n"
    "RAG 即检索增强生成，先把文档切成小块存进向量库，提问时检索相关块再交给模型作答。"
    "分块策略直接决定召回质量，块太大塞不进上下文，块太小又丢失语义。"
)

# ---------- 1) 固定大小：按字符数硬切。最简单，但常把句子拦腰斩断 ----------
def chunk_fixed(text, size):
    return [text[i:i + size] for i in range(0, len(text), size)]   # ★1 每隔 size 切一刀

# ---------- 2) 重叠固定：固定切 + 相邻 chunk 重叠 overlap 个字，给跨界句子留接缝 ----------
def chunk_overlap(text, size, overlap):
    step = size - overlap                              # 步长 = 窗口 - 重叠，越小重叠越多
    return [text[i:i + size] for i in range(0, len(text), step)]   # ★2 滑窗带回退

# ---------- 3) 递归：依次试"段落→句号→逗号→字符"，沿最大自然边界切，超长才降级 ----------
SEPARATORS = ["\n\n", "。", "，", ""]   # 优先级从粗到细
def chunk_recursive(text, size, seps=SEPARATORS):
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    sep = seps[0]
    if sep == "":
        parts = list(text)
    elif sep == "\n\n":
        parts = [p for p in text.split(sep) if p]       # 段落分隔符不回贴
    else:
        parts = [p + sep for p in text.split(sep) if p] # 标点回贴，保留句意
    chunks, cur = [], ""
    for p in parts:
        if len(cur) + len(p) <= size:
            cur += p
        else:
            if cur: chunks.append(cur.strip())
            if len(p) > size:                          # 这一片还超长 -> 用更细的分隔符递归切
                chunks += chunk_recursive(p, size, seps[1:])   # ★3 换更细分隔符再切
                cur = ""
            else:
                cur = p
    if cur.strip(): chunks.append(cur.strip())
    return chunks

# ---------- 真嵌入：nomic-embed-text 把文本变成向量，算相邻 chunk 余弦相似度 ----------
def embed(text):
    body = json.dumps({"model": EMBED, "prompt": text}).encode()
    req = urllib.request.Request(OLLAMA, body, {"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())["embedding"]

def cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)); nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb)

def show(name, chunks):
    print(f"\n=== {name}：{len(chunks)} 块 ===")
    for i, c in enumerate(chunks):
        print(f"  [{i}] ({len(c):2d}字) {c.replace(chr(10),'⏎')}")

if __name__ == "__main__":
    SIZE = 50
    show(f"固定大小 size={SIZE}", chunk_fixed(TEXT, SIZE))
    show(f"重叠固定 size={SIZE} overlap=10", chunk_overlap(TEXT, SIZE, 10))
    rec = chunk_recursive(TEXT, SIZE)
    show(f"递归分块 size={SIZE}", rec)

    print("\n— 观察：固定大小常把句子斩断；重叠给接缝；递归沿句号/段落更整齐 —")

    try:
        print("\n=== 真嵌入：递归块相邻相似度（越低=主题切得越干净）===")
        vs = [embed(c) for c in rec]
        for i in range(len(vs) - 1):
            print(f"  块{i}↔块{i+1} 余弦={cos(vs[i], vs[i+1]):.3f}")
        print("跑通即达标：3 种分块都打印了，且相邻相似度算出来了（跨主题处明显更低）。")
    except (urllib.error.URLError, TimeoutError):
        print("⚠ 连不上 Ollama，跳过向量验证（三种分块器已演示完毕，达标）。")

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  return [text[i:i + size] for i in range(0, len(text), size)]
#   ★2  return [text[i:i + size] for i in range(0, len(text), step)]   # step=size-overlap
#   ★3  chunks += chunk_recursive(p, size, seps[1:])
# 看到固定块斩句、递归块沿句号/段落对齐、且跨主题处相邻相似度更低，就成功了。

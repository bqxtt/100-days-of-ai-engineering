"""
Day 24 练习：结构化文档分块（Markdown 标题层级 + 表格转文本 + 图片用 caption），
真嵌入入库 + 相似度检索。纯 Python 标准库，无需 numpy、无需付费 key。

为什么不无脑按长度切：Markdown 的结构本身就是语义——# 标题 = 块边界，
表格是二维数据要序列化成带表头的文本，图片不可嵌入只能存 caption。每块带元数据。

⚠️ 需要 Ollama：本机装好并启动 ollama，且拉过两个模型：
    ollama serve                 # 默认 http://localhost:11434
    ollama pull nomic-embed-text # 嵌入模型（约 274MB）
    ollama pull qwen2.5:3b       # 生成模型（约 1.9GB）
跑通即达标：cd /Users/zqr/projects/daily-learn && uv run day-24/practice.py

练习方式：先把标 ★ 的几行自己写一遍，再对照文末「参考答案」。下面已是完整可跑版。
"""
import json, math, re, urllib.request

OLLAMA = "http://localhost:11434"
EMBED, GEN = "nomic-embed-text", "qwen2.5:3b"

# 一份"真实"文档：有标题层级、一张表格、一张图。后端文档常长这样。
DOC = """\
# 销售周报

## macOS 安装
先装好 ollama，再拉 nomic-embed-text。命令行一行搞定。

## 区域销量
| 城市 | 销量 | 同比 |
| 上海 | 88 | +12% |
| 北京 | 64 | -3% |
| 深圳 | 71 | +20% |

![各区域月度趋势折线图](trend.png)
"""

# ---------- 1) 按 Markdown 标题层级 + 表格 + 图片 分块，每块带元数据 ----------
def chunk_markdown(md, source="report.md"):
    chunks, path, buf = [], [], []   # path=当前标题路径栈，buf=正文缓冲
    def flush(kind="text"):
        text = "\n".join(buf).strip()
        if text:
            chunks.append({"type": kind, "heading": " > ".join(path), "source": source, "text": text})
        buf.clear()
    for line in md.splitlines():
        if line.startswith("#"):                              # 标题=天然块边界
            flush()
            level = len(line) - len(line.lstrip("#"))         # # 数=层级
            path[level-1:] = [line.lstrip("# ").strip()]      # 截断到该层并替换
        elif line.startswith("|"):                            # 表格行：行展开成带列名的句子
            buf.append(line)
        elif line.startswith("!["):                           # 图片：不可嵌入，存 caption
            flush()
            cap = re.search(r"\[(.*?)\]", line).group(1)      # ★1 取 [...] 里的 caption 文字
            chunks.append({"type": "image", "heading": " > ".join(path), "source": source, "text": cap})
        else:
            buf.append(line)
    flush()
    return [serialize_table(c) for c in chunks]

def serialize_table(c):
    rows = [r for r in c["text"].splitlines() if r.startswith("|")]
    if len(rows) < 2: return c
    cells = lambda r: [x.strip() for x in r.strip("|").split("|")]
    head = cells(rows[0])
    sentences = ["，".join(f"{h}={v}" for h, v in zip(head, cells(r))) for r in rows[1:]]
    c.update(type="table", text=" 表头(" + "/".join(head) + ")：" + "；".join(sentences))  # 列名+值
    return c

# ---------- 2) 真嵌入 + 余弦相似度检索 ----------
def embed(text):
    body = json.dumps({"model": EMBED, "prompt": text}).encode()
    r = urllib.request.urlopen(OLLAMA + "/api/embeddings", body, timeout=60)
    return json.load(r)["embedding"]

def cosine(a, b):
    dot = sum(x*y for x, y in zip(a, b))
    return dot / (math.hypot(*a) * math.hypot(*b))            # ★2 余弦=点积/模长积

def gen(prompt):
    body = json.dumps({"model": GEN, "prompt": prompt, "stream": False}).encode()
    r = urllib.request.urlopen(OLLAMA + "/api/generate", body, timeout=120)
    return json.load(r)["response"].strip()

print(f"嵌入={EMBED}  生成={GEN}\n")
chunks = chunk_markdown(DOC)
for c in chunks:
    c["vec"] = embed(c["heading"] + " " + c["text"])          # 标题路径拼正文一起嵌入
    print(f"[{c['type']:5}] {c['heading']:<14} {c['text'][:36]}")

q = "上海销量是多少"
qv = embed(q)
top = max(chunks, key=lambda c: cosine(qv, c["vec"]))         # ★3 取相似度最高的块
print(f"\n问：{q}\n命中块（{top['type']} @ {top['heading']}）：{top['text'][:60]}")
print("\n答：", gen(f"只看资料回答。资料：{top['text']}\n问题：{q}"))

# ============ 参考答案（被你应当先自己写的 3 行）============
#   ★1  cap = re.search(r"\[(.*?)\]", line).group(1)
#   ★2  return dot / (math.hypot(*a) * math.hypot(*b))
#   ★3  top = max(chunks, key=lambda c: cosine(qv, c["vec"]))
# 命中"区域销量"那张表、答出 88，就说明结构化分块+检索全通了。
# 连接拒绝=没开 ollama：先 `ollama serve` 并 pull nomic-embed-text / qwen2.5:3b。

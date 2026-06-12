"""
Day 41 实践：手写 LLM 的三种记忆（Memory）系统，全程真连本机 Ollama。
  短期记忆 = 对话历史窗口（最近几轮消息）         —— 后端类比：进程内缓存（命中即用，满了就挤）
  长期记忆 = 向量库存事实（nomic 嵌入 + 余弦检索） —— 后端类比：数据库（存得久、按相关性查）
  摘要记忆 = 超窗口时让模型 summarize 旧消息       —— 后端类比：日志归档（冷数据压成摘要，省空间）
本练习演示两件事：
  1) 对话越聊越长 -> 超过窗口阈值时，自动让 qwen2.5:3b 把旧消息压成一句摘要；
  2) 在长期向量库里存几条"事实"，新问题来时用 nomic 嵌入 + numpy 余弦把相关旧事实召回，喂回模型。

纯标准库 urllib + numpy，真调 Ollama，无 mock、无付费 key。

⚠️ 需要 Ollama：本机装好并启动，且拉过两个模型（一个生成、一个嵌入）。
    brew install ollama                  # macOS（已装可跳过）
    ollama serve                         # 启动服务（默认 http://localhost:11434）
    ollama pull qwen2.5:3b               # 生成模型（约 1.9GB）
    ollama pull nomic-embed-text         # 嵌入模型（约 274MB，输出 768 维）
跑通即达标：    cd ~/projects/daily-learn && uv run day-41/practice.py

练习方式：先把标 ★ 的 5 行自己写一遍，再对照文末「参考答案」。下面已是完整版，直接跑。
"""
import json, urllib.request
import numpy as np

OLLAMA = "http://localhost:11434"
GEN_MODEL   = "qwen2.5:3b"          # 对话 + 摘要
EMBED_MODEL = "nomic-embed-text"    # 长期记忆事实嵌入，768 维

# ---------- 0) Ollama 客户端：chat 生成 + embeddings 嵌入（真调，stdlib urllib） ----------
def chat(messages):  # 默认 /api/chat，给一串消息拿一句回复
    body = json.dumps({"model": GEN_MODEL, "stream": False, "messages": messages}).encode()
    r = urllib.request.urlopen(OLLAMA + "/api/chat", body, timeout=120)
    return json.load(r)["message"]["content"].strip()

def embed(t):        # 一句话 -> 768 维向量（长期记忆的"主键"）
    body = json.dumps({"model": EMBED_MODEL, "prompt": t}).encode()
    return json.load(urllib.request.urlopen(OLLAMA + "/api/embeddings", body, timeout=60))["embedding"]

def cos(a, b):       # numpy 余弦相似度
    a, b = np.asarray(a), np.asarray(b)
    return float(a @ b / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))

# ---------- 1) 短期记忆：对话历史窗口。满了就触发摘要，把旧消息压成一行（摘要记忆） ----------
class Memory:
    def __init__(self, window=6):
        self.window = window       # 短期窗口：最多保留几条 user/ai 消息（缓存容量）
        self.short = []            # 短期 = 最近对话（缓存）
        self.summary = ""          # 摘要 = 旧消息压成的归档（日志归档）
        self.long = []             # 长期 = [(事实文本, 向量)] 列表（数据库）

    def add(self, role, text):
        self.short.append({"role": role, "content": text})
        if len(self.short) > self.window:               # 超窗口 -> 归档旧消息
            self._summarize()

    def _summarize(self):
        old = self.short[:-self.window]                 # 要被挤出窗口的旧消息
        self.short = self.short[-self.window:]           # ★1 只保留窗口内最近 window 条
        prior = f"已有摘要：{self.summary}\n" if self.summary else ""
        log = "\n".join(f"{m['role']}: {m['content']}" for m in old)
        s = chat([{"role": "user", "content":
                   f"{prior}把下面对话压成一句中文摘要，保留关键事实：\n{log}"}])
        self.summary = s                                # 旧对话 -> 一句摘要，省窗口

    def remember(self, fact):                           # 写入长期记忆（存数据库）
        self.long.append((fact, embed(fact)))           # ★2 事实 + 其嵌入向量一起存

    def recall(self, query, k=2):                       # 按相关性召回长期事实（查数据库）
        qv = embed(query)
        ranked = sorted(self.long, key=lambda f: cos(qv, f[1]), reverse=True)  # ★3 余弦排序
        return [f[0] for f in ranked[:k]]

    def context(self, query):                           # 拼给模型的上下文：摘要+召回事实+短期窗口
        facts = self.recall(query)
        sys = "你是助手。" + (f"【对话摘要】{self.summary} " if self.summary else "")
        sys += "【相关旧事实】" + "；".join(facts) if facts else ""
        return [{"role": "system", "content": sys}] + self.short  # ★4 system 装摘要+事实，再接窗口

# ---------- 2) 主流程：模拟一段会变长的对话，演示摘要触发 + 长期检索召回 ----------
def turn(mem, user_msg):
    mem.add("user", user_msg)
    reply = chat(mem.context(user_msg))                 # ★5 用拼好的上下文真调模型
    mem.add("assistant", reply)
    return reply

if __name__ == "__main__":
    print("⏳ 连接 Ollama，预存长期事实 ...")
    m = Memory(window=4)
    for fact in ["用户叫张三，是后端工程师。", "用户最爱的数据库是 PostgreSQL。",
                 "用户在做一个 RAG 项目。", "用户不喜欢 MongoDB。"]:
        m.remember(fact)                                # 长期库：4 条事实入向量库
    print(f"✅ 长期记忆就绪：{len(m.long)} 条事实，向量 {len(m.long[0][1])} 维\n")

    for q in ["你好，今天聊点数据库", "讲讲索引怎么选", "再说说分库分表", "性能调优有啥经验",
              "对了，你还记得我最爱哪个数据库吗？"]:
        print(f"❓ {q}")
        print(f"🤖 {turn(m, q)}\n")

    print(f"📦 短期窗口现存 {len(m.short)} 条 | 摘要: {m.summary[:40]}...")
    print("跑通即达标：对话变长触发了摘要，最后一问从长期库召回 PostgreSQL 答对。")

# ============ 参考答案（应先自己写的 5 行）============
#   ★1  self.short = self.short[-self.window:]
#   ★2  self.long.append((fact, embed(fact)))
#   ★3  ranked = sorted(self.long, key=lambda f: cos(qv, f[1]), reverse=True)
#   ★4  return [{"role": "system", "content": sys}] + self.short
#   ★5  reply = chat(mem.context(user_msg))
#
# 接生产：短期换 Redis 会话、长期换 Chroma/pgvector、摘要换 LangChain ConversationSummaryMemory，
# 三层各司其职——这就是 MemGPT(arXiv:2310.08560) 把记忆当"操作系统分页"管理的雏形。

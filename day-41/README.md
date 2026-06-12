# Day 41 — 🧠 Memory 系统设计：短期记忆、长期记忆、摘要记忆

> **阶段**：Phase 4 · AI Agent（Day 41）
> **主题**：给 Agent 一套记忆系统——短期记忆（short-term）、长期记忆（long-term）、摘要记忆（summary）
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：模型本身是无状态（stateless）的，每次请求只看见你塞进 prompt 的东西。"记忆"不是模型自带的，是你在外面搭的一套三层存储——和你后端做的**缓存 + 数据库 + 日志归档**一模一样：最近对话进缓存（短期），关键事实进库按需检索（长期），旧消息装不下就压成摘要归档（summary）。

---

## 📖 学习内容（约 25 分钟）

### 0. 为什么要记忆：上下文窗口（context window）是有限的
LLM 一次只能看进固定长度的 token。对话越聊越长，迟早撑爆窗口。记忆系统就是在窗口外面建三层存储，按需把"该看的"塞回 prompt。后端类比：内存放不下全部数据，你才分了**缓存/数据库/归档**三级——LLM 记忆就是这套分级存储（tiered storage）搬到对话上。

| 记忆类型 | 中文 | 存什么 | 后端类比 | 失效方式 |
|---|---|---|---|---|
| Short-term | 短期记忆 | 最近 N 轮对话 | 进程内缓存（cache） | 超窗口被挤出 |
| Long-term | 长期记忆 | 关键事实向量 | 数据库（DB / vector store） | 不删，按相关性查 |
| Summary | 摘要记忆 | 旧对话压缩成一句 | 日志归档（log archive） | 冷数据压成摘要 |

### 1. 短期记忆 = 对话历史窗口（缓存）
保留最近几条 user/assistant 消息，原样接进 prompt。命中快、最新，但**容量固定**——满了就得淘汰旧的，就像 LRU 缓存挤出最早条目。Day41 里就是一个 `window=4` 的 list。

### 2. 长期记忆 = 向量库存事实（数据库）
把"用户最爱 PostgreSQL"这类事实用 **nomic-embed-text** 嵌成 768 维向量存起来。新问题来时嵌成向量，用 **numpy 余弦相似度（cosine）** 检索召回（recall）最相关的几条塞回 prompt。容量近乎无限，按相关性查——就是给对话装了个 `SELECT ... ORDER BY similarity`。

### 3. 摘要记忆 = 超窗口让模型 summarize 旧消息（日志归档）
窗口装不下时，把要挤出的旧消息交给模型压成一句摘要，累加到 summary 里。冷数据不丢、只压缩，省 token 又保关键事实——和你把旧日志 gzip 归档一个道理。MemGPT 更进一步：把记忆当**操作系统分页**调度，主动在窗口内外搬运。

### 4. 三层协同：拼上下文（context assembly）
回答时 `system = 摘要 + 召回事实`，再接短期窗口。三层各司其职：摘要给背景、长期给事实、短期给最新——LangChain 的 `Memory` 抽象就是这套，你今天手写一遍。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **LangChain — Memory 概念**（三种 memory 的工业抽象，对照你手写版）— https://python.langchain.com/docs/concepts/memory/
2. **MemGPT 论文**（把记忆当 OS 分页管理，长期/短期分层调度）— https://arxiv.org/abs/2310.08560
3. **nomic-embed-text 模型卡**（今天长期记忆用的 768 维嵌入）— https://ollama.com/library/nomic-embed-text
4. **Ollama API**（本机 chat + embeddings 两个接口）— https://github.com/ollama/ollama/blob/main/docs/api.md

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**stdlib urllib + numpy + 真连 Ollama**：手写一个 `Memory` 类，三层全有。补 5 个 `★` 行再对答案。演示对话变长触发摘要、长期向量库召回旧事实。

```bash
# 前置：起服务，拉生成 + 嵌入两个模型
ollama serve                         # 默认 http://localhost:11434
ollama pull qwen2.5:3b               # 生成（约 1.9GB）
ollama pull nomic-embed-text         # 嵌入（约 274MB，768 维）
uv run day-41/practice.py
```
预期：5 轮对话越聊越长，超 `window=4` 触发摘要；最后一问"我最爱哪个数据库"从长期库召回 **PostgreSQL** 答对——即达标。

### 🎨 可视化（先玩再读理论更直观）
双击 `visualize.html`（纯 canvas、深色 #0e1117、零依赖）。逐轮加消息看短期窗口被挤、旧消息压成摘要、新问题从长期库按余弦召回——三层记忆怎么搬数据一目了然。

---

## 🤔 思考题（边做边想）

1. 短期窗口设大点不就行了，何必要长期 + 摘要？窗口、token 成本、延迟之间怎么权衡？
2. 摘要记忆会丢信息，长期库不会但要嵌入+检索开销。一条"用户最爱 PostgreSQL"该进哪层？凭什么决定？
3. 长期库越来越大，检索会变慢、可能召回过期事实。该怎么做淘汰/更新？（接 MemGPT 分页思路，也为后续多 Agent 协作埋伏笔）

> 答案记到 `notes.md`。明天 Day 42 继续 Phase 4 Agent——记忆会成为 Agent 自主决策的状态来源。

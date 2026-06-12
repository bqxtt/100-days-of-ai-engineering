# Day 35 — 🏗️ 实践日：构建可用的个人知识库问答系统

> **阶段**：Phase 3 · RAG 系统设计与实现（收官实践日 · Day21-34 总整合）
> **主题**：把整条 RAG 链路拼成一个真跑通的 mini 知识库问答（加载→分块→嵌入→混合检索→rerank→带引用生成）
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：前 14 天你拆开看了 RAG 的每个零件，今天把它们焊成一台机器。一个能用的知识库问答系统，本质就是一条 7 段流水线（pipeline）：**文档 → chunk → embed → 向量库 → hybrid retrieve → rerank → generate（带 citation）**。每一段都是你前面学过的，今天只做一件事——按顺序串起来，让它端到端跑通。

---

## 📖 学习内容（约 25 分钟）

### 0. Phase 3 脉络回顾：14 天，一条流水线
今天不引入新概念，而是把 Day21-34 的零件归位。看清这条主线你就懂了整个 RAG：

| 知识点 | 在系统里的角色 | 一句话 |
|---|---|---|
| Day21 Embedding | 把文本编译成 768 维向量 | 语义 = 坐标 |
| Day22 向量库（Vector DB） | 存向量、按余弦 ANN 召回 | 召回层 |
| Day23/24 分块（Chunking） | 长文切小块再嵌入 | 重叠保边界 |
| Day25 检索（Retrieval） | 向量 + 关键词混合（Hybrid） | 语义补术语 |
| Day26 Rerank | Cross-Encoder 精排 Top-K | 召回换精度 |
| Day27/28 Pipeline | 加载→分块→入库→查→答 | 把上面串起来 |
| Day29-31 高级 RAG | Query 改写/HyDE/Multi-hop | 提升召回质量 |
| Day32 评估 | Faithfulness/Relevancy/RAGAS | 有据可查 |
| Day33 多模态 | PDF/表格/图混合 | 扩展文档类型 |
| Day34 生产化 | 缓存/增量/监控 | 跑得住 |

今天的产物：**拼完整知识库问答（KB Q&A）**，把上面竖排的零件横向焊成一条流水线。

### 1. 系统骨架：7 段流水线
```
本地文档 ──chunk──▶ 小块 ──embed(nomic)──▶ 向量库
                                              │
问题 query ──embed──▶ ┌─ 向量检索(cos) ─┐    │ 混合召回 Top-5
                      └─ 关键词(BM25)  ─┘────▶ rerank(qwen) Top-3 ──▶ 生成带[引用]
```
后端类比：和你写的任何"入库 + 查询"服务一模一样——离线建索引（嵌入入库），在线查（嵌 query → 召回 → 精排 → 渲染）。RAG 只是把 `ORDER BY` 换成了余弦相似度。

### 2. 召回 ≠ 精排：为什么要两段
**混合检索（Hybrid Search）**先用语义 + 关键词宽召回 Top-5：向量擅长"如何提速≈优化延迟"这类近义，关键词补"RAG、HNSW"这类术语缩写。但召回追的是"别漏"，难免有噪声。**Rerank** 再用更重的模型把 query 与每个候选一起打分，精排出 Top-3——这就是"先广撒网、再精挑"，召回换速度、精排换精度。

### 3. 带引用生成：把幻觉摁住
生成 prompt 里给每段资料编号 `[1][2]`，要求"只依据资料、句末标引用、没有就说不知道"。这一步把 Day32 的 **忠实度（faithfulness）** 落地——答案可追溯到来源，干扰块（天气）即使混进库也不该被选中。这是知识库问答从"能跑"到"可信"的分水岭。

### 4. 嵌入缓存：生产化第一招
同一句话嵌两次是浪费。给 `embed()` 加一层内存缓存（Day34），重复内容直接命中。真项目里换成 Redis / 持久化向量库，增量更新只嵌新文档——这就是把 demo 变成"跑得住"的第一步。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Ollama 官方文档**（本机跑嵌入+生成两个模型的基础）— https://github.com/ollama/ollama/blob/main/docs/api.md
2. **nomic-embed-text 模型卡**（今天的 768 维嵌入模型）— https://ollama.com/library/nomic-embed-text
3. **Pinecone — RAG 全景指南**（把今天的 7 段流水线讲透）— https://www.pinecone.io/learn/retrieval-augmented-generation/
4. **LlamaIndex — 从零搭 RAG**（生产级实现，对照看你 demo 缺什么）— https://docs.llamaindex.ai/en/stable/understanding/rag/
5. **RAGAS 评估框架**（Day32 评估的落地）— https://docs.ragas.io/

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：一个完整 CLI 知识库问答——7 篇文档分块、nomic 嵌入入库、混合检索、qwen2.5:3b rerank、带引用回答。先补 5 个 `★` 行，再对照文末答案。HTTP 只用 `urllib`，相似度只用 `math`，无需装包。

```bash
# 前置：起 Ollama 服务，拉嵌入模型 + 生成模型
ollama serve                         # 默认 http://localhost:11434
ollama pull nomic-embed-text         # 嵌入 274MB，输出 768 维
ollama pull qwen2.5:3b               # 生成 1.9GB
# 直接跑（仅 stdlib）：
uv run day-35/practice.py
```
预期：7 篇文档 → 13 个块、每块 768 维；3 问都据库作答且带 `[来源]` 引用；天气干扰块**不被选中**——即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击打开 `visualize.html`（纯浏览器、零依赖、深色）。把端到端 RAG 系统流程做成可点的流水线：选一个问题，逐段亮起 chunk→embed→向量库→混合检索→rerank→生成，命中片段高亮、干扰块被剔除，亲眼看一条 query 怎么走完 7 段拿到带引用的答案。

---

## 🤔 思考题（边做边想）

1. 召回 Top-5 再 rerank Top-3，为什么不直接召回 Top-3？多召回再精排换来了什么、代价是什么？
2. 给生成 prompt 加"没有就说不知道"，对忠实度（faithfulness）有什么影响？天气干扰块如果被选中，引用机制能补救吗？
3. 现在文档写死在代码里、向量库在内存。要变成"跑得住"的生产系统，缓存/增量更新/向量库该怎么换？（接 Day34，也为 Phase 4 Agent 埋伏笔）

> 把答案记在 `notes.md`，并写下 Phase 3 复盘。明天起 Day 36 进入 Phase 4 · AI Agent——RAG 会成为 Agent 的一个工具。

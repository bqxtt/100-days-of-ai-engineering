# Day 26 — Reranking：Cross-Encoder、Cohere Rerank

> **阶段**：Phase 3 · RAG 系统设计与实现
> **主题**：两阶段检索（two-stage retrieval）——先用向量召回 top-N，再用 reranker 精排 top-K
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：向量召回快但"看不准"，它判断相似度时 query 和 doc 从没"见过面"——各自独立算出向量再比距离。**重排（rerank）** 就是把 query 和每个候选**拼一起喂给一个模型**，让它逐对打分。后端类比：召回=数据库 `WHERE` 粗筛出 100 条（快、宽进），rerank=对这 100 条跑一遍"精确相关性评估"排出前 5（准、严出）。今天用 nomic-embed-text 召回、qwen2.5:3b 当 LLM-reranker 精排，亲眼看重排把对的文档从第 6 名提到第 1 名。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器，零依赖，深色）。它把两阶段检索画在一屏：左边是**召回**给出的 top-N 顺序（按向量相似度），右边是 **rerank 后**的新顺序。点「重排」看一根根连线把候选重新排队——你能直观看到"召回第 4、第 6 的好文档被提到最前，注水文档沉底"。先玩后读。

---

## 📖 学习内容（约 30 分钟）

### 1. Bi-Encoder vs Cross-Encoder：差在"见没见过面"

| | Bi-Encoder（双塔） | Cross-Encoder（交叉编码） |
|---|---|---|
| 结构 | query、doc **各自**过模型 → 两个向量 → 算余弦 | query+doc **拼成一句**过模型 → 直接出 1 个相关分 |
| query 与 doc | 编码时**互不可见** | 编码时**逐 token 交叉注意**，互相可见 |
| 速度 | 极快：doc 向量可**离线预算好**，查询只算 query | 慢：每个 (query,doc) 对都要现算一次 |
| 准度 | 一般（粗筛够用） | 高（精排专用） |
| 适合 | **召回**百万级文档 | **重排**几十个候选 |

一句话：bi-encoder 是 nomic/bge 这类 **embedding 模型**，doc 向量提前算好存进向量库，召回只算 query 再比距离——所以能秒查百万条。cross-encoder（cross-encoder）牺牲速度换准度，query 和 doc 拼在一起算，能捕捉"否定、限定、谁修饰谁"这类双塔丢失的细节。

### 2. 为什么召回后还要 rerank

向量召回为了快，把每个 doc 压成一个固定向量——**信息有损**。它常把"字面像但答非所问"的文档排前面。两阶段就是分工：

```
百万 doc ──向量召回(top-N=20)──> 20 候选 ──reranker 精排(top-K=5)──> 喂给 LLM
         bi-encoder：宽进、快、有损          cross-encoder：严出、慢、准
```

- **召回（recall）求全**：宁可多召（top-N 大），别漏掉正确答案；漏了 rerank 也救不回来。
- **重排（rerank）求准**：在小候选集里精挑，把正确答案顶到 top-K。top-K 决定塞进上下文的量，省 token 又减幻觉。
- 成本只翻一点点：cross-encoder 只跑 20 次，不是百万次。**用 1% 的算力买大半准度**。

### 3. 三种 reranker：托管 API / 开源模型 / LLM-as-reranker

1. **Cohere Rerank（cohere）**：一行 API 给 query+docs 直接回 relevance score，最省事，按量付费。
2. **bge-reranker（bge-reranker）**：BAAI 开源 cross-encoder，可本地部署、免费、中文强，`v2-m3` 多语言。
3. **LLM-as-reranker**：直接让一个生成模型对每个候选打"相关分"。今天用 qwen2.5:3b 走这条——无需额外依赖，理解了原理换 cohere/bge 只是换打分函数。

### 4. 两阶段检索：在 RAG 流水线里的位置

```
query → [召回 nomic-embed-text top-N] → [rerank top-K] → 拼上下文 → [LLM 生成 qwen2.5:3b] → 答
        Day22-25 干的事                    今天插这一层      Day23           Day20 学过
```

rerank 是**插在召回和生成之间的一层**，召回侧/生成侧都不用改。这就是好架构：**新增一层就提升质量，旧逻辑不动**。生产里 cohere/bge 的 cross-encoder 比小 LLM 又快又准，原理完全一样。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Cohere Rerank 概览（托管 reranker，最省事）** — https://docs.cohere.com/docs/rerank-overview — query+docs→relevance score 的 API、top_n 与计费模型，呼应模块 3。
2. **bge-reranker-v2-m3（开源 cross-encoder，可本地跑）** — https://huggingface.co/BAAI/bge-reranker-v2-m3 — 多语言中文强，配套 https://github.com/FlagOpen/FlagEmbedding 有 reranker 用法。
3. **Sentence-Transformers · Retrieve & Re-Rank（bi vs cross 范例）** — https://www.sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html — 两阶段检索官方教程；cross-encoder 用法 https://www.sbert.net/docs/cross_encoder/usage/usage.html

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**真连本地 Ollama**：先用 nomic-embed-text 向量召回 top-N，再用 qwen2.5:3b 当 LLM-reranker 逐个打相关分重排，对比 rerank 前后顺序。补齐多个 `★`，再对照文末答案。

```bash
# 先备好 Ollama（已装可跳过）：
ollama serve                    # 启动服务（默认 http://localhost:11434）
ollama pull nomic-embed-text    # 召回用的嵌入模型（约 274MB）
ollama pull qwen2.5:3b          # 当 reranker 打分的生成模型（约 1.9GB）
# 真跑：
uv run day-26/practice.py
```

预期：一个"字面像但答非所问"的注水文档被向量召回排进前列，rerank 后正确文档顶到第 1 名、注水文档沉底。看到前后顺序对比表即达标。

### 🎨 可视化

`visualize.html` 把"召回顺序→重排顺序"画成深色连线动画，先玩它最直观。

---

## 🤔 思考题（边做边想）

1. 召回 top-N 设太小（如 5）会怎样？为什么"漏召回了，rerank 也救不回来"？这和分库分表先粗筛的权衡像不像？
2. cross-encoder 准但慢——为什么不直接用它跑全量百万文档，省掉召回？算笔账。
3. LLM-as-reranker 用生成模型打分，cohere/bge 用专用 cross-encoder——同样是"query+doc 拼一起出 1 个分"，差别在哪？哪个更适合生产？
4. rerank 把候选裁到 top-K=5，对喂给 LLM 的 token、成本、幻觉各有什么好处？

> 把答案记进 `notes.md`。明天 Day 27 继续 RAG：上下文压缩与查询改写。

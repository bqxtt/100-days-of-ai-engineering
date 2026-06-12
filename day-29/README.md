# Day 29 — 高级 RAG（上）：Query Transformation 与 HyDE

> **阶段**：Phase 3 · RAG 系统设计与实现
> **主题**：查询改写（Query Transformation）—— Multi-Query、HyDE（假设文档嵌入）、Step-Back
> **预计耗时**：约 1 小时（后端 1h/天）
> **给后端工程师的一句话**：朴素 RAG 的命门在第一步——**用户的问题，往往不是检索的好钥匙**。一个口语化短问句「HNSW 干嘛的？」和库里那条工整的陈述句「HNSW 是一种基于跳表的图索引……」语义形态差很远，向量未必近，检索就漏。今天学的不是换模型、换库，而是**在问题进库之前，先把它改写成更好检索的形态**——这一类技术叫 Query Transformation（查询变换）。它便宜、对现有库零改动、收益立竿见影，是 RAG 调优的第一杠杆。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器、零依赖、深色、纯 canvas）。它把「原问题检索」和「HyDE 检索」并排放：左边用一句短问题去查文档，右边先让模型**编一个假设答案**再去查，你能看到 HyDE 那条的相似度条更长、命中更准。先玩后读，先有直觉再看原理。

---

## 📖 学习内容（约 30 分钟）

### 1. 为什么查询改写（Query Transformation）很重要

朴素 RAG = 问题 → 嵌入 → 查最近文档 → 拼进 prompt。它假设「问题向量」和「答案文档向量」天然就近，但现实常崩在这一步：

- **形态错位**：问题是疑问句、口语、缩写（"咋治幻觉？"），文档是陈述句、术语（"RAG 检索增强生成……减少幻觉"）。同一个事，向量距离却不近。
- **太短太泛**：问题信息量小，嵌入"抓不住重点"，召回一堆似是而非。
- **太具体**："2023 年 Q3 营收同比"——卡在某个细节，错过讲背景的好文档。

后端类比：**没改写的问题就像没规整的查询参数**——你不会拿用户原始输入直接拼 SQL，会先 normalize、补全、纠错。RAG 也一样：在检索前把 query 处理好，召回质量就上一个台阶。这就是 **Query Transformation**。三种主力手段：Multi-Query（多发几个）、HyDE（先编答案再查）、Step-Back（先退一步问大问题）。

### 2. Multi-Query（多查询改写）——一个问题拆成几个，并集召回

让 LLM 把原问题改写成 3~5 个不同措辞/角度的等价问题，每个都去检索，再把结果**去重合并**：

```
原问：HNSW 干嘛的？
 → ① HNSW 索引的原理是什么？
 → ② 向量检索为什么用 HNSW？
 → ③ HNSW 和 IVF 有何区别？
全部检索 → 合并去重 → 喂模型
```

核心收益：**靠覆盖面对冲单次召回的随机性**。单个 query 可能因措辞偏差漏掉对的文档，五个不同措辞总有一个命中。代价是多花几次嵌入+检索。LangChain 把它封成 `MultiQueryRetriever`，一行接入：见 https://python.langchain.com/docs/how_to/MultiQueryRetriever/

### 3. HyDE：先生成"假设答案"，再用它检索（今天主角）

HyDE = Hypothetical Document Embeddings（假设文档嵌入）。反直觉但极妙：**别用问题去查，先让 LLM 瞎编一个像样的答案，用这个假答案去查。**

```
问题：嵌入向量怎么比相似？
 1) 让 LLM 编个答案：「嵌入向量通过余弦相似度计算来比较相似度。」（可能编得不全对）
 2) 嵌入这条假答案（而非问题）
 3) 拿假答案向量去查文档库
```

为什么有效：**答案和文档同形态**（都是陈述句、含术语），「答案↔文档」比「问题↔文档」距离更近，命中更准。假答案对不对不重要——它只是个"形状对的诱饵"，把检索拉到正确的语义邻域。论文：HyDE《Precise Zero-Shot Dense Retrieval without Relevance Labels》arXiv 2212.10496 — https://arxiv.org/abs/2212.10496 。今天 `practice.py` 就是亲手跑一遍：同样的问题，直接检索 vs HyDE，看相似度和命中谁更好。

> 边界：假答案编得太歪也会把检索带偏（practice 里能看到一例）。HyDE 吃模型质量，用 3B 编会一般，换大模型更稳。

### 4. Step-Back（退一步提问）——先答大问题，再答小问题

具体问题太"窄"会漏背景。Step-Back 让模型先退一步抽象出一个大问题，检索它的背景知识，再回答原问题：

```
原问：HNSW 在 100 万向量下的内存占用？
退一步：向量索引的内存与什么有关？  ← 先检索这个更通用的，拿到原理背景
然后再答原问题
```

适合需要原理/背景支撑的细节题。三招对比：**Multi-Query 拓宽，Step-Back 拔高，HyDE 对齐形态**——可叠加。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **HyDE 原论文（必看，今天主角）** — https://arxiv.org/abs/2212.10496 — 《Precise Zero-Shot Dense Retrieval without Relevance Labels》，读 1/3.2 节就懂"用假设文档嵌入"的妙处。
2. **LangChain MultiQueryRetriever 文档** — https://python.langchain.com/docs/how_to/MultiQueryRetriever/ — 多查询改写的标准实现，一行接入，呼应模块 2。
3. **LangChain Query Transformations 博客** — https://blog.langchain.dev/query-transformations/ — Multi-Query / HyDE / Step-Back / RAG-Fusion 全家桶横评，今天三招的"地图"。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**numpy + 标准库，真连本地 Ollama**：嵌入用 `nomic-embed-text`，编假设答案用 `qwen2.5:3b`。同一批问题各跑两条路——直接把问题嵌入检索 vs HyDE（先编答案再嵌入检索），打印命中文档与余弦相似度对比。补齐标 `★` 的 3 行，再对照文末答案。

```bash
# 先备好 Ollama（已装可跳过前两步）：
ollama serve                  # 启动服务（默认 http://localhost:11434）
ollama pull nomic-embed-text  # 嵌入模型（约 274MB）
ollama pull qwen2.5:3b        # 编假设答案（约 1.9GB）
# 真跑：
cd ~/projects/daily-learn && uv run day-29/practice.py
```

预期：3 个口语短问题，HyDE 的相似度普遍**高于**直接检索，HNSW 那题还会把命中纠到更对的文档；同时会看到一例假答案编歪导致命中漂移——这正是 HyDE 的边界，文末会点明。能跑出对比即达标。

### 🎨 可视化

`visualize.html` 把"原问题 vs HyDE"的检索过程画成并排深色 canvas，先玩它最直观。

---

## 🤔 思考题（边做边想）

1. HyDE 的假设答案"编错了"也常能检索更准——为什么？它依赖的是答案的"内容对"还是"形态对"？
2. Multi-Query 召回更全但要多发几次检索请求——这成本/收益和你给搜索加同义词扩展像不像？什么场景下不值得？
3. HyDE 多了一次 LLM 生成（延迟+成本），Step-Back 多了一跳检索。线上 QPS 高时，这三招你会先上哪个、怎么缓存？
4. 三招能叠加（先 HyDE 编答案、再 Multi-Query 多发、命中后合并）——叠加会更好还是过拟合到噪声？怎么用一个评估集量化收益？

> 把答案记进 `notes.md`，明天 Day 30 进「高级 RAG（下）」：Re-ranking 重排与混合检索，把今天召回的一堆文档再筛精。

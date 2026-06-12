# Day 22 — 向量数据库：Chroma / Pinecone / Milvus 对比与选型

> **阶段**：Phase 3 · RAG 系统设计与实现
> **主题**：向量库（Vector Database）做什么、HNSW/IVF 索引直觉、四大主流库对比、怎么选型
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：你建过 MySQL 索引、用过 Redis 做缓存、上过 ES 做全文检索。向量库（Vector DB）就是给「语义」建的索引——把句子变成一串数（embedding），再用「找最近邻」代替「精确匹配」。今天不学新数学，只把它当成一种新的存储引擎：它有写入（add）、有查询（query topk）、有索引（HNSW/IVF）、有选型权衡——和你选 MySQL 还是 MongoDB 是同一类决策。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器、零依赖、深色）。它把一个向量库在你眼前跑一遍：① 一批句子「入库」成平面上的点 ② 输入一条查询，向量库点亮 **Top-K 最近邻** ③ 切换「暴力检索 vs 近似检索（HNSW 直觉）」看两者命中差异与扫描量。看完你就懂：**向量检索 = 在高维空间里找离你最近的几个点**，剩下全是工程优化。先玩后读。

---

## 📖 学习内容（约 30 分钟）

### 1. 向量库做什么：把「精确匹配」换成「语义最近邻」

传统数据库找的是「等于」：`WHERE title = '订单超时'`。但用户搜「下单很久没发货」，关键词对不上，就查不到。**向量库找的是「意思最近」**：

```
入库：句子 --(嵌入模型)--> 向量[768维]  存进库
查询：问题 --(嵌入模型)--> 向量[768维]  → 找库里离它最近的 K 个 → 返回原句
```

三个动作，后端全都熟：
- **add（写入）**：把文本嵌成向量，连同原文一起存。等于 `INSERT`。
- **query topk（查询）**：把问题嵌成向量，返回最相似的 K 条。等于带排序的 `SELECT ... LIMIT K`，只是排序键是「相似度」。
- **相似度（distance）**：最常用**余弦相似度（cosine similarity）= 两向量夹角的 cos**。归一化后越接近 1 越像。这就是 RAG「检索」那一步的全部内核——下一天接 LLM 生成。

> 一句话：向量库 = 给语义建索引的存储引擎，CRUD 不变，只是把「==」换成「最近邻 nearest-neighbor」。

### 2. HNSW / IVF 索引直觉：百万向量为什么不能一条条算

暴力检索（brute-force / flat）= 拿查询向量和**每一条**算余弦，N 条就 N 次。几千条没问题，**百万条每次查询都全表扫**就崩了——和没建索引的 `LIKE '%x%'` 一样。两大近似最近邻（ANN）索引：

| 索引 | 直觉类比 | 怎么省 | 代价 |
|---|---|---|---|
| **IVF**（倒排+聚类） | 像图书馆先分区，只进相关书架找 | 先把向量聚成 N 个簇，查询只算最近几个簇 | 召回率随簇数下降 |
| **HNSW**（分层小世界图） | 像地铁先坐快线再换慢线，逐层逼近 | 多层跳点图，从稀疏层跳到密集层快速逼近邻居 | 内存占用大、构建慢 |

核心权衡是 **召回率 vs 速度 vs 内存** 的三角：暴力检索召回 100% 但最慢；ANN 牺牲一点召回换几十倍加速。**今天 practice.py 手写的是暴力检索**——千条以内最准，先把内核吃透，索引是后续的优化。

### 3. Chroma / Pinecone / Milvus / pgvector 对比

| 维度 | **Chroma** | **Pinecone** | **Milvus** | **pgvector** |
|---|---|---|---|---|
| 形态 | 本地嵌入式库 | 全托管 SaaS | 自建分布式集群 | PostgreSQL 扩展 |
| 部署 | `pip install` 即用 | 注册即用、无运维 | 需自己运维/k8s | 已有 PG 即可 |
| 规模 | 万~百万 | 亿级、托管伸缩 | 十亿级 | 千万级 |
| 索引 | HNSW | 托管（黑盒） | HNSW/IVF/DiskANN 等 | HNSW/IVF |
| 上手 | 最快、教程级 | 快、要付费 key | 重、运维成本高 | 0 新组件、SQL 原生 |
| 成本 | 免费开源 | 按量付费 | 开源但运维贵 | 免费、复用 PG |
| 适合 | 原型/小项目 | 不想运维、要 SLA | 海量、高 QPS | 已有 PG、想少加组件 |

口诀：**原型用 Chroma，懒得运维买 Pinecone，海量自建上 Milvus，已有 Postgres 就 pgvector**。

### 4. 选型决策：四个问题问下来就有答案

```
1) 数据量？  <百万→Chroma/pgvector  亿级→Pinecone/Milvus
2) 谁运维？  不想运维→Pinecone(SaaS)  能自建→Milvus  想复用→pgvector
3) 已有栈？  已有Postgres→pgvector  纯新→Chroma
4) SLA/合规？ 要托管SLA→Pinecone  要数据自留→Milvus/pgvector
```

后端经验直接迁移：80% 的 RAG 项目起步「Chroma 或 pgvector」就够了，别一上来就上 Milvus 集群——和「别拿 K8s 跑一个定时脚本」是同款过度设计。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Chroma 官方文档** — https://docs.trychroma.com — 最快上手的嵌入式向量库，看 Getting Started 即可对应今天的 add/query 心智。
2. **Pinecone 官方文档** — https://docs.pinecone.io — 全托管 SaaS，看「Indexes / Upsert / Query」三页就懂托管向量库的形态。
3. **Milvus 官方文档** — https://milvus.io/docs — 看 Overview 与 Index 章节，HNSW/IVF/DiskANN 各索引的取舍写得很全，呼应模块 2。
4. （加餐）**pgvector** — https://github.com/pgvector/pgvector — 给 Postgres 加向量列与索引，后端最低心智负担的选项。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`：**纯 NumPy 手写一个 mini 向量库**（add / query topk / 余弦相似度 / 暴力检索），并**真连本地 Ollama 的 nomic-embed-text** 把几句话嵌成向量入库、再嵌一条问题检索 Top-K。补齐标 ★ 的几行，再对照文末答案。

```bash
# 先备好 Ollama（已装可跳过）：
ollama serve                      # 启动服务（默认 http://localhost:11434）
ollama pull nomic-embed-text      # 嵌入模型（约 270MB，768 维）
ollama pull qwen2.5:3b            # 生成模型（约 1.9GB，文末演示用）
# 真跑：
uv run day-22/practice.py
```

预期：6 句话入库，查「下单后很久不发货」→ Top-3 命中订单/物流相关句，明显高于无关句；qwen2.5:3b 用检索结果生成一句简短回答（RAG 雏形）。看到相似度排序合理即达标。

### 🎨 可视化

`visualize.html` 把「入库 + Top-K 检索 + 暴力 vs 近似」画成深色动画，先玩它最直观。

---

## 🤔 思考题（边做边想）

1. 余弦相似度只看「方向」不看「长度」——为什么这正适合比较句子语义？什么时候你反而需要欧氏距离？
2. 暴力检索召回 100% 但 O(N)。HNSW/IVF 牺牲召回换速度——这和你「加缓存换一致性」「分库分表换查询复杂度」的权衡像不像？
3. 你现在的业务，落地 RAG 会选 Chroma / Pinecone / Milvus / pgvector 哪个？把「数据量/谁运维/已有栈/SLA」四问走一遍。
4. 嵌入维度从 768 升到 3072，存储和检索成本怎么变？这对「选小模型还是大模型嵌入」意味着什么？

> 把答案记进 `notes.md`。明天 Day 23 接着用真实向量库（Chroma）+ LLM 把今天的检索拼成完整 RAG。

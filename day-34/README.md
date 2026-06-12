# Day 34 — RAG 生产化：缓存、增量更新、监控告警

> **阶段**：Phase 3 · RAG 系统设计与实现
> **主题**：embedding 缓存 / 增量索引（新增/删除不重建）/ 语义缓存命中 / 监控指标与告警
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：今天没有新模型概念，全是你最熟的活——缓存、增量、监控。把"调下游服务"换成"调嵌入模型 + 查向量库"，省钱靠**别重算**、扩容靠**别重建**、稳定靠**盯指标**。会扛流量峰值的后端，天生会做 RAG 生产化。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器、零依赖、深色）。两块画布：① **缓存命中率**——请求流进来，相同/相近的走缓存（绿），首次走真算（橙），看命中率曲线随重复度爬升；② **增量更新**——库里一排向量块，点"新增"插一块、点"删除"弹一块，对比"全量重建"要把所有块红闪一遍，一眼看懂为什么增量是上线刚需。先玩后读，"命中"和"增量"的形状立刻就懂。

---

## 📖 学习内容（约 30 分钟）

### 1. Embedding 缓存：同一段文本只算一次

嵌入是 RAG 里最高频的开销——每条文档、每个查询都要算一次向量。但文本是**重复的**：同一篇文档反复入库、同一个问题反复被问。用 `hash(text)` 当 key 把向量缓存起来，二次直接命中内存，省掉一次模型调用、延迟从几十毫秒降到微秒。这就是你给数据库查询加 Redis 的那一套，key 换成文本指纹而已。要点：嵌入是**确定性**的（同文本同向量），所以缓存零风险；索引和查询必须用**同一个模型**（本课统一 nomic-embed-text，768 维），换模型整库失效。

文档：LangChain 嵌入缓存 `CacheBackedEmbeddings` — https://python.langchain.com/docs/how_to/caching_embeddings/

### 2. 增量索引：新增/删除只动一行，绝不重建

向量库上线后文档天天变。最蠢的做法是每次都把全部文档重新嵌入、重建索引——10 万篇文档改一篇要等几小时。正确做法是**增量**：`add` 只插一条、`delete` 只弹一条，其余向量纹丝不动。生产向量库（Chroma/Milvus/PGVector）都支持 upsert/delete，配上文档 `id` 与内容 hash，就能"只重嵌入变化的那几篇"。这就是数据库的增删改——别因为它是向量就忘了你会写 OLTP。

文档：Chroma 增删改（add/update/delete） — https://docs.trychroma.com/docs/collections/update-data

### 3. 语义缓存命中：相近问题复用旧答案

普通缓存只在文本**完全相同**时命中；语义缓存更狠——把"问题向量"存下来，新问题向量与历史向量余弦相似度超阈值（如 0.92）就**直接复用旧答案**，跳过检索 + 生成。"什么是 RAG？"和"RAG 是啥意思"措辞不同语义相同，命中后省一整条链路。代价是阈值要调好：太松会错复用、太紧等于没缓存。生产里常加 TTL + 命中后仍轻量校验。

文档：RAG 生产实践 — Pinecone 语义缓存 — https://www.pinecone.io/learn/semantic-cache/

### 4. 监控指标与告警：上线后 80% 的工作

RAG 跑起来就是个服务，照样要盯：**缓存命中率**（掉了说明成本飙升）、**检索延迟 p95**、**库规模/向量数**、**嵌入调用数**（直接对应账单）、**召回为空率**。一行 JSON 打出来就能接 Prometheus，配 Grafana 看曲线、配告警阈值（命中率 < 50% / p95 > 500ms 报警）。这跟你给微服务做可观测性零差别——指标、面板、告警三件套。

文档：RAG 生产化最佳实践 — https://www.databricks.com/blog/long-context-rag-performance-llms

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **LangChain — Caching Embeddings（必读）** — https://python.langchain.com/docs/how_to/caching_embeddings/ — 嵌入缓存怎么落到本地/Redis，看清 key 与 store 怎么接。
2. **Pinecone — Semantic Cache** — https://www.pinecone.io/learn/semantic-cache/ — 语义缓存的阈值取舍与命中逻辑。
3. **Chroma — Update / delete 数据** — https://docs.trychroma.com/docs/collections/update-data — 增量 upsert/delete 的官方用法。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`：手写一个**带缓存的向量库**——① 嵌入缓存（同文只算一次）② 增量 `add/delete`（不重建）③ 语义缓存命中演示，最后打一行监控指标。真调本地 ollama 的 nomic-embed-text 产生真实向量，没装也有离线兜底。先补 3 个 ★ 行再对答案。

```bash
ollama serve                     # 默认监听 http://localhost:11434
ollama pull nomic-embed-text     # 一次性拉嵌入模型（约 274MB）
cd ~/projects/daily-learn && uv run day-34/practice.py
```

预期：建库全 miss → 同文重入嵌入命中 → 删除后库规模降而其余不动 → 相近问题语义缓存命中提速 → 末尾打出命中率/向量数/调用数。能跑出这四段就达标。

---

## 🤔 思考题（边做边想）

1. 嵌入缓存为什么"零风险"？换嵌入模型时整库为什么必须失效？
2. 语义缓存阈值调 0.99 和 0.80 各会出什么问题？怎么加 TTL 兜底？
3. 哪些指标该配告警、阈值定多少？命中率突然掉到 10% 你先查什么？

> 答案随手记 `notes.md`，明天 Day 35 实践日把前面分块/检索/缓存/增量串成一个能用的个人知识库问答系统。

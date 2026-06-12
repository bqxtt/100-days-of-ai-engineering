# Day 32 — RAG 评估：Faithfulness、Relevancy、RAGAS

> **阶段**：Phase 3 · RAG 系统设计与实现
> **主题**：用「裁判 LLM（LLM-as-Judge）」给 RAG 答案自动打分——忠实度 Faithfulness、答案相关度 Answer Relevancy、上下文相关度 Context Relevancy，以及把它们打包的 RAGAS 框架
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：你上线一个接口会写监控、会有 P99、会有错误率。RAG 也一样——只是「对不对」没法用 `assertEqual` 判，得换一把尺子。今天就学这把尺子：让另一个模型当**裁判**，给「答案有没有编、答得切不切题、检索的料对不对路」分别打分。听着玄，落地就是几个 prompt + 一个平均数，本机 qwen2.5:3b 就能跑。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器、零依赖、深色）。一张 **RAG 质量雷达图** + 指标条：左边切换「好答案 / 编造答案 / 跑题答案」三个样例，看 Faithfulness（忠实度）、Answer Relevancy（答案相关度）、Context Relevancy（上下文相关度）三根指标条此消彼长，雷达图随之变形。一眼就懂：**同一个 RAG，不同失败模式会塌陷在不同的维度上**——编造塌 Faithfulness，跑题塌 Answer Relevancy，检索差塌 Context Relevancy。先玩后读。

---

## 📖 学习内容（约 35 分钟）

### 1. 为何要评估：RAG 的两段路，每一段都会坏

RAG = **检索（Retrieval）+ 生成（Generation）**。坏的地方就两类，对应两段路：

```
问题 ──检索──> 上下文(context) ──生成──> 答案
        ↑坏1：检索回来的料不对/不全        ↑坏2：模型不照料答、编、跑题
```

后端工程师最熟的反例：接口 200 但内容是错的。RAG 也会「成功地给你一个错答案」——单测过不了它，错误率监控也抓不到。所以要专门一套**质量指标**，把这两段拆开各打一分：

- **答案在不在料里**（编没编）→ 忠实度 Faithfulness
- **答案切不切题**（答没答到点上）→ 答案相关度 Answer Relevancy
- **料对不对路**（检索给力不给力）→ 上下文相关度 Context Relevancy

为什么用「另一个模型当裁判」（LLM-as-Judge）而不是 BLEU/ROUGE 这类老指标？因为开放问答没有唯一标准答案，字面匹配会冤枉「换种说法但对」的答案。让模型读题、读料、读答案，像人一样判，反而更准。代价是裁判自己也可能错——所以**裁判要钉死随机性（temperature=0）**，并尽量只让它做「是非小判断」。

### 2. Faithfulness 忠实度：答案有没有「编」

定义：**答案里的每一句，能不能从上下文推出来。** 全能推=1.0，凭空捏造=往 0 掉。它专治 RAG 的头号病——**幻觉（hallucination）**。

落地算法（RAGAS 同款思路）：

```
1) 把答案拆成若干「陈述句」(claims)
2) 逐句问裁判：这句能由 context 支持吗？(yes/no)
3) faithfulness = 被支持的句数 / 总句数
```

例：料里只说「公司 2021 年成立」，答案却写「2021 年成立、员工 500 人」——后半句料里没有，2 句中 1 句被支持，忠实度 0.5。**注意它不管答得对不对，只管「是不是照着料说」**，这正是 RAG「有据可查」的命根子。

### 3. Answer / Context Relevancy：切不切题 vs 料对不对

两个都叫 relevancy，盯的两段路不同，别搞混：

| 指标 | 中文 | 衡量什么 | 塌了说明 |
|---|---|---|---|
| **Answer Relevancy** | 答案相关度 | 答案对**问题**切题吗？有没有跑题/废话/答非所问 | 生成端跑题 |
| **Context Relevancy** | 上下文相关度 | 检索回的**料**对问题有用吗？还是混了一堆噪声 | 检索端拉胯 |

- **Answer Relevancy**：忠实但跑题也是废。问「成立年份」，模型照着料把公司历史背了一段——忠实度满分，但没正面答，相关度低。RAGAS 做法是反向：让模型从答案「猜原问题」，猜得越像、越相关。
- **Context Relevancy**：检索回 10 段只有 2 段有用，分就低。它直接体现你的 embedding/重排好不好——**多数 RAG 烂在检索而非生成**，先盯这条。

三者合看才完整：**Faithfulness 管「没编」、Answer Relevancy 管「答到点」、Context Relevancy 管「找对料」**。缺一个都能让另两个的高分变成假象。

### 4. RAGAS：把三件套打成一个框架

[RAGAS](https://docs.ragas.io)（Retrieval-Augmented Generation Assessment）就是把上面这套用代码标准化的开源框架，一行调出三指标，还能批量跑数据集、出报告。它解决两个工程痛点：① **无参考答案也能评**（unsupervised，靠 LLM 拆句/反问）；② **指标可复现**（裁判 temperature=0、prompt 固定）。

```python
# RAGAS 真实用法（今天 practice.py 用标准库手搓同款逻辑，理解原理）
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_relevancy
score = evaluate(dataset, metrics=[faithfulness, answer_relevancy, context_relevancy])
```

记住一句：**RAGAS 不是黑魔法，就是「拆句 + 逐句问裁判 + 求平均」**。今天我们不用 RAGAS 库，用本机模型把这个平均数亲手算出来，看清里子；上生产再换官方库享受批量/报告。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **RAGAS 官方文档（必看，今天三指标的权威定义）** — https://docs.ragas.io — 看 Metrics 章 Faithfulness / Answer Relevancy / Context Relevancy 的定义与公式，和本文一一对应。
2. **RAGAS 论文 arXiv:2309.15217《RAGAS: Automated Evaluation of RAG》** — https://arxiv.org/abs/2309.15217 — 提出「无参考、LLM 拆句打分」的原始论文，理解为何这么算。
3. **RAGAS 源码** — https://github.com/explodinggradients/ragas — 看 `faithfulness` 是怎么拆句逐句判的，正是 `practice.py` 的同款骨架。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯 Python 标准库，无需付费 key，真连本地 Ollama**：用 qwen2.5:3b 当裁判，对两组真实「问题+料+答案」分别打 Faithfulness / Answer Relevancy / Context Relevancy。第一组是好答案（应高分），第二组掺了编造+跑题（应在对应维度塌）。补齐 `★` 行，对照文末答案。

```bash
# 先备好 Ollama（已装可跳过前两步）：
ollama serve            # 启动服务（默认 http://localhost:11434）
ollama pull qwen2.5:3b  # 拉裁判模型（约 1.9GB）
# 真跑：
cd ~/projects/daily-learn && uv run day-32/practice.py
```

预期：两组答案各出三项分数，第一组三项均高、第二组 Faithfulness 与 Answer Relevancy 明显低——亲眼看到「编造/跑题塌在不同维度」即达标。

### 🎨 可视化

`visualize.html` 把三指标画成雷达图+条形，对照三种失败样例最直观，先玩它。

---

## 🤔 思考题（边做边想）

1. 裁判模型自己也可能判错——你会怎么降低它的方差？（temperature、多次投票、用更强的模型当裁判）
2. Faithfulness 高但 Answer Relevancy 低，是哪段路坏了？反过来呢？该先修检索还是生成？
3. 没有标准答案也能评分——这对你给线上 RAG 接做「质量监控/告警」意味着什么？哪个指标最该实时盯？
4. 用小模型当裁判去评同档小模型的答案，会不会「裁判太菜冤枉好答案」？生产里你会怎么取舍成本与可信度？

> 把答案记进 `notes.md`。明天 Day 33 继续 Phase 3：把评估接进 RAG 迭代闭环。

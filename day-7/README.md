# Day 7 — 预训练范式：BERT vs GPT、自监督学习、Scaling Laws

> **阶段**：Phase 1 · 大模型核心原理
> **主题**：自监督学习（MLM vs 自回归）、双向 BERT vs 单向 GPT、Scaling Laws、Chinchilla
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：监督学习要人工标数据，贵又慢；**自监督学习**让模型自己出题自己改卷——"挖掉一个词让它猜"就是标注。今天看清两种出题方式（完形填空 vs 续写），以及"模型多大、喂多少数据"和 loss 之间那条几乎像物理定律的曲线。

---

## 📖 学习内容（约 25 分钟）

### 1. 自监督学习：让数据自己当标注 (Self-Supervised Learning)

后端工程师标过数据吗？人工打标又贵又慢。**自监督学习**的核心：**把输入的一部分藏起来，让模型用剩下的去预测它**——标签来自数据本身，零人工。无限的互联网文本瞬间变成无限的训练样本。两种主流"出题法"：

| 范式 | 英文 | 怎么出题 | 类比 | 代表 |
|---|---|---|---|---|
| 掩码语言建模 | **MLM** (Masked LM) | 随机挖掉 15% 词，看上下文猜空 | 完形填空 | BERT |
| 自回归 | **Autoregressive / Causal LM** | 只给前文，逐字预测下一个 | 接龙续写 | GPT |

```
原句:  我 今天 [MASK] 了 一个 bug
MLM:   两边都能看 → 猜中间这个 "[MASK]"="修复"   (完形填空，双向)
GPT:   我→今天→修复→了→一个→? 只能看左边 → 猜下一个 "bug"  (续写，单向)
```

**关键直觉**：自监督学到的不是某个具体任务，而是**语言的通用规律**（语法、常识、搭配）。先在海量文本上预训练得到"通才"，再用少量标注做微调变"专才"——这就是 pretrain + finetune 范式。

### 2. 双向 BERT vs 单向 GPT（一张图说清）

| | **BERT** (Encoder) | **GPT** (Decoder) |
|---|---|---|
| 注意力 | 双向，每个词能看全句 | 单向，只能看左边（causal mask） |
| 训练目标 | MLM 完形填空 | 预测下一个 token |
| 擅长 | **理解**：分类、检索、NER | **生成**：续写、对话、写代码 |
| 类比 | 阅读理解（来回看全文） | 自动补全（边写边猜） |

工程类比：BERT 像**读完整份日志再判断异常**（看到全文），GPT 像**流式处理边读边输出**（只能看已到的部分）。为什么大模型时代是 GPT 赢了？因为单向"预测下一个词"天生就是生成任务，规模一上去就能写、能聊、能 few-shot，而 MLM 难以直接生成。今天大模型几乎都是 decoder-only。

### 3. Scaling Laws：loss 像物理定律一样可预测 (2020, OpenAI)

最反直觉也最重要的发现：**模型 loss 随参数量 N、数据量 D、算力 C 的增加，呈幂律下降**，在 log-log 图上是**直线**。

```
L(N) ≈ (Nc / N)^αN        参数越多 loss 越低，斜率 αN≈0.076
L(D) ≈ (Dc / D)^αD        数据越多 loss 越低
```

幂律 `L ∝ N^(-a)` 的工程含义：**翻倍投入只换来固定的 loss 下降**（边际递减），但**极其平滑可外推**——能用小模型实验预测大模型表现，先算 ROI 再砸钱。后端类比：像缓存命中率 vs 缓存大小，前期投入收益大、后期边际递减，但曲线稳得能写进容量规划文档。

### 4. Chinchilla：算力一定，参数和数据怎么分？(2022, DeepMind)

GPT-3 有 175B 参数但只喂了 300B token——**模型太大、数据太少，钱没花在刀刃上**。Chinchilla 重做实验：固定算力下，**参数和数据应同比增长**，最优配比约 **20 token / 参数**。70B 的 Chinchilla 喂 1.4T token，性能反超 175B 的 GPT-3。

> 一句话：别盲目堆参数，**算力预算先分给数据**。这条"20:1"是后来 LLaMA 等开源模型的圈钱地图。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **BERT 原论文** — https://arxiv.org/abs/1810.04805 （MLM + 双向，看 §3.1 训练目标即可）
2. **GPT-2 论文《Language Models are Unsupervised Multitask Learners》** — https://cdn.openai.com/better-language-models/language_models_are_unsupervised_multitask_learners.pdf
3. **Scaling Laws for Neural Language Models（必读）** — https://arxiv.org/abs/2001.08361 — 看图 1 的幂律直线就够直觉
4. **Chinchilla《Training Compute-Optimal LLMs》** — https://arxiv.org/abs/2203.15556 — 20 token/参数的来源
5. **Jay Alammar — The Illustrated BERT**（图解，可视化天花板）— https://jalammar.github.io/illustrated-bert/

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**只用 NumPy**：生成一组符合 `loss ∝ N^-a` 的"实验数据"，再用最小二乘在 log-log 空间拟合出幂律指数 a，亲眼看到散点几乎压在一条直线上。完成标了 ★ 的行即可，文末有参考答案。

```bash
# 项目用 uv 管理，依赖已装好，直接跑：
uv run day-7/practice.py
```

预期：拟合出的指数 a ≈ 0.076（接近论文里的 αN），并打印外推：参数翻倍 loss 大约只降百分之几——亲手体会"边际递减但可预测"。

### 🎨 可视化（先玩这个再读理论，更直观）

双击打开 `visualize.html`（纯浏览器、深色、无需安装）。拖动**参数量 N** 和**数据量 D** 两个滑块，实时看 loss 下降曲线，并切换线性/对数坐标看幂律如何变成直线；还能开 Chinchilla 模式，体会"算力一定时把预算偏给参数还是数据"对最终 loss 的影响。

---

## 🤔 思考题（边做边想）

1. 同样是自监督，为什么 BERT 学不会"写文章"而 GPT 可以？双向能看全句反而成了生成的障碍，为什么？
2. Scaling Law 是幂律不是指数——如果你想把 loss 再降一半，参数大概要乘几倍？这对成本预算意味着什么？
3. Chinchilla 说 20 token/参数最优。但推理是要部署很久的——为什么很多产品反而故意"过度训练"小模型（喂超过 20:1）？（埋伏笔：Day 9 量化、Day 8 推理优化呼应部署成本）

> 把你的答案随手记在 `notes.md` 里，明天 Day 8 接着讲推理优化（KV Cache）。

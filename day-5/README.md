# Day 5 — Transformer 架构（下）：Decoder、Causal Mask、GPT 演进

> **阶段**：Phase 1 · 大模型核心原理
> **主题**：Decoder 结构、Causal Mask（因果掩码 / Causal Mask）、GPT 系列（GPT-1→GPT-4）演进与缩放定律（Scaling Laws）
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：你写过的最像 GPT 的代码，是「流式接口逐字节往输出 buffer 里 append」。GPT 推理就是一个 **for 循环里反复调用同一个纯函数**，每次吐一个 token、append 回输入、再调一次。今天把这个循环和它唯一的「防作弊规则」——只能看左边——彻底讲清。

---

## 📖 学习内容（约 30 分钟）

### 1. Decoder = 自回归生成器（一次预测下一个 token）

Day 4 讲的 Encoder 把整句话一次性读完，输出每个 token 的「上下文向量」。Decoder 干的是另一件事：**逐个吐字**。

```
后端类比：     for chunk in stream:  out.append(chunk); flush()   # 流式响应
GPT 生成：     for _ in range(N):   tok = model(已生成序列); 把 tok 接回输入
```

这就叫 **自回归（Autoregressive, AR）**：第 t 个输出会被喂回去当第 t+1 步的输入。结构上 Decoder block 比 Encoder 多/改一处：

| 组件 | Encoder | Decoder-only（GPT） |
|---|---|---|
| Self-Attention | 双向，能看全句 | **带 causal mask，只能看左边** |
| FFN（前馈） | 有 | 有 |
| 残差 + LayerNorm | 有 | 有（现代多用 Pre-LN，norm 在前） |
| 训练目标 | 完形填空（MLM） | **预测下一个词（Next-Token Prediction）** |

记住一句：**Decoder-only 模型 = N 个「带因果掩码的 self-attention + FFN」串起来，最后接一个 softmax 选下个词**。

### 2. Causal Mask = 防偷看未来（防作弊规则）

注意力的核心是 `softmax(QKᵀ/√d)·V`——每个 token 对所有 token 算权重。训练时整句一起喂进去，第 3 个词如果能「看到」第 5 个词，就等于**抄了答案**（标签泄漏），上线时根本没有未来可看，会崩。

解决办法极简：把 QKᵀ 的**上三角**（未来位置）置成 `-∞`，softmax 后这些位置的权重 ≈ 0。

```
QKᵀ 原始分数        加 mask 后（▓=封死）     softmax 后每行只在左侧有权重
[a b c d]           [a ▓ ▓ ▓]               token1 只看自己
[a b c d]   --->    [a b ▓ ▓]      --->     token2 看 1,2
[a b c d]           [a b c ▓]               token3 看 1,2,3
[a b c d]           [a b c d]               token4 看全部
```

类比：限流器只让「时间戳 ≤ 当前」的请求通过，未来的全拒。一行代码 `scores += mask`（mask 上三角是 -1e9）就实现了。今天 `practice.py` 就手写它。

### 3. GPT-1→2→3→4：演进就是「堆」+ Scaling Law

GPT 系列的进步可以粗暴概括为「同一个架构，参数和数据指数级变大」：

| 代际 | 年份 | 参数量 | 关键变化 / 启示 |
|---|---|---|---|
| GPT-1 | 2018 | 1.17 亿 | 证明「预训练 + 微调」范式可行 |
| GPT-2 | 2019 | 15 亿 | 不微调也能 zero-shot，规模带来涌现 |
| GPT-3 | 2020 | 1750 亿 | **In-context Learning**：给几个例子就会做，不改权重 |
| GPT-4 | 2023 | 未公开（疑似 MoE） | 多模态、强推理；指令对齐（RLHF）成熟 |

**Scaling Law（缩放定律）**：loss 随「参数量 / 数据量 / 算力」按幂律平滑下降——把规模放大 10 倍，loss 可预测地降一截。这是 GPT-3 敢直接造 1750 亿参数的底气。工程类比：QPS 上去前先压测拟合曲线，照曲线扩容，不靠玄学。

### 4. 为什么 Decoder-only 成了主流？

BERT（Encoder-only）、T5（Encoder-Decoder）也曾各领风骚，但生成式大模型几乎全押 Decoder-only，原因很工程：

1. **任务统一**：万物皆「续写下一个词」，翻译/问答/代码都能塞进同一目标，无需两套结构。
2. **训练信号密集**：一句 N 词，每个位置都是一次预测，样本利用率拉满。
3. **推理可缓存**：因为只看左边，算过的左侧 KV 能复用——这就是 **KV Cache**（埋伏笔，Day 8 详讲），省一半算力。
4. **简单可扩展**：结构单一，最契合 Scaling Law 往大堆。

---

## 🔗 推荐资源（约 10 分钟，按兴趣选）

1. **Jay Alammar — The Illustrated GPT-2**（必看，causal mask 与自回归的图解天花板）— https://jalammar.github.io/illustrated-gpt2/
2. **GPT-1 论文** Improving Language Understanding by Generative Pre-Training — https://cdn.openai.com/research-covers/language-unsupervised/language_understanding_paper.pdf
3. **GPT-3 论文** Language Models are Few-Shot Learners — https://arxiv.org/abs/2005.14165
4. **Scaling Laws for Neural Language Models** — https://arxiv.org/abs/2001.08361

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**只用 NumPy** 手写 ① 一个带 causal mask 的 self-attention，② 一步自回归采样（拿最后一个 token 的分布选下个词）。看清「上三角封死 → softmax → 选 token」的全过程。完成 3 个 ★ TODO 即可。

```bash
# 项目用 uv 管理环境，依赖已装好，直接跑：
uv run day-5/practice.py
```

预期：先打印 mask 后的注意力矩阵（上三角全是 ~0，下三角概率和=1），再从一个迷你词表自回归生成 6 个 token。能看到「每个 token 只把权重分给自己左边」就达标。

### 🎨 可视化（先玩这个再读理论，更直观）

双击打开 `visualize.html`（纯浏览器，无需安装）。两块画布：① **因果掩码三角矩阵**——鼠标悬停看每个位置能否互看，红=封死(未来)绿=可见；② **逐 token 自回归动画**——点「生成」看序列一个个吐出来，被掩掉的未来格子保持灰色，直观感受「只能看左边」。深色主题。

---

## 🤔 思考题（边做边想）

1. 训练时整句并行喂入需要 causal mask，**推理时**逐 token 生成、本来就没有未来——这时 mask 还需要吗？为什么？
2. GPT-3 不改权重、只看几个例子就会做新任务（In-context Learning），这和你给函数传不同参数有何异同？
3. 因为「只看左边」，左侧算过的 K/V 能复用 —— 想想这对长对话推理的显存和延迟意味着什么？（Day 8 KV Cache 会接）

> 把答案随手记在 `notes.md`，明天我们从 Decoder 的输出层接着讲采样与温度。

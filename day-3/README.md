# Day 3 — Attention 机制深入：Self-Attention 的数学推导与直觉

> **阶段**：Phase 1 · 大模型核心原理
> **主题**：Self-Attention 的数学推导与直觉理解（Q/K/V、点积相似度、缩放、softmax 加权）
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：Self-Attention 本质上就是一次"数据库查询"——每个词拿自己的 **query** 去匹配全场的 **key**，按匹配度从对应的 **value** 里加权取信息。看懂这一句，Transformer 的心脏就停不下来跳。

---

## 📖 学习内容（约 25 分钟）

### 1. Q/K/V：一次 self-attention 就是一次"数据库模糊查询"

后端工程师对 KV 存储太熟了：给一个精确 key，取出对应 value。注意力机制只多了一个变化——**模糊匹配**：不是非黑即白命中某条记录，而是按相似度对**所有** value 做加权平均。

| 数据库查询 | Self-Attention | 直觉 |
|---|---|---|
| query（你要查啥） | **Q**uery 向量 | 当前词的"我想知道什么" |
| key（每条记录的索引） | **K**ey 向量 | 每个词的"我能回答什么" |
| value（取出的内容） | **V**alue 向量 | 每个词真正携带的信息 |
| `WHERE key = q` 精确命中 | 点积相似度做软命中 | 不是命中一条，而是按分数取一片 |

关键点：Q、K、V 三者都是**同一份输入** X 各乘一个可学习矩阵投影出来的——`Q=X·Wq, K=X·Wk, V=X·Wv`。"self"（自注意力）就是 query 和 key 都来自同一句话，让每个词去看句子里的其他词。

### 2. 点积相似度 → 缩放 → softmax 加权（核心三步）

```
scores = Q · Kᵀ            # 点积越大 = 两向量越同向 = 越相关
scores = scores / √d_k     # 缩放：维度越高点积越大，除 √d_k 拉回正常量级
attn   = softmax(scores)   # 每一行变成"取多少"的概率，行和=1
out    = attn · V          # 按权重从 V 里加权求和，得到新表示
```

- **点积 = 相似度**：两个向量越"同向"，点积越大，相关性越高（和余弦相似度同源）。
- **为什么缩放 √d_k**：d_k 越大，点积数值越容易变得很大，softmax 会被推到饱和区（一个值≈1、其余≈0），梯度几乎消失。除以 √d_k 把方差拉回 1，让 softmax 保持"该分谁就分谁"。
- **softmax 把分数变权重**：Day 1 学的 softmax 又出现了——一组分数 → 概率分布，行和恒为 1。
- **加权求和**：每个词的输出 = 全场 value 的加权混合，权重就是注意力。一个词从此"看见"了上下文。

### 3. self-attention 全流程一图流

```
X (seq, d)
  │  ×Wq ×Wk ×Wv          投影成三种身份
  ▼
Q,K,V (seq, d_k)
  │  Q·Kᵀ                 谁该看谁：相似度打分
  ▼
scores (seq, seq) ──÷√d_k──► softmax ──► attn (seq, seq)  每行和=1
  │  attn·V               按权重取 value
  ▼
out (seq, d_k)            每个词被上下文重新表示
```

记一条铁律：**attn 是 seq×seq 的方阵，第 i 行就是 token i 分给全场的注意力**。这也是为什么注意力是 O(n²)——埋个伏笔，后面学 KV Cache / FlashAttention 全在跟这个 n² 较劲。

### 4. 后端类比：限流、缓存、加权路由

Self-attention 像极了一个**加权路由器**：每来一个请求（query），按相似度对所有后端节点（key）打分，再把它们的响应（value）加权聚合返回。softmax 就是"归一化的权重分配"，缩放就是"防止某个节点权重爆表把流量全吞掉"。本质都是——**按相关性，软分配资源**。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Jay Alammar《The Illustrated Transformer》**（必看，attention 可视化天花板）— https://jalammar.github.io/illustrated-transformer/
2. **《Attention Is All You Need》原论文** — https://arxiv.org/abs/1706.03762 — 只看 3.2 节 Scaled Dot-Product Attention，理解 √d_k 从哪来。
3. **3Blue1Brown — Attention in transformers** — https://www.youtube.com/watch?v=eMlx5fFNoYc — Q/K/V 几何直觉，配 B 站官方中字。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**只用 NumPy** 手写一个 single-head self-attention：QKV 投影 → 缩放点积 → softmax → 输出。不许用 PyTorch，目的是看清每一步矩阵运算。完成 3 个 ★ TODO 即可。

```bash
# 项目用 uv 管理环境，依赖已装好，直接跑：
uv run day-3/practice.py
```

预期：打印出 4×4 的注意力权重矩阵，**每行求和都为 1**，输出形状 (4, 8)。能跑出这个就达标。

### 🎨 可视化（先玩这个再读理论，更直观）

双击打开 `visualize.html`（纯浏览器，无需安装）。里面是交互式 attention 权重**热力图**：改输入 token、调缩放温度，实时看权重怎么变——颜色越亮代表那一对 token 关系越紧。亲手验证"某个 token 改了，整列权重跟着变"，缩放过小看 softmax 怎么塌成 one-hot。

---

## 🤔 思考题（边做边想）

1. 为什么要分 Q 和 K 两套矩阵？直接拿 X 自己点自己（`X·Xᵀ`）当注意力不行吗？
2. 把缩放 √d_k 拿掉，d_k 很大时 softmax 会变成什么样？梯度会怎样？
3. 注意力是 seq×seq 的方阵，序列翻倍计算量变几倍？这对长文本/长上下文意味着什么？（埋伏笔，后面 KV Cache 会呼应）

> 把你的答案随手记在 `notes.md` 里，明天 Day 4 我们从多头注意力（Multi-Head）接着讲。

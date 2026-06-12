# Day 10 — 🏗️ 实践日：手写一个简化版 Attention 机制

> **阶段**：Phase 1 · 大模型核心原理（收官日）
> **主题**：从零拼一个 mini 自注意力 block（Self-Attention block），把 Day 1-9 串成一条线
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：前 9 天我们一块块拆零件，今天把它们焊成一个能跑的整体。一个 Transformer block 说穿了就是 `Attention(QKV) → Add&Norm → FFN`——里面用到的全是你这两周亲手写过的东西：矩阵乘法、softmax、ReLU。今天用纯 NumPy 焊一遍，Phase 1 就毕业了。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器，无需安装）。这是一个 mini self-attention 的**前向流程动画**：输入几个 token → 拆出 Q/K/V → 算注意力权重热图（attention map）→ 加权求和出新表示。鼠标悬停某一行，看它"看向"了谁、权重多大；切换多头（multi-head）看不同头关注不同关系。先玩出"每个 token 都在加权看所有 token"的直觉，再读理论与跑代码。

---

## 📖 Phase 1 脉络回顾 + 今日目标（约 25 分钟）

### 1. 前 9 天我们到底拼了什么（一条线串起来）

今天不是新知识，是把零件焊起来。回顾这条主链：

| Day | 主题 | 今天用到的零件 |
|---|---|---|
| 1 | 神经网络 / 反向传播 | 矩阵乘法 + 激活函数 = block 里的 FFN |
| 2 | 词向量 Word Embedding | token → 向量，attention 的输入就是它 |
| 3 | Attention 机制 | **今天的主角**：QKV + softmax 加权 |
| 4 | Transformer（上）| 多头 Multi-Head、位置编码 Positional Encoding |
| 5 | Transformer（下）| Decoder、因果掩码 Causal Mask（我们顺手加） |
| 6 | Tokenization | 文本怎么变成 token id（输入前的一步） |
| 7 | 预训练 Pretraining | 这些权重原本怎么学来的 |
| 8 | 推理 / KV Cache | attention 算完缓存 K/V，下一步省算力 |
| 9 | 量化 Quantization | 焊好的 block 怎么压进消费级显卡 |

一句话总结：**Embedding(D2) 把 token 变向量 → Attention(D3) 让 token 互相看 → 多头+位置(D4) 增强表达 → FFN(D1) 逐位置加工 → 推理(D8) 时缓存、量化(D9) 时压缩。** 今天写的就是这条链最核心的一环。

### 2. 今日目标：从零拼一个 mini 自注意力 block

我们要用纯 NumPy 实现一个**单层 self-attention block** 的前向，看清每一步张量怎么流动：

```
tokens(id)  →  embedding 查表  →  X[seq, d_model]
X  →  ×Wq/Wk/Wv  →  Q, K, V[seq, d_model]
拆成多头 → 每头算 scores = Q·Kᵀ / √d_head  → softmax → 权重
权重 · V → 拼回多头 → ×Wo → 输出[seq, d_model]
```

### 3. 自注意力的一句话本质：Q 问、K 答、V 取

把它想成一次**软查询（soft lookup）**，后端的字典查询是硬的，这里是软的：

- **Q（Query）**：每个 token 提出"我想找什么"
- **K（Key）**：每个 token 公布"我能提供什么"
- **V（Value）**：每个 token 真正携带的信息

`Q·Kᵀ` 算出每个 token 跟其他所有 token 的"匹配分"，`/√d_head` 防止数值过大，`softmax` 把分变成概率权重，再用权重对 V 加权求和——每个 token 都得到一个"看过全场后"的新表示。

```
Attention(Q,K,V) = softmax(Q·Kᵀ / √d_head) · V   # 整篇 Transformer 最重要的一行
```

### 4. 多头（Multi-Head）= 多个查询视角并行

把 d_model 切成 h 份，各算一套小 attention，再拼回来。一头看语法、一头看指代、一头看长程依赖——和你给同一份数据开多个并行 worker 各管一类逻辑一样。最后 `×Wo` 把多头结果融合。

### 5. 因果掩码（Causal Mask）：写文章只能看左边

GPT 这类 decoder（Day 5）生成时第 i 个 token 不能偷看未来。做法：softmax 前把上三角填 `-∞`，权重就归零。我们在练习里加一个开关，亲眼看权重矩阵变成下三角——这正是 KV Cache（Day 8）能成立的前提。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Andrej Karpathy — nanoGPT**（必看，工业级最小 GPT，今天 block 的"成品参照"）— https://github.com/karpathy/nanoGPT — 重点读 `model.py` 里的 `CausalSelfAttention`，跟你今天写的几乎一一对应。
2. **Andrej Karpathy — minGPT** — https://github.com/karpathy/minGPT — nanoGPT 的教学前身，注释更细，PyTorch 版 attention 看一眼。
3. **The Illustrated Transformer**（Jay Alammar，全网最佳图解）— https://jalammar.github.io/illustrated-transformer/ — QKV/多头/权重热图的图都在这，对照可视化看。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**只用 NumPy** 拼一个单层多头 self-attention block：embedding 查表 → QKV 投影 → 多头拆分 → 缩放点积 + softmax → 加权聚合 → 输出投影。完成 4 个 ★ 即可，是 Phase 1 的"毕业焊接"。

```bash
# 在项目根目录跑（环境用 uv 管理，依赖已装好）：
uv run day-10/practice.py
```

预期：每个 token 输出一个 d_model 维新向量；权重矩阵每行和为 1；开因果掩码后权重变下三角。看到这些就算焊通了。

### 🎨 配合可视化

跑通 `practice.py` 后回到 `visualize.html`，把代码里的 `Q·Kᵀ→softmax→·V` 三步在动画里逐帧对上号，热图越亮=权重越大=越关注，这就是大模型"理解上下文"的物理动作。

---

## 🤔 思考题（边做边想）

1. 为什么 `Q·Kᵀ` 要除以 `√d_head`？维度变大不除会发生什么（提示：softmax 会被极端值"饱和"）？
2. 多头注意力把 d_model 切成 h 份分别算，**总计算量**和单头一整块相比变了吗？为什么实践中仍偏好多头？
3. 因果掩码让权重变下三角——第 i 个 token 的 K/V 在生成后续 token 时是否会变？这正是 Day 8 KV Cache 省算力的根据，说说怎么省。
4. 复盘整个 Phase 1：从神经网络到量化，你最想下一步深挖的是哪块？把它记进 `notes.md` 的总复盘模板。

> 把答案记在 `notes.md`，填完 Phase 1 总复盘。明天进入 Phase 2 — LLM API 开发，前两周的原理就是你做架构决策的底气。

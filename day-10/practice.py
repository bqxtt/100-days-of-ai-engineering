"""
Day 10 实践日：只用 NumPy 拼一个单层「多头自注意力 block」(Multi-Head Self-Attention)。
把 Phase 1 全焊起来：embedding(D2) -> QKV(D3) -> 多头+缩放点积(D4) -> softmax(D1) -> 输出。

练习方式：先把 4 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，跑通即达标：
    uv run day-10/practice.py
"""
import numpy as np

np.random.seed(0)

# ---- 超参（mini 版，越小越看得清）----
seq_len   = 4    # 序列里 4 个 token
vocab     = 10   # 词表大小（来自 D6 tokenize）
d_model   = 8    # 每个 token 的向量维度（来自 D2 embedding）
n_heads   = 2    # 多头数（D4），d_head = d_model / n_heads = 4
d_head    = d_model // n_heads

# 一句话 4 个 token 的 id（D6: 文本 -> id）
tokens = np.array([1, 5, 2, 7])

# 可学习参数：embedding 表 + 四个投影矩阵。预训练(D7)就是在学这些数。
Emb = np.random.randn(vocab, d_model)                 # D2 词向量查表
Wq  = np.random.randn(d_model, d_model)
Wk  = np.random.randn(d_model, d_model)
Wv  = np.random.randn(d_model, d_model)
Wo  = np.random.randn(d_model, d_model)                # 多头拼回后的融合投影

def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)             # 减最大值防溢出（D1 的 softmax）
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)

def attention_block(tokens, causal=False):
    # 1) token id -> 向量：embedding 查表（D2）
    X = Emb[tokens]                                    # [seq, d_model]

    # 2) 线性投影出 Q/K/V（D3）：Q问、K答、V取
    Q = X @ Wq                                         # ★1 [seq, d_model]
    K = X @ Wk
    V = X @ Wv

    # 3) 拆成多头：[seq, d_model] -> [n_heads, seq, d_head]（D4）
    def split(t): return t.reshape(seq_len, n_heads, d_head).transpose(1, 0, 2)
    Qh, Kh, Vh = split(Q), split(K), split(V)

    # 4) 缩放点积注意力：scores = Q·Kᵀ / √d_head（每头并行）
    scores = Qh @ Kh.transpose(0, 2, 1) / np.sqrt(d_head)   # ★2 [n_heads, seq, seq]

    # 5) 可选因果掩码（D5）：上三角填 -inf，token 只能看左边
    if causal:
        mask = np.triu(np.ones((seq_len, seq_len)), k=1).astype(bool)
        scores = np.where(mask, -1e9, scores)

    # 6) softmax 成权重 -> 加权聚合 V（整个 Transformer 最重要的一步）
    weights = softmax(scores)                          # ★3 每行和为 1
    ctx = weights @ Vh                                 # [n_heads, seq, d_head]

    # 7) 多头拼回 + 输出投影
    ctx = ctx.transpose(1, 0, 2).reshape(seq_len, d_model)
    out = ctx @ Wo                                     # ★4 [seq, d_model]
    return out, weights

out, w = attention_block(tokens, causal=False)
print("输入 token:", tokens, " 形状:", out.shape, "(每个 token 得到一个新表示)")
print("每行权重和应为 1:", w.sum(-1).round(2).ravel())  # 全是 1.0 才对

out_c, w_c = attention_block(tokens, causal=True)
print("\n因果掩码下 head0 权重(下三角才对)：")
print(w_c[0].round(2))

# ============ 参考答案（应先自己写的 4 行）============
#   ★1  Q = X @ Wq          # K/V 同理：X @ Wk / X @ Wv
#   ★2  scores = Qh @ Kh.transpose(0,2,1) / np.sqrt(d_head)
#   ★3  weights = softmax(scores)
#   ★4  out = ctx @ Wo
# 看到 out 形状 (4, 8)、权重每行和=1、因果掩码权重呈下三角，就焊通了 Phase 1。

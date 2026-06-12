"""
Day 5 练习：只用 NumPy 手写「带 causal mask 的 self-attention」+「一步自回归采样」。
目标：亲眼看清 GPT 是怎么「只看左边、逐个吐字」的。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，跑出 mask 后下三角概率、生成 6 个 token 即达标：
    uv run day-5/practice.py
"""
import numpy as np

np.random.seed(0)


def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)        # 减最大值防溢出
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)


def causal_attention(X, Wq, Wk, Wv):
    """X:(T,d) -> 上下文向量:(T,d)。每个 token 只能看自己及左边（防偷看未来）。"""
    T, d = X.shape
    Q, K, V = X @ Wq, X @ Wk, X @ Wv             # 投影出 Query/Key/Value
    scores = Q @ K.T / np.sqrt(d)                # (T,T) 相关性打分
    # 上三角(未来位置)封死成 -∞：第 i 行只保留 j<=i
    mask = np.triu(np.ones((T, T)), k=1) * -1e9  # ★1 上三角=-1e9，下三角(含对角)=0
    scores = scores + mask
    attn = softmax(scores)                       # 每行只在左侧有权重，未来位置≈0
    return attn @ V, attn


# ---- 造一句 4 个 token 的假序列，d=8 ----
T, d = 4, 8
X = np.random.randn(T, d)
Wq, Wk, Wv = (np.random.randn(d, d) for _ in range(3))
ctx, attn = causal_attention(X, Wq, Wk, Wv)

print("causal mask 后的注意力矩阵（每行应=1，上三角≈0）：")
print(attn.round(2))
print("每行和：", attn.sum(1).round(2), "  上三角和(应≈0)：", round(np.triu(attn, 1).sum(), 4))

# ============ 一步自回归采样：拿最后一个 token 的分布选下一个词 ============
vocab = ["你", "好", "世", "界", "！", "?"]
np.random.seed(7)
emb = np.random.randn(len(vocab), d)             # 每个词的固定向量（迷你 embedding）
W_out = np.random.randn(d, len(vocab))           # 输出层：上下文向量 -> 词表打分

def step(seq_vec):
    """seq_vec:(t,d) 已生成的向量序列 -> 下一个 token 的索引 + 概率分布"""
    c, _ = causal_attention(seq_vec, Wq, Wk, Wv)
    logits = c[-1] @ W_out                        # ★2 只取最后一个位置预测下一词
    probs = softmax(logits)
    return int(np.argmax(probs)), probs           # 贪心采样：选概率最大的

print("\n自回归生成（每步把新 token 接回输入再算）：")
seq = emb[0:1].copy()                            # 从「你」这个 token 开始
out = ["你"]
for _ in range(5):
    idx, probs = step(seq)
    out.append(vocab[idx])
    seq = np.vstack([seq, emb[idx:idx+1]])         # ★3 把新 token 的向量接回序列，序列变长
print("生成序列：", " ".join(out))
print("末步分布：", {v: round(float(p), 2) for v, p in zip(vocab, probs)})
print("生成序列：", " ".join(out))

# ============ 参考答案（你应当先自己写的 3 行）============
#   ★1  mask = np.triu(np.ones((T, T)), k=1) * -1e9
#   ★2  logits = c[-1] @ W_out
#   ★3  seq = np.vstack([seq, emb[idx:idx+1]])
# 看到注意力矩阵上三角≈0、每行和=1，并能稳定吐出 6 个 token 就成功了。

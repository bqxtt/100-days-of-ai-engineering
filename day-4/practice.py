"""
Day 4 练习：只用 NumPy 手写 Multi-Head Attention + 正弦位置编码。
目标：把「512 怎么切成 8×64、8 个头怎么拼回来、位置指纹怎么算」每个张量形状摸清。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，断言全过即达标：
    uv run day-4/practice.py
"""
import numpy as np

np.random.seed(0)

# ---------- 超参数：经典论文配置缩小版 ----------
batch, seq, d_model, h = 2, 6, 512, 8     # 2 句、每句 6 token、向量 512 维、8 个头
d_head = d_model // h                       # 每个头管 64 维（512 = 8 * 64，关键省钱点）

def softmax(z):
    z = z - z.max(-1, keepdims=True)        # 减最大值防溢出
    e = np.exp(z)
    return e / e.sum(-1, keepdims=True)

# ========== 1. 正弦位置编码：给「无序」注意力补上语序 ==========
def positional_encoding(seq, d):
    pos = np.arange(seq)[:, None]                       # [seq,1]
    i   = np.arange(d)[None, :]                          # [1,d]
    angle = pos / np.power(10000, (2 * (i // 2)) / d)    # 每维不同频率
    pe = np.zeros((seq, d))
    pe[:, 0::2] = np.sin(angle[:, 0::2])                 # 偶数维用 sin
    pe[:, 1::2] = np.cos(angle[:, 1::2])                 # ★1 奇数维用 cos
    return pe

# ========== 2. 单头缩放点积注意力（Day 3 的螺丝）==========
def attention(Q, K, V):
    scores = Q @ K.transpose(0, 1, 3, 2) / np.sqrt(d_head)   # [B,h,seq,seq]
    w = softmax(scores)
    return w @ V, w

# ========== 3. 多头注意力：512 切成 8×64，并行后拼回来 ==========
def multi_head_attention(x, Wq, Wk, Wv, Wo):
    B, S, _ = x.shape
    def split(M):                                            # [B,S,512] -> [B,8,S,64]
        return (x @ M).reshape(B, S, h, d_head).transpose(0, 2, 1, 3)
    Q, K, V = split(Wq), split(Wk), split(Wv)
    out, w = attention(Q, K, V)
    out = out.transpose(0, 2, 1, 3).reshape(B, S, d_model)   # ★2 8 个头拼回 512
    return out @ Wo, w                                       # 最后一道投影 Wo

# ---------- 跑起来 ----------
x = np.random.randn(batch, seq, d_model)
pe = positional_encoding(seq, d_model)
x = x + pe                                                   # ★3 输入 = 词向量 + 位置编码
Wq = np.random.randn(d_model, d_model) * 0.02
Wk = np.random.randn(d_model, d_model) * 0.02
Wv = np.random.randn(d_model, d_model) * 0.02
Wo = np.random.randn(d_model, d_model) * 0.02
out, w = multi_head_attention(x, Wq, Wk, Wv, Wo)

print(f"输入 x          : {x.shape}")
print(f"切成多头 Q/K/V  : [B={batch}, h={h}, seq={seq}, d_head={d_head}]")
print(f"注意力权重 w    : {w.shape}  每个数=token 对 token 的关注度")
print(f"多头输出 out    : {out.shape}  拼回 d_model")
print(f"位置编码取值范围: [{pe.min():.2f}, {pe.max():.2f}]  应落在 [-1,1]")
print(f"位置0 与 位置1 编码是否不同: {not np.allclose(pe[0], pe[1])}")

assert out.shape == (batch, seq, d_model), "多头输出应回到 [B,seq,d_model]"
assert np.allclose(w.sum(-1), 1), "每行注意力权重应和为 1（softmax）"
assert pe.max() <= 1 and pe.min() >= -1, "位置编码应在 [-1,1]"
print("\n全部断言通过，Encoder 的两大组件你已手写一遍。")

# ============ 参考答案（被你应当先自己写的 3 行）============
#   ★1  pe[:, 1::2] = np.cos(angle[:, 1::2])
#   ★2  out = out.transpose(0,2,1,3).reshape(B, S, d_model)
#   ★3  x = x + pe
# 看到 out=[2,6,512]、权重每行和=1、PE∈[-1,1] 且位置两两不同就成功了。

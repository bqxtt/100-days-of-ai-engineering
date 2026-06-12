"""
Day 3 练习：只用 NumPy 手写一个 single-head Self-Attention。
目标：亲眼看清"QKV 投影 -> 缩放点积 -> softmax 加权 -> 输出"这条流水线。
核心直觉：每个 token 用自己的 Query 去问全场的 Key，按匹配度从 Value 里加权取信息。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，跑出权重矩阵每行和为 1 即达标：
    uv run day-3/practice.py
"""
import numpy as np

np.random.seed(0)

# 4 个 token、每个 8 维。把它当成一句话过了词嵌入后的结果。
seq_len, d_model = 4, 8
X = np.random.randn(seq_len, d_model)

# Q/K/V 三套投影矩阵，就是把同一份输入投影成"问句 / 索引 / 内容"三种身份。
d_k = 8                                  # 这里 head 维度=8，单头
Wq = np.random.randn(d_model, d_k)
Wk = np.random.randn(d_model, d_k)
Wv = np.random.randn(d_model, d_k)

def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)      # 减最大值防溢出
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)

# --- 1) 投影：同一份 X 生出 Q、K、V 三种身份 ---
Q = X @ Wq                               # 每个 token 的"查询" query
K = X @ Wk                               # 每个 token 的"键"   key
V = X @ Wv                               # 每个 token 的"值"   value

# --- 2) 点积相似度 + 缩放：Q 去匹配每个 K，越像分越高 ---
scores = Q @ K.T                         # (4,4)：第 i 行 = token i 对全场的打分
scores = scores / np.sqrt(d_k)           # ★1 除以 sqrt(d_k) 缩放，防止点积过大把 softmax 推到饱和

# --- 3) softmax 把每行分数变成"取多少"的权重，每行和为 1 ---
attn = softmax(scores)                   # ★2 沿最后一维做 softmax，得到注意力权重矩阵

# --- 4) 加权求和：按权重从 V 里取信息，得到每个 token 的新表示 ---
out = attn @ V                           # ★3 权重 @ 值 = 加权后的输出 (4,8)

print("注意力权重矩阵 attn（每行=该 token 分配给全场的注意力，和应为 1）：")
print(attn.round(2))
print("每行求和：", attn.sum(1).round(3), "（应全为 1）")
print("输出 out 形状：", out.shape, "（4 个 token，各 8 维新表示）")

# ============ 参考答案（被你应当先自己写的 3 行）============
#   ★1  scores = scores / np.sqrt(d_k)
#   ★2  attn = softmax(scores)
#   ★3  out = attn @ V
# 看到 attn 每行和=1、out 形状 (4,8) 就成功了——这就是一层 self-attention。

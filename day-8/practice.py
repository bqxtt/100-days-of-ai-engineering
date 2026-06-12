"""
Day 8 练习：只用 NumPy 模拟自回归推理，对比「有/无 KV Cache」的计算量。
目标：亲眼看清缓存把每步重算历史(n²)变成只算新token(n)，而结果完全一致。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，跑出两版token序列一致 + 省下>=90%算力即达标：
    uv run day-8/practice.py
"""
import numpy as np

np.random.seed(0)

D = 32                 # 每个 token 的向量维度
N = 64                 # 一共自回归生成多少个 token
Wq = np.random.randn(D, D) / D**0.5   # 把 token 投影成 Q
Wk = np.random.randn(D, D) / D**0.5   # 投影成 K
Wv = np.random.randn(D, D) / D**0.5   # 投影成 V

# 一次注意力 = Q 看所有 K 算权重(softmax) 再加权所有 V。flops 用矩阵规模近似计费。
def attention(Q, K, V):
    s = Q @ K.T / D**0.5
    w = np.exp(s - s.max(1, keepdims=True)); w /= w.sum(1, keepdims=True)
    flops = Q.shape[0] * K.shape[0] * D            # Q×K 这一步的近似计算量
    return w @ V, flops

# ---------- 无 KV Cache：每生成一步，把前面所有 token 重新算一遍 Q/K/V ----------
def gen_naive(seq):
    out, total = [], 0
    for n in range(1, N + 1):
        ctx = seq[:n]                              # 前 n 个 token 全量
        Q, K, V = ctx @ Wq, ctx @ Wk, ctx @ Wv     # ★1 整段重算 Q/K/V（这就是浪费）
        o, f = attention(Q, K, V)
        out.append(o[-1]); total += f + 3 * n * D * D
    return np.array(out), total

# ---------- 有 KV Cache：历史 K/V 存下来，只为新 token 算一次 ----------
def gen_cached(seq):
    out, total, Kc, Vc = [], 0, [], []
    for n in range(1, N + 1):
        tok = seq[n - 1:n]                          # 只取「新来的 1 个 token」
        q, k, v = tok @ Wq, tok @ Wk, tok @ Wv
        Kc.append(k[0]); Vc.append(v[0])           # ★2 把新 K/V 追加进 cache（append）
        o, f = attention(q, np.array(Kc), np.array(Vc))
        out.append(o[0]); total += f + 3 * D * D    # ★3 每步只算 1 个 token 的投影
    return np.array(out), total

seq = np.random.randn(N, D)                         # 假装这是 N 个已嵌入的 token
o1, c1 = gen_naive(seq)
o2, c2 = gen_cached(seq)

print(f"两版输出是否一致: {np.allclose(o1, o2)}  (缓存只省算力，不改结果)")
print(f"无缓存总计算量: {c1:,}  (随长度 ~n²)")
print(f"有缓存总计算量: {c2:,}  (随长度 ~n，线性)")
print(f"KV Cache 省下: {(1 - c2 / c1) * 100:.1f}% 计算量，序列越长省得越多")

# ============ 参考答案（被你应当先自己写的 3 行）============
#   ★1  Q, K, V = ctx @ Wq, ctx @ Wk, ctx @ Wv      # 无缓存每步整段重算
#   ★2  Kc.append(k[0]); Vc.append(v[0])            # 历史 K/V 进 cache 不再重算
#   ★3  total += f + 3 * D * D                      # 缓存版每步只算 1 个 token
# 看到「一致=True、省下 90%+」就成功了。

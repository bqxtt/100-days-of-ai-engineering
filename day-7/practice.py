"""
Day 7 练习：只用 NumPy 拟合 Scaling Law 的幂律曲线 loss ∝ N^-a。
目标：亲眼看到 "模型越大 loss 越低" 是一条幂律 —— 在 log-log 图上压成一条直线，
      并把斜率（指数 a）拟合出来，验证它接近论文里的 αN≈0.076。

练习方式：先把 2 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，跑出拟合指数 a≈0.076 即达标：
    uv run day-7/practice.py
"""
import numpy as np

np.random.seed(7)

# --- 造一组符合 Scaling Law 的"实验数据" ---
# 参数量 N 从 1e6 跨到 1e10，对数均匀采样（论文里横轴就是 log）
N = np.logspace(6, 10, 12)          # 12 个不同大小的模型
a_true, L0 = 0.076, 6.0             # 真实幂律指数、系数
loss = L0 * N ** (-a_true)          # 理想幂律：L = L0 * N^-a
loss *= 1 + 0.03 * np.random.randn(12)   # 加点观测噪声，更像真实跑出来的点

# --- 关键：幂律 L=L0*N^-a 取对数后变直线 ---
#     log L = log L0 - a * log N      →  线性回归就能拟出 a
x = np.log(N)
y = np.log(loss)
a_fit, b_fit = np.polyfit(x, y, 1)              # ★1 一阶最小二乘拟合 log-log 直线
a_hat = -a_fit                                  # 斜率取负就是幂律指数 a
L0_hat = np.exp(b_fit)

print(f"真实指数 a={a_true:.3f}   拟合指数 a={a_hat:.3f}   系数 L0≈{L0_hat:.2f}")

# --- 用拟合曲线外推：参数翻倍，loss 降多少？(边际递减，可预测) ---
ratio = 2 ** (-a_hat)                            # ★2 N 翻倍 → loss 乘 2^-a
print(f"参数翻倍后 loss 仅降到 {ratio*100:.1f}%（即下降约 {(1-ratio)*100:.1f}%）→ 边际递减")

# --- 看几个点：散点几乎压在拟合直线上 ---
print("\n  参数量N        实测loss   拟合loss")
for n, l in zip(N[::3], loss[::3]):
    print(f"  {n:9.2e}    {l:6.3f}     {L0_hat * n**-a_hat:6.3f}")

# ============ 参考答案（被你应当先自己写的 2 行）============
#   ★1  a_fit, b_fit = np.polyfit(x, y, 1)
#   ★2  ratio = 2 ** (-a_hat)
# 看到拟合指数 a≈0.076、实测loss≈拟合loss，就成功了：loss∝N^-a 是条直线。

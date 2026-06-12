"""
Day 9 练习：只用 NumPy 手写 float32 -> int8 量化 + 反量化，测量误差。
目标：亲眼看清"省一半/四分之三体积，只赔一点点精度"，并体会离群值的破坏。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，跑出误差对比即达标：
    uv run day-9/practice.py
"""
import numpy as np

np.random.seed(0)

# 造一段模拟权重：大多挤在 0 附近（正态），更像真实模型权重
W = np.random.randn(10000).astype(np.float32) * 0.1


def quantize(x, bits):
    """对称量化：浮点 -> 整数。scale 是唯一的"比例尺"。"""
    qmax = 2 ** (bits - 1) - 1                 # INT8=127, INT4=7
    scale = np.max(np.abs(x)) / qmax           # ★1 比例尺 = 最大绝对值 / 台阶数
    q = np.round(x / scale).clip(-qmax, qmax)  # 压进整数台阶，越界则截断
    return q.astype(np.int8), scale


def dequantize(q, scale):
    """整数 -> 近似浮点。"""
    return q.astype(np.float32) * scale        # ★2 反量化就是乘回 scale


def report(x, bits):
    q, scale = quantize(x, bits)
    xhat = dequantize(q, scale)
    err = np.abs(x - xhat)
    rel = err.mean() / (np.abs(x).mean() + 1e-9)
    print(f"INT{bits:<2d} | scale={scale:.5f} | 平均误差={err.mean():.5f} "
          f"| 相对误差={rel*100:5.2f}% | 体积={bits/16:.2f}x FP16")


print("=== 量化精度 vs 位数：INT8 几乎无损，INT4 误差陡增 ===")
report(W, 8)
report(W, 4)

print("\n=== 离群值的破坏：一个超大值撑大 scale，正常值精度被稀释 ===")
W2 = W.copy(); W2[0] = 5.0                      # ★3 注入一个离群值，scale 被它撑爆
report(W2, 8)
print("→ scale 变大后，原本 0 附近的权重误差明显上升，这正是 GPTQ/AWQ 的痛点")

# ============ 参考答案（应当先自己写的 3 行）============
#   ★1  scale = np.max(np.abs(x)) / qmax
#   ★2  return q.astype(np.float32) * scale
#   ★3  W2 = W.copy(); W2[0] = 5.0
# 看到 INT8 相对误差 < ~0.5%、INT4 明显更大、注入离群值后误差上升，就成功了。

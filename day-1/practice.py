"""
Day 1 练习：只用 NumPy 手写一个 2 层前馈网络 + 梯度下降。
目标：让 loss 真的下降，亲眼看清"加权求和 -> 激活 -> 算loss -> 反向更新"。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，跑出 loss 下降即达标：
    uv run day-1/practice.py
"""
import numpy as np

np.random.seed(0)

# 造一点假数据：学一个简单关系 y = (x1 AND x2)
X = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=float)
y = np.array([[0], [0], [0], [1]], dtype=float)

# 两层网络：2 -> 4 -> 1。W/b 就是要学的参数。
W1 = np.random.randn(2, 4); b1 = np.zeros((1, 4))
W2 = np.random.randn(4, 1); b2 = np.zeros((1, 1))

def relu(z):      return np.maximum(0, z)
def sigmoid(z):   return 1 / (1 + np.exp(-z))

lr = 0.5
for step in range(2000):
    # --- 前向：加权求和 + 激活 ---
    z1 = X @ W1 + b1
    a1 = relu(z1)
    pred = sigmoid(a1 @ W2 + b2)            # ★1 第二层加权求和后接 sigmoid 输出概率

    # --- 损失：均方误差 ---
    loss = np.mean((pred - y) ** 2)

    # --- 反向：链式求导，把误差摊到每个权重 ---
    d_pred = 2 * (pred - y) / len(X)
    d_z2 = d_pred * pred * (1 - pred)
    dW2 = a1.T @ d_z2;  db2 = d_z2.sum(0, keepdims=True)
    d_a1 = d_z2 @ W2.T
    d_z1 = d_a1 * (z1 > 0)
    dW1 = X.T @ d_z1;   db1 = d_z1.sum(0, keepdims=True)

    # --- 更新：W = W - lr * 梯度 ---
    W2 -= lr * dW2; b2 -= lr * db2
    W1 -= lr * dW1; b1 -= lr * db1          # ★2 ★3 同样的方式更新 W1 和 b1

    if step % 400 == 0:
        print(f"step {step:4d}  loss={loss:.4f}")

print("最终预测：", pred.round(2).ravel(), " 目标：", y.ravel())

# ============ 参考答案（被你应当先自己写的 3 行）============
#   ★1  pred = sigmoid(a1 @ W2 + b2)
#   ★2  W1 -= lr * dW1
#   ★3  b1 -= lr * db1
# 看到 loss 从 ~0.25 一路降到 0.01 以下、预测≈[0,0,0,1] 就成功了。

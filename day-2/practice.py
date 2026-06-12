"""
Day 2 练习：只用 NumPy 手算词向量的余弦相似度，并验证 king - man + woman ≈ queen。
目标：亲眼看清"语义 = 向量的方向"——意思近，夹角就小。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，跑出排名第一是 queen 即达标：
    uv run day-2/practice.py
"""
import numpy as np

# 7 个词的"迷你 embedding 表"（手工设计，4 维便于演示语义关系）
# 维度直觉： [是否王室, 性别(+男/-女), 是否动物, 大小]
vecs = {
    "king":  np.array([0.95,  0.90, 0.0, 0.7]),
    "queen": np.array([0.95, -0.90, 0.0, 0.6]),
    "man":   np.array([0.10,  0.90, 0.0, 0.6]),
    "woman": np.array([0.10, -0.90, 0.0, 0.5]),
    "cat":   np.array([0.00,  0.05, 0.95, 0.1]),
    "dog":   np.array([0.00,  0.10, 0.95, 0.3]),
    "lion":  np.array([0.05,  0.10, 0.90, 0.6]),
}

def cosine(a, b):                                  # ★1 余弦相似度 = 点积 / 模长之积
    return a @ b / (np.linalg.norm(a) * np.linalg.norm(b))

# --- 1) 语义近 → 相似度高；语义远 → 相似度低 ---
print("cat  vs dog  :", round(cosine(vecs["cat"], vecs["dog"]), 3), " 都是动物，应高")
print("cat  vs king :", round(cosine(vecs["cat"], vecs["king"]), 3), " 动物 vs 王室，应低")
print("king vs queen:", round(cosine(vecs["king"], vecs["queen"]), 3), " 都是王室，应中高")

# --- 2) 著名等式：国王 - 男人 + 女人 ≈ 女王 ---
target = vecs["king"] - vecs["man"] + vecs["woman"]   # ★2 减性别留王权，落点在女王

print("\nking - man + woman 的最近邻排名：")
ranks = []
for w, v in vecs.items():
    if w in ("king", "man", "woman"):   # 排除算式里用过的词
        continue
    ranks.append((w, cosine(target, v)))               # ★3 对每个候选词算相似度
ranks.sort(key=lambda x: x[1], reverse=True)
for w, s in ranks:
    print(f"  {w:6s} {s:.3f}")
print("=> 预测：", ranks[0][0], "（应为 queen）")

# ============ 参考答案（应当先自己写的 3 行）============
#   ★1  return a @ b / (np.linalg.norm(a) * np.linalg.norm(b))
#   ★2  target = vecs["king"] - vecs["man"] + vecs["woman"]
#   ★3  ranks.append((w, cosine(target, v)))
# 看到 cat-dog 高、cat-king 低、且 king-man+woman 最近邻=queen 就成功了。

"""
Day 16 练习：尽量"真连"本机 Ollama 跑多模态（带优雅降级，不联网不报错）。
把"图片如何进模型"串通三步，并在最后真发一次请求：
  1) NumPy 造小图 -> base64 编码 -> 拼出 Claude 多模态 messages（text + image block）
  2) 图按 patch 网格切分（ViT 直觉：patch = 视觉 token）
  3) 估算视觉 token 数（图越大越多 token，越贵越慢）
  4) 调本机 Ollama /api/chat：有 vision 模型就真发图，没有就跑文本模型讲解（优雅降级）

仅用标准库 + numpy，图像走 Ollama 的 messages[].images=[b64]（PNG 自带 zlib 生成，无需 Pillow）。
本机若无 vision 模型，请先：  ollama pull llava   （或 llava:7b / bakllava 等）。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
跑：  uv run day-16/practice.py   （无 vision 模型也能跑通，不报错）
"""
import base64
import json
import struct
import urllib.error
import urllib.request
import zlib

import numpy as np

np.random.seed(0)

OLLAMA = "http://localhost:11434"
VISION_HINTS = ("llava", "llama3.2-vision", "bakllava", "moondream", "minicpm-v", "qwen2-vl", "gemma3", "vision")

# ---------- 0) 造一张小图（8x8 灰度，越小越看得清）----------
H, W = 8, 8
img = (np.linspace(0, 255, H * W).reshape(H, W)).astype(np.uint8)   # 简单渐变图
raw = img.tobytes()                                                  # 原始字节流


def png_bytes(gray: np.ndarray) -> bytes:
    """把灰度 ndarray 编成最小可用 PNG（标准库 zlib，给 vision 模型能解码的真图）。"""
    h, w = gray.shape
    rows = b"".join(b"\x00" + gray[r].tobytes() for r in range(h))   # 每行前缀 filter=0
    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)              # 8bit, 灰度
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))

# ---------- 1) 图 -> base64 -> 多模态 messages ----------
png = png_bytes(img)
b64 = base64.b64encode(png).decode("ascii")                          # ★1 字节流 -> base64 字符串

messages = [{
    "role": "user",
    "content": [
        {"type": "text", "text": "describe this image"},            # 文字块：先给任务上下文
        {"type": "image", "source": {                                # 图像块：base64 方式
            "type": "base64", "media_type": "image/png", "data": b64,
        }},
    ],
}]
print("messages 含 %d 个 block：%s" % (
    len(messages[0]["content"]),
    [b["type"] for b in messages[0]["content"]]))
print("base64 长度 =", len(b64), "前 16 字符:", b64[:16], "...")

# ---------- 2) patch 切分：4x4 像素一块 -> 视觉 token ----------
P = 4
patches = []
for r in range(0, H, P):
    for c in range(0, W, P):
        patch = img[r:r+P, c:c+P]                                    # ★2 取出 PxP 的小方块
        patches.append(patch.flatten())                             # 拍扁成一个向量(=1个视觉token)
patches = np.stack(patches)                                          # [n_patch, P*P]
n_patch = patches.shape[0]
print(f"\n图 {H}x{W} 按 {P}x{P} patch -> {n_patch} 个视觉 token，每个维度 {patches.shape[1]}")

# ---------- 3) 估算视觉 token（Claude 经验值 ~ 宽*高/750）----------
est_tokens = (W * H) // 750 + n_patch                                # ★3 像素估算 + patch 数
print("视觉 token 估算 ≈", est_tokens, "（图越大越多，越贵越慢）")

print("\n直觉：图片 = 切成 patch 的一串 token，拼到文字 token 后面，进同一个 Transformer。")


# ---------- 4) 尽量真连本机 Ollama（优雅降级，永不抛错）----------
def list_models():
    try:
        req = urllib.request.Request(OLLAMA + "/api/tags")
        with urllib.request.urlopen(req, timeout=3) as r:
            return [m["name"] for m in json.load(r).get("models", [])]
    except (urllib.error.URLError, OSError, ValueError):
        return None  # 没装/没起


def ollama_chat(model, msgs):
    body = json.dumps({"model": model, "messages": msgs, "stream": False}).encode()
    req = urllib.request.Request(OLLAMA + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["message"]["content"]


print("\n========== 真连 Ollama（无则优雅降级）==========")
names = list_models()
if names is None:
    print("⚠️  本机 Ollama 未运行，跳过真发；patch/base64 演示已完成（达标）。")
    print("    想试：装 https://ollama.com 后 `ollama serve`，再 `ollama pull llava`。")
else:
    vision = next((n for n in names if any(h in n.lower() for h in VISION_HINTS)), None)
    if vision:
        # 真发图：Ollama 图像走 messages[].images=[b64]，与 Claude 的 image block 等价
        print(f"✅ 检测到 vision 模型 {vision}，真发图…")
        try:
            ans = ollama_chat(vision, [{"role": "user", "content": "describe this image",
                                        "images": [b64]}])
            print("模型看图回复：", ans.strip())
        except Exception as e:                                       # noqa: BLE001 演示稳健
            print("发图失败，降级文本：", e)
            vision = None
    if not vision:
        text = next((n for n in names if "qwen" in n.lower()), names[0])
        print(f"⚠️  无 vision 模型 → 优雅降级：用文本模型 {text} 讲解（patch/base64 已演示）。")
        print("    要真看图请：  ollama pull llava")
        try:
            ans = ollama_chat(text, [{"role": "user",
                "content": "一句话说清：8x8 灰度图按 4x4 patch 切成 4 块，"
                           "每块=1个视觉token，与文字token拼一起进 Transformer。"}])
            print("文本模型描述：", ans.strip())
        except Exception as e:                                       # noqa: BLE001
            print("文本调用失败（不影响达标）：", e)

# ============ 参考答案（应先自己写的 3 行）============
#   ★1  b64 = base64.b64encode(png).decode("ascii")
#   ★2  patch = img[r:r+P, c:c+P]
#   ★3  est_tokens = (W * H) // 750 + n_patch
# 看到 messages 有 2 个 block、8x8 图按 4x4 切出 4 个 patch、token 估算有数，就串通了。
# 有 llava 时还能看到模型真把图描述出来；没有就用文本模型讲解，全程不报错。

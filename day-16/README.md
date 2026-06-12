# Day 16 — 多模态 API：Vision 能力、图像理解、音频处理

> **阶段**：Phase 2 · Prompt Engineering 与 LLM API 开发
> **主题**：图像如何进模型（patch + embedding）、多模态 message 结构、Vision 用例、音频概览
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：前几天你把"文字进、文字出"的 API 玩熟了。今天只多一件事——**把图片塞进同一条 messages 里**。模型不会"看"像素，它把图片切成一堆小方块（patch）当成"额外的 token"，和文字 token 拼在一起送进同一个 Transformer。会拼 message block，你就会用 Vision 了。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器，零依赖）。一张图片在你眼里是"图"，在模型眼里是**一串 token**。页面演示：① 画/换一张小图 → ② 按 patch 网格切成方块 → ③ 每块拍扁成一个向量（embedding）→ ④ 拉成一条序列接到文字后面。看完你就明白：**图片对模型来说就是"更多 token"，所以 1 张图 ≈ 上千 token 的成本**。先玩后读，效果最好。

---

## 📖 学习内容（约 30 分钟）

### 1. 图像如何进模型：patch + embedding（核心直觉）

模型不直接吃像素。一张图先被切成固定大小的小方块（**patch**，比如 16×16 像素一块），每块拍扁成一个向量，过一层投影 → 一个 patch 就成了一个"视觉 token"。这是 **ViT（Vision Transformer）** 的核心思路。

```
1024×1024 图  →  切成 16×16 的 patch  →  64×64 = 4096 个 patch  →  4096 个视觉 token
文字 "describe this" → 2 个文字 token
两串拼一起 → 一起进同一个 Transformer，attention 让文字 token 去"看"图像 token
```

后端类比：图片不是新接口，而是被**序列化**成了和文字同构的 token 流。你之前学的 Day 3 Attention、Day 6 Tokenization，这里原样复用——只是 token 的来源从分词器换成了"切图器"。

> **成本直觉（要记牢）**：图越大、patch 越多、token 越多、越贵越慢。Claude 估算 `tokens ≈ (宽×高)/750`。所以 1568px 以上会被自动缩小——**上传前压到够用即可，别传原图**。

### 2. 多模态 message 结构：content 从"字符串"变"数组"

纯文本时 `content` 是一个字符串；多模态时 `content` 变成一个 **block 数组**，每个 block 有 `type`。常见两种：文字块和图像块。

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "这两张图有什么不同？"},
    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": "<base64...>"}},
    {"type": "image", "source": {"type": "url", "url": "https://example.com/b.jpg"}}
  ]
}
```

- **base64 方式**：本地图片读字节 → base64 编码塞进 `data`，自带不依赖外网（生产常用，注意 token 膨胀）。
- **url 方式**：给公网可访问链接，模型侧拉取（省你流量，但图片必须外网可达）。
- 一条 user 消息可塞**多张图 + 多段文字**，顺序就是模型读到的顺序——先文字铺背景再放图，往往效果更稳。

### 3. Vision 用例：能干什么

| 用例 | 说明 | 后端落地点 |
|---|---|---|
| 图像描述/打标 | 给图生成 caption、标签 | 内容审核、素材库自动归类 |
| OCR / 文档理解 | 读截图、发票、表格、手写 | 票据录入、合同抽取 |
| 图表/UI 理解 | 看懂折线图、读懂界面截图 | 报表问答、UI 自动化测试 |
| 视觉比对 | 多图找不同、判断一致性 | 质检、A/B 截图 diff |
| 视觉 + 结构化 | 看图直接吐 JSON（接 Day 15） | 把图片变成可入库的字段 |

实用守则：① 图清晰、别过曝；② 一次别堆太多图（4 张内最稳）；③ 让它输出结构化就配 Day 15 的 schema；④ 文字提示放在图**前面**给任务上下文。

### 4. 音频概览：Vision 之外的另一只眼

文本/视觉模型本身**不直接吃音频波形**，主流落地是"先转文字再喂 LLM"的两段式：

```
音频文件 → ASR/转写(Speech-to-Text，如 Whisper) → 文本 → LLM 处理 → (可选) TTS 文本转语音
```

- **STT（语音转文字）**：把会议录音/客服通话转成 transcript，再丢给 LLM 做摘要、提取待办。
- **TTS（文字转语音）**：LLM 出文本 → 合成语音，做播报/语音助手。
- **原生多模态**（如 GPT-4o 端到端音频）正在普及，但工程上**两段式最稳、最可控、最便宜**，建议默认从它起步。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Anthropic Vision 官方文档**（今天的主线，必读）— https://docs.anthropic.com/en/docs/build-with-claude/vision — 看 base64/url 两种 block 写法、尺寸与 token 估算、多图限制。
2. **ViT 论文《An Image is Worth 16×16 Words》** — https://arxiv.org/abs/2010.11929 — 一图切 patch 当 token 的开山之作，呼应模块 1。
3. **OpenAI Whisper（STT 起步）** — https://github.com/openai/whisper — 音频两段式里"先转文字"的经典开源选择。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯 Python + NumPy**。三步把今天串通：① 用 NumPy 造一张小图 → base64 编码 → 拼出 Claude 的多模态 `messages`；② 把图按 patch 网格切分；③ 估算视觉 token 数。完成 3 个 `★` 即达标，最后还会尝试真连本机 Ollama 发一次请求。

> **环境**：需本机 [Ollama](https://ollama.com)（`ollama serve`），可选拉一个 vision 模型 `ollama pull llava` 才能真看图；没装/没 vision 模型会优雅降级（用文本模型讲解或跳过），均能跑通不报错。

```bash
# 直接跑（依赖已装好；有 llava 真发图，没有则降级）：
uv run day-16/practice.py
```

预期：打印出含 `text` + `image` 两个 block 的 messages，patch 切分形状对得上（如 8×8 图按 4×4 patch → 4 块），token 估算合理。

---

## 🤔 思考题（边做边想）

1. 同一张图传 base64 vs 传 url，成本/延迟/隐私上各有什么取舍？生产里你怎么选？
2. patch 越小（视觉 token 越多）理解越细，但更贵更慢——这和你调"分页 size / 批量大小"的权衡像不像？
3. 让 Vision 直接吐 JSON（接 Day 15 schema）vs 先描述再二次解析，哪种更稳？为什么？
4. 音频为什么主流仍是"先转文字"两段式而非端到端？可控性、成本、可观测性上各赢在哪？

> 把答案记进 `notes.md`，Day 17 我们讲流式输出（SSE/WebSocket），让多模态结果边生成边返回。

# Day 33 — Multi-modal RAG：图片/PDF/表格混合文档

> **阶段**：Phase 3 · RAG 系统设计与实现
> **主题**：多模态文档的统一检索——把图片、PDF 版面、表格塞进同一个向量空间
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：真实文档从来不是纯文本——一份 PDF 里有标题、正文、配图、扫描表格。RAG 检索器（retriever）只认向量，向量只从文本来。所以今天的核心套路就一句：**先把一切非文本（图片、表格、版面）"翻译"成文本，再统一嵌入**——图转 caption、表格序列化、PDF 拆版面。后端味十足：这就是给异构数据做一次序列化（serialization）入库。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器，零依赖）。你会看到三种模态（图片 / PDF 段落 / 表格）原本各说各话，点「统一嵌入」后它们全被翻译成文本、投到**同一个向量空间**；输入一个问题向量，看检索器如何跨模态命中最近邻——图片和表格也能被一句话问出来。先玩后读，"混合文档统一检索"的直觉一眼到手。

---

## 📖 学习内容（约 30 分钟）

### 1. 多模态文档的挑战：检索器只认文本向量

线上一个 RAG（Retrieval-Augmented Generation）库里塞进来的真实文档长这样：扫描合同（图片）、季度财报（PDF 带版面）、价格表（表格）。问题是 **embedding 模型 + 向量库只吃文本**——一张图、一张表，你直接 `embed(图片字节)` 是行不通的（除非用专门的图文模型）。

| 模态 | 直接嵌入文本？ | 难点 |
|---|---|---|
| 段落文字 | ✅ 直接嵌 | 无 |
| 图片/扫描件 | ❌ | 信息在像素里，检索器看不见 |
| PDF | ⚠️ 半 | 版面（layout）混乱：双栏、页眉页脚、图表混排 |
| 表格 | ⚠️ 半 | 拍平成文本会丢行列结构，"哪行对哪列"全乱 |

**统一思路（今天的主线）**：不追求一个能吃所有模态的万能模型，而是把每种模态**各自翻译成一段文本**，再走同一条 `nomic-embed-text` 嵌入 → 同一个向量空间 → 同一套检索。异构进、同构出。

### 2. 图转 caption 嵌入（Image → Caption → Embedding）

图片没法直接嵌，那就先让它"开口说话"：用 vision 模型生成一段 caption（描述），把 caption 当文本嵌进库。检索时命中 caption，回答时把原图一并给生成模型。

```
图片 → [vision: llava/qwen2-vl] 生成 caption → 文本块 → nomic 嵌入 → 入库
                        ↑ 没 vision 模型？降级用图旁的文件名/alt/上下文当 caption
```

> **优雅降级（degrade）**：本机没 vision 模型很常见。降级策略：用图片的文件名、alt 文本、周边正文当"伪 caption"——检索照样跑通，只是细节少些。**永不因缺模型而崩**，这是生产 RAG 的底线。

### 3. PDF 版面解析（Layout Parsing）

PDF 不是文本流，是"画在纸上的盒子"。直接 `pdftotext` 会把双栏读串、把表格读烂。正经做法是**版面解析**：识别每个元素的类型（标题/正文/列表/图/表）和阅读顺序，按块（element）切，而不是按字符切。

```
PDF → [unstructured / 版面识别] → 元素列表：Title｜NarrativeText｜Table｜Image
     → 每个元素一个 chunk，带类型 metadata → 嵌入
```

按元素切的好处：标题不会被切碎、表格整块保留、图独立成块可单独转 caption。检索回来的 chunk 自带"我是表格/标题"的 metadata，下游能区别对待。

### 4. 表格检索（Table Retrieval）

表格直接拍平成一行字，行列关系全丢。套路是**序列化（serialize）成"自描述文本"**：每行展开成 `列名=值` 的句子，让每一行/整表变成一段语义完整、可嵌入的文本。

```
| 城市 | 人口 | GDP |       →  "城市=北京, 人口=2189万, GDP=4.0万亿"
| 北京 | 2189万 | 4.0万亿|     "城市=上海, 人口=2487万, GDP=4.7万亿"
| 上海 | 2487万 | 4.7万亿|
```

这样"上海人口多少"就能被向量检索命中，而不是被一堆数字噪声淹没。整表还可附一段 caption（"2024 一线城市人口与 GDP 表"）做粗检索。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Unstructured 官方文档**（今天的主线工具，必读）— https://docs.unstructured.io/open-source/introduction/overview — 看它怎么把 PDF/图片切成 Title/Table/Image 等元素，按版面解析后再喂 RAG。
2. **LlamaIndex《Multi-Modal RAG》指南** — https://docs.llamaindex.ai/en/stable/use_cases/multimodal/ — 图转 caption 嵌入 vs 统一多模态嵌入两条路线的工程对比。
3. **nomic-embed-text 模型卡** — https://ollama.com/library/nomic-embed-text — 今天嵌入用的模型，本地 `ollama pull nomic-embed-text` 即可，768 维。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯 Python 标准库**（不用 numpy）。把一份混合文档（1 张图 + 2 段 PDF 文本 + 1 张表）统一嵌入到同一向量空间，再真跑一次跨模态问答：① 图转 caption（有 vision 真生成、无则降级用上下文）② 表格序列化成自描述文本 ③ 全部走 `nomic-embed-text` 嵌入 ④ 问句向量做最近邻检索 ⑤ 把命中块喂 `qwen2.5:3b` 真生成答案。完成 3 个 `★` 即达标。

> **环境**：需本机 [Ollama](https://ollama.com)（`ollama serve`），并拉：`ollama pull nomic-embed-text` 和 `ollama pull qwen2.5:3b`。可选 `ollama pull llava` 才能真给图配字；没有 vision 模型会优雅降级（用上下文当 caption），仍能跑通不报错。

```bash
# cd 到项目根，依赖已装好，直接跑：
cd ~/projects/daily-learn && uv run day-33/practice.py
```

预期：打印 4 个 chunk 的模态与嵌入维度（768）、问"上海人口多少/合同金额"时检索命中对应表格/图 caption，最后 qwen2.5:3b 给出带来源的回答。

---

## 🤔 思考题（边做边想）

1. 图转 caption 嵌入 vs 用 CLIP 这类图文统一嵌入，两条路线在召回率、成本、可维护性上各有什么取舍？你的库里图多还是少，会怎么选？
2. 表格按"整表一块"嵌 vs "每行一块"嵌，对"查某一行" vs "问全表趋势"两类问题分别更有利？怎么折中？
3. 检索回来的 chunk 自带"我是表格/图/标题"的 metadata，生成阶段能怎么用？（提示：原图回填、表格重排版、引用标注）
4. 没 vision 模型就降级到文件名当 caption——这种降级会让哪类问题召回变差？生产里如何监控这种"静默退化"？

> 把答案记进 `notes.md`，Day 34 我们讲 RAG 生产化（缓存/增量更新/监控），正好接住"静默退化怎么监控"。

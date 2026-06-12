# Day 24 — 文本分块（下）：结构化文档、表格、图片处理

> **阶段**：Phase 3 · RAG 系统设计与实现
> **主题**：结构化文档（Markdown/HTML）按标题分块、表格序列化、图片用 caption、元数据保留
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：Day 23 把"一大段纯文本"切成块。但真实文档不是大段纯文本——是 README、API 文档、Confluence 导出的 HTML、带表格的财报、夹图的手册。这些文档的**结构本身就是语义**：标题告诉你"这块讲什么"，表格是二维数据，图片得用文字描述。今天学怎么**顺着结构切**而不是无脑切长度，把数据库主键、外键、JOIN 那套"保留结构"的本能用到分块上。

---

## 📖 学习内容（约 25 分钟）

### 模块 1：Markdown / HTML 按标题分块（结构 = 边界）

Day 23 的递归分块只会数字符。但 Markdown 的 `#`、`##` 和 HTML 的 `<h1>`、`<h2>` 已经把文档切好了——**标题就是天然的块边界**，比固定长度强得多：一个块 = 一个标题下的完整内容，语义自包含。

- **Markdown**：按 `#`(H1) / `##`(H2) / `###`(H3) 层级切，每块带上它的标题路径（如 `安装 > macOS`）。LangChain 的 `MarkdownHeaderTextSplitter` 就干这个：先按标题切，再对超长块用字符递归切。
- **HTML**：DOM 是棵树，`<h1>`/`<h2>`/`<table>`/`<img>` 是结构标签。`HTMLHeaderTextSplitter` 把每段正文挂到它最近的标题路径上。

> 类比：这就是后端的"按业务边界拆服务"，不是按代码行数拆。标题路径 ≈ 你给每条日志带的 trace_id——检索命中后能立刻知道它在文档哪一节。

### 模块 2：表格序列化（二维数据 → 一维可嵌入文本）

Embedding 模型只吃一维文本，但表格是二维的。直接把表格按行切碎会丢表头，块就变成无意义的 `3 | 上海 | 88`。两种序列化法：

| 方式 | 输出形态 | 适合 |
|---|---|---|
| Markdown 表格保留 | `\| 城市 \| 销量 \|\n\| 上海 \| 88 \|` | 整张小表当一块，结构清晰 |
| 行展开为句 | `城市=上海, 销量=88` | 大表逐行嵌入，每行自带列名 |

关键：**每个表格块都要带表头**。行展开法把"列名+值"拼成自然句，嵌入后检索"上海销量"才命中得了。整表保留法适合几十行的小表，让模型一眼看到全貌。

### 模块 3：图片用 caption（图 → 文字才能检索）

向量库存的是文本向量，图片本身不可嵌入。三种把图变文字的途径：

1. **alt / figcaption**：HTML 里 `<img alt="...">`、`<figcaption>` 现成的描述，最便宜。
2. **VLM 生成 caption**：用多模态模型（Day 16）生成"这张图讲了什么"，再嵌入这段文字。
3. **占位 + 引用**：块里留 `[图1: 架构图]` 占位，检索命中后回原文取图。

unstructured.io 这类库会把图当一个独立 element，连同它的 caption 入库——检索到 caption，回去取图。

### 模块 4：元数据保留（块的"户口本"）

切完一定要给每块带元数据：来源文件、标题路径、类型（正文/表格/图）、页码。这就是检索时的过滤条件和给用户看的出处。没有元数据的块 = 没主键的记录。

```
{ "text": "...", "source": "guide.md", "heading": "安装 > macOS", "type": "table", "page": 3 }
```

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **LangChain · MarkdownHeaderTextSplitter**（必看，本日 1:1 对应）— https://python.langchain.com/docs/how_to/markdown_header_metadata_splitter/
2. **LangChain · HTMLHeaderTextSplitter** — https://python.langchain.com/docs/how_to/HTML_header_metadata_splitter/
3. **Unstructured.io — 文档分区与表格/图片提取**（生产级处理 PDF/HTML 的事实标准）— https://docs.unstructured.io/open-source/core-functionality/partitioning
4. **Unstructured 表格抽取说明** — https://docs.unstructured.io/open-source/core-functionality/extracting-tables

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯 Python 标准库（无需 numpy、无需付费 key），真连本地 Ollama**：把一份带标题、表格、图片的 Markdown 文档，按标题层级切块 + 表格转文本 + 图片用 caption，每块带元数据，真嵌入入库，再做一次相似度检索。补齐多个 `★`，再对照文末答案。

```bash
# 先备好 Ollama（已装可跳过）：
ollama serve
ollama pull nomic-embed-text   # 嵌入模型（约 274MB）
ollama pull qwen2.5:3b         # 生成模型（约 1.9GB）
# 真跑：
cd /Users/zqr/projects/daily-learn && uv run day-24/practice.py
```

预期：文档被切成多个带"标题路径+类型"的块（表格序列化为文本、图片用 caption），问"上海销量是多少"能检索到那张销量表的块，最后 qwen2.5:3b 据此答出 88。

### 🎨 可视化

双击 `visualize.html`（纯浏览器、深色），把一份 Markdown 文档实时解析成"结构化分块树"——标题嵌套、表格块、图片块各有标记，看清"顺着结构切"长什么样。

---

## 🤔 思考题（边做边想）

1. 同一个标题下内容超长，仍得二次切——这时标题路径要怎么"复制"给每个子块？为什么不能丢？
2. 表格行展开 vs 整表保留，对召回率和给模型的 token 量各有什么取舍？50 行的表你选哪个？
3. 图片只存 caption，检索准不准取决于 caption 质量——这把皮球踢给了谁？VLM caption 失真了会怎样？
4. 元数据里的 `source`、`heading`、`page` 在最终回答里能干嘛？和你后端给接口返回 traceId 的动机像不像？

> 把答案记进 `notes.md`。明天 Day 25 学检索策略：向量检索 + 关键词 + Hybrid Search。

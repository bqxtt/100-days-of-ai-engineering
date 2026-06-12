# Day 6 — Tokenization 深入：BPE、SentencePiece、tiktoken

> **阶段**：Phase 1 · 大模型核心原理
> **主题**：分词（Tokenization）的原理与实践——BPE、SentencePiece、tiktoken、token 计费
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：模型不认识文字，只认识整数 ID。分词器（tokenizer）就是文字和整数之间的"序列化协议"——和你把 JSON 编码成字节流一模一样。今天搞懂这把"尺子"是怎么造的、为什么按它收钱。

---

## 📖 学习内容（约 30 分钟）

### 1. 为什么要分词：模型只吃整数

GPT 的输入不是字符串，是一串整数 ID。所以任何文字都要先**编码（encode）**成 `[1234, 567, 89]`，模型输出后再**解码（decode）**回文字。问题是：怎么切？三种朴素方案都不行：

| 切法 | 问题 | 后端类比 |
|---|---|---|
| 按**词**切 | 词表爆炸，没见过的词直接 OOV（out-of-vocab） | 枚举所有可能字段，一来新字段就崩 |
| 按**字符**切 | 序列太长，"international"= 13 个 token，浪费算力 | 把所有数据按单字节存，没有压缩 |
| 按**字节**切 | 同上，太碎 | 同上 |

**subword（子词）** 是折中：高频词整块成一个 token，生僻词拆成几块。`tokenization` 可能被切成 `token` + `ization`。这样词表可控（约 5 万–10 万），又永不 OOV。

### 2. BPE 合并算法直觉：高频组合就建索引

**BPE（Byte Pair Encoding）** 本是个压缩算法，1994 年提出，2015 被搬到 NLP。核心一句话：**反复把语料里出现最多的相邻字符对，合并成一个新 token**。

```
初始：  l o w   l o w   l o w e r          每个字符是一个 token
统计：  最高频相邻对是 'l'+'o' (出现 4 次) -> 合并成 'lo'
再统计：'lo'+'w' 最高频          -> 合并成 'low'
再统计：'low' 已成一块；下一个高频是 'e'+'r' -> 'er' ...
```

每合并一次，词表 +1，序列变短一点。合并几万次就停——这几万条**合并规则**就是词表。后端直觉：**热点组合值得建索引**。高频 SQL 建索引、热点接口加缓存，BPE 是给高频字符串建"专属 token"。你今天的 `practice.py` 手写的就是这套：统计 bigram → 合并最高频 → 重复。

### 3. SentencePiece vs tiktoken：两套工业实现

- **SentencePiece**（Google）：语言无关，**不依赖空格分词**（中文/日文没空格也能切），训练自己的词表，BERT/T5/LLaMA 系用它。BPE 和 Unigram 两种算法都支持。
- **tiktoken**（OpenAI）：GPT 系用的 **byte-level BPE**——先把文字转 UTF-8 字节再做 BPE，所以**任何字符都不会 OOV**（最差也能拆到单字节），且超快（Rust 内核）。GPT-4 用 `cl100k_base`，GPT-4o 用 `o200k_base`。
- 中文要点：一个汉字 UTF-8 是 3 字节，常被切成 1–2 个 token。**同样字数，中文比英文更费 token**，这直接影响成本和上下文窗口。

### 4. token 计费意义：为什么按 token 收钱

API 按 token 数计费、上下文窗口按 token 算上限、速率限制（TPM）也按 token。所以 token = LLM 的"流量单位"。工程影响：① 估算成本要先 `count_tokens()` 而不是 `len(string)`；② 中文别按字符估；③ prompt 模板里塞的每个固定前缀都在持续花钱；④ 上下文 8K/128K 指的是 token 不是字。**会算 token = 会算 LLM 的电费。**

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **tiktoken（OpenAI 官方分词库）** — https://github.com/openai/tiktoken — 看 README 三行代码 `encode/decode`，理解 byte-level BPE 在工程里长什么样；想直接玩可视化用官方 https://platform.openai.com/tokenizer
2. **Hugging Face — Tokenizer 教程（官方文档）** — https://huggingface.co/docs/tokenizers/index 与课程 https://huggingface.co/learn/nlp-course/chapter6/5 — BPE/WordPiece/Unigram 三种算法逐步图解。
3. **BPE 原始论文《Neural Machine Translation of Rare Words with Subword Units》(Sennrich 2015)** — https://arxiv.org/abs/1508.07909 — subword 的奠基论文，10 页，看摘要+算法图即可。
4. **Karpathy《Let's build the GPT Tokenizer》** — https://www.youtube.com/watch?v=zduSFxRajkE — 2 小时从零手写 tiktoken 级别 BPE，后端味十足（选看）。

---

## 💻 动手练习（约 15 分钟）

打开 `practice.py`，**纯 Python 零依赖**手写一个 BPE 训练器：统计相邻 bigram → 反复合并最高频 → 长出词表，再用规则切没见过的新词。先补 3 个 `★` 行，再对答案。

```bash
# 项目用 uv 管理环境，直接跑：
uv run day-6/practice.py
```

预期：看到合并日志依次并出 `low</w>`、`est</w>`、`newest</w>`，最后切 `wildest`（没训练过）也能靠 subword 拼出来不 OOV，今天就达标。

### 🎨 可视化（先玩这个再读理论，更直观）

双击打开 `visualize.html`（纯浏览器，无需安装）。一个 **Tokenizer Playground**：输入任意中英文，实时高亮切分出的 token、统计 token 数，并按 GPT-4o 价格估算成本——亲手对比"同样意思中文比英文贵多少 token"。

---

## 🤔 思考题（边做边想）

1. 为什么 byte-level BPE 能保证"永不 OOV"？它和按字符切相比，序列长度上赢在哪？
2. 同样一句话用中文写比英文 token 多 2–3 倍。这对你设计中文 RAG 的 chunk 大小、上下文预算有什么影响？
3. 分词器是和模型一起训练并固定的——如果换了 tokenizer，旧权重还能用吗？为什么微调一般不动它？
4. 你的 prompt 模板里每次都带 500 字固定前缀，QPS 1000，按 GPT-4o 输入价估算一天烧多少钱？

> 把答案随手记在 `notes.md`，明天 Day 7 我们接着讲预训练范式与 Scaling Laws。

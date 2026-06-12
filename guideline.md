# AI 全栈工程师系统学习计划

> 学习者背景：后端开发工程师 | AI基础：了解 Transformer、Prompt Engineering，用过一些 API
> 目标：从原理到应用全面提升，成为 AI 领域的全栈工程师
> 每日学习时间：约 1 小时 | 起始日期：2026-04-23
> 总计：20 周（约 100 个工作日）

---

## Phase 1: 大模型核心原理（第 1-2 周 | Day 1-10）

这一阶段的目标是从底层理解大语言模型的工作原理，而不仅仅停留在"会用API"的层面。作为后端工程师，理解底层机制能帮助你在后续的应用开发中做出更好的架构决策。

- **Day 1** — 神经网络基础回顾：前馈网络、激活函数、反向传播的直觉理解
- **Day 2** — 词嵌入与语言建模：从 Word2Vec 到语言模型的概率视角
- **Day 3** — Attention 机制深入：Self-Attention 的数学推导与直觉
- **Day 4** — Transformer 架构（上）：Encoder 结构、Multi-Head Attention、位置编码
- **Day 5** — Transformer 架构（下）：Decoder 结构、GPT 系列演进路线
- **Day 6** — Tokenization 深入：BPE、SentencePiece、tiktoken 的原理与实践
- **Day 7** — 预训练范式：BERT vs GPT、自监督学习、Scaling Laws
- **Day 8** — 大模型推理原理：KV Cache、Speculative Decoding、推理优化
- **Day 9** — 模型量化基础：INT8、GPTQ、AWQ、量化对性能的影响
- **Day 10** — 🏗️ 实践日：手写一个简化版 Attention 机制（Python 实现）

## Phase 2: Prompt Engineering 与 LLM API 开发（第 3-4 周 | Day 11-20）

这一阶段聚焦于如何高效地与大模型交互，掌握 API 开发的方方面面。这是将 AI 能力集成到后端系统中的核心技能。

- **Day 11** — LLM API 基础：Chat Completions API、参数详解（temperature, top_p 等）
- **Day 12** — Prompt Engineering 核心技巧：Zero/Few-shot、Chain of Thought
- **Day 13** — 高级 Prompt 技巧：Self-Consistency、Tree of Thoughts、ReAct
- **Day 14** — Function Calling / Tool Use：让模型调用外部工具
- **Day 15** — Structured Output：JSON Mode、Schema 约束、输出格式控制
- **Day 16** — 多模态 API：Vision 能力、图像理解、音频处理
- **Day 17** — 流式输出与实时交互：SSE、WebSocket 集成模式
- **Day 18** — Prompt 模板管理：版本控制、A/B 测试、评估框架
- **Day 19** — 生产化考量：成本优化、速率限制、错误处理、重试策略
- **Day 20** — 🏗️ 实践日：构建一个带 Tool Use 的智能命令行助手

## Phase 3: RAG 系统设计与实现（第 5-7 周 | Day 21-35）

RAG（检索增强生成）是当前最实用的 AI 应用模式之一。这一阶段将从零到一掌握 RAG 系统的完整链路。

- **Day 21** — Embedding 原理：文本向量化、语义相似度的本质
- **Day 22** — 向量数据库：Chroma、Pinecone、Milvus 对比与选型
- **Day 23** — 文本分块策略（上）：固定大小、语义分块、递归分块
- **Day 24** — 文本分块策略（下）：结构化文档处理、表格与图片
- **Day 25** — 检索策略：向量检索、关键词检索、Hybrid Search
- **Day 26** — Reranking 机制：Cross-Encoder、Cohere Rerank
- **Day 27-28** — 基础 RAG Pipeline 实现：从文档加载到问答的完整链路
- **Day 29** — 高级 RAG 模式（上）：Query Transformation、HyDE
- **Day 30** — 高级 RAG 模式（下）：Self-RAG、CRAG、Adaptive RAG
- **Day 31** — Multi-hop RAG：多跳推理、知识图谱增强
- **Day 32** — RAG 评估体系：Faithfulness、Relevancy、RAGAS 框架
- **Day 33** — Multi-modal RAG：处理图片、PDF、表格混合文档
- **Day 34** — RAG 生产化：缓存策略、增量更新、监控告警
- **Day 35** — 🏗️ 实践日：构建一个可用的个人知识库问答系统

## Phase 4: AI Agent 开发（第 8-11 周 | Day 36-55）

Agent 是 AI 应用的高级形态，也是 2025-2026 年最热门的方向。这一阶段将深入 Agent 的设计模式与工程实践。

- **Day 36** — Agent 概念与架构模式：ReAct、Plan-and-Execute、Reflection
- **Day 37** — LangChain 核心概念：Chain、Memory、Tool、Agent 模块
- **Day 38** — LangGraph 入门：图状态机、节点与边、条件路由
- **Day 39** — LangGraph 进阶：Human-in-the-loop、持久化状态
- **Day 40** — Tool 设计原则：如何为 Agent 设计好用的工具
- **Day 41** — Memory 系统设计：短期记忆、长期记忆、摘要记忆
- **Day 42-43** — 单 Agent 系统实战：构建一个代码分析 Agent
- **Day 44** — Multi-Agent 架构：协作模式、委托模式、竞争模式
- **Day 45** — CrewAI / AutoGen 框架对比与实践
- **Day 46** — MCP（Model Context Protocol）：理解 MCP 协议
- **Day 47** — MCP 实践：开发自定义 MCP Server
- **Day 48** — Agent 的可观测性：日志、追踪、LangSmith
- **Day 49** — Agent 安全性：Prompt Injection 防御、输出验证、权限控制
- **Day 50-51** — Agent 评估：如何系统化测试 Agent 的能力
- **Day 52-53** — Multi-Agent 实战：构建一个开发团队模拟系统
- **Day 54** — Agent 生产化部署：容错、扩展、成本控制
- **Day 55** — 🏗️ 实践日：Agent 系统回顾与优化

## Phase 5: 模型微调与训练（第 12-14 周 | Day 56-70）

作为全栈 AI 工程师，你需要具备微调模型的能力，以应对通用模型无法满足的特定场景。

- **Day 56** — 微调概述：为什么需要微调、全量微调 vs 参数高效微调
- **Day 57** — LoRA 原理深入：低秩适配、秩的选择、适配层设计
- **Day 58** — QLoRA 与量化微调：4-bit 量化 + LoRA 的高效训练
- **Day 59** — 训练数据准备：数据收集、清洗、格式化的最佳实践
- **Day 60** — Hugging Face 生态：Transformers、Datasets、PEFT 库
- **Day 61-62** — 微调实战（上）：使用 LoRA 微调一个对话模型
- **Day 63** — RLHF 与 DPO：人类偏好对齐的原理与实践
- **Day 64** — 模型评估：Benchmark 体系、人工评估、自动评估
- **Day 65** — 模型合并技术：Model Merging、MoE 的直觉理解
- **Day 66-67** — 模型部署：vLLM、TGI、Ollama 部署方案对比
- **Day 68** — 模型服务化：API 设计、负载均衡、Auto-scaling
- **Day 69** — 持续微调：数据飞轮、增量训练、灾难性遗忘
- **Day 70** — 🏗️ 实践日：端到端完成一次模型微调与部署

## Phase 6: AI 应用架构与工程化（第 15-17 周 | Day 71-85）

将前面学到的所有技能串联起来，聚焦于构建生产级 AI 应用的架构设计与工程实践。

- **Day 71** — AI 应用架构总览：常见架构模式与选型决策
- **Day 72** — 后端集成模式：AI 能力如何融入现有后端系统
- **Day 73** — 异步任务处理：长时间 AI 任务的队列设计
- **Day 74** — 缓存与语义缓存：减少 API 调用、提升响应速度
- **Day 75** — 对话系统设计：会话管理、上下文窗口优化
- **Day 76** — 多租户 AI 系统：隔离、配额、个性化配置
- **Day 77** — AI Gateway 设计：路由、限流、模型切换、Fallback
- **Day 78** — 可观测性体系：LLM 调用追踪、成本监控、质量指标
- **Day 79** — A/B 测试与灰度发布：AI 功能的渐进式发布
- **Day 80** — 安全与合规：数据隐私、内容审核、合规要求
- **Day 81-82** — 全栈 AI 应用实战（上）：需求分析与架构设计
- **Day 83-84** — 全栈 AI 应用实战（下）：核心功能开发
- **Day 85** — 🏗️ 实践日：完成一个生产级 AI 应用 MVP

## Phase 7: 前沿方向与持续进化（第 18-20 周 | Day 86-100）

最后一个阶段探索前沿方向，建立持续学习的能力和框架。

- **Day 86** — 多模态模型发展：GPT-4o、Gemini、多模态融合趋势
- **Day 87** — AI 代码生成：Copilot、Cursor 背后的技术原理
- **Day 88** — AI 搜索引擎：Perplexity 模式、搜索增强生成
- **Day 89** — 小模型与端侧部署：SLM、Edge AI、模型压缩
- **Day 90** — AI 硬件与基础设施：GPU 生态、推理芯片、云服务选型
- **Day 91** — Reasoning 模型：o1/o3、DeepSeek-R1 的推理范式
- **Day 92** — 世界模型与具身智能：Sora、机器人基础模型
- **Day 93** — AI 产品设计：如何设计好的 AI 用户体验
- **Day 94** — 开源生态深度：Meta Llama、Mistral、Qwen 系列解读
- **Day 95** — AI 创业与商业模式：AI-Native 产品的机会
- **Day 96-98** — 毕业项目：选择一个感兴趣的方向，完成一个完整项目
- **Day 99** — 项目展示与复盘
- **Day 100** — 🎓 学习总结、知识体系梳理、后续学习路径规划

---

## 学习原则

1. **理论与实践交替**：每个知识点都配合动手实践，不做纯理论学习
2. **循序渐进**：每个阶段都建立在前一阶段的基础之上
3. **实践驱动**：每个阶段末尾都有综合实践项目
4. **持续回顾**：定期回顾和巩固之前的学习内容
5. **灵活调整**：根据学习进度和反馈动态调整难度和节奏

## 每日任务格式

每个工作日 10:30，你将收到当天的学习任务，包括：
- 📖 **学习内容**：当天需要理解的核心概念
- 🔗 **推荐资源**：精选的学习材料（文章、视频、论文）
- 💻 **动手练习**：实际编码或实验任务
- 🤔 **思考题**：帮助深化理解的问题

## 课程内容标准模板（每个 day-x 文件夹四件套）

每节课用 `day-x/` 文件夹存放，固定包含以下四个文件：

1. **README.md** — 主课程，含四个模块：📖 学习内容 / 🔗 推荐资源 / 💻 动手练习 / 🤔 思考题。
   面向后端工程师：多用工程类比，控制在约 1 小时；保持中文 + 英文术语；不做深度数学推导。
2. **practice.py** — 可独立运行的小练习（`uv run day-x/practice.py`），关键行用 `★` 标注，文末注释保留参考答案。
3. **visualize.html** — 单文件、纯 canvas、零依赖，把当天核心概念做成可交互演示，双击即玩。
4. **notes.md** — 笔记 + 思考题作答模板。

**环境**：项目根用 uv 统一管理（`pyproject.toml` / `.venv`），新依赖用 `uv add`。
**资源链接**必须为真实可访问 URL。每天可视化页面优先于理论，让学习者先玩后读。

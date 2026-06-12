# 100 Days of AI Engineering · AI 全栈工程师 100 天

> A self-paced, hands-on curriculum that takes a **backend engineer** from neural-network fundamentals to production **LLM / RAG / Agent** systems — ~1 hour/day for 100 days.
>
> 面向**后端工程师**的大模型全栈进阶课:从神经网络原理一路到 RAG、Agent、微调与工程化,每天约 1 小时,共 100 天。

每节课双语(中文 + 英文术语),重直觉、轻数学,所有动手练习真连本地 **[Ollama](https://ollama.com)** 跑通,不用付费 API、不靠离线 mock。

## Why this exists

市面上的 AI 课要么停在"会调 API",要么一上来就是数学推导。这套课用**后端工程师听得懂的类比**(状态机、路由表、缓存、RBAC、熔断…)把原理讲透,每天配一个能跑的 `practice.py` 和一个零依赖可视化页,先玩后读。

## Roadmap

| Phase | 主题 | Days | 状态 |
|---|---|---|---|
| 1 | 大模型核心原理 (NN / Transformer / Tokenizer / 推理优化) | 1–10 | ✅ |
| 2 | Prompt Engineering 与 LLM API 开发 | 11–20 | ✅ |
| 3 | RAG 系统设计与实现 (embedding / 检索 / rerank / 评估) | 21–35 | ✅ |
| 4 | AI Agent 开发 (ReAct / LangGraph / MCP / Multi-Agent) | 36–55 | ✅ |
| 5 | 模型微调与训练 (LoRA / QLoRA / RLHF / 部署) | 56–70 | ⏳ |
| 6 | AI 应用架构与工程化 | 71–85 | ⏳ |
| 7 | 前沿方向与持续进化 | 86–100 | ⏳ |

完整大纲见 [`guideline.md`](guideline.md)。

## Each lesson = four files

每个 `day-x/` 文件夹固定四件套:

| 文件 | 作用 |
|---|---|
| `README.md` | 主课:📖 学习内容 · 🔗 推荐资源 · 💻 动手练习 · 🤔 思考题 |
| `practice.py` | 可独立运行的练习,关键行 `★` 标注,文末留参考答案 |
| `visualize.html` | 单文件纯 canvas 零依赖交互演示,双击即玩 |
| `notes.md` | 笔记 + 思考题作答模板 |

## Quick start

```bash
git clone https://github.com/bqxtt/100-days-of-ai-engineering.git
cd 100-days-of-ai-engineering

uv sync                          # 环境(numpy)
uv run day-1/practice.py         # 跑某天练习
open day-1/visualize.html        # 看可视化

# LLM / RAG / Agent 练习需本地 Ollama:
ollama pull qwen2.5:3b           # 对话 / Agent / 工具调用
ollama pull nomic-embed-text     # 嵌入(RAG)
uv run day-36/practice.py        # 真连 ollama 的 ReAct agent
```

纯数学日 (Day 1–10) 仅用 numpy,可离线;其余真连 Ollama,`OLLAMA_MODEL` 可覆盖默认模型。

## Tech stack

`Python 3.12` · `uv` · `numpy` · `Ollama (qwen2.5 / nomic-embed-text)` · `纯 stdlib 手写 agent`(不绑 LangChain/CrewAI,先讲清原理)· `vanilla canvas` 可视化

## License

MIT

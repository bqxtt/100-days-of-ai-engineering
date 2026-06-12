# 100 Days of AI Engineering

> **English** · [中文](README.md)

> A self-paced, hands-on curriculum that takes a **backend engineer** from neural-network fundamentals to production **LLM / RAG / Agent** systems — about 1 hour a day for 100 days.

Every lesson is intuition-first and light on math. All exercises run against a local **[Ollama](https://ollama.com)** instance — no paid API, no offline mocks.

## Why this exists

Most AI courses either stop at "you can call an API" or open with dense math. This one explains the internals with analogies a backend engineer already knows — state machines, routing tables, caches, RBAC, circuit breakers — and pairs every day with a runnable `practice.py` and a zero-dependency visualization you can open and play with first.

## Roadmap

| Phase | Topic | Days | Status |
|---|---|---|---|
| 1 | LLM fundamentals (NN / Transformer / tokenizer / inference) | 1–10 | ✅ |
| 2 | Prompt engineering & LLM API development | 11–20 | ✅ |
| 3 | RAG systems (embedding / retrieval / rerank / eval) | 21–35 | ✅ |
| 4 | AI agents (ReAct / LangGraph / MCP / multi-agent) | 36–55 | ✅ |
| 5 | Fine-tuning & training (LoRA / QLoRA / RLHF / serving) | 56–70 | ⏳ |
| 6 | AI application architecture & engineering | 71–85 | ⏳ |
| 7 | Frontiers & continuous learning | 86–100 | ⏳ |

Full outline: [`guideline.md`](guideline.md).

## Each lesson = four files

Every `day-x/` folder ships the same four-file set:

| File | Purpose |
|---|---|
| `README.md` | Lesson: concepts · resources · exercise · reflection |
| `practice.py` | Standalone runnable exercise; key lines marked `★`, answers at the bottom |
| `visualize.html` | Single-file canvas demo, zero dependencies — double-click to play |
| `notes.md` | Note-taking + reflection template |

## Quick start

```bash
git clone https://github.com/bqxtt/100-days-of-ai-engineering.git
cd 100-days-of-ai-engineering

uv sync                          # set up env (numpy)
uv run day-1/practice.py         # run a day's exercise
open day-1/visualize.html        # open the visualization

# LLM / RAG / Agent days need a local Ollama:
ollama pull qwen2.5:3b           # chat / agent / tool calls
ollama pull nomic-embed-text     # embeddings (RAG)
uv run day-36/practice.py        # ReAct agent over real Ollama
```

Days 1–10 (pure math) use numpy only and run offline; the rest call Ollama. Override the model with `OLLAMA_MODEL`.

## Tech stack

`Python 3.12` · `uv` · `numpy` · `Ollama (qwen2.5 / nomic-embed-text)` · agents hand-written in pure stdlib (no LangChain/CrewAI lock-in — internals first) · vanilla-canvas visualizations.

## License

MIT

# Day 37 — LangChain 核心概念：Chain、Memory、Tool、Agent 模块

> **阶段**：Phase 4 · AI Agent 开发（第 8 周 · Day36-55）
> **主题**：拆穿 LangChain 四大模块——Chain（链）/ Memory（记忆）/ Tool（工具）/ Agent（智能体），看清它们就是你天天写的后端模式
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：LangChain 不是黑魔法。Day36 你画了 Agent 架构图，今天就把它落成四块积木——而这四块全是你熟的：Chain=函数串联（pipeline），Memory=会话历史 list（session），Tool=函数注册表（dispatch table），Agent=ReAct 循环（while+if）。学完你会知道：装不装 LangChain，套路都一样，它只是替你把胶水代码封装好。

---

## 📖 学习内容（约 25 分钟）

### 0. 为什么先手写、不直接装 LangChain
Day36 你知道了 Agent = LLM + 工具 + 循环。今天本该上 LangChain，但它依赖重、API 改得勤，新手容易陷在装包和调版本里，反而看不清"它到底帮我做了什么"。所以今天**不装包**，用 100 行 stdlib 自己捏出四大模块，你会发现 LangChain 的每个抽象都对得上一个后端老套路。下次再看官方文档，全是"哦原来就这样"。

| LangChain 模块 | 它的本质 | 后端类比 |
|---|---|---|
| **Chain** | 几个步骤按顺序串起来 | pipeline / 函数 compose |
| **Memory** | 一个对话历史 list | session / 上下文存储 |
| **Tool** | 名字 → 函数的映射 | dispatch table / 路由表 |
| **Agent** | 模型自己决定调哪个工具、循环到出答案 | while + if/else 状态机 |

### 1. Chain：步骤串联，LCEL 的 `|` 就是 compose
一条链 = 把多个步骤接龙。最经典三段：**prompt 模板 → 模型 → 解析器**。LangChain 用 LCEL（LangChain Expression Language）写成 `prompt | model | parser`——那个竖线就是函数组合，`f3(f2(f1(x)))`。后端类比：你的中间件链、ETL 的 `extract→transform→load`，一模一样。`practice.py` 里 `chain()` 就是把模板、调模型、去空白三个函数串成一条，没有任何魔法。

### 2. Memory：模型本无记忆，是你把历史拼回去
LLM 是**无状态**的——每次请求都从零开始，不记得上一句。所谓"记忆"，是把整段对话历史塞进 `messages` 一起发。Memory 模块干的就这件事：维护一个 list，每轮 append 用户和 AI 的话，下次连历史一起发。这就是后端的 session：HTTP 无状态，靠 cookie/session 把上下文带回来。LangChain 的 `ConversationBufferMemory` 本质是个会自动拼接的 list。

### 3. Tool：一个注册表 + 一个解析协议
工具 = `{名字: 函数}` 注册表，加上"模型怎么说要调谁"的约定。用装饰器 `@tool` 把函数登记进字典，模型输出 `add|7 5` 这种指令，代码查表执行。这就是后端的 dispatch table / 命令路由——前两天 Day14 的 Function Calling 也是它。区别只在：谁来决定调用？普通代码是程序员，Agent 里是模型。

### 4. Agent：ReAct = 让模型在循环里反复选工具
把上面三块焊一起：一个 `while` 循环，每步让模型读问题"想"一下（**Reason**）、输出要调的工具（**Act**），代码执行拿结果喂回（**Observe**），直到模型说 `ANSWER`。这就是 Day36 的 ReAct 落地——一个会自我纠错的状态机。Tool 给手脚、Memory 给短期记忆、Chain 给单步流程，Agent 是把它们编排起来的循环。LangChain 的 `AgentExecutor` 就是这个 while 的工业版（加了限步、错误重试、解析兜底）。

### 5. 那 LangChain 到底帮你省什么？
省的是胶水：统一的 prompt 模板、各家模型的适配、20+ 种 Memory、几百个现成 Tool、解析兜底、流式、回调追踪。**值不值装**取决于你——简单串联手写更轻，多模型/多工具/要观测就用框架。但底层就这四块，今天捏一遍，框架对你再无黑盒。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **LangChain 官方文档 · 入门**（今天概念的权威出处）— https://python.langchain.com/docs/introduction/
2. **LangChain · Conceptual guide**（Chain/Memory/Tool/Agent/LCEL 逐个讲透）— https://python.langchain.com/docs/concepts/
3. **LCEL（表达式语言）**（理解 `prompt | model | parser` 那个竖线）— https://python.langchain.com/docs/concepts/lcel/
4. **Ollama API 文档**（本机 /api/chat，今天 chat helper 的基础）— https://github.com/ollama/ollama/blob/main/docs/api.md
5. **ReAct 论文**（Agent 循环的源头，对照 Day36）— https://arxiv.org/abs/2210.03629

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**纯标准库 + 真连本机 Ollama**：手写迷你 LangChain 四件套，各跑一遍。先补 5 个 `★` 行，再对照文末答案。HTTP 只用 `urllib`，无需装包，更不装 LangChain。

```bash
# 前置：起 Ollama 服务，拉生成模型
ollama serve                         # 默认 http://localhost:11434
ollama pull qwen2.5:3b               # 1.9GB；OLLAMA_MODEL 可覆盖成 qwen2.5:7b 等
# 直接跑（仅 stdlib）：
uv run day-37/practice.py
```
预期：[1] Chain 一句话解释「缓存」；[2] Memory 第二轮记得名字；[3] Tool add/upper 直调可用；[4] Agent 选 add 算出 7+5=12——即达标。

### 🎨 可视化（先玩这个再读理论，更直观）
双击打开 `visualize.html`（纯浏览器、零依赖、深色）。四个面板分别演示 Chain 数据逐段流过、Memory 历史一轮轮堆叠、Tool 名字命中注册表、Agent 在 Reason→Act→Observe 圈里转。点一下看一块抽象怎么动起来。

---

## 🤔 思考题（边做边想）

1. Memory 把全部历史每轮都发回去，对话越长 token 越多。生产里 LangChain 用窗口/摘要 Memory 压缩历史——这跟你做分页/会话过期是不是一回事？怎么权衡"记得全"与"省钱"？
2. Agent 让**模型**决定调哪个工具，普通代码是**程序员**决定。多了什么能力、又多了什么风险（选错工具、死循环、超步数）？practice 里的 `max_steps` 防的是什么？
3. 你手写的 chain/memory/tool/agent 全跑通了，那装 LangChain 还图什么？什么项目值得上框架、什么项目手写更轻？把"省胶水"和"加依赖"的账算一算。

> 把答案记在 `notes.md`。明天 Day 38 起，你将不再手写循环，而是用真 LangChain/LangGraph 编排 Agent——但记住：底层还是今天这四块。

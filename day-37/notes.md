# Day 37 笔记 · LangChain 核心概念：Chain / Memory / Tool / Agent

## 四件套对照（一句话记 LangChain 模块 = 哪个后端套路）
- **Chain** 链 = 函数串联 / pipeline（LCEL 的 `prompt | model | parser` 就是 compose）：
- **Memory** 记忆 = 对话历史 list / session（模型无状态，靠拼历史制造记忆）：
- **Tool** 工具 = 名字→函数 注册表 / dispatch table：
- **Agent** 智能体 = ReAct 循环 = while + 模型选工具 + 执行喂回：

## 思考题答案
1. Memory 全量回传越长越贵 → 窗口/摘要 Memory vs 分页/会话过期，怎么权衡：

2. 模型选工具 vs 程序员选工具，多了什么能力 / 风险，max_steps 防什么：

3. 四件套都能手写了，LangChain 还图什么？什么项目值得上框架：

## 关键命令
- 跑通：`uv run day-37/practice.py`
- 换模型：`OLLAMA_MODEL=qwen2.5:7b uv run day-37/practice.py`

## 今日卡点 / 疑问

## 一句话总结
LangChain 没黑魔法：Chain=串联、Memory=历史list、Tool=注册表、Agent=ReAct循环，全是后端老套路，框架只替你封装胶水。

# Day 55 笔记 · Agent 系统回顾与优化（Phase 4 收官·毕业作品）

## Phase 4 一句话地图（Day36-54）
- ReAct(36) = 主循环 while：想→做工具→看结果→再想，max_steps 护栏。
- 工具(40)+安全(49) = 模型只决定调谁，代码才执行；错误当 Observation 让模型自纠。
- 记忆(41) = messages 即短期状态，结果回填下一轮可见。
- 多 Agent(44/52)、MCP(46-47)、可观测(48)、评估(50)、生产化(54) = 后端的拆服务/标准接口/日志/单测/容错。
- LangChain/LangGraph(37-39)、CrewAI/AutoGen(45) = 把上面零件标准化的框架。

## 思考题答案
1. 工具结果"忘了"又重查，靠什么纠：

2. 工具出错 raise vs 返回错误串，对鲁棒性影响：

3. 3 题 100% 能说好用吗，评估还该补哪些维度：

## 关键实现点
- ReAct：`for _ in range(max_steps)` 调模型，有 tool_calls 就本地执行回填，否则=Final。
- 工具容错：calc 把字符串数字 float() 转，错了返回 `err:...` 当 Observation 不 raise。
- trace：每步落 `Action 名(参) -> obs` / `Final`，结束打印=最朴素可观测。
- 重试：urllib 超时/URLError 退避 0.5s 再试一次。
- 评估：标准答案做包含式断言，期望列表放阿拉伯+中文两种，算命中率出分。

## 今日卡点 / 疑问
- 真连 ollama 时小模型常把数字传成字符串、跨步丢值——容错工具+宽松断言是务实解。

## 一句话总结
Agent = while 循环 + 工具 + 会话状态 + trace + 重试 + 评估；Phase 4 毕业，下一步 Phase 5 微调模型本身。

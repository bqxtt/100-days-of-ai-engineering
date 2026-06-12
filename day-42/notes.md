# Day 42-43 笔记 · Phase 4 实战日（代码分析 Agent）

## 思考题答案
1. 去掉 8 步护栏 + 工具描述写模糊会怎样（不收手 / 调错工具 各对应哪行）：

2. 给 Agent 加 write_file，安全边界要加什么（接 Day49 权限控制）：

3. messages 无限追加会爆 token，摘要记忆压缩点在循环哪一步：

## ReAct 循环复盘（Day36-41，各记一条）
- Day36 ReAct（思考-行动）：
- Day37 LangChain Tool/Agent：
- Day38/39 LangGraph（状态机/HITL）：
- Day40 工具设计（描述+schema）：
- Day41 记忆（短期=messages / 摘要）：
- Day42-43 实战（单 Agent 焊起来）：

## 实战观察（跑 uv run 看 🔧 行）
- Agent 自主调了几步、调了哪些工具：
- 换 ANALYZE_DIR=day-20 后步数/工具有变化吗：

## 今日卡点 / 疑问

## 一句话总结
Agent = 会用工具的脚本，下一步由 LLM 决策：Thought→Action→Observation 循环到出报告，记忆=不断追加的 messages。

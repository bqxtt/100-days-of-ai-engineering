# Day 36 笔记 · Agent 概念与架构模式

## 一图速记
Agent = LLM(大脑) + Tools(胳膊/路由表) + Loop(while) + Memory(上下文)
- ReAct：Thought→Action→Observation 循环，边想边做，错了下轮纠（每步调一次模型，慢）
- Plan-and-Execute：先拆全计划再逐步执行，省调用、可控，计划僵需 replan
- Reflection：draft→critique→revise 自评重做，多花算力换质量

## 思考题答案
1. ReAct 慢，哪类任务改 Plan-and-Execute 更划算？计划僵硬怎么补（replan）：

2. 为什么必须有 MAX_STEPS？没有它小模型会怎样：

3. 把 search 换成 RAG 后再加一个工具，加哪个、Observation 长啥样：

## 练习卡点 / 疑问
- 5 个 ★ 行哪几行卡住：
- qwen2.5:3b 会不会跳过 search 直接凭记忆答（system prompt 怎么逼它取证）：

## 今日卡点 / 疑问

## 一句话总结
Agent 就是给 LLM 加循环+工具+记忆；ReAct 是默认主力（边想边做），Plan-and-Execute 省钱、Reflection 提质。

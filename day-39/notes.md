# Day 39 笔记 · Phase 4 LangGraph 进阶

## 思考题答案
1. checkpoint 为什么每步存、崩在第 5 步会怎样：

2. interrupt 只拦 delete_db，审批阈值怎么定（类比金额阈值）：

3. thread_id 在并发里的作用、换 Postgres 注意点：

## 核心概念一句话
- checkpoint（持久化）：每步把 state 存盘，崩了从断点 resume = 任务可恢复。
- interrupt（人在回路）：高危动作前暂停落盘，人 approve 才执行 = 审批工作流。
- thread_id：一次任务/会话的线程 ID = 工单/session。

## 后端类比
- 审批挂起 → 人工 approve → 续跑 ≈ 金额超阈值转人工审批工作流。
- 每步 state 落盘 → 崩溃 resume ≈ 断点续传 / 消息重投。

## 今日卡点 / 疑问

## 一句话总结
Agent 生产化两件套：state 存盘可恢复（checkpoint）+ 高危暂停等人批（interrupt/HITL）。

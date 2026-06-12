# Day 38 笔记 · LangGraph 入门：图状态机、节点与边、条件路由

## 思考题答案
1. 必须用「图」（循环+分支）才能干的 Agent 任务，必须在哪：

2. router 凭什么决定去 tool / END；LLM 输出 DONE/SEARCH vs 代码硬判断"够不够"，各自风险：

3. 去掉步数上限最坏会怎样；除计数外还能用什么信号安全收尾（tool 结果重复 / 置信度 / …）：

## 核心概念（一句话各记一条）
- State（状态）：
- Node（节点）：
- Edge（边）：
- 条件路由 conditional edge：
- 回边 / 循环：
- recursion_limit（步数上限）：
- 图 > 线性链 的理由：

## 后端类比
- 图状态机 ≈ 我熟的（FSM / Step Functions / Temporal / 审批工作流）：
- 单一真相源 State ≈ 无状态 handler + 显式 context：

## practice 里的 5 个 ★（自己写对了吗）
- ★1 step 上限收尾：
- ★2 DONE -> finish：
- ★3 SEARCH -> tool：
- ★4 agent 后走 router：
- ★5 tool 回边 -> agent（循环）：

## 今日卡点 / 疑问

## 一句话总结
LangGraph = 用有向图编排 Agent：State(dict)+Node(函数)+Edge(跳转)+条件路由；图能循环能分支，所以比直线链装得下"想一步查一步"。

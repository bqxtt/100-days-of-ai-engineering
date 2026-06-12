# Day 44 笔记 · Multi-Agent 架构（协作 / 委托 / 竞争）

## 思考题答案
1. 协作模式哪些环节能并行？reviewer 不通过回退到 planner 还是 coder（补偿/回滚）：

2. 委托模式 supervisor 选错处理者怎么办？加「可回收重派」=哪种后端模式：

3. 竞争模式 n=3 是 3 倍算力——什么任务值这个价？judge 模型投票 vs 规则多数表决各适合啥：

## 三模式 ↔ 后端类比（各记一条）
- 协作 collaboration（各司其职流水线）↔ 微服务编排：
- 委托 delegation（supervisor 分派）↔ 主从/dispatcher 路由：
- 竞争 competition（多方案投票）↔ 负载均衡多副本+仲裁：
- 单 Agent 够用就别上团队（协调成本）：

## 实战观察（跑 uv run 看三段输出）
- 协作段：planner 拆的步数 / coder 出码是否对 / reviewer 给的结论：
- 委托段：阶乘派给谁、广告语派给谁，分对了吗：
- 竞争段：3 方案差异大不大、评委选了第几个：

## 今日卡点 / 疑问

## 一句话总结
多 Agent = 多个单 Agent + 协作协议：协作=流水线编排、委托=主管路由、竞争=多副本投票；下一步框架(CrewAI/AutoGen)只是把它包起来。

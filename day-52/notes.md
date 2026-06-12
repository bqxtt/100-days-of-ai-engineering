# Day 52-53 笔记 · Phase 4 实战日（多 Agent 开发团队）

## 思考题答案
1. 去掉 QA、只靠 Reviewer 会怎样（哪行是 ground truth）：

2. demo 是串行，哪步能并行、收益（对照 Anthropic 多 worker 省 90% 时间）：

3. 加 write_file 真落盘，安全边界要加什么（接 Day49 权限/沙箱）：

## 角色分工复盘（各记一条：它读什么、产出什么）
- Supervisor（orchestrator）：
- PM（口语需求→规格）：
- Coder（按规格+反馈写码）：
- QA（exec 真跑断言 = 硬反馈）：
- Reviewer（双绿才放行的另一只眼）：

## 实战观察（跑 uv run 看 📋💻🧪👀 流水线）
- 第几轮就双绿交付、有没有被打回重写：
- 故意把 is_prime 改红后，QA 异常回灌→Coder 修没修对：
- 换 TASK="reverse_str(s)" 后步数/各轮代码变化：

## 单 Agent → 多 Agent 升级点（对照 Day42）
- Day42：一个 Agent 揽全活（loop=ReAct）
- Day52：分工 5 角色，supervisor 编排，QA exec 卡关，红打回
- 编排逻辑不变，worker 换 Claude / QA 换 pytest / 主管换 LangGraph 即生产级

## 今日卡点 / 疑问

## 一句话总结
Multi-Agent = 微服务编排：supervisor 拆活派 worker，QA exec 是 ground truth 关卡，双绿才交付，红了回灌打回——分工=独立上下文，编排=循环派单。

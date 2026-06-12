# Day 14 笔记 — Function Calling / Tool Use

## 思考题答案
1. 模型只申请不执行，为什么是特性不是缺陷（权限/审计/安全）：

2. 不回填 tool_result 会怎样 / tool_use_id 为何必须对上：

3. 并行省的是哪种成本 / 什么时候并行不安全：

4. calculator 用 eval 的风险 / 如何约束模型可调工具与参数：

## 今日卡点 / 疑问

## 一句话总结
> 模型当调度器（输出 tool_use），后端当执行器（跑函数回填 tool_result），来回循环到 end_turn。我的版本：

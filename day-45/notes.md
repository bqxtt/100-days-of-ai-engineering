# Day 45 笔记 · CrewAI vs AutoGen 多 Agent 框架对比

## 核心差异（一句话）
- CrewAI = 角色+任务+流程（role/task/crew），流程写死、顺序流水线，步数固定 = 后端的 pipeline/DAG。
- AutoGen = 对话式群聊（conversational），流程涌现自来回，聊到 DONE 才停、步数不定 = 微服务 RPC 协商收敛。

## 思考题答案
1. Crew 步数永远 3（可控）vs GroupChat 上限更高但不定，业务该选谁：

2. GroupChat 没人说 DONE 会怎样？max_turns 对应 CrewAI 的什么（CrewAI 为何不需此护栏）：

3. Crew 改成产物分别喂两人再合并 = DAG，对应 LangGraph 的什么：

## 实战观察（跑 uv run）
- mini_crew 三步产物变化（研究员→作者→审稿）：
- mini_groupchat 几句收敛 DONE、提议/挑刺各说了啥：
- 换 OLLAMA_MODEL=qwen2.5:7b 收敛质量有变好吗：

## 今日卡点 / 疑问

## 一句话总结
多 Agent 的根本分歧是「谁定流程」：CrewAI 你排死（流水线），AutoGen 涌现自对话（群聊到 DONE）。

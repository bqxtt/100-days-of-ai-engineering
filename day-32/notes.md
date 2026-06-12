# Day 32 笔记 — RAG 评估：Faithfulness / Relevancy / RAGAS

## 思考题答案
1. 怎么降低裁判模型自身的方差（temperature=0 / 多次投票 / 用更强模型当裁判）：

2. Faithfulness 高但 Answer Relevancy 低是哪段路坏了？反过来呢？先修检索还是生成：

3. 没标准答案也能评分——对线上 RAG 质量监控/告警意味着什么？哪个指标最该实时盯：

4. 小裁判评同档小答案会不会冤枉好答案？生产里怎么权衡成本与可信度：

## 三指标一句话
- Faithfulness 忠实度：答案每句能否由 context 支持 →「没编」
- Answer Relevancy 答案相关：答案切不切问题的题 →「答到点」
- Context Relevancy 上下文相关：检索回的料对不对路 →「找对料」

## 今日卡点 / 疑问

## 一句话总结

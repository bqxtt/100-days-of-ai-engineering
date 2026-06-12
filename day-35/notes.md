# Day 35 笔记 · Phase 3 实践日

## 思考题答案
1. 召回 Top-5 再 rerank Top-3，而不直接召回 Top-3：

2. "没有就说不知道" + 干扰块的引用补救：

3. 文档/向量库写死 → 生产化（缓存/增量/向量库）该怎么换：

## Phase 3 复盘（Day21-34，一句话各记一条）
- Day21 Embedding：
- Day22 向量数据库：
- Day23/24 分块策略：
- Day25 检索（Hybrid）：
- Day26 Rerank：
- Day27/28 RAG Pipeline：
- Day29/30 高级 RAG（Query 改写/HyDE/Self-RAG/CRAG）：
- Day31 Multi-hop：
- Day32 评估（RAGAS/忠实度）：
- Day33 多模态 RAG：
- Day34 生产化（缓存/增量/监控）：

## 今日卡点 / 疑问

## 一句话总结
RAG 知识库问答 = 7 段流水线：文档→chunk→embed→向量库→hybrid检索→rerank→带引用生成。

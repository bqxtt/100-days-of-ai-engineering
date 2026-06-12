# Day 16 笔记 — 多模态 API

## 思考题答案
1. base64 vs url（成本/延迟/隐私取舍，生产怎么选）：

2. patch 越小越细但越贵 vs 分页 size/批量大小的权衡：

3. Vision 直接吐 JSON vs 先描述再二次解析，哪种更稳：

4. 音频为何主流是"先转文字"两段式而非端到端：

## 今日卡点 / 疑问

## 一句话总结
> 图片 = 切成 patch 的一串视觉 token，拼到文字 token 后面进同一个 Transformer；content 从字符串变 block 数组（text + image），base64/url 二选一。我的版本：

# Day 17 笔记 — 流式输出与实时交互（SSE / WebSocket）

## 思考题答案
1. 流式只砍 TTFT 不缩总时长，为何体验像快一倍 / 是不是同 loading 占位一招：

2. SSE 单向够用，什么场景非 WebSocket 不可 / 无脑上 WS 的代价：

3. 后端中转里前端断了要不要继续烧 token / 怎么优雅取消：

4. 流式中途出错（限流/超时）怎么收尾 / 半截内容留不留：

## 今日卡点 / 疑问

## 一句话总结
> 流式 = 边生成边返回，把回答拆成一串 SSE `data:` 事件逐 token 推前端；只盯 `content_block_delta.text_delta` 拼接成全文。LLM 单向流默认用 SSE，双向才上 WebSocket；前端永不直连，走后端中转藏 Key。我的版本：

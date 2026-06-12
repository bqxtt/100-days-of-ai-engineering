# Day 13 — 高级 Prompt 技巧：Self-Consistency、Tree of Thoughts、ReAct

> **阶段**：Phase 2 · Prompt Engineering 与 LLM API 开发
> **主题**：Self-Consistency 多路投票、Tree of Thoughts（ToT）树搜索、ReAct 推理+行动交替、三者适用场景对比
> **预计耗时**：约 1 小时
> **给后端工程师的一句话**：Day 12 的 CoT 是"一条直线推到底"。今天三招都是给它加保险：**Self-Consistency** 是"同一请求重试 N 次再取多数"，**ToT** 是"把推理变成搜索树，能回溯换路"，**ReAct** 是"带工具调用的 while 循环——想一步、调一次工具、看反馈再想"。本质都是把单次直答升级成有冗余/有回溯/有外部反馈的流程。练习真连本地 ollama（默认 qwen2.5:3b）跑通这两招。

---

## 🎨 先玩可视化（5 分钟）

双击打开 `visualize.html`（纯浏览器，无需安装）。两块画布把今天两个核心机制画活：左边 **ToT 树搜索**——点"搜索"看模型从根问题展开多条思路分支、给每条打分、剪掉差的、沿最优路往下钻；右边 **ReAct 循环**——点"运行"看 Thought→Action→Observation 三色卡片一步步弹出，循环到 Final Answer。先玩出"多路+回溯"和"想做交替"的直觉，再读理论、跑代码。

---

## 📖 学习内容（约 25 分钟）

### 1. Self-Consistency：多路采样 + 投票取多数

CoT 一条路走到黑，一步算岔全盘皆错。Self-Consistency 的想法极简：**同一道题用温度采样跑 N 条不同的 CoT，各自给答案，最后投票取多数**。错误五花八门会分散，正确答案最容易被多条路径殊途同归——出现频次最高，投票就把它顶出来。

- 后端类比：一个偶发抖动的接口，重试 3 次取多数返回，比信一次稳。
- 代价：N 倍 token 与延迟。N 取 5~40，先小后调。`practice.py` 的 ★1 就是这一行投票。

实测（见练习）：本地小模型对同一道题温度采样 5 次，偶有"算岔"的离群答案被多数票出局——冗余换准确率。

### 2. Tree of Thoughts：把推理变成可回溯的搜索树

Self-Consistency 是"多条独立直线再投票"，仍不能中途换路。**ToT** 更进一步：每一步生成**多个候选想法**当树的分支，给每个分支打分（自评好坏），用 BFS/DFS 沿高分往下展开、剪掉差的，差到底就**回溯**换条路。从"一条链"升级成"一片可搜索、可回溯的树"。

- 后端类比：不是顺序执行，是带剪枝的搜索/状态机——走不通就回退换分支。
- 适合：解谜、规划、24点这类需试错回溯的题；代价是调用爆炸（每层 ×分支数），最贵。

### 3. ReAct：推理（Reason）与行动（Act）交替

前两招在"脑内"算，不碰外界。**ReAct** 让模型边想边用工具，循环交替：
> **Thought**（想下一步）→ **Action**（调工具：搜索/计算/查库）→ **Observation**（拿回结果）→ 再 Thought…直到 **Final Answer**。

写出 Thought 是推理外化（接 CoT），Action+Observation 引入真实反馈纠偏——治"一本正经胡说"。这就是 Agent 的雏形：一个带工具的 while 循环。`practice.py` 的 ★2/★3 就是 Action→Observation 与收敛输出。

### 4. 三者对比：何时用哪个

| 技巧 | 一句话 | 多路？ | 回溯？ | 用工具？ | 成本 | 适合 |
|---|---|---|---|---|---|---|
| CoT(Day12) | 一条链推到底 | ✗ | ✗ | ✗ | 低 | 一般多步推理 |
| Self-Consistency | 多条链投票取多数 | ✓ | ✗ | ✗ | 中 | 答案唯一、算术/逻辑 |
| ToT | 树搜索+剪枝回溯 | ✓ | ✓ | ✗ | 高 | 规划/解谜/试错 |
| ReAct | 想做交替+外部反馈 | ✗ | 弱 | ✓ | 中 | 查实时信息、用工具、Agent |

> 先 CoT；答案唯一不放心 → Self-Consistency；要试错回溯 → ToT；要查外部/用工具 → ReAct。三招正交，可叠加。

---

## 🔗 推荐资源（约 15 分钟，按兴趣选）

1. **Self-Consistency 原论文**（Wang et al., 2022，多路投票的出处，必看）— https://arxiv.org/abs/2203.11171 — 看它怎么在 GSM8K 上靠投票把 CoT 又抬一截。
2. **Tree of Thoughts 原论文**（Yao et al., 2023，ToT 出处）— https://arxiv.org/abs/2305.10601 — 看 24点/填字这类题如何靠"搜索+回溯"碾压直链 CoT。
3. **ReAct 原论文**（Yao et al., 2022，推理+行动交替，Agent 鼻祖）— https://arxiv.org/abs/2210.03629 — 理解 Thought/Action/Observation 三件套与 Agent 循环的起点。

---

## 💻 动手练习（约 20 分钟）

打开 `practice.py`，**真连本地 ollama** 跑两招：① Self-Consistency——同题温度采样 5 次各自答，投票取多数；② ReAct——真模型产出 Thought/Action，本地 mock 计算器执行 Observation 回填，循环到答案。完成 3 个 ★ 即可（采样数刻意取小以控时长）。

```bash
# 先起本地 ollama 并拉小模型（约 2GB）：
ollama serve            # 另开一个终端常驻
ollama pull qwen2.5:3b
# 在项目根目录跑（stdlib 直连 http://localhost:11434，无需第三方依赖）：
uv run day-13/practice.py
# 想换模型：OLLAMA_MODEL=qwen2.5:7b uv run day-13/practice.py
```

预期：5 条票投票顶出多数命中 7（28×¼，"5 人组长"是干扰项）；ReAct 两三步算出 9（23−20+6）。看到"投票顶出多数""想做交替收敛"就达标。

### 🎨 配合可视化

跑通后回到 `visualize.html`：左边 ToT 树对应"多路+回溯"，右边 ReAct 三色卡片对应代码里 react_loop 的 Thought/Action/Observation。把投票准确率那段对上 ToT 的打分剪枝、把 react_loop 对上右栏动画即可。

---

## 🤔 思考题（边做边想）

1. Self-Consistency 投 5 票已 89%，投 100 票收益还多大？这跟你给抖动接口加重试次数的边际收益像不像？
2. ToT 最贵——哪些题值得"搜索+回溯"（24点/规划），哪些纯属浪费（情感分类）？怎么判断？
3. ReAct 的 Observation 来自真实工具，把"幻觉"拉回地面。这一步去掉就退化成 CoT——为什么说它是 Agent（Day 36+）的雏形？

> 把答案记在 `notes.md`，明天 Day 14 继续 Prompt 工程进阶。

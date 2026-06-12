"""
Day 13 练习：用真实本地模型跑两个进阶 Prompt 技巧——Self-Consistency 多路投票 + ReAct 循环。

需要本地 ollama：先 `ollama serve` 起服务，并 `ollama pull qwen2.5:3b`（约 2GB）。
默认连 http://localhost:11434，模型 qwen2.5:3b（可用环境变量 OLLAMA_MODEL 覆盖）。运行：
    uv run day-13/practice.py

把它当成后端：Self-Consistency 是"同一请求温度采样 N 次再取多数"，
ReAct 是"带工具调用的 while 循环：模型先 Thought 想一步，再 Action 调工具，
本地执行回填 Observation，循环直到出 Final Answer"。本练习真调本地模型，
工具(计算器)在本地 mock 执行。采样数刻意取小以控时长，看清两件事的物理动作。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
"""
import json
import os
import re
import urllib.request
from collections import Counter

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")


def chat(messages, **kw):
    """最小 ollama 客户端：stdlib，无第三方依赖。**kw 传 options(如 temperature)。"""
    body = {"model": MODEL, "messages": messages, "stream": False, **kw}
    req = urllib.request.urlopen(OLLAMA_URL, json.dumps(body).encode(), timeout=120)
    return json.load(req)["message"]["content"]


# ============ 第一部分：Self-Consistency（多路采样投票） ============
# 真实做法：对同一道题用温度采样跑 N 条不同 CoT，各自给答案，最后投票取多数。
# 错误五花八门会分散，正确答案殊途同归频次最高，投票就把它顶出来。
QUESTION = "一个班 28 名学生，其中 3/4 报名了春游，报名的人里又有 5 人是组长。多少人没报名？只算人数。"
TRUE = 7  # 28 * 1/4 = 7


def extract_int(text):
    """从一段自由文本里抓最后一个整数当作答案。"""
    nums = re.findall(r"-?\d+", text)
    return int(nums[-1]) if nums else None


def self_consistency(n, temperature=1.0):
    msgs = [{"role": "user", "content": QUESTION + " 先简要推理再在最后单独一行写答案。"}]
    votes = []
    for _ in range(n):
        out = chat(msgs, options={"temperature": temperature})
        v = extract_int(out)
        if v is not None:
            votes.append(v)
    answer, cnt = Counter(votes).most_common(1)[0]   # ★1 投票：取出现次数最多的答案
    return answer, votes, cnt


print("=" * 56)
print(f"① Self-Consistency：温度采样多条，投票取多数（模型 {MODEL}）")
print("=" * 56)
ans, votes, cnt = self_consistency(5)
print(f"  问题: {QUESTION}")
print(f"  5 条票面: {votes}")
print(f"  → 多数选中 {ans}（{cnt}/{len(votes)} 票），正确答案 {TRUE}  "
      f"{'✅' if ans == TRUE else '❌'}\n")

# ============ 第二部分：ReAct 循环（Thought→Action→Observation） ============
# 真实做法：模型先想(Thought)，再发一个工具调用(Action)，外部执行回传(Observation)，
# 拿反馈继续想，直到 Final Answer。这里真用模型产出 Thought/Action，
# 工具(calc)本地 mock 执行 Observation 回填，循环直到 Final Answer。
SYS = (
    "你在解一道算术题，按 ReAct 格式回复，每次只输出一步，不要一次写完。"
    "需要计算时只输出两行: `Thought: ...` 和 `Action: calc[表达式]`，然后停下等 Observation。"
    "确定结果后才只输出一行: `Final Answer: 数字`。两者不要同时出现。表达式只用 + - * / 和数字。"
)


def calculator(expr):                 # 本地 mock 工具
    return str(eval(expr, {"__builtins__": {}}))


def react_loop(question, max_steps=5):
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": question}]
    steps = []
    for _ in range(max_steps):
        reply = chat(msgs, options={"temperature": 0})
        msgs.append({"role": "assistant", "content": reply})
        if "Final Answer:" in reply:
            steps.append((reply.strip(), None))      # ★3 出 Final Answer，循环收敛退出
            break
        m = re.search(r"Action:\s*calc\[(.+?)\]", reply)
        if m:
            obs = calculator(m.group(1))             # ★2 Action→Observation：本地工具执行回填
            steps.append((reply.strip(), f"Observation: {obs}"))
            msgs.append({"role": "user", "content": f"Observation: {obs}"})
    return steps


print("=" * 56)
print("② ReAct：模型想一步→调一次本地工具→看反馈，循环到答案")
print("=" * 56)
trace = react_loop("23 个苹果，用掉 20，又买 6，现在几个？")
for reply, obs in trace:
    print(f"  {reply}")
    if obs:
        print(f"  {obs}")
print("  ✅ 收敛")

# ============ 参考答案（被你应当先自己写的 3 行）============
#   ★1  answer, cnt = Counter(votes).most_common(1)[0]
#   ★2  obs = calculator(m.group(1))            # 工具执行 Action 的表达式
#   ★3  steps.append((reply.strip(), None)); break   # 见 Final Answer 即收敛退出
# 看到 5 条票投出多数命中 7、ReAct 几步算出 9 就成功了。

"""
Day 12 练习：Zero-shot / Few-shot / Chain-of-Thought 三种 prompt 真调本地 LLM。
对同一道题分别用三种 prompt 真连本地 ollama，打印三种真实回答做对比。

需要本地 ollama，模型 qwen2.5:3b：
    ollama serve            # 跑在 http://localhost:11434
    ollama pull qwen2.5:3b
然后在项目根目录跑：
    uv run day-12/practice.py
（可用 OLLAMA_MODEL 环境变量换模型。）

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版。
"""

import json, os, urllib.request

# ---- 共享设定：System Prompt + 这次要解的题 ----
SYSTEM = "你是严谨的数学助教，只输出最终答案，不解释。"
QUESTION = "食堂有 23 个苹果，午餐用掉 20 个，又买进 6 个，现在有几个？"

# ---- Few-shot 示例池（demonstration）：每条都是「问→答」配对 ----
EXAMPLES = [
    {"q": "盒子里有 5 支笔，拿走 2 支，又放进 4 支，现在几支？", "a": "7"},
    {"q": "停车场有 10 辆车，开走 3 辆，又来 5 辆，现在几辆？",   "a": "12"},
]

def chat(messages, **kw):
    """把 messages 发给本地 ollama，返回模型真实回答文本。"""
    body = {"model": os.getenv("OLLAMA_MODEL", "qwen2.5:3b"), "messages": messages, "stream": False, **kw}
    return json.load(urllib.request.urlopen(
        "http://localhost:11434/api/chat", json.dumps(body).encode(), timeout=120
    ))["message"]["content"]

# 1) Zero-shot：不给任何示例，直接问。靠模型自带能力。
def zero_shot():
    msgs = [{"role": "system", "content": SYSTEM},
            {"role": "user", "content": QUESTION}]                                  # ★1 只有一条 user 消息
    return chat(msgs)

# 2) Few-shot：先塞 N 条「问→答」示范，再问真题。模型照葫芦画瓢。
def few_shot():
    msgs = [{"role": "system", "content": SYSTEM}]
    for ex in EXAMPLES:
        msgs.append({"role": "user", "content": ex["q"]})
        msgs.append({"role": "assistant", "content": ex["a"]})                      # ★2 示例答案作为 assistant 回合
    msgs.append({"role": "user", "content": QUESTION})
    return chat(msgs)

# 3) CoT：在真题后追加「让我们一步步想」，逼模型先写推理步骤再给答案。
def cot():
    trigger = "让我们一步步思考，写出每一步再给最终答案。"
    msgs = [{"role": "system", "content": "你是严谨的数学助教，先逐步推理再给答案。"},
            {"role": "user", "content": QUESTION + " " + trigger}]                  # ★3 题目末尾拼 CoT 触发语
    return chat(msgs)

def show(name, answer):
    print("=" * 56)
    print(f"【{name}】qwen2.5:3b 的真实回答：")
    print("-" * 56)
    print(answer.strip())
    print()

if __name__ == "__main__":
    print(f"题目：{QUESTION}\n（正确答案 9。下面看三种 prompt 真实回答的差异）\n")
    show("Zero-shot 零样本", zero_shot())
    show("Few-shot 少样本(2 例)", few_shot())
    show("Chain-of-Thought 思维链", cot())
    print("观察：Zero/Few-shot 只回最终答案，CoT 会先逐步推理再给答案；")
    print("对算术/多步题 CoT 通常更稳，代价是输出更长、更慢、更贵。")

# ============ 参考答案（先自己写的 3 行）============
#   ★1  msgs = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": QUESTION}]
#   ★2  msgs.append({"role": "assistant", "content": ex["a"]})
#   ★3  msgs = [{"role": "system", ...}, {"role": "user", "content": QUESTION + " " + trigger}]
# 跑通后能看出三种 prompt 喂给同一模型得到的真实回答差异，今天就达标了。

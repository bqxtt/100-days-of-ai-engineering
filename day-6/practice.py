"""
Day 6 练习：纯 Python 手写一个 BPE（Byte Pair Encoding）训练器 + 编码器。
目标：亲眼看清"统计相邻 bigram -> 反复合并最高频 pair -> 词表逐步长出"这条主线，
理解 GPT / tiktoken / SentencePiece 背后那把"分词的尺子"是怎么造出来的。

练习方式：先把 3 个标了 ★ 的行自己写一遍，再对照文末「参考答案」。
下面已是可直接运行的完整版，跑出合并日志即达标：
    uv run day-6/practice.py

不用 numpy、不用任何第三方库——分词本质上就是字符串统计，纯 Python 足矣。
"""
from collections import Counter

# 训练语料：故意把高频子串塞进来，方便观察 BPE 把它们合并成一个 token
CORPUS = "low low low low low lower lower newest newest newest widest widest"

# 后端类比：BPE = 给字符串做"频次驱动的压缩字典"。高频组合 -> 升级成一个独立 token，
#           就像热点 SQL 建索引、热点接口加缓存：高频的东西值得单独优化。


def get_word_freqs(text):
    """统计每个词出现次数；词内部先拆成单字符，并加一个结束符 </w> 标记词尾。"""
    freqs = Counter(text.split())
    # "low" -> ('l','o','w','</w>')  结束符让 BPE 区分"词尾的 st"和"词中的 st"
    return {tuple(w) + ("</w>",): c for w, c in freqs.items()}


def count_pairs(vocab):
    """扫一遍所有词，统计相邻 token 两两组成的 bigram 出现频次。"""
    pairs = Counter()
    for word, freq in vocab.items():
        for i in range(len(word) - 1):
            pairs[(word[i], word[i + 1])] += freq          # ★1 统计相邻 bigram，按词频加权
    return pairs


def merge_pair(pair, vocab):
    """把语料里所有该 pair 的相邻出现合并成一个新 token。"""
    a, b = pair
    new_vocab = {}
    for word, freq in vocab.items():
        merged, i = [], 0
        while i < len(word):
            if i < len(word) - 1 and word[i] == a and word[i + 1] == b:
                merged.append(a + b)                       # ★2 命中就合并，跳过下一个
                i += 2
            else:
                merged.append(word[i]); i += 1
        new_vocab[tuple(merged)] = freq
    return new_vocab


def train_bpe(text, num_merges):
    """反复合并最高频 bigram，记录学到的合并规则（就是词表的成长史）。"""
    vocab = get_word_freqs(text)
    merges = []
    for step in range(num_merges):
        pairs = count_pairs(vocab)
        if not pairs:
            break
        best = max(pairs, key=pairs.get)                   # ★3 选当前出现最多的 pair 来合并
        vocab = merge_pair(best, vocab)
        merges.append(best)
        print(f"merge {step+1:2d}: {best[0]!r}+{best[1]!r} -> {best[0]+best[1]!r}  (出现 {pairs[best]} 次)")
    return merges


def encode(word, merges):
    """用学到的规则切一个新词：按合并顺序依次套用。"""
    toks = list(word) + ["</w>"]
    for a, b in merges:
        i = 0
        while i < len(toks) - 1:
            if toks[i] == a and toks[i + 1] == b:
                toks[i:i + 2] = [a + b]
            else:
                i += 1
    return toks


if __name__ == "__main__":
    print("=== 训练 BPE（合并 10 次）===")
    merges = train_bpe(CORPUS, num_merges=10)

    print("\n=== 用学到的规则切词 ===")
    for w in ["low", "lowest", "newest", "wildest"]:
        print(f"{w:9s} -> {encode(w, merges)}")
    # 观察：'low</w>' 已被压成 1 个 token；'lowest' 复用 'low'+'est'；
    #       'wildest' 没见过，靠 subword 拼出来，不会 OOV——这就是 subword 的价值。

# ============ 参考答案（应当先自己写的 3 行）============
#   ★1  pairs[(word[i], word[i+1])] += freq
#   ★2  merged.append(a + b)
#   ★3  best = max(pairs, key=pairs.get)
# 看到合并日志先并 't'+'</w>'、'es'、'est'，再把 'low</w>' 整体并掉，就成功了。

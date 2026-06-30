# AI-flavor removal — concrete before/after

**When this applies:** the humanizer pass (S5), and the writer pre-empting tells (S3).

**The pattern / rule:** replace generic, balanced, hedged model-prose with a specific,
committed, dated claim. Lead with the thing only this week could produce.

**Before → after:**
- ❌ "随着人工智能的飞速发展，大模型领域不断涌现出令人瞩目的新成果。"
- ✅ "6 月 24 日，Anthropic 把 Claude 的上下文窗口提到了 100 万 token [S1]——这件事比它听起来更重要。"

- ❌ "总而言之，这一进展无疑具有重要意义，值得我们持续关注。"
- ✅ "如果你在做 agent，这条变化直接改了你能塞进一次调用的工具数量。下一个要盯的是定价。"

- ❌ tricolon reflex: "更快、更强、更智能。"
- ✅ pick the one that's true and say why: "快不是重点，重点是它第一次能一次读完整个 repo [S2]。"

**Why:** these openers/transitions are the highest-signal markers that a model wrote
the text. Removing them is the cheapest, biggest credibility win.

**Source:** seed note (style_patterns.md §3 distilled into worked examples).

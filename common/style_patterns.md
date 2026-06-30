# style_patterns.md — the in-repo single source of truth for voice & structure

Every writing agent (writer, humanizer, editorial-reviewer) Reads this first. It is
in-repo (not a skill) because it is always-needed and version-controlled — the same
reasoning that keeps sas2pyspark's `translation_patterns.md` in-repo.

Article body is **Chinese**; this file is English (it is a spec, not deliverable prose).

## 1. Voice
- Write for a Chinese reader who follows AI but is not an insider. Explain the jargon
  once, then use it.
- Concrete before abstract: lead a point with the specific example, then generalize.
  (This mirrors how the human you write for actually learns.)
- Direct and honest. State the trade-off, not just the upside. If a claim is contested,
  say who disputes it — don't smooth it into false consensus.
- One idea per paragraph. Vary sentence and paragraph length deliberately.

## 2. Structure
- Open with a hook grounded in a concrete, dated fact (`[Sn]`) — not a generic "随着
  人工智能的飞速发展". The first sentence must be one only this week could produce.
- Each section delivers one job (its contract's Purpose) and hands to the next.
- Close with a "为什么它重要 / 接下来看什么" that gives the reader a lens, not a recap.

## 3. The "去 AI 味" checklist (the humanizer enforces; the writer pre-empts)
Kill these tells:
- Formulaic openers: "在当今快速发展的…", "随着…的不断…", "毫无疑问".
- Empty transitions: "值得注意的是", "总而言之", "综上所述", "不仅如此".
- Tricolon reflex: forcing every idea into a list of exactly three.
- The "首先…其次…最后" scaffold where the ideas aren't actually sequential.
- Hollow hedging: "在某种程度上", "可以说", stacked qualifiers that commit to nothing.
- Uniform rhythm: every paragraph the same length, every sentence the same shape.
- Symmetry padding: inventing a counterpoint just to balance a sentence.
- Over-explaining the obvious; restating the heading as the first sentence.
- **English-calque Chinese (翻译腔):** any phrasing that reads as a direct translation of
  English. Rewrite into what a native speaker actually says. Banned tics, per Hanfei:
  「炸」「硬」「诚实地说 / 诚实讲」, plus the usual AI giveaways 「值得注意的是」「总而言之」
  「深入」「赋能」「打造」「拥抱」「无缝」「强大的」「丰富的」.
- **Safer-calque tic:** avoid 「更稳的做法」「更稳」 as a generic recommendation. It often
  reads like a direct translation of "safer / safer way". Replace it with the actual
  judgement: 「风险更低」「不容易翻车」「先保留人工确认」「先把 X 跑通」, or cut the filler.

## 4. Citation discipline (non-negotiable — it is what makes the oracle work)
- Every factual sentence (number, date, named release, quote, attribution) carries an
  inline `[Sn]` marker resolving to `source_pack.json`.
- Analysis/opinion is allowed and good — but mark it as the writer's read, not as a
  fact. "这意味着…" is analysis; "X 公司融资 20 亿美元" is a fact and needs `[Sn]`.
- Never state as fact anything you cannot cite. Soften or drop it.

## 5. Freshness (this domain's hard edge)
- Prefer the most recent primary source. A 6-month-old source on an AI topic is a
  staleness risk — the audit WARNs on it; justify or replace it.
- Date-anchor time-sensitive claims ("截至 2026 年 6 月…") so they age gracefully.

## 6. Adding to this file
New durable style rule → add a numbered line here. A conditional / situational
technique → a `behavior_notes/` note instead (see that folder's README). This is the
self-improvement loop: every shipped article that revealed a tell feeds back here.

## 7. Hard-rule checklist (the §14 analog — writer + humanizer gate on this)
A flat checklist the writer self-checks before declaring done and the humanizer enforces.
This is the article-writer analog of `translation_patterns.md §14` in sas2pyspark: append
a numbered line each time a shipped piece teaches a new always-true rule.

1. Every factual sentence carries an inline `[Sn]` marker (no 裸论断). [non-negotiable]
2. No claim ships without a dated source; un-anchor superlatives (date them). [§5]
3. Open on a concrete dated fact, not a generic "随着…的发展". [§2]
4. Kill the 去-AI-味 tells in §3 (formulaic openers, empty transitions, tricolon reflex,
   English-calque phrases like 「更稳的做法」).
5. One idea per paragraph; vary rhythm; don't restate the heading as the first sentence.
6. Mark analysis as the writer's read ("我的感受是…"), never as a cited fact. [§4]
7. (小红书) No 破折号 in the body; dates have no space (`6月29日`); 网感 ending;
   小红书-native hashtags. See `behavior_notes/xiaohongshu-output-mode.md`. [channel-specific]

> Provenance of this checklist: each line traces to a shipped piece or a behavior note.
> When a review (S6) or the human surfaces a recurring miss, add the rule here (always-true)
> or to a behavior_notes file (situational), then cite where it came from.

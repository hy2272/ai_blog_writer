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
  「深入」「赋能」「打造」「拥抱」「无缝」「强大的」「丰富的」, and 「岁月静好」(及其引申/反讽
  用法 —— 该词已带贬义,不要用它形容“温馨/治愈”的画面,改说「治愈系」「松弛感」「温柔的氛围」).
- **Sentence structure 翻译腔 (英文式倒装 / 不断补充):** 中文不像英文那样把限定语前置倒装、
  或用从句无限往后补。写成中文人真会说的短句、按自然语序。Per Hanfei:
  - 不好(英文式):「可能有人这两天刷到了关于 X 发布了能 4 秒出图的 Y、但目前只有开发者能用
    的那条新闻」—— 倒装 + 一路补充。
  - 好(中文式):「这两天有人应该刷到一条新闻,谷歌出了能 4 秒出图的 Y。虽然目前只有开发者/
    企业能用,但以后大概率会逐步开放给普通人。」
  - 中文不追求绝对精确:用「一条新闻」泛指具体那条即可,不必把日期、全部产品名一一摊开。
    能省的细节(冗长的官方型号名等)就省,别为“完整”牺牲口语感。
- **Safer-calque tic:** avoid 「更稳的做法」「更稳」 as a generic recommendation. It often
  reads like a direct translation of "safer / safer way". Replace it with the actual
  judgement: 「风险更低」「不容易翻车」「先保留人工确认」「先把 X 跑通」, or cut the filler.
- **More AI-味 / 翻译腔 word bans (per Hanfei, 2026-06-30 round 2):**
  - 「最香的」「最香的一点」—— reads AI-ish and isn't actually common. Say what you mean:
    「这次最实用的」「真正好用的是」「最值的一点」, or just state the thing.
  - 「吃」表示“使用/消耗素材”(如「它吃的是你自己的素材」)—— not natural Chinese. Use
    「用你自己的素材」「调用你相册里的内容」.
  - 「开发者玩具」—— direct calque of “developer toy”. Prefer 「离普通人很远的东西」「只有
    开发者才碰得到的东西」.
  - 「直白」误用于“操作/用法简单”—— 「直白」only describes 语言/表达. For ease-of-use say
    「很简单」「超级简单」(「超级」is more 口语).
- **Omit the subject (中文省略主语):** Chinese drops subjects that English keeps. Repeating
  「它/它/它」across adjacent sentences reads machine-translated. Drop the subject when context
  carries it: ❌「开了之后，它能直接调用你的内容，它会顺着你的素材出图」✅「开了之后，能直接
  调用你的内容，顺着你的素材出图」.
- **Don't cluster the same word:** avoid repeating one word in neighbouring sentences
  (「这才是这次…这次功能…」). Vary it or cut it — varied phrasing reads more 优美.
- **Frame demo/经验 positively, not defensively:** present hands-on guidance as 「我亲测有效
  的用法」「分享几个我的写法」—— NOT a defensive negation like 「这不是官方说明」, and not a
  throat-clear like 「我习惯把…」. Just give the move directly: 「想发封面,就把主体和文字
  位置先讲清楚」. (This is the positive-framing form of §4's “mark analysis as your read”.)
- **More calibration (per Hanfei's published-post edits, 2026-06-30 round 3):**
  - **No brand+product stacking:** 「谷歌Gemini」→「Gemini」. Pick one; saying both is redundant.
  - **「影子」→「审美」:** describing personalized output as 「带着你的影子」reads vague; 「带着
    你的审美」is the natural, flattering phrasing for "reflects you".
  - **Confident over hedged (网感):** drop 对冲 like 「没那么容易撞款」→「绝对不撞款」;
    「没那么/还算/应该能」hedges deflate a 小红书 line. Commit to the claim (it is the
    writer's experiential read, so a confident 网感 statement is fine here).
  - **第一人称踩坑 > 抽象名词:** 「绕不开的准入坑」→「我踩过的坑」. Lead with lived experience,
    not an abstract noun phrase.

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
   小红书-native hashtags; avoid platform-sensitive words —— don't spell out VPN / 翻墙 /
   科学上网; for a region-locked tool say it vaguely (e.g. 「有个美国账号就能马上用,懂的都
   懂」) instead of describing how to get around the lock. See
   `behavior_notes/xiaohongshu-output-mode.md`. [channel-specific]

> Provenance of this checklist: each line traces to a shipped piece or a behavior note.
> When a review (S6) or the human surfaces a recurring miss, add the rule here (always-true)
> or to a behavior_notes file (situational), then cite where it came from.

# 小红书 (Xiaohongshu/RED) output mode

**When this applies:** the output stage (S7) when the target platform is 小红书, and the
editorial stage (S2) when setting per-section word ranges for a 小红书 piece. The default
is now a **long-image technical post**: cover + multiple 1080×1440 text cards + a short
caption. This is the common shape for technical explainers on 小红书: the useful content
lives in images, while the caption sells the save/read.

**The pattern / rule — the 小红书 deliverable has five parts:**

1. **标题 (title)** — ≤ 20 字, 1-2 emoji, a hook or a concrete payoff. Front-load the
   benefit or the "你不知道的". NOT a formal headline.
   - ✅ "📱Cursor 出手机版了！通勤路上也能让 AI 帮你写代码"
   - ❌ "Cursor 发布移动应用程序：功能概述与分析"

2. **长图正文 cards (default)** — 1080×1440 图片：**封面(已并入“这篇讲什么”阅读路线)**
   + 每个 final.md 章节一张正文卡(放不下才拆成两张)。**不再单独出目录卡或参考来源卡。**
   每张卡只讲一个点；技术帖允许信息密度高,但要把卡**填满**(不要上三分之一一点字、下面
   一片空白)。**`[Sn]` 标记在渲染时从图里去掉** —— 卡片是直接发帖的成品,图里出现 [S1]
   像 debug;来源仍留在 final.md(citation 审计照跑)和 manifest 的 citation_ids 里。

3. **Caption / 正文框** — short paste-ready text, not the full article. It should say why
   to save the post, list the card route, and include topic suggestions. The full content
   is already in the images.

4. **封面图 (cover)** — the single highest-leverage asset on 小红书. A big-type 标题 +
   one visual hook, readable as a thumbnail. The default adapter generates `card_01`
   as the cover.

5. **话题 (hashtags)** — 4-8 at the end: a mix of broad (#AI #程序员) + specific
   (#Cursor #AI编程 #vibecoding). Chinese tags; match what the audience actually searches.

**Tone:** 真诚分享体, not 测评体. "我试了下…", "踩了个坑…", "亲测…". Avoid the
去-AI-味 tells (see [[style_patterns]] §3) — 小红书 punishes formulaic AI prose hard.
NOTE: 「最香的是…」is now demoted — it reads AI-ish on re-read; say 「最实用的是」or just
state the thing (see §3 word bans, 2026-06-30 round 2).

**Word-count contract:** for a 小红书 long-image piece, allow a longer verified draft
(roughly 900-1,800 字). The adapter chunks it into readable cards; do not force the
source article into a tiny caption.

**How to build the default package:**
```
python3 tools/xhs_image_post.py articles/article_<slug>/final.md \
  --out-dir articles/article_<slug>/assets/xhs
```
This emits `card_01.png`... (PNG-only when Chrome is available), `post_xiaohongshu.txt`,
and `content_manifest.json`. HTML cards are written only as a fallback under `--no-render`
(or when Chrome is missing) — the post folder otherwise holds just images.

**How to post (hand-off to the human):** 小红书 App → ➕发布 → 上传 `card_01.png` ...
`card_N.png`（封面放第一张）→ 标题贴进标题栏 → `post_xiaohongshu.txt` 贴进正文框
→ 末尾逐个加 #话题 → 发布。图里不带 `[Sn]`(已去掉,直接能发);caption 不必提来源。

**Why:** the long-form blog contract (4,500 字, references section) is wrong for 小红书 —
it would tank reach. The factual-fidelity machinery (citation/grounding) is platform-
independent and stays on; only the SHAPE of the output changes. This keeps the system's
correctness guarantees while fitting the channel.

## Calibration from Hanfei's first real post (2026-06-30) — apply these
Learned by diffing the generated draft against what she actually posted. These are HARD:
- **No 破折号 (——) in the body.** Break with 句号 or a 语气词 instead.
  ❌ "更骚的是 Remote Control——它能…"  ✅ "更骚的是 Remote Control，它能…"
- **Dates carry NO space:** `6月29日`, `7月5日`. (But keep spaces in mixed quantities
  like `600 亿美元`, `75% off`, and around Latin terms like `app 内`, `Composer 2.5`.)
- **Inside 括号 no space at the CJK↔Latin edge:** `iOS（iPhone）` (full-width parens).
- **标题:** drop emoji, shorter + punchier, "！！" is fine; no space at the CJK↔Latin
  edge in the title (`Cursor出手机版了`).
- **更口语 / 网感 ending:** end with self-deprecating humor, not a polite 分享体 sign-off.
  ✅ "我已经在试了～～牛马的手根本停不下来😅"  ❌ "等踩完坑再回来跟你们唠"
- **Hashtags = 小红书-native topic tags, not generic keywords.** Prefer phrase tags the
  community actually uses: `#howto用AI抢救一切 #科技资讯早知道 #人工智能 #效率神器
  #vibecoding #科技新闻`. NOT `#Cursor #程序员 #AI工具`.

## Deliverable shape (fixed)
- Images → **default primary deliverable** in `<article>/assets/xhs/`: `card_01.png` ...
  `card_N.png` when Chrome is available. **PNG-only** in that case — `.html` is written
  only as the `--no-render` / no-Chrome fallback.
- Caption → `post_xiaohongshu.txt` in the same folder (NO markdown headings) — short
  save/read hook + route + topic suggestions.
- Manifest → `content_manifest.json`: card count, output format, citations, publish status.

## Calibration round 2 (2026-06-30, post-design feedback) — apply these
From Hanfei's feedback on the Nano-Banana cards. These are HARD:
- **Card layout (now in the adapter):** cover merges with the "这篇讲什么" reading route
  (no sparse standalone outline/目录 card; the reader gets hook + map on image 1); one card
  per `final.md` section, split only on overflow; NO 参考来源 card; `[Sn]` stripped from the
  rendered cards; PNG-only output; cards must FILL the height (`MAX_BODY_CHARS` calibrated).
  Visual language borrows the course `beautiful-html` `cartesian` template (warm neutral,
  CJK serif titles, eyebrow + accent bar, faded page-number watermark).
- **平台敏感词 / 审查敏感角度 (UPDATED 2026-06-30, supersedes "say it vaguely"):** never
  spell out VPN / 翻墙 / 科学上网. AND — stronger than before — **avoid the region-access /
  censorship-adjacent angle altogether**, don't just vague it up. The earlier advice was to
  say 「有个美国账号就能马上用,懂的都懂」; Hanfei's stance now: that framing (e.g. the published
  「有个美国（非中国区）账号就能马上用」line) is itself censorship-adjacent and 小红书 limits it.
  DROP it, lead with value/玩法; for an inherently region-sensitive topic, consider another
  platform. We adapt, we don't editorialize. (Also in [[style_patterns]] §7; memory
  `xhs-political-sensitivity`; [[xhs-narrative-value-first]].)
- **禁用「岁月静好」**(及反讽引申义) — the word now reads ironically; use 「治愈系」「松弛感」
  「温柔的氛围」for a cozy-image vibe. (Also in [[style_patterns]] §3.)
- **句子结构别用英文式倒装 / 一路补充补语;** write natural short Chinese sentences; vague
  「一条新闻」reference is fine; drop long official model-name details. (See [[style_patterns]]
  §3 sentence-structure rule for the before/after example.)
- **No #hashtags on the last card (or any card).** Tags live only in `post_xiaohongshu.txt`.
  The adapter now extracts a draft's trailing hashtag line into the caption's tag block and
  keeps it off the images — so the draft MAY end with a `#a #b` line (it becomes the caption
  tags), but it will never be burned into a card.
- **More word bans (2026-06-30 round 2):** 「最香的」/「吃(素材)」/「开发者玩具」/「直白(误用)」;
  中文省略主语 (don't repeat 它/它); don't cluster the same word; frame demos as 「亲测/分享」
  not 「不是官方说明」or 「我习惯把…」. All detailed in [[style_patterns]] §3.

**Source:** 小红书 试水; first applied to the Cursor-mobile-app article (calibrated
2026-06-30 vs the author's published post); design + tone refined 2026-06-30 on the
Nano-Banana-2 article.

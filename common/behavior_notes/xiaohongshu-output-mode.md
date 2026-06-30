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

2. **长图正文 cards (default)** — 6-10 张 1080×1440 图片：封面、目录、正文卡、参考来源卡。
   每张卡只讲一个点；技术帖允许信息密度高，但必须有标题层级和留白。Keep every factual
   claim's `[Sn]` marker in the image text — the audit still runs before rendering.

3. **Caption / 正文框** — short paste-ready text, not the full article. It should say why
   to save the post, list the card route, and include topic suggestions. The full content
   is already in the images.

4. **封面图 (cover)** — the single highest-leverage asset on 小红书. A big-type 标题 +
   one visual hook, readable as a thumbnail. The default adapter generates `card_01`
   as the cover.

5. **话题 (hashtags)** — 4-8 at the end: a mix of broad (#AI #程序员) + specific
   (#Cursor #AI编程 #vibecoding). Chinese tags; match what the audience actually searches.

**Tone:** 真诚分享体, not 测评体. "我试了下…", "踩了个坑…", "最香的是…". Avoid the
去-AI-味 tells (see [[style_patterns]] §3) — 小红书 punishes formulaic AI prose hard.

**Word-count contract:** for a 小红书 long-image piece, allow a longer verified draft
(roughly 900-1,800 字). The adapter chunks it into readable cards; do not force the
source article into a tiny caption.

**How to build the default package:**
```
python3 tools/xhs_image_post.py articles/article_<slug>/final.md \
  --out-dir articles/article_<slug>/assets/xhs
```
This emits `card_01.html`... plus PNGs when Chrome is available, `post_xiaohongshu.txt`,
and `content_manifest.json`.

**How to post (hand-off to the human):** 小红书 App → ➕发布 → 上传 `card_01.png` ...
`card_N.png`（封面放第一张）→ 标题贴进标题栏 → `post_xiaohongshu.txt` 贴进正文框
→ 末尾逐个加 #话题 → 发布。`[Sn]` 标记可留在图片里；caption 里用一句来源说明即可。

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
  `card_N.png` when Chrome is available, with matching `.html` card sources always kept.
- Caption → `post_xiaohongshu.txt` in the same folder (NO markdown headings) — short
  save/read hook + route + topic suggestions.
- Manifest → `content_manifest.json`: card count, output format, citations, publish status.

**Source:** 小红书 试水; first applied to the Cursor-mobile-app article; calibrated
2026-06-30 by diffing the generated draft against the author's actual published post.

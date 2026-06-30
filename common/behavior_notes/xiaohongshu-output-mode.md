# 小红书 (Xiaohongshu/RED) output mode

**When this applies:** the output stage (S7) when the target platform is 小红书, and the
editorial stage (S2) when setting per-section word ranges for a 小红书 piece. 小红书 is
NOT a long-form blog — it is a short, image-first, conversational post. Adjust the
contract accordingly; the oracle (citation_audit + grounding) still applies unchanged.

**The pattern / rule — the 小红书 deliverable has five parts:**

1. **标题 (title)** — ≤ 20 字, 1-2 emoji, a hook or a concrete payoff. Front-load the
   benefit or the "你不知道的". NOT a formal headline.
   - ✅ "📱Cursor 出手机版了！通勤路上也能让 AI 帮你写代码"
   - ❌ "Cursor 发布移动应用程序：功能概述与分析"

2. **正文 (body)** — ~600–900 字 (短！), 口语第一人称, 分点 (emoji 小标题或 ▪️/1️⃣),
   段落短、留白多. Keep every factual claim's `[Sn]` marker — the audit still runs.
   小红书 readers skim: lead each point with the payoff, then the detail.

3. **配图图说 (image captions/overlays)** — for each of 3-6 images, the overlay text +
   a one-line caption. 封面图 text is the most important asset (see below). List a
   **shot list**: which screenshots the human must grab (the tool's UI, a real result).

4. **封面图 (cover)** — the single highest-leverage asset on 小红书. A big-type 标题 +
   one visual hook, readable as a thumbnail. The system has no image sub-agent yet, so
   produce: cover copy (大字主标题 ≤ 12 字 + 副标题) + optionally an SVG/HTML mockup.

5. **话题 (hashtags)** — 4-8 at the end: a mix of broad (#AI #程序员) + specific
   (#Cursor #AI编程 #vibecoding). Chinese tags; match what the audience actually searches.

**Tone:** 真诚分享体, not 测评体. "我试了下…", "踩了个坑…", "最香的是…". Avoid the
去-AI-味 tells (see [[style_patterns]] §3) — 小红书 punishes formulaic AI prose hard.

**Word-count contract:** for a 小红书 piece set the section `word_min/word_max` low
(e.g. a 3-node post: ~200-320 字 per node) so total body lands ~600–900 字.

**How to post (hand-off to the human):** 小红书 App → ➕发布 → 上传封面 + 配图（封面放第一张）
→ 标题贴进标题栏 → 正文贴进正文框 → 末尾逐个加 #话题 → 发布。`[Sn]` 标记在贴前可保留为
文末"参考来源"链接，或精简为一句"资料来自 Cursor 官方 + TechCrunch 等"。

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
- Body → a **plain-text** file `post_xiaohongshu.txt` in the article folder (NO markdown
  `#`/`##`, no `标题:` labels) — 小红书 does not render markdown, so a clean .txt pastes
  cleanly. Hashtags listed at the bottom but flagged "用 # 选，别直接粘" (pasted `#tags`
  do NOT link to topics; she must pick them via 小红书's # picker).
- Images → **PNG** files in `<article>/assets/` (cover.png + 1 real screenshot is enough;
  2 images total). Official-page screenshots via the playwright browser; in-app shots are
  hers to take.

**Source:** 小红书 试水; first applied to the Cursor-mobile-app article; calibrated
2026-06-30 by diffing the generated draft against the author's actual published post.

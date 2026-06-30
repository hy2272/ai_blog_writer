# 小红书 default paradigm: image long-form + shortened caption + hook cover

**When this applies:** the output stage (S7) for a 小红书 piece. This refines
[[xiaohongshu-output-mode]] with the concrete 爆款 paradigm the default adapter targets.
It governs the two assets the deterministic adapter cannot derive well on its own — the
**cover hook title** and the **shortened caption** — which the agent writes into a meta
sidecar.

**Reference shape (calibrated against a real 科技/AI 爆款):**
"我用了一年Claude Code，确信这6件事会发生" — first person + a number + a curiosity gap,
each prediction one card, a short teaser caption. The useful content lives in the images;
the caption only sells the save/read.

## The split (why a sidecar, not pure string-building)
The card bodies are mechanical and must stay machine-correct (verified text, `[Sn]` kept,
no overflow) — the adapter owns those. The cover hook and the caption are **editorial /
网感** judgement — an LLM job. So the agent writes `xhs_meta.json`; the adapter consumes
it and falls back to the dry article title only when it is absent.

```json
{
  "cover_title": "用了一年X，我确信这6件事会发生",
  "cover_subtitle": "技术帖长图版 · 先看结论再看依据",
  "caption": "谁懂啊…（hook）。先码后看，干货全在图里。别划走。"
}
```

Build with:
```
python3 tools/xhs_image_post.py articles/article_<slug>/final.md \
  --out-dir articles/article_<slug>/assets/xhs \
  --meta articles/article_<slug>/xhs_meta.json --check-caption
```

## Cover title — the highest-leverage asset (≤ 14 字)
- **Quantify it.** A number beats an adjective: 「这6件事」「省了3小时」「踩了5个坑」.
  量化制造爽感和价值感 — the single strongest cover technique. *Calibrated against real
  data (`tools/xhs_research.py`, keyword 「AI编程」, n=26, 2026-07-01): titles containing a
  number had ~4.3× the median engagement of those without (11,196 vs 2,602). Small,
  noisy sample — directional, not precise — but the effect is large enough to act on.*
- **First person + stake.** 「我用了一年…」「亲测」「我赌」 — earned experience, not 测评体.
- **Curiosity gap.** Promise a payoff without giving it: 「确信这6件事会发生」「最后一个最意外」.
- Readable as a thumbnail; `card_01` is the cover.

## Caption — a shortened teaser, NOT the article
- AIDA: hook (Attention) → why it matters to you (Interest/Desire) → 收藏/关注 (Action).
- 口语 + 网感, used sparingly and naturally (never stacked): 「谁懂啊」「听劝」「别划走」
  「先码后看」「一整个…住」「救命」. Stacking them reads as fake — pick one.
- End on a save/read CTA; the full content is already in the images.
- Hashtags are appended by the adapter with the 「用#选别直接粘」 note — do not paste `#tags`
  into the caption prose yourself.

## The hard edge (machine-checkable, project DNA)
A shortened teaser is the one place an invented fact can slip in past the citation audit
(the audit ran on the body, not the caption). So the adapter checks: **every number in
the caption must already appear in the verified body.** `--check-caption` exits nonzero on
a violation; `content_manifest.json.caption_unverified_numbers` lists them. A 网感 caption
still may not invent a 「提升99%」 that the body never claimed.

## Style hard rules still apply (see [[style_patterns]] §7)
小红书 body/caption: no 破折号; dates have no space (`6月29日`); 网感 ending; keep `[Sn]`
markers in the image text. The 去-AI-味 tells in §3 apply doubly — 小红书 punishes
formulaic AI prose hard.

**Source:** 小红书 试水; paradigm calibrated 2026-06-30 against a 科技/AI 图文爆款
(first-person + numbered-prediction listicle) and the platform's standard 封面/标题/结构
公式 (AIDA, 量化封面, 口语化).

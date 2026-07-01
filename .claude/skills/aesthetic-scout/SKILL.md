---
name: aesthetic-scout
description: Aesthetic-track (aesthetic_lifestyle mode) concept workflow + output contract. Read-by-path by the scout shell when the orchestrator dispatches S1 on the aesthetic track. No web — the mood pack is created, not researched.
disable-model-invocation: true
---

# aesthetic-scout — the mood pack (no research)

You are the scout shell running in **aesthetic mode**. There is nothing factual to fetch here: an
aesthetic post has no claims and no source pack. Your job is to CREATE a compact **mood pack** — the
theme, tone, and card arc the three writer variants will realize. **Do not use WebSearch/WebFetch**;
this mode's workflow has no external-retrieval step. (You may have the tools — capability is not
instruction; the workflow is what you follow.)

Read `common/style_patterns.md` and `common/behavior_notes/aesthetic-track.md` for voice and the
去 AI 味 rules. This skill is the workflow.

## Inputs (from the dispatch)
`theme` (e.g. 《把今天，过成一部电影》) · `card_count` (default 6) · `visual_style` (e.g.
`photo-triptych` / a named preset). Confirm/refine the theme and 栏目 into a coherent mood.

## Workflow
1. Fix the `overline` (default 「生活美学」 — never mention AI) and the `card_count`.
2. Write the **arc**: one beat per card across a day/mood (morning → commute → afternoon → dusk →
   night → 一句独白). Each beat is a one-line direction, not the final card text (the writers write
   the lines).
3. Set a short `tone` note (the feeling: 轻、慢、留白 …) so the three variants stay in one mood.
4. If a real film line / lyric fits the theme, you MAY note it as an UNVERIFIED `quote_candidate`
   (text + work). Do NOT mark it verified — verification (with provenance) is a later step, not the
   scout's.

**Completion criterion:** `mood_pack.json` exists, matches the schema, has `card_count` arc beats,
overline free of any AI mention, and no self-verified quote.

## Output contract
Write `mood_pack.json`. The writer variants and the orchestrator's curate step read it.
```json
{"track":"aesthetic_lifestyle","theme":"…","overline":"生活美学","card_count":6,
 "visual_style":"photo-triptych","tone":"轻、慢、留白",
 "arc":["morning：醒来的光","commute：把通勤走成散步","…","night：一句独白"],
 "quote_candidate":{"text":"…","work":"《情书》"}}
```
`quote_candidate` is optional and always unverified here.

## What you do NOT do
- Do not WebSearch/WebFetch — this mode has no research step.
- Do not write the final card lines (that is the writer's job) or mention AI.
- Do not mark any quote `verified` — you do not hold the key to that check.

## Completion string
`MOOD PACK COMPLETE — mood_pack.json written`

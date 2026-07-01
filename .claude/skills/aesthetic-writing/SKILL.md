---
name: aesthetic-writing
description: Aesthetic-track (aesthetic_lifestyle mode) writing workflow + output contract. Read-by-path by the writer shell when the orchestrator dispatches S3 on the aesthetic track.
disable-model-invocation: true
---

# aesthetic-writing — one 氛围 variant

You are the writer shell running in **aesthetic mode**. You produce ONE independent **variant**
of a 生活美学 / 治愈系 card post: a short poetic card sequence for a theme. No contract, no source
pack, no `[Sn]`, no citation audit — the objective is mood, rhythm, resonance. The orchestrator
dispatches THREE of you and curates; write YOUR take, do not converge on a safe middle (independent
variants are this harness's substitute for a sampling temperature).

Shared rules live in `common/style_patterns.md` and `common/behavior_notes/aesthetic-track.md`
(去 AI 味, the quote-provenance rule) — read them; this skill is the workflow, not a copy of them.

## Inputs (from the dispatch)
`theme` · `overline` (default 「生活美学」) · `card_count` (default 6) · `visual_style` · `variant` number `n`.

## Workflow
1. Write `card_count` short card lines that arc across a day/mood (morning → commute → afternoon
   → dusk → night → 一句独白). One image per card. Keep each card short — `aesthetic_audit` WARNs
   past 32 visible chars; this 栏目 is 一句一卡.
2. Vary the opening character of every card. Two adjacent cards starting on the same character is
   氛围 collapse (the oracle WARNs on it).
3. **No 破折号 (—).** Use 。，： or a new line. No AI 味 / 翻译腔 (see `common/banned_phrases.json`).
   Never mention AI — the overline stays 「生活美学」.
4. If a card uses a real film line / lyric, put it in 「」 (ideally the LAST card) and record it
   under `quotes` with its `work`. Leave `verified` for the curator/verifier — do NOT self-assert
   `verified: true` (a bare boolean is not verification; see the aesthetic-track note).

**Completion criterion:** `sections/aesthetic_variant_<n>.json` exists, matches the schema below,
has `card_count` cards with varied openings, zero 破折号, no AI mention, and any 「」 card carries a
matching `quotes` record (with `work`, `verified` left unset).

## Output contract (this is what downstream consumes — get the shape exactly right)
Write `sections/aesthetic_variant_<n>.json`. The curated final `aesthetic_post.json` (orchestrator
builds it by merging variants) is what `tools/aesthetic_audit.py` gates, so the card/quote shape
here must already be audit-valid.

```json
{"track":"aesthetic_lifestyle","variant":1,"theme":"…","overline":"生活美学",
 "cards":[{"index":1,"total":6,"text":"…"},
          {"index":6,"total":6,"text":"「…」","quote":true}],
 "quotes":[{"text":"…","work":"《情书》"}]}
```
- `cards[].index` is 1..N contiguous; every `total` equals the real card count (the 0X/0N rule).
- A whole-card 「…」 or a `quote:true` card MUST have a matching `quotes[]` entry.
- Do NOT add `verified`, `verified_source`, or `quote_verification_required` — verification is the
  verifier's step, and the writer must not hold the key to its own check.

## What you do NOT do
- Do not cite `[Sn]`, read a source pack, or run `citation_audit.py` — a category error here.
- Do not merge variants or pick a winner — that is the orchestrator's curate step.
- Do not mention AI, use 破折号, or self-mark a quote verified.

## Completion string
`AESTHETIC VARIANT <n> DRAFTED — aesthetic_variant_<n>.json written`

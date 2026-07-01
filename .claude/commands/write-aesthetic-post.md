---
description: Write a 生活美学 / 治愈系 aesthetic card post (non-factual track). Diversity-by-variants, no fact gates.
---

Enter the orchestrator playbook at `.claude/orchestrator.md` on the **aesthetic track**
(`track: aesthetic_lifestyle`). This is the non-factual pipeline — the fact machine is a
category error on poetry, so the citation / grounding / fact-check gates are SKIPPED and
the oracle shrinks to `tools/aesthetic_audit.py`.

Theme: $ARGUMENTS

Read first: `.claude/orchestrator.md` (S0 track router), `common/style_patterns.md`,
`common/behavior_notes/aesthetic-track.md`, `common/behavior_notes/ai-image-card-pipeline.md`.

## Steps

1. **S0 — set the track.** Scaffold with `/new-article <slug>` if needed; set the STATE.md
   `track` block to the `aesthetic_lifestyle` variant (`fact_gates: false`,
   `quote_verification_required: true`, `visual_style: photo-triptych` or a named preset).
   Confirm the theme + 栏目 (e.g. 《把今天，过成一部电影》) and the card count (default 6).

2. **S2-lite — concept.** One short concept: 主题 / overline (「生活美学」, never mention AI) /
   tone / the 6-card arc (morning → commute → afternoon → dusk → night → 一句独白). No
   fact contract; no source pack.

3. **S3 — diversity by variants (the aesthetic substitute for temperature).** Dispatch the
   **`aesthetic-writer`** (NOT the factual `writer` — that one implements a contract + cites a
   source pack, the wrong objective here) **three times independently**. This harness cannot
   set a sampling temperature on a subagent, so independent variants ARE the diversity knob.
   Each writes `sections/aesthetic_variant_<n>.json`. Then **curate**: you (the orchestrator)
   merge the strongest line per card into one final set — do not just pick one variant
   wholesale. Log the merge choices in DECISIONS.md. Keep each card short (aesthetic_audit
   WARNs past ~32 chars).

4. **Quote verification (the ONE residual fact surface).** If a card quotes a real film line /
   lyric / attribution, verify the exact wording + its work with a quick web check and record
   it in the post JSON `quotes` list with BOTH `verified: true` AND provenance
   (`verified_source`: the URL you checked, or `verified_by`: who@date). A bare `verified:true`
   is self-certifying and the audit rejects it — provenance is the aesthetic version of the
   news track's dated-URL rule. If you cannot verify, drop the attribution (keep it as a free
   paraphrase). Every quote CARD must have a matching, verified record. This is the aesthetic
   track's whole oracle for facts.

5. **S5 — humanize.** Remove AI 味 per `style_patterns.md`. No 破折号. Overline stays 「生活美学」.

6. **Assemble the aesthetic post JSON** (`aesthetic_post.json`) — the deliverable the audit
   consumes:
   ```json
   {"track":"aesthetic_lifestyle","theme":"…","overline":"生活美学",
    "visual_style":"photo-triptych",
    "cards":[{"index":1,"total":6,"text":"…"}, …,
             {"index":6,"total":6,"text":"「…」","quote":true}],
    "caption":"… #生活美学 #治愈系日常","hashtags":["#生活美学","#治愈系日常"],
    "quotes":[{"text":"…","work":"《情书》","verified":true}]}
   ```

7. **S6-oracle — the aesthetic audit (machine gate).**
   `python3 tools/aesthetic_audit.py articles/article_<slug>/aesthetic_post.json`
   FAIL (破折号 / unbalanced 「」/ bad 0X-0N numbering / AI in overline / unverified attributed
   quote / banned phrase) → fix and re-run. This is the HARD gate for this track; only PASS
   advances. (`--strict` promotes the WARN checks — long cards, misplaced quote card, missing
   hashtags — to failures.)

8. **Visuals — decoupled from text.** Generate background images with
   `tools/gen_image.py` (prompt MUST say `no text`; all card text is rendered by the adapter,
   never burned into the AI image). Record provenance with `--manifest`; verify a prompt with
   `--dry-run` (no API cost) before spending. Reference the image files from the post JSON
   (`images.cover_bands` / `images.body_images` / `images.font`).

9. **Render from the audited JSON (single source of truth).** Render the SAME
   `aesthetic_post.json` the audit passed — do NOT hand-write a separate markdown, which could
   drift from the audited text:
   `python3 platforms/xiaohongshu/adapter.py --aesthetic-json articles/article_<slug>/aesthetic_post.json --out-dir articles/article_<slug>/assets/xhs`
   The adapter builds cards straight from the JSON (forces photo-triptych, no `[Sn]`), and
   `content_manifest.json` records each card's `text` so the published cards provably match
   the audited object.

## Hard rules (aesthetic track)
- Do NOT run citation_audit / grounding / fact-check — they are a category error here.
- Do NOT mention AI anywhere (overline 「生活美学」, not 「AI·生活美学」).
- Verify any named quote; everything else is free poetic prose.
- The AI image carries NO text; the adapter renders every character.

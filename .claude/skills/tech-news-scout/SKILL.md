---
name: tech-news-scout
description: Factual AI-news track (factual_ai_news mode) research workflow + output contract. Read-by-path by the scout shell when the orchestrator dispatches S1 on the factual track.
disable-model-invocation: true
---

# tech-news-scout — dated source pack

You are the scout shell running in **factual mode**. You gather the factual ground truth for one
AI-hot-topic article. Your output is the baseline every later section is checked against, so
**accuracy and dating matter more than volume**. The hard edge (CLAUDE.md): no claim without a
dated source.

## Workflow
1. Run live `WebSearch` on the topic + its sub-angles. Prefer PRIMARY sources (the lab's own post,
   the paper, the official release) over secondary commentary. Consult `common/source_authority.json`
   for tier-1 (primary) / tier-2 (reputable) / blacklisted domains — anchor the angle on tier-1/2,
   never on a blacklisted aggregator (resolve it to the primary publisher).
2. `WebFetch` each candidate to confirm it says what the title implies, and pull the publication
   date. **No parseable date → the source is unusable for an AI-hot-topic piece; drop it.**
3. Write `source_pack.json` with stable `S<n>` ids (the writer cites these exact ids):
```json
{"sources":[
  {"id":"S1","url":"…","title":"…","date":"YYYY-MM-DD","publisher":"…",
   "tier":"tier1|tier2|unknown","note":"what it supports"}
]}
```
   Tag each `tier` by matching its domain against `common/source_authority.json` (the citation audit
   re-derives this from the domain, so the field is for the human + S0 reuse — tag it honestly). If
   every source is `unknown`, that is a research-quality flag: surface it for the human gate.
4. Write `research_brief.md`: the proposed angle, the 5-8 strongest sources with one line each on
   what claim they support, and any contradiction between sources (flag it — do not pick a side).
5. Write `stage_results/S1-research.json` with `stage:"S1-research"`, `status`, `files`, and any
   contradictions / source gaps as `findings`.

**Completion criterion:** `source_pack.json` (every source dated + id'd), `research_brief.md`, and
`stage_results/S1-research.json` are written; the brief surfaces any contradiction or all-`unknown`
tier gap for the human angle gate.

## Output contract
`source_pack.json` (schema above) is consumed by every later stage and by `citation_audit.py`.
`research_brief.md` is what the human reads at the S1 angle gate.

## What you do NOT do
- Do not write article prose or an outline (that is editorial's job).
- Do not include a source without a parseable `date`.
- Do not resolve a factual contradiction yourself — surface it for the human gate.
- Do not invent or guess a URL, date, or statistic.

## Completion string
`RESEARCH COMPLETE — source_pack.json + brief written`

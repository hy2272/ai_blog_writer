---
name: tech-news-writing
description: Factual AI-news track (factual_ai_news mode) writing workflow + output contract. Read-by-path by the writer shell when the orchestrator dispatches S3 on the factual track.
disable-model-invocation: true
---

# tech-news-writing — one cited section

You are the writer shell running in **factual mode**. You write ONE section of the article in
Chinese, implementing its contract exactly and citing every factual claim, then iterate on
fact-check / grounding / citation-audit findings until the section passes. Your governing law is
the section contract; your ground truth is the source pack.

Shared voice lives in `common/style_patterns.md`; glob `common/behavior_notes/` for relevant notes
(e.g. `freshness-and-sourcing.md`). This skill is the workflow, not a copy of them.

## Inputs (from the dispatch)
The section number `k`, its `contracts/sec<k>_contract.md` + `.json`, and `source_pack.json`.

## The iteration loop
1. Draft `sections/sec<k>_draft.md` covering every "Must cover" bullet, hitting the word range,
   in the voice from `style_patterns.md`.
2. **Cite as you write.** Every factual sentence (a number, date, named release, quote, claim)
   carries an inline `[Sn]` marker resolving to a source in the pack. If you cannot cite a claim,
   you may NOT state it as fact — soften it to clearly-marked analysis, or drop it and flag the gap.
3. Self-run the oracle before declaring done (dispatcher picks citation_audit for this mode):
   `python3 tools/run_oracle.py --mode factual_ai_news sections/sec<k>_draft.md -- --source-pack <pack> --contract <contract.json>`
4. On FAIL: read each finding, fix the specific sentence (add the missing `[Sn]`, correct an
   invalid id, meet a missing keyword), re-run. **Do not declare done on red.**
5. Write `sections/sec<k>_writer.json` (see the output contract). Write ONLY this stage's file —
   never a shared `sec<k>_result.json` (the next stage would overwrite it and destroy resume state).

**Completion criterion:** `sections/sec<k>_draft.md` passes `run_oracle --mode factual_ai_news`
(exit 0) with every "Must cover" bullet covered, and `sec<k>_writer.json` is written.

## Output contract
- `sections/sec<k>_draft.md` — Chinese prose; every factual sentence carries an `[Sn]` marker
  resolving to a `source_pack.json` id. This is what `citation_audit.py` (via the dispatcher) gates.
- `sections/sec<k>_writer.json`:
```json
{"stage":"S3-writer","section":1,"status":"pass",
 "files":["sections/sec1_draft.md"],"findings":[]}
```
  Use `status:"blocked"` + a `findings` entry when you are handing a problem back (see below).

## When the contract is wrong
If the contract requires a claim no source supports, or contradicts the source pack, STOP and flag
it to the orchestrator (`status:"blocked"`). Do not guess a reading or fabricate a source to satisfy
it.

## What you do NOT do
- Do not edit the contract or the source pack (those are inputs / law).
- Do not write sections other than the one dispatched.
- Do not state a fact you cannot cite. No `[Sn]` → not a fact.
- Do not invent a source id to silence the auditor.

## Completion string
`SECTION <k> DRAFTED — sec<k>_draft.md written`

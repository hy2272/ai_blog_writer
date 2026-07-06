# RUNBOOK — writing one article, end to end

The step-by-step. Conventions live in `CLAUDE.md`; the stage logic in
`.claude/orchestrator.md`; the per-article state in `articles/article_<slug>/STATE.md`.

## A. Start
1. `/new-article <slug>` — scaffold the workspace.
2. Pick the track (S0 sets the STATE.md `track` block; it decides which gates run):
   - factual AI-news → `/write-article <topic>` (the pipeline in §B).
   - 生活美学 / 治愈系 / 诗意 card post → `/write-aesthetic-post <theme>` (§B-aesthetic).

## B-aesthetic. The aesthetic track (non-factual)
No fact machine — poetry has no `[Sn]` claims, so citation / grounding / fact-check are a
category error and are skipped. Flow: scout (`aesthetic-scout` skill → `mood_pack.json`, no web)
→ editorial-lite → **3 independent `writer` variants (`aesthetic-writing` skill) → curate/merge**
→ verify only a quoted film line → humanize → S5.5 Gemini polish (high temp) → `aesthetic_post.json` →
`tools/aesthetic_audit.py` (HARD gate: 破折号 / card length / banned phrases / 「」 closure /
0X-0N numbering / overline / quote verification) → `adapter.py --style photo-triptych`.
See `common/behavior_notes/aesthetic-track.md`.

## B. The pipeline (what happens, where it stops)
| Stage | Agent | Output | Gate? |
|---|---|---|---|
| S0 topic + decompose | you (main) | section node list in STATE.md | — |
| S1 scout | scout (`tech-news-scout` skill) | `source_pack.json` + brief (English) | ⏸ human approves angle |
| S2 editorial | editorial | per-section contracts (Chinese) | (⏸ if complex) |
| S2→3 grounding 1→2 | grounding-checker | outline grounded in sources | ⏸ PASS to advance |
| S3 write → fact-check → fix | writer (`tech-news-writing` skill), then fact-checker — **all sections in parallel waves** | section drafts + factchecks | — |
| S3→4 grounding 2→3 | grounding-checker (per section, inside the wave) | draft grounded in outline | ⏸ PASS to advance |
| S4 citation audit | citation-auditor (per section, inside the wave) | audit verdict | ⏸ HARD: every `sec<k>_audit.json` = pass |
| S5 humanize | humanizer | de-flavored draft (audit re-run) | — |
| S5.5 Gemini polish | you (`gemini_polish.py`) | polished draft + oracle-checked diff | ⏸ human picks in diff at S6 |
| S5.9 findings triage | findings-triage (optional; skip when zero findings) | deduped, source-verified worklist | — |
| S6 editorial review | editorial-reviewer ×2-3 panel, majority merge | BLOCKER/WARN/NOTE | you decide → fixer |
| S7 output | output | `final.md` / `final.html` | article audit green |

S3 concurrency: sections have disjoint files and independent contracts, so the
orchestrator dispatches every unconverged section's next step in one parallel message
(wave), looping until every section's `sec<k>_audit.json` says pass. Within one section
the chain stays sequential; the per-section step budget (max 3 iterations) still applies.
Every dispatch/result/gate lands in `run_journal.jsonl` (`tools/journal.py`), which is
also where token/cost totals come from (`/status` shows the cost column).

## C. Resuming a paused article
Reconcile three layers, in order: per-stage result JSONs (what is GREEN) →
`run_journal.jsonl` (what RAN: dispatch counts, step budget, costs, human decisions) →
`STATE.md` (the human-readable summary). If STATE.md lags the journal, backfill it from
the journal + result files, then re-enter at the first not-done stage. `/status` prints
the matrix (+ cost column); `python3 tools/journal.py summary <dir>` prints the ledger
rollup.

## D. Re-running one section
`/write-section <k>` runs only that section's write → fact-check → grounding → audit loop. Use it
when S4 fails a single section or S6 flags one section for a fix.

## E. The self-improvement step (do not skip)
After S6, if a recurring AI-tell or sourcing mistake showed up, write it back:
- durable voice rule → a line in `common/style_patterns.md`;
- conditional technique → a note in `common/behavior_notes/` (copy `_TEMPLATE.md`).
This is the compounding-quality loop. An article that taught you nothing back is a
missed opportunity.

## F. Definition of done
See `.claude/runtime.md` — (1) audit PASS every section; (2) all claims SUPPORTED +
`audit_article.py --check-links --strict` green; (3) human sign-off at S6.

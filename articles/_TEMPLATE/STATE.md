# STATE — article_<slug>

Resumable pipeline state. The orchestrator updates this after every stage. To resume,
read this file and re-enter at the first stage not marked done.

- **slug:** <slug>
- **topic:** <one line>
- **angle:** <the approved take — filled at S1 gate>
- **research as-of date:** <YYYY-MM-DD — pins the audit --as-of>

## Track (set at S0 — decides which gates run)
The content track is a first-class field, not an inference the agents make mid-run. The
orchestrator reads it at S0 and routes gates accordingly (see `.claude/orchestrator.md`
S0 track router). Copy the block that matches; delete the other.

```json
{
  "track": "factual_ai_news",
  "platform": "xiaohongshu",
  "fact_gates": true,
  "quote_verification_required": false,
  "visual_style": "typographic-cards",
  "gemini_polish": true,
  "gemini_temperature": 0.3
}
```

```json
{
  "track": "aesthetic_lifestyle",
  "platform": "xiaohongshu",
  "fact_gates": false,
  "quote_verification_required": true,
  "visual_style": "photo-triptych",
  "gemini_polish": true,
  "gemini_temperature": 0.85
}
```

- `fact_gates`: whether S1 scout / grounding / fact-check / citation-audit / source-
  authority run. `true` for factual, `false` for aesthetic (those gates are a category
  error on non-factual prose — see `behavior_notes/aesthetic-track.md`).
- `quote_verification_required`: aesthetic posts skip fact gates but MUST still verify any
  named film line / lyric / attribution (the residual fact surface) via `aesthetic_audit.py`.
- `visual_style`: the card style preset (`typographic-cards`, `photo-triptych`, or a named
  preset like `film_morning`).
- `gemini_polish`: whether the S5.5 Gemini polish pass runs (default `true`, all tracks). The
  polish is never auto-applied — the orchestrator prepares a diff for the S6 human gate.
- `gemini_temperature`: the sampling temperature for that pass. Low (0.3) for factual/explainer
  (don't reword facts); high (0.85) for aesthetic (want a fresher phrasing — the aesthetic oracle
  + diff catch any overreach). See `behavior_notes/gemini-polish-pass.md`.

`mixed_explainer` is RESERVED (needs a paragraph-level claim classifier that does not exist
yet) — do not use it; pick `factual_ai_news` or `aesthetic_lifestyle`.

## Section nodes (set at S0)
| k | section purpose | status | loop count | audit |
|---|---|---|---:|---|
| 1 | <purpose> | todo | 0 | — |
| 2 | <purpose> | todo | 0 | — |
| 3 | <purpose> | todo | 0 | — |

## Stage progress
| stage | status | note |
|---|---|---|
| S0 decompose | todo | |
| S1 scout | todo | ⏸ human angle gate |
| S2 editorial | todo | |
| S2→3 grounding (1→2) | todo | ⏸ outline grounded in sources |
| S3 write → fact-check → fix | todo | all sections in parallel waves |
| S3→4 grounding (2→3) | todo | ⏸ draft grounded in outline (per section) |
| S4 citation audit | todo | ⏸ HARD gate — every sec<k>_audit.json pass |
| S5 humanize | todo | |
| S5.9 findings triage | todo | optional 归口 — skip if zero findings |
| S6 editorial review | todo | 2-3 reviewer panel, majority merge |
| S7 output | todo | |

## Open items
- BLOCKER: none
- WARN: none

## Machine-readable state
- Article-level stages write one file per stage under `stage_results/`.
- Section stages write per-stage files: `sections/sec<k>_writer.json`,
  `sec<k>_factcheck.json`, `sec<k>_grounding.json`, `sec<k>_audit.json`.
- The orchestrator appends every dispatch/result/gate/human decision (+ tokens/cost when
  known) to `run_journal.jsonl` via `tools/journal.py` — the append-only run ledger.
- Treat this Markdown file as the human-readable summary. On resume, reconcile in this
  order: result JSONs + artifacts (what is green) → `run_journal.jsonl` (what ran:
  budgets, costs, decisions) → this file; backfill this file from the journal when it
  lags (see `.claude/orchestrator.md` "State you own").

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
  "visual_style": "typographic-cards"
}
```

```json
{
  "track": "aesthetic_lifestyle",
  "platform": "xiaohongshu",
  "fact_gates": false,
  "quote_verification_required": true,
  "visual_style": "photo-triptych"
}
```

- `fact_gates`: whether S1 research / grounding / fact-check / citation-audit / source-
  authority run. `true` for factual, `false` for aesthetic (those gates are a category
  error on non-factual prose — see `behavior_notes/aesthetic-track.md`).
- `quote_verification_required`: aesthetic posts skip fact gates but MUST still verify any
  named film line / lyric / attribution (the residual fact surface) via `aesthetic_audit.py`.
- `visual_style`: the card style preset (`typographic-cards`, `photo-triptych`, or a named
  preset like `film_morning`).

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
| S1 research | todo | ⏸ human angle gate |
| S2 editorial | todo | |
| S2→3 grounding (1→2) | todo | ⏸ outline grounded in sources |
| S3 write → fact-check → fix | todo | |
| S3→4 grounding (2→3) | todo | ⏸ draft grounded in outline |
| S4 citation audit | todo | ⏸ HARD gate |
| S5 humanize | todo | |
| S6 editorial review | todo | |
| S7 output | todo | |

## Open items
- BLOCKER: none
- WARN: none

## Machine-readable state
- Article-level stages write one file per stage under `stage_results/`.
- Section stages write `sections/sec<k>_result.json`.
- Treat this Markdown file as the human-readable summary; when there is disagreement,
  inspect the JSON result files and the concrete artifacts before resuming.

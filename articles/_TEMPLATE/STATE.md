# STATE — article_<slug>

Resumable pipeline state. The orchestrator updates this after every stage. To resume,
read this file and re-enter at the first stage not marked done.

- **slug:** <slug>
- **topic:** <one line>
- **angle:** <the approved take — filled at S1 gate>
- **research as-of date:** <YYYY-MM-DD — pins the audit --as-of>

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

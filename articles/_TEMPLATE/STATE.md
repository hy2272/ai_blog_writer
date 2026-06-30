# STATE — article_<slug>

Resumable pipeline state. The orchestrator updates this after every stage. To resume,
read this file and re-enter at the first stage not marked done.

- **slug:** <slug>
- **topic:** <one line>
- **angle:** <the approved take — filled at S1 gate>
- **research as-of date:** <YYYY-MM-DD — pins the audit --as-of>

## Section nodes (set at S0)
| k | section purpose | status | audit |
|---|---|---|---|
| 1 | <purpose> | todo | — |
| 2 | <purpose> | todo | — |
| 3 | <purpose> | todo | — |

## Stage progress
| stage | status | note |
|---|---|---|
| S0 decompose | todo | |
| S1 research | todo | ⏸ human angle gate |
| S2 editorial | todo | |
| S2→3 grounding (1→2) | todo | ⏸ outline grounded in sources |
| S3 write ∥ fact-check | todo | |
| S3→4 grounding (2→3) | todo | ⏸ draft grounded in outline |
| S4 citation audit | todo | ⏸ HARD gate |
| S5 humanize | todo | |
| S6 editorial review | todo | |
| S7 output | todo | |

## Open items
- BLOCKER: none
- WARN: none

# STATE — article_demo

Resumable pipeline state. The orchestrator updates this after every stage. To resume,
read this file and re-enter at the first stage not marked done.

- **slug:** demo
- **topic:** June 2026 AI model-release cluster
- **angle:** 推理能力与长上下文正在从厂商卖点变成新一代模型的默认竞争项。
- **research as-of date:** 2026-06-09

## Section nodes (set at S0)
| k | section purpose | status | loop count | audit |
|---|---|---|---:|---|
| 1 | Show the June release cluster and its shared emphasis on reasoning + long context. | done | 1 | PASS |

## Stage progress
| stage | status | note |
|---|---|---|
| S0 decompose | done | synthetic one-section demo |
| S1 research | done | source_pack.json has three dated sources |
| S2 editorial | done | outline.md + sec1 contract |
| S2→3 grounding (1→2) | skipped | demo only includes 2→3 fixture |
| S3 write → fact-check → fix | done | synthetic draft |
| S3→4 grounding (2→3) | done | grounding_2to3.json PASS |
| S4 citation audit | done | citation_audit PASS |
| S5 humanize | skipped | not needed for smoke test |
| S6 editorial review | skipped | not needed for smoke test |
| S7 output | skipped | not needed for smoke test |

## Open items
- BLOCKER: none
- WARN: none

## Machine-readable state
- Article-level stages write one file per stage under `stage_results/`.
- Section stages write `sections/sec<k>_result.json`.
- Treat this Markdown file as the human-readable summary; when there is disagreement,
  inspect the JSON result files and the concrete artifacts before resuming.

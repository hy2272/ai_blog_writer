# RUNBOOK — writing one article, end to end

The step-by-step. Conventions live in `CLAUDE.md`; the stage logic in
`.claude/orchestrator.md`; the per-article state in `articles/article_<slug>/STATE.md`.

## A. Start
1. `/new-article <slug>` — scaffold the workspace.
2. `/write-article <topic>` — enter the orchestrator at S0.

## B. The pipeline (what happens, where it stops)
| Stage | Agent | Output | Gate? |
|---|---|---|---|
| S0 topic + decompose | you (main) | section node list in STATE.md | — |
| S1 research | research | `source_pack.json` + brief (English) | ⏸ human approves angle |
| S2 editorial | editorial | per-section contracts (Chinese) | (⏸ if complex) |
| S2→3 grounding 1→2 | grounding-checker | outline grounded in sources | ⏸ PASS to advance |
| S3 write → fact-check → fix | writer, then fact-checker | section draft + factcheck | — |
| S3→4 grounding 2→3 | grounding-checker | draft grounded in outline | ⏸ PASS to advance |
| S4 citation audit | citation-auditor | audit verdict | ⏸ HARD: PASS to advance |
| S5 humanize | humanizer | de-flavored draft (audit re-run) | — |
| S6 editorial review | editorial-reviewer | BLOCKER/WARN/NOTE | you decide → fixer |
| S7 output | output | `final.md` / `final.html` | article audit green |

## C. Resuming a paused article
Read `articles/article_<slug>/STATE.md`; it records the last done stage and per-section
verdicts. Re-enter at the first not-done stage. `/status` prints the table.

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

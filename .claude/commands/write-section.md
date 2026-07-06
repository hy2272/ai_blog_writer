---
description: (Re-)run a single section's write → fact-check → grounding → citation-audit loop.
---

Run the S3-S4 loop for ONE section without redoing the others. (This is the sequential
single-section path — a full `/write-article` run fans ALL sections out in parallel
waves; see `.claude/orchestrator.md` S3.)

Section number: $ARGUMENTS

Steps (orchestrator):
1. Read the section's contract (`contracts/sec<k>_contract.md` + `.json`) and STATE.md.
2. Dispatch the `writer` shell for section <k> with mode `factual_ai_news`, naming the
   `.claude/skills/tech-news-writing/SKILL.md` skill to follow.
3. Dispatch `fact-checker` against the draft that writer produced. If any claim is not
   SUPPORTED, loop back to `writer` with the exact findings.
4. Dispatch `grounding-checker` for 2→3. It must cite `outline_ids`; `source_ids` are optional.
5. Dispatch `citation-auditor` for section <k>.
6. If grounding or AUDIT FAIL → loop back to `writer` with the findings until PASS.
7. Update STATE.md; each agent writes its own per-stage file (`sec<k>_writer.json`,
   `sec<k>_factcheck.json`, `sec<k>_grounding.json`, `sec<k>_audit.json`). Run
   `python3 tools/status.py articles/article_<slug>` for the section × stage matrix.
8. Journal as you go (`tools/journal.py append …`): a `dispatch` event before each
   agent, a `result` when it returns, a `gate` per oracle exit — same ledger discipline
   as the full pipeline, so resume and the step budget stay truthful.

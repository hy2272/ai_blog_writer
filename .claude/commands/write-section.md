---
description: (Re-)run a single section's write → fact-check → grounding → citation-audit loop.
---

Run the S3-S4 loop for ONE section without redoing the others.

Section number: $ARGUMENTS

Steps (orchestrator):
1. Read the section's contract (`contracts/sec<k>_contract.md` + `.json`) and STATE.md.
2. Dispatch `writer` for section <k>.
3. Dispatch `fact-checker` against the draft that writer produced. If any claim is not
   SUPPORTED, loop back to `writer` with the exact findings.
4. Dispatch `grounding-checker` for 2→3. It must cite `outline_ids`; `source_ids` are optional.
5. Dispatch `citation-auditor` for section <k>.
6. If grounding or AUDIT FAIL → loop back to `writer` with the findings until PASS.
7. Update STATE.md and `sections/sec<k>_result.json` with the section verdict.

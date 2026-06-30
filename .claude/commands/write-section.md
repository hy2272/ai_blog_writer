---
description: (Re-)run a single section's write → fact-check → citation-audit loop.
---

Run the S3-S4 loop for ONE section without redoing the others.

Section number: $ARGUMENTS

Steps (orchestrator):
1. Read the section's contract (`contracts/sec<k>_contract.md` + `.json`) and STATE.md.
2. Dispatch `writer` and `fact-checker` for section <k> in parallel.
3. Dispatch `citation-auditor` for section <k>.
4. If AUDIT FAIL → loop back to `writer` with the findings until PASS.
5. Update STATE.md with the section verdict.

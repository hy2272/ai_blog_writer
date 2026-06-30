# Section 1 contract — <purpose in a few words>

Contract is law: the writer implements this, the fact-checker tests against it, the
citation auditor validates against it. If it is wrong, STOP and flag — do not write
around it. Companion machine-readable file: `sec1_contract.json`.

## Purpose
<the one job this section does in the article's arc>

## Must cover
- <claim cluster bullet 1>
- <claim cluster bullet 2>

## Must cite
- <source ids this section depends on, e.g. S1, S3>

## Voice / length
- Target: <word_min>-<word_max> words. Voice per `common/style_patterns.md`.
- <any tone note specific to this section>

## Acceptance (Given / When / Then)
- Given the section draft, When run through `citation_audit.py`, Then it PASSes with
  no FAIL findings.
- Given the draft, Then every numeric/dated claim carries an `[Sn]` marker.
- Given the draft, Then <the must-cite source> is actually cited.

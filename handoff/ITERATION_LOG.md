# Iteration log

A living, append-only record — **one entry per system-iteration PR**, newest first. This
is the lightweight continuity stream that lets the next architect (or Hanfei) resume from
the repo alone, without re-reading every PR. The full per-session `handoff/handoff-<date>.md`
docs remain for session boundaries; this is the per-PR pulse between them.

**Convention (also in CLAUDE.md):** every PR that changes the system appends an entry here
in the same PR — `what / why / risk / verified`. Keep each entry tight; the PR + commit
carry the detail.

---

## 2026-07-01 — #13 factcheck_gate: make "cited but wrong" a machine gate
- **What:** `tools/factcheck_gate.py` — sibling of `grounding_gate.py`. The fact-checker
  emits a per-claim verdict JSON (`sec<k>_factcheck.json`, verdict ∈ SUPPORTED /
  MISATTRIBUTED / UNSOURCED / UNVERIFIED); the gate exits 1 on any non-SUPPORTED claim and
  FAILs **closed** on an empty verdict. Wired into fact-checker.md + orchestrator S3.
- **Why:** Cursor finding #2 + the project's own most-dangerous gap — the green-dashboard
  trap was only LLM/prose-advisory, not machine-enforced. (temperature=0's actionable form:
  structured judge output → Python gate; the gate, not the temperature, is the 保险丝.)
- **Risk:** the gate only validates the verdict structure, not the judge's correctness — a
  same-tier judge can still mis-verdict; this enforces the protocol, not omniscience.
- **Verified:** CI good→PASS; misattributed / unverified / empty → FAIL.

## 2026-07-01 — #11 source-authority: rank cited sources by domain tier
- **What:** `common/source_authority.json` (tier-1/2 allowlist + aggregator blacklist) +
  `citation_audit.py --source-authority` (blacklist→FAIL, no tier-1/2 anchor→WARN, unknown→WARN);
  research records `tier`; `news_discover --min-tier`.
- **Why:** closes the "green-dashboard trap" — cited + faithful didn't prove the *source* is
  authoritative.
- **Risk:** allowlist is a seed, not exhaustive; name-based `--min-tier` is approximate.
- **Verified:** CI tier-1 PASS / blacklist FAIL / no-anchor FAIL under --strict; demo article
  PASSes while flagging two unranked sources.

## 2026-07-01 — #10 xhs_research: 小红书 爆款 calibration
- **What:** `tools/xhs_research.py` scrapes RedNote search via Apify, distils a calibration
  summary (top titles, hashtags, 量化封面 check); grounds the baokuan note in real data.
- **Why:** the paradigm note's strongest claim was hand-waved.
- **Risk:** ToS-gray + per-result cost; small/noisy sample; never run in CI.
- **Verified:** real run n=26 — number-in-title ≈4.3× median engagement.

## 2026-07-01 — #9 news_discover: S0 topic discovery via Apify
- **What:** `tools/apify_client.py` (stdlib) + `tools/news_discover.py` — fresh dated AI
  headlines for S0. Discovery aid, NOT a citation source (Google-News-redirect urls).
- **Why:** switched the news-source plan to Apify after Particle's API proved podcast-only.
- **Risk:** Apify cost per run; CI never runs the actor.
- **Verified:** live run, 8 dated items; offline CI guard for the no-token path.

## 2026-06-30 — #8 xhs baokuan paradigm (meta sidecar + caption fact-check)
- **What:** `--meta xhs_meta.json` (hook cover_title + shortened caption) + `--check-caption`
  (a caption number absent from the verified body → exit nonzero); behavior note.
- **Why:** default 小红书 output should match the real 爆款 paradigm; caption is the one place
  an invented fact can slip past the citation audit.
- **Risk:** caption number-check is Arabic-numeral based (CN-numeral aliasing only for 0–10).
- **Verified:** CI good-meta passes / invented-number fails.

## 2026-06-30 — #7 xhs adapter: split over-wide paragraphs
- **What:** `chunk_paragraphs` splits over-wide paragraphs on sentence boundaries (citations
  stay attached); manifest `max_body_chars` invariant.
- **Why:** cards are the product; a long paragraph silently overflowed a fixed-size card.
- **Risk:** a no-punctuation mega-sentence is hard-split by width (rare).
- **Verified:** CI asserts `max_body_chars <= 430` on a long-paragraph fixture.

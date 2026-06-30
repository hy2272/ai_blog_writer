# CONTEXT.md — domain glossary (the ubiquitous language)

Use these terms exactly; they are the shared vocabulary across agents and docs.

- **article** — the deliverable: one Chinese blog post on an AI hot topic.
- **section node** — the smallest independently-verifiable unit of an article (one
  claim cluster / one angle). The analog of a sas2pyspark "node". 3-5 per article.
- **the angle** — the article's specific take; chosen at S0, approved by the human at S1.
- **source pack** — `source_pack.json`: the dated sources that are the factual ground
  truth. The "baseline" every section is checked against.
- **claim** — a factual assertion (number, date, named release, quote, attribution).
  Every claim must carry a citation. Opinion/analysis is not a claim.
- **citation** — an inline `[Sn]` marker tying a claim to a source-pack id.
- **裸论断 / uncited claim** — a claim-like sentence with no citation. The primary
  hallucination failure mode; the audit FAILs on it.
- **the contract** — `sec<k>_contract.md` + `.json`: the law a section is built and
  judged against (coverage, must-cite, word range, acceptance). Contract is law.
- **the audit / the oracle** — `tools/citation_audit.py`: the machine-checkable gate.
  The article-writer analog of sas2pyspark's per-node diff (`csv_compare_v2`).
- **freshness** — how recent a source is. AI news goes stale fast; the audit WARNs on
  sources older than the threshold.
- **去 AI 味 / de-flavoring** — removing the stylistic tells that mark text as
  model-written (see `style_patterns.md` §3).
- **the gate** — a stage where the orchestrator stops: S1 (human approves angle) and
  S4 (citation audit) are hard gates.
- **advisory review** — S6: the editorial-reviewer judges taste/argument and reports;
  it does not edit or decide. The orchestrator decides.
- **the self-improvement loop** — feeding a shipped tell/error back into
  `style_patterns.md` or `behavior_notes/` so the next article starts better.

# runtime.md — how to run things, where files go

The single catalog of run commands + the per-article layout. Agents resolve "how do I
run the audit / where does this go" HERE — do not hardcode a runtime assumption elsewhere.

## Runtime
The citation audit is pure Python stdlib — **no special environment**. Run it with the
system `python3`. (Contrast sas2pyspark, which needs a JVM + PySpark; this system does
not, by design — the oracle is a text linter, not a data engine.)

```
python3 tools/citation_audit.py <draft.md> \
  --source-pack articles/article_<slug>/source_pack.json \
  --contract    articles/article_<slug>/contracts/sec<k>_contract.json \
  --as-of       <YYYY-MM-DD research date>
```

Flags: `--check-links` (resolve URLs, needs network — final pass only),
`--strict` (WARN→FAIL), `--max-age-days N` (freshness threshold, default 180).
Exit code: 0 = PASS, 1 = FAIL.

The grounding gate (faithfulness, 1→2 and 2→3) turns an LLM verdict into PASS/FAIL:
```
python3 tools/grounding_gate.py <grounding_1to2.json | grounding_2to3.json> \
  --allowed-source-ids S1,S2,S3 \
  --allowed-outline-ids 1,2,3
```
Exit 0 = PASS, 1 = FAIL. The `grounding-checker` agent writes the verdict JSON, then
runs this. Cross-lingual: Chinese downstream judged against English upstream.

Verdict ids are explicit:
- `1->2`: each item must cite `source_ids` from `source_pack.json`.
- `2->3`: each item must cite `outline_ids` from `outline.md`; optional `source_ids`
  can show which original sources still back the claim, but they do not replace outline
  traceability.

The run journal (append-only ledger; the ORCHESTRATOR appends, agents never do):
```
python3 tools/journal.py append articles/article_<slug> --event dispatch \
  --stage S3-writer --section 2 --agent writer
python3 tools/journal.py append articles/article_<slug> --event result \
  --stage S3-writer --section 2 --agent writer --status pass \
  --tokens-total 48213 --cost-usd 0.31        # usage flags only when the harness showed them
python3 tools/journal.py append articles/article_<slug> --event gate \
  --stage S4-citation-audit --section 2 --gate citation_audit --exit-code 0
python3 tools/journal.py summary articles/article_<slug>   # rollup + step-budget counts
```
Events: `dispatch` / `result` / `gate` / `human_gate` / `stage` / `note`. Exit 2 on a
malformed append (nothing written); `summary` is read-only, always exit 0. Stage names =
the result-file stems, so `tools/status.py` joins journal cost onto its matrix (the
`cost` column appears only when `run_journal.jsonl` exists). Resume order:
result JSONs (what is green) → journal (what ran) → STATE.md (summary) — see
`.claude/orchestrator.md` "State you own".

Run the full article audit after humanizing and before output:
```
python3 tools/audit_article.py articles/article_<slug> \
  --as-of <YYYY-MM-DD research date>
python3 tools/audit_article.py articles/article_<slug> \
  --as-of <YYYY-MM-DD research date> --check-links --strict
```
This runs per-section citation audits and, if `final.md` exists, checks the final article
against the union of section `required_keywords` and `must_cite`. The final-stage gate
also checks that each section draft's heading or `<!-- section:<k> -->` marker is present,
that section markers match the number of contracts when markers are used, and that every
source id cited by section drafts is still cited somewhere in `final.md`.

Web research uses the `WebSearch` / `WebFetch` tools (research + fact-checker agents).
Sources are English; the article body is Chinese (see CLAUDE.md "Cross-lingual by design").

Final language polish (optional, last step after both oracles are green):
```
python3 tools/gemini_polish.py <final.txt> --out <final.polished.txt> --dry-run                # cost estimate
python3 tools/gemini_polish.py <final.txt> --out <final.polished.txt> --check-facts            # send + fact-diff
```
Reads `GEMINI_API_KEY` or `GOOGLE_API_KEY` (+ optional `GEMINI_MODEL`) from a gitignored
`.env` at the project root — copy `.env.example`. Fluency only. `--check-facts` diffs
numbers/units pre→post and exits 3 on a mismatch (polish can flip a fact, e.g.
`75% off`→`75折`); then re-run `citation_audit.py` on the polished text for marker integrity.
Cost guard: refuses if estimate > $1 (≈$0.001/post normally). See
`common/behavior_notes/gemini-polish-pass.md`. A bulk run that could exceed $1 → ask Hanfei first.

Default Xiaohongshu output is a long-image technical post:
```
python3 tools/xhs_image_post.py articles/article_<slug>/final.md \
  --out-dir articles/article_<slug>/assets/xhs \
  --meta articles/article_<slug>/xhs_meta.json --check-caption
```
The adapter writes `card_01.html`... always, renders `card_01.png`... when Chrome is
available, and emits `post_xiaohongshu.txt` + `content_manifest.json`. Use `--no-render`
only for CI or environments without Chrome. The `--meta` sidecar supplies the hook
`cover_title` + shortened `caption` (paradigm: `common/behavior_notes/xiaohongshu-baokuan-paradigm.md`);
`--check-caption` fails if the caption invents a number the verified body never claims.

## Per-article layout
`/new-article <slug>` scaffolds:
```
articles/article_<slug>/
  STATE.md              resumable pipeline state (orchestrator owns)
  DECISIONS.md          audit trail: angle, dropped claims, accepted WARNs
  run_journal.jsonl     append-only run ledger: dispatches, results, gate exits,
                        human decisions, tokens/cost (tools/journal.py; orchestrator owns)
  source_pack.json      dated sources (research writes; everyone cites these ids)
  research_brief.md     proposed angle + strongest sources
  outline.md            section order + through-line (editorial writes)
  contracts/
    sec<k>_contract.md      human-readable contract (editorial)
    sec<k>_contract.json    machine-readable, consumed by the audit (editorial)
  sections/
    sec<k>_draft.md         the section prose (writer)
    sec<k>_factcheck.md     claim→verdict table (fact-checker)
    sec<k>_audit.md         tool output + verdict (citation-auditor)
    sec<k>_writer.json      per-stage status/findings (writer)
    sec<k>_factcheck.json   per-stage verdict + factcheck_gate input (fact-checker)
    sec<k>_grounding.json   per-stage status/findings (grounding 2→3)
    sec<k>_audit.json       per-stage status/findings (citation-auditor)
                            — one file per stage; `tools/status.py` aggregates them
  stage_results/
    S1-research.json            machine-readable status/findings (append new stage files, never overwrite prior stages)
    S2-editorial.json
    S5-humanize.json
    S5-9-findings-triage.json      deduped + source-verified worklist (findings-triage, optional)
    S6-editorial-review-<v>.json   one per S6 panel variant (each reviewer writes its own)
    S6-editorial-review.json       canonical panel merge by majority (the ORCHESTRATOR writes this one)
    S7-output.json
  final.md / final.html     the deliverable (output)
  assets/xhs/               default Xiaohongshu long-image post package
```

## Definition of done (3 tiers)
1. `citation_audit.py` PASS on every section (no FAIL findings).
2. fact-checker: every claim SUPPORTED; `audit_article.py` green with `--check-links --strict`.
3. Human editorial sign-off at S6 (angle + argument).

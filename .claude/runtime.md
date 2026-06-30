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
  --allowed-ids S1,S2,S3      # source ids (1→2) or outline item ids (2→3)
```
Exit 0 = PASS, 1 = FAIL. The `grounding-checker` agent writes the verdict JSON, then
runs this. Cross-lingual: Chinese downstream judged against English upstream.

Web research uses the `WebSearch` / `WebFetch` tools (research + fact-checker agents).
Sources are English; the article body is Chinese (see CLAUDE.md "Cross-lingual by design").

Final language polish (optional, last step after both oracles are green):
```
python3 tools/gemini_polish.py <final.txt> --out <final.polished.txt> --dry-run   # cost estimate
python3 tools/gemini_polish.py <final.txt> --out <final.polished.txt>             # send to Gemini
```
Reads `GEMINI_API_KEY` (+ optional `GEMINI_MODEL`) from a gitignored `.env` at the project
root — copy `.env.example`. Fluency only; re-run `citation_audit.py` on the polished text.
Cost guard: refuses if estimate > $1 (≈$0.001/post normally). See
`common/behavior_notes/gemini-polish-pass.md`. A bulk run that could exceed $1 → ask Hanfei first.

## Per-article layout
`/new-article <slug>` scaffolds:
```
articles/article_<slug>/
  STATE.md              resumable pipeline state (orchestrator owns)
  DECISIONS.md          audit trail: angle, dropped claims, accepted WARNs
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
  final.md / final.html     the deliverable (output)
```

## Definition of done (3 tiers)
1. `citation_audit.py` PASS on every section (no FAIL findings).
2. fact-checker: every claim SUPPORTED; final audit green with `--check-links --strict`.
3. Human editorial sign-off at S6 (angle + argument).

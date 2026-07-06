# Orchestrator playbook — aiblog

You are the main session. You own state, dispatch sub-agents, and STOP at every gate.
You are the ONLY coordinator: sub-agents cannot spawn sub-agents. Enter this playbook
via `/write-article`. Do not let this file be dispatched as a sub-agent.

Read `CLAUDE.md`, `.claude/runtime.md`, `common/style_patterns.md` before dispatching.

## State you own
`articles/article_<slug>/STATE.md` is the resumable source of truth. Before any stage,
read it; after any stage, update it. Never redo a stage already marked done.

`articles/article_<slug>/run_journal.jsonl` is the append-only run ledger (agent-fleet
journal pattern). Append one event per orchestration action via `tools/journal.py append`
— `dispatch` before each sub-agent, `result` when it returns (with `--tokens-total` /
`--cost-usd` when the harness surfaces usage; never invent numbers), `gate` for each
oracle exit code, `human_gate` for S1/S6 decisions, `stage` for start/done/skip. Never
edit or rewrite existing lines. Stage names = the result-file stems (`S3-writer`,
`S4-citation-audit`, …) so `tools/status.py` can join cost onto its matrix.

**On resume, reconcile three layers in this order:** (1) per-stage result JSONs + the
artifacts they point to = ground truth for WHAT IS GREEN; (2) the journal = ground truth
for WHAT RAN (dispatch counts / step budget, gate history, costs, human decisions);
(3) STATE.md = the human-readable summary. If STATE.md lags the journal (e.g. a session
died between an agent's return and the STATE update), backfill STATE.md from the journal
+ result files before continuing — the journal fills STATE's blind spots, not the other
way around. `tools/journal.py summary <article_dir>` prints the rollup incl. per-section
writer-dispatch counts (the step budget); `tools/status.py <article_dir>` prints the
stage matrix with the journal's cost column.

## Stage loop

**S0 — topic + decompose (you do this, no sub-agent).**
Pick / confirm the hot topic with the human. Split the article into 3-5 **section
nodes**, each the smallest independently-verifiable unit (one claim cluster, one
angle). Write the node list into STATE.md. Log the angle decision in DECISIONS.md.

**S0 track router (decide FIRST — it selects the pipeline).** Set the `track` block in
STATE.md before anything else; it is a first-class field, never inferred mid-run:
- **`factual_ai_news`** (`fact_gates: true`) — AI hot-topic explainer. Runs the FULL chain
  below: research → contract → grounding → fact-check → citation audit → source authority.
- **`aesthetic_lifestyle`** (`fact_gates: false`) — 生活美学 / 治愈系 / 诗意 card post. The
  fact machine is a category error here (poetry has no `[Sn]` claims), so **SKIP S1 research,
  the grounding gates, S3 fact-check, and S4 citation audit**. Keep editorial (lite), the
  **`aesthetic-writer`** (spawn 3 variants + curate — NOT the factual `writer`; see
  `/write-aesthetic-post`), the humanizer, and taste review. The oracle SHRINKS to
  `tools/aesthetic_audit.py` (破折号 / card length / banned
  phrases / 「」 closure / 0X-0N numbering / overline / **quote verification**). Enter via
  `/write-aesthetic-post`; the runbook is `common/behavior_notes/aesthetic-track.md`.
- **`mixed_explainer`** — RESERVED; not implemented. It needs a paragraph-level claim
  classifier (factual paragraphs get the fact gates; 感受 paragraphs are free prose) that does
  not exist yet. Do NOT select it — a half-built mixed track that silently skips fact gates on
  a factual paragraph is more dangerous than picking a clean single track. Until the classifier
  ships, route a mixed piece to `factual_ai_news` (gate everything) and hand-soften the 感受
  lines, or split it into two posts.
The stages below (S1–S7) are the factual-track chain. For the aesthetic track, follow the
skip list above and jump to the aesthetic runbook.

**S1 — research.** Dispatch `research`. It returns `source_pack.json` (dated sources)
+ a research brief. ⏸ **HUMAN GATE**: present the angle + the 5-8 strongest sources;
ask the human to approve the angle and confirm sources are fresh enough. Do not proceed
without approval. Log dropped angles in DECISIONS.md.

**S2 — editorial.** Dispatch `editorial`. For each section node it writes
`contracts/sec<k>_contract.md` + a machine-readable `contracts/sec<k>_contract.json`
(`word_min/max`, `required_keywords`, `must_cite`). Contract is law.
- Complexity dial (controls ONLY whether the contract gets a human-approval gate):
  `simple`/`moderate` → proceed once written; `complex`/contentious angle → ⏸ human
  approves the contract before writing.

**S2→3 GROUNDING GATE (1→2 faithfulness).** Dispatch `grounding-checker` for stage
`1->2`: is each Chinese outline point grounded in the English source pack? It writes a
per-item verdict + runs `grounding_gate.py` (PASS/FAIL). FAIL → back to `editorial` to
add a source or cut the unsupported point. This catches an angle that drifted beyond
what research found — the gap citation_audit cannot see.

**S3 — write → fact-check → fix (ALL sections, parallel waves).** Precondition: every
section contract exists and PASSed its S2 review (human-approved when `complex`) AND the
1→2 grounding gate is green. Then fan out — sections are independent verifiable units
with disjoint files (`sec<k>_*`), so run their loops CONCURRENTLY instead of one after
another:
- **Wave dispatch.** In one message, dispatch the NEXT pending step of EVERY unconverged
  section as parallel Agent calls (all `writer`s first wave; mixed steps later — sec1 at
  fact-check while sec3 re-drafts is normal). When the wave returns, journal each result,
  update STATE.md, dispatch the next wave. Never dispatch two agents on the SAME section
  in one wave — within a section the chain stays strictly sequential:
  `writer → fact-checker → (writer fix →) grounding 2→3 → citation audit`.
- **Per-section chain, unchanged.** Once `sections/sec<k>_draft.md` exists, `fact-checker`
  verifies that exact draft: it writes `sections/sec<k>_factcheck.json` and runs
  `tools/factcheck_gate.py` (exit 1 on ANY non-SUPPORTED claim; FAILs closed on an empty
  verdict). The gate exit — not the prose — is what you gate on: FAIL → targeted `writer`
  fix before grounding/audit. This is the machine antidote to the green-dashboard trap
  (cited ≠ true). A gate FAIL only loops ITS section; the other sections' waves keep going.
- **Convergence.** S3+S4 are done when every section has `sections/sec<k>_audit.json`
  with `status:"pass"`. The audit JSON is written on FAIL too — existence alone is not
  green; check the status field (`tools/status.py` audit column = pass on every row).
- **Step budget, per section (unchanged: max 3 iterations).** The journal's `dispatch`
  events are the durable count across resumes (`tools/journal.py summary`). On a
  section's 3rd FAIL, STOP that section and escalate to the human; do not stall the
  other sections while you wait.
Sequential fallback: `/write-section <k>` remains the single-section path (debugging, a
S6 fix loop, or when the human asks to watch one section closely).

**S3→4 GROUNDING GATE (2→3 faithfulness — a step inside each section's wave chain).**
After a section is drafted and fact-checked, dispatch `grounding-checker` for stage
`2->3`: is each claim in the Chinese draft grounded in the outline? The verdict MUST use
`outline_ids`; `source_ids` are optional supporting evidence, not a substitute. FAIL →
back to `writer` to cut the invented claim. (This is the faithfulness layer; the
citation audit at S4 is the marker-existence layer.)

**S4 — citation audit (HARD gate — the last step of each section's wave chain).**
Dispatch `citation-auditor` per section. It runs `tools/citation_audit.py` against the
section draft + source pack + contract JSON. FAIL → send the findings back to `writer`
for another iteration; only PASS advances. The article advances to S5 only on the S3
convergence condition: every `sec<k>_audit.json` present with `status:"pass"`.

**S5 — humanizer.** Once all sections PASS S4, dispatch `humanizer`. It writes the
assembled, de-flavored draft to `humanized.md` (a first-class artifact), removes "AI 味",
self-audits against `style_patterns.md`, and **audits humanized.md itself** (so the audit
checks the de-flavored text, not the stale section drafts):
`python3 tools/audit_article.py articles/article_<slug> --draft humanized.md --as-of <research date>`.
A red audit means humanizing dropped a citation/section/keyword — fix before S6.

**S5.5 — Gemini polish (you run this tool; auto, all tracks).** After S5 is green and BEFORE
you hand the draft to the human for S6, run `tools/gemini_polish.py` so the human reads the
humanized draft and a polished alternative side by side. This is automatic — do not wait to be
asked. Pass `--mode <track>` (sets the per-mode temperature: `factual_ai_news`/`mixed_explainer`
low 0.3, `aesthetic_lifestyle` high 0.85 — the `gemini_temperature` from the STATE `track` block)
and forward the track's oracle args after a bare `--`:
`python3 tools/gemini_polish.py humanized.md --mode <track> --out polished.md --diff-html stage_results/polish_diff.html -- --source-pack source_pack.json --contract contracts/sec1_contract.json`
(aesthetic: input is `aesthetic_post.json`, no oracle args needed). The tool re-runs the track's
oracle (via `run_oracle.py`) on BOTH the pre- and post-polish artifact and writes the delta into
the diff banner — this is the machine signal; the per-hunk 🟢🟡🔴 tags point the human at each
change. **The polish is never auto-applied.** Present the diff at the S6 gate; the human picks
which changes to keep. Any accepted change is just an edit to the draft and re-enters the normal
gate (re-run the citation audit / aesthetic audit before S7). Skip only if
`track.gemini_polish == false`. See `common/behavior_notes/gemini-polish-pass.md`.

**S5.9 — findings triage (optional 归口; factual track).** Run it when ANY findings or
WARNs survived S3–S5 (fact-check non-SUPPORTED history, grounding notes, audit WARNs
like freshness / unranked source, humanizer findings); skip it — journal a `stage` skip
event — when everything is empty. Dispatch `findings-triage` (read-only). It aggregates
every finding across `sections/sec*_{writer,factcheck,grounding,audit}.json` +
`stage_results/S5-humanize.json`, dedupes across stages/sections, **verifies each item
against the contract's `must_cite` + the source pack before it reaches the table**
(对照 must_cite/来源验真后再上桌 — checker agents confidently misfire; a confident false
positive gets `verdict:"reject"` with the refutation, 宁可驳回也不放行错误修改), and
ranks the rest `adopt` / `needs_editor` into `stage_results/S5-9-findings-triage.json`.
Triage filters and ranks; it never edits, and it never re-opens what an oracle already
decided green. Its output is the S6 panel's (and your) worklist — not another review.

**S6 — editorial-review PANEL (advisory).** Dispatch 2–3 INDEPENDENT `editorial-reviewer`
variants in ONE parallel message — read-only, same axes as before (the axes the audit
can't see: freshness of angle, narrative, AI 味, argument soundness, tone). Panel size:
2 by default; 3 when S2's complexity dial said `complex` or S5.9 left `needs_editor`
items. Give each variant a distinct lens EMPHASIS in the dispatch prompt (A: argument +
angle freshness; B: narrative + residual AI 味; C: audience fit + tone) — emphasis
weights depth, it does not narrow scope, so every variant still covers all axes and
majority voting stays meaningful. Point each at `stage_results/S5-9-findings-triage.json`
(when it ran): do not re-report an item triage rejected unless you can refute the
rejection. Each variant writes its OWN `stage_results/S6-editorial-review-<variant>.json`
(+ `review-<variant>.md`) — never the shared filename.
**You merge the panel by MAJORITY** into the canonical
`stage_results/S6-editorial-review.json` (add a `panel` field listing the variant files;
journal the merge as your own `result` event):
- findings match when they point at the same location and the same essence; when in
  doubt, keep them separate rather than over-merging;
- merged severity = majority severity: BLOCKER iff more than half the panel says
  BLOCKER; else WARN iff more than half says WARN-or-higher; else NOTE. A lone BLOCKER
  in a 2–3 panel downgrades to WARN — log the downgrade in DECISIONS.md; you may still
  escalate it manually if you judge the minority reviewer is right.
Then as before: the panel does NOT edit or decide. YOU decide what to fix, dispatch the
fixer (`writer`/`humanizer`), and re-verify (citation audit green again). BLOCKER must
be resolved; WARN/NOTE are your call (log it).

**S7 — output.** Dispatch `output`: emit `final.md` (+ `final.html`). Run the final gate
with source-authority + the shared banned-phrase list enabled (factual track):
`python3 tools/audit_article.py articles/article_<slug> --as-of <research date> --check-links --strict --source-authority common/source_authority.json --banned-phrases common/banned_phrases.json`.
Update STATE.md to done only on green. (Aesthetic track: run `tools/aesthetic_audit.py`
on the card post JSON instead — no citation/source-authority audit.)

**↻ self-improvement (you do this).** If S6 surfaced a recurring "AI 味" or sourcing
pattern, write it back to `common/behavior_notes/` (copy `_TEMPLATE.md`) or add a line
to `style_patterns.md`. Every article makes the next one better.

## Proactive handoff
At a natural stopping point (a gate cleared, the human says stop), ask whether to
generate a handoff doc. Do not auto-generate; do not nag mid-stage.

## Expected completion strings (gate on these exact strings)
- research: `RESEARCH COMPLETE — source_pack.json + brief written`
- editorial: `CONTRACTS COMPLETE — <n> section contracts written`
- grounding-checker: `GROUNDING <stage>: PASS` or `GROUNDING <stage>: FAIL — <n> ungrounded`
- writer: `SECTION <k> DRAFTED — sec<k>_draft.md written`
- fact-checker: `FACT-CHECK COMPLETE — section <k>: <n> claims, factcheck_gate <PASS|FAIL>`
- citation-auditor: `AUDIT <k>: PASS` or `AUDIT <k>: FAIL — <n> findings`
- humanizer: `HUMANIZE COMPLETE — draft de-flavored, audit re-run green`
- findings-triage: `TRIAGE COMPLETE — <n> items: <a> adopt / <r> reject / <e> needs_editor`
- editorial-reviewer: `REVIEW COMPLETE — <b> BLOCKER / <w> WARN / <n> NOTE` (one per
  panel variant; you gate on receiving it from EVERY variant before merging)
- output: `OUTPUT COMPLETE — final.md written`

Each agent must also write a machine-readable result JSON next to its primary output. For
section stages, use a **stage-specific filename so verdicts never overwrite each other**
(a single shared `sec<k>_result.json` was last-writer-wins, which made resume lie about
which stage was green):
- `sections/sec<k>_writer.json`     (S3 writer)
- `sections/sec<k>_factcheck.json`  (S3 fact-check — also the `factcheck_gate.py` input)
- `sections/sec<k>_grounding.json`  (S3→4 grounding 2→3)
- `sections/sec<k>_audit.json`      (S4 citation audit)

Article-level stages use `stage_results/<stage>.json` (`S1-research.json`,
`S2-editorial.json`, `S2-grounding-1to2.json`, `S5-humanize.json`,
`S5-9-findings-triage.json`, `S6-editorial-review-<variant>.json` — one per panel
variant, `S6-editorial-review.json` — the canonical panel merge, written by YOU, the one
exception to "agents write their own results", and `S7-output.json`). Every result JSON
carries `stage`, `section` (for section stages), `status` (`pass`/`fail`/`blocked`),
`files`, and `findings`. Completion strings are for humans; result JSON is the resumable
protocol. `python3 tools/status.py articles/article_<slug>` aggregates them into a
section × stage matrix (+ the journal's cost column).

## Hard rules
1. Never skip the S1 human gate (angle) or the S4 citation gate (facts).
2. Never let a sub-agent decide what to fix — that is your job (S6).
3. Every dropped claim / angle / accepted WARN goes in DECISIONS.md.
4. No claim ships without a dated `[Sn]` source.
5. Re-run the citation audit after ANY edit to a verified section (humanizer, fixer).
6. Update STATE.md after every stage so the run is resumable.
7. Journal every dispatch, result, gate exit, and human decision as it happens
   (`tools/journal.py append`) — never batch-reconstruct events later, never edit past
   lines. Record tokens/cost only when the harness surfaces them.

## Multi-agent failure-mode防范 (from the AI Builder's Handbook Ch15)
Multi-agent systems fail in five known ways. Each is countered by an existing mechanism
here — keep them intact:
- **Loops** (agents ping-pong forever) → every section has a **step budget**: max 3
  write→fact-check→grounding→audit iterations; on the 3rd FAIL, STOP and escalate to the human. Do not
  auto-loop a 4th time.
- **Goal drift** (each agent re-defines the task) → every agent reads the SAME contract
  + STATE.md goal. The contract is the canonical goal statement; nobody works around it.
- **责任模糊 / diffusion** → each agent spec has a role boundary + "what you do NOT do".
  Roles are mutually exclusive by design (auditor never edits, writer never re-scopes).
- **Error compounding** → every section is independently verified (fact-checker +
  citation-audit) before it can feed the assembled draft. A bad section cannot silently
  propagate.
- **Cost blowup** → research/fact-check fan-out is bounded to the 3-5 section nodes; do
  not spawn open-ended agent swarms. If a stage needs > 2 retries, escalate, don't respawn.
  The journal makes spend VISIBLE while it happens (`tools/journal.py summary`, the
  status cost column) — a 1M-token surprise discovered after the fact is an agent-fleet
  incident this repo does not repeat.

Parallel-wave note (S3): concurrency adds no new shared-write risk BECAUSE the existing
rules already isolate sections — every section-stage file is `sec<k>_*` (disjoint), and
only YOU write STATE.md, DECISIONS.md, and the journal. Keep it that way: never let two
agents touch the same section in one wave, and never delegate a STATE/journal write to a
sub-agent. The S6 panel is safe the same way: each variant writes its own
`S6-editorial-review-<variant>.json`; the shared canonical file is written only by you.

Honest scope note: **research** (open-ended concurrent exploration), **fact-check**
(adversarial independent eval), the **S3 per-section fan-out** (independent contracts →
real wall-clock parallelism), and the **S6 panel** (independent judges → majority kills
single-judge false positives) genuinely use sub-agent isolation. The remaining
article-level stages (editorial, humanizer, output) are a linear workflow; they are
sub-agents only for uniformity. A lighter build could run those inline and fan out only
at S1/S3/S6.

## Skills you can invoke (user-invoked, not auto-loaded)
- `/new-article <slug>` — scaffold a per-article workspace.
- `/status` — print the pipeline state table.
- `/write-section <k>` — (re-)run a single section's write→fact-check→audit loop.
- `/write-article <topic>` — the full factual AI-news pipeline (this playbook).
- `/write-aesthetic-post <theme>` — the aesthetic track: 3 variant drafts → curate →
  humanize → `aesthetic_audit.py`. No fact/citation/grounding gates.

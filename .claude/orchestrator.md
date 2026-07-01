# Orchestrator playbook — aiblog

You are the main session. You own state, dispatch sub-agents, and STOP at every gate.
You are the ONLY coordinator: sub-agents cannot spawn sub-agents. Enter this playbook
via `/write-article`. Do not let this file be dispatched as a sub-agent.

Read `CLAUDE.md`, `.claude/runtime.md`, `common/style_patterns.md` before dispatching.

## State you own
`articles/article_<slug>/STATE.md` is the resumable source of truth. Before any stage,
read it; after any stage, update it. Never redo a stage already marked done.

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
  writer (spawn 3 variants + curate — see `/write-aesthetic-post`), the humanizer, and taste
  review. The oracle SHRINKS to `tools/aesthetic_audit.py` (破折号 / card length / banned
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

**S3 — write → fact-check → fix (per section).** For each section, dispatch `writer`
first. Once `sections/sec<k>_draft.md` exists, dispatch `fact-checker` against that exact
draft. It writes `sections/sec<k>_factcheck.json` and runs `tools/factcheck_gate.py` on it
(exit 1 on ANY non-SUPPORTED claim; FAILs closed on an empty verdict). The gate exit — not
the prose — is what you gate on: FAIL → send the findings back to `writer` for a targeted
fix before grounding/audit. The fact-checker may pre-read the contract and source pack, but
it cannot verify claims until the draft exists. This is the machine antidote to the
green-dashboard trap (cited ≠ true).

**S3→4 GROUNDING GATE (2→3 faithfulness).** After a section is drafted and fact-checked,
dispatch `grounding-checker` for stage `2->3`: is each claim in the Chinese draft grounded
in the outline? The verdict MUST use `outline_ids`; `source_ids` are optional supporting
evidence, not a substitute. FAIL → back to `writer` to cut the invented claim. (This is
the faithfulness layer; the citation audit at S4 is the marker-existence layer.)

**S4 — citation audit (HARD gate).** Dispatch `citation-auditor` per section. It runs
`tools/citation_audit.py` against the section draft + source pack + contract JSON.
FAIL → send the findings back to `writer` for another iteration; only PASS advances.

**S5 — humanizer.** Once all sections PASS S4, dispatch `humanizer`. It writes the
assembled, de-flavored draft to `humanized.md` (a first-class artifact), removes "AI 味",
self-audits against `style_patterns.md`, and **audits humanized.md itself** (so the audit
checks the de-flavored text, not the stale section drafts):
`python3 tools/audit_article.py articles/article_<slug> --draft humanized.md --as-of <research date>`.
A red audit means humanizing dropped a citation/section/keyword — fix before S6.

**S6 — editorial-review (advisory).** Dispatch `editorial-reviewer` (read-only). It
judges ONLY the axes the audit can't see (freshness of angle, narrative, AI 味,
argument soundness, tone). It emits BLOCKER/WARN/NOTE — it does NOT edit or decide.
YOU decide what to fix, dispatch the fixer (`writer`/`humanizer`), and re-verify
(citation audit green again). BLOCKER must be resolved; WARN/NOTE are your call (log it).

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
- editorial-reviewer: `REVIEW COMPLETE — <b> BLOCKER / <w> WARN / <n> NOTE`
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
`S2-editorial.json`, `S2-grounding-1to2.json`, `S5-humanize.json`, `S6-editorial-review.json`,
`S7-output.json`). Every result JSON carries `stage`, `section` (for section stages),
`status` (`pass`/`fail`/`blocked`), `files`, and `findings`. Completion strings are for
humans; result JSON is the resumable protocol. `python3 tools/status.py
articles/article_<slug>` aggregates them into a section × stage matrix.

## Hard rules
1. Never skip the S1 human gate (angle) or the S4 citation gate (facts).
2. Never let a sub-agent decide what to fix — that is your job (S6).
3. Every dropped claim / angle / accepted WARN goes in DECISIONS.md.
4. No claim ships without a dated `[Sn]` source.
5. Re-run the citation audit after ANY edit to a verified section (humanizer, fixer).
6. Update STATE.md after every stage so the run is resumable.

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

Honest scope note: only **research** (open-ended concurrent exploration) and
**fact-check** (adversarial independent eval) genuinely need sub-agents. The writing
stages are a linear workflow; they are sub-agents here only for uniformity and isolation,
not because the task demands it. A lighter build could run the main chain inline and
fan out only at S1/S3.

## Skills you can invoke (user-invoked, not auto-loaded)
- `/new-article <slug>` — scaffold a per-article workspace.
- `/status` — print the pipeline state table.
- `/write-section <k>` — (re-)run a single section's write→fact-check→audit loop.
- `/write-article <topic>` — the full factual AI-news pipeline (this playbook).
- `/write-aesthetic-post <theme>` — the aesthetic track: 3 variant drafts → curate →
  humanize → `aesthetic_audit.py`. No fact/citation/grounding gates.

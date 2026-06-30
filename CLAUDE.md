# CLAUDE.md — AI-hot-topic Chinese blog writer (staged, contract-first)

Project context for Claude Code working in this folder. This system is a sibling of
`sas_to_pyspark/` and **deliberately ports its architecture standards** to a different
domain: writing Chinese blog articles about the latest AI hot topics.

**Project name: `aiblog`** (lives in the folder `ai_blog_writer/`).

## What this is
A Claude Code multi-agent system that writes a verified Chinese AI-hot-topic blog
article **one section at a time**, proving each section satisfies a written contract
**and** passes a machine-checkable fact/citation audit before moving on.

The leverage is the same as sas2pyspark's: a **machine-checkable correctness
criterion**. SAS migration has it for free (per-node output equality). Prose does
not — so we manufacture the closest analog: **every factual claim must trace to a
dated source** (`tools/citation_audit.py`). That partial oracle is what lets agents
do the bulk writing while the human keeps judgement + accountability.

## The core idea: what replaces the diff oracle
Prose quality splits into two layers. Put each where it belongs:

| Machine-checkable (the oracle — `citation_audit.py`) | LLM-judge only (editorial-reviewer) |
|---|---|
| every claim has a `[Sn]` citation (no 裸论断/hallucination) | angle is fresh / non-obvious |
| every `[Sn]` exists in the source pack | narrative flows |
| cited sources are dated + fresh (AI news goes stale) | "AI 味" is gone |
| word count / required keywords / must-cite coverage | argument actually holds |
| links resolve (opt-in) | tone fits the audience |

The oracle is the spine. The LLM-judge (Stage 6) only covers what a machine genuinely
cannot — it never re-judges anything the oracle already decided.

**This is Zain's "混合漏斗" (hybrid funnel) from the evals course**, now four layers:
`citation_audit.py` (automated hard rules — marker existence) → `grounding-checker`
(LLM-as-judge faithfulness — does each downstream item trace to upstream?) →
`editorial-reviewer` (LLM-as-judge taste/argument, screening only) → human gates (S1
angle, S6 sign-off). Keeping correctness in the automated layer is deliberate: it
sidesteps the LLM-as-judge saturation pitfall (a judge cannot reliably grade output
stronger than itself).

**The faithfulness layer (grounding-checker) is distinct from the other two:**
`citation_audit` checks a claim *has* a marker (existence); the fact-checker checks the
source is *true* (external correctness); the grounding-checker checks each downstream
item *derives from* upstream (faithfulness / 可追溯). It runs at two hops — 1→2 (is the
outline grounded in the sources?) and 2→3 (is the draft grounded in the outline?) — so a
drifted angle or an invented claim is caught at the hop it appears, not at the end. Its
LLM verdict is made gate-able by `grounding_gate.py` (per-item structured → exit 0/1):
text for the "why", structure for the "does it pass".

**The green-dashboard trap (evals course §8):** `citation_audit` proves a claim is
*cited*, not that it is *true* — every claim could carry an `[Sn]` while the source
says no such thing. That is the "dashboard全绿、底下全烂" failure. The `fact-checker`
agent (S3) is the antidote: it actually reads the cited source, and emits a per-claim
verdict that `tools/factcheck_gate.py` turns into a HARD gate (any non-`SUPPORTED` claim →
exit 1; fails CLOSED on an empty verdict). The audit is necessary, not sufficient; the
fact-check gate is what makes "never ship on a green audit without the fact-check having
run" machine-enforced rather than a hope.

## Cross-lingual by design: Chinese output, English source boundary
The deliverable is a **Chinese** article. The factual ground truth — the source pack —
is **English** (primary AI sources: lab blogs, papers, release notes are overwhelmingly
English). So the language boundary sits at the source edge:
- `research` fetches and records **English** sources (with English titles/dates).
- `editorial`, `writer`, `humanizer`, the final article → **Chinese**.
- The faithfulness checks are therefore **cross-lingual**: the `grounding-checker` judges
  a Chinese outline/draft against an English source pack by MEANING, not surface words —
  this is exactly where an LLM judge earns its keep over a string tool.
- `citation_audit.py` is language-agnostic (CJK-aware word count; `[Sn]` markers are
  language-neutral); `required_keywords` in a contract are Chinese.
- The fact-checker reads the **English** source and verifies the **Chinese** claim — the
  one place a translation error could inject a factual error, so it reads carefully.

## The hard edge (this domain's "PHI never leaves KP")
**No claim without a dated source.** AI hot topics go stale in days, and a confident
wrong fact is the worst failure mode. Every factual sentence in the body carries a
`[Sn]` marker resolving to a source in `source_pack.json` with a `date`. The
citation audit is a HARD gate (Stage 4) — a draft that fails it does not advance.

## Authority & conventions
- **Style rules:** `common/style_patterns.md` is the in-repo single source of truth
  for voice, structure, and the "去 AI 味" checklist. Every writing agent Reads it
  first. It lives in-repo (not a skill) because it is always-needed + version-controlled.
- **Deep notes:** `common/behavior_notes/` — conditional knowledge the writer/humanizer
  globs when relevant (e.g. `ai-flavor-removal.md`, `freshness-and-sourcing.md`).
  Copy `_TEMPLATE.md` to add one.
- **The oracle:** `tools/citation_audit.py` — exit 0=PASS / 1=FAIL, like sas2pyspark's
  `csv_compare_v2`. Always pass `--source-pack`; pass `--contract` for word-count /
  required-keyword / must-cite checks; `--check-links` to resolve URLs; `--strict` to
  promote WARN→FAIL. Pure stdlib — runs on system `python3`, no special env.
- **Citation convention:** factual claims carry inline `[S1]` / `[S1,S3]` markers
  resolving to `source_pack.json` ids. This is non-negotiable — it is what makes the
  oracle work.
- **Chinese body, English scaffolding:** article body is Chinese (the deliverable);
  all specs, code, comments, contracts, commit messages are English.
- **Decisions are logged:** every angle choice, dropped claim (no source), tolerance
  call, and accepted risk goes in `articles/article_<slug>/DECISIONS.md`. Ambiguous
  editorial calls → present 2-3 options with trade-offs, log the choice.
- **Freshness provenance:** every source is dated; the audit's `--as-of` pins a
  reference date so a run is reproducible and not system-clock dependent.
- **Every system-iteration PR updates the iteration log:** a PR that changes the system
  (an agent, a tool, a gate, a behavior note) appends one short entry to
  `handoff/ITERATION_LOG.md` (`what / why / risk / verified`) **in the same PR**. This is
  the per-PR continuity pulse so the next architect can resume from the repo alone; the
  full per-session `handoff/handoff-<date>.md` docs (via `/handoff`) remain for session
  boundaries. The log is the stream; the handoff is the snapshot. A committed `pre-commit`
  hook (`.githooks/pre-commit`, enable once with `git config core.hooksPath .githooks`)
  enforces this locally — it rejects a commit touching system paths unless
  `handoff/ITERATION_LOG.md` is staged too; CI enforces the same at the PR layer.
- **Architect end-of-session ritual (you, when iterating THIS system — NOT the orchestrator
  running the article pipeline):** before you wrap up, or as soon as the human says stop,
  ASK the human two things, in order: (1) write a handoff doc (`/handoff`)? (2) open a PR
  with the system changes + the ITERATION_LOG entry (+ the handoff)? Do not auto-generate or
  auto-open; do not nag mid-task; but do not end silently either — this end-of-session check
  is the architect's counterpart to the orchestrator's gates. (The orchestrator role has its
  own, separate proactive-handoff note in `.claude/orchestrator.md`.)

## Pipeline (who does what)
Orchestrator (main session) owns state, dispatches subagents, stops at every gate.
Subagents cannot spawn subagents (Claude Code rule) — the orchestrator is the only
coordinator. Stages mirror sas2pyspark:

- **S0 topic + decompose** — pick the hot topic, split the article into 3-5 section
  nodes; each section = the smallest independently-verifiable unit. (You do this.)
- **S1 research** — live web search/fetch → a dated `source_pack.json` (the "baseline"
  truth each section must not contradict). ⏸ HUMAN gate: right angle? sources fresh enough?
- **S2 editorial** — write a per-section contract (coverage points, must-cite sources,
  word range, Given/When/Then acceptance). Contract is law.
- **S3 write → fact-check → fix** — per section: `writer` drafts first; `fact-checker`
  verifies that exact draft against the source pack; writer fixes any unsupported claim.
- **S4 citation audit (HARD gate)** — `citation_audit.py` on each section: no 裸论断,
  every `[Sn]` valid + fresh, coverage met. Fail → back to writer. (= sas fidelity-auditor.)
- **S5 humanizer** — remove "AI 味" + self-audit against `style_patterns.md`; re-run
  `audit_article.py` so final assembly cannot drop section coverage.
- **S6 editorial-review (advisory)** — read-only reviewer judges ONLY the axes the
  audit can't see; emits BLOCKER/WARN/NOTE → orchestrator decides → fixer → re-verify.
- **S7 output** — assemble + emit md / html.
- **↻ self-improvement** — a shipped "AI 味" or hallucination pattern is written back
  to `common/behavior_notes/` so the next article starts better. This compounding loop
  is the standard the v3 SEO writer lacks.

Each article gets `articles/article_<slug>/` (scaffold via `/new-article <slug>`).
Full runbook: `RUNBOOK.md`. Domain glossary: `CONTEXT.md`.

## Agent topology + what to read first
You (main session) = orchestrator, the only thing that spawns sub-agents. The
orchestrator's playbook is `.claude/orchestrator.md` — a main-session file, never
dispatched as a sub-agent. Enter it via `/write-article`.

```
you ─ orchestrator (owns state, dispatches, stops at every gate)
        ├─ S0  topic + decompose into section nodes          (you do this)
        ├─ S1  research ............. dated source_pack.json  →  ⏸ HUMAN approves angle
        ├─ S2  editorial ............ per-section contract
        ├─ S3  per section:  writer → fact-checker → writer fix
        ├─ S4  citation-auditor ..... HARD gate (citation_audit.py)
        ├─ S5  humanizer ............ 去 AI 味 + self-audit
        ├─ S6  editorial-reviewer ... advisory → you decide → fixer → re-verify
        └─ S7  output ............... md / html
```

Read first, in order, when starting an article session:
1. `CLAUDE.md` (this file) — project brain + rules.
2. `.claude/runtime.md` — how to run the audit, where files go.
3. `common/style_patterns.md` — the voice/structure single source of truth.
4. `RUNBOOK.md` — the step-by-step; then the per-article `STATE.md`.

## Conventions (doc style for agent specs)
- Sentence-case headings; no decorative emoji.
- Imperative, second person, terse. One idea per paragraph.
- Every agent spec carries: a role boundary, a "what you do NOT do" section, and a
  fixed completion string the orchestrator gates on.

## Borrowed standards from sas2pyspark (the承重墙)
1. Machine-checkable judge (here: citation audit, not output equality).
2. Contract is law (per-section contract binds writer + fact-checker + auditor).
3. Smallest verifiable unit (section node, not whole article).
4. Stage gates, orchestrator-only coordination, human owns the angle.
5. Review is advisory; the orchestrator decides + dispatches the fixer + re-verifies.
6. Self-improvement loop (behavior_notes) → compounding quality.
7. Resumable STATE.md + audit-trail DECISIONS.md.

## What this system is NOT (scope boundary)
- Not an autonomous one-shot generator. Every article passes human gates (angle, final).
- Not SEO-keyword-stuffing. Quality + factual fidelity first; keywords are a contract
  field, not the goal.
- Not a publisher. S7 emits files; posting to a platform is out of scope this round.

# aiblog — a verified multi-agent writer for Chinese AI-hot-topic posts

A Claude Code multi-agent system that writes a **Chinese** blog / 小红书 post about a
**latest AI hot topic**, one section at a time, proving each section against a written
contract **and** a machine-checkable fact/citation audit before moving on.

It is a deliberate port of a SAS→PySpark migration system's architecture standards to
prose: the leverage in both is a **machine-checkable correctness criterion**. SAS
migration gets one for free (per-node output equality). Prose does not — so this system
manufactures the closest analog: **every factual claim must trace to a dated source.**

> Output language is **Chinese**; the factual source boundary is **English** (primary AI
> sources — lab blogs, papers, release notes — are overwhelmingly English). The system is
> cross-lingual by design.

## Why it's different from a one-shot "AI blog writer"

Most LLM article generators are a linear pipeline ending in a soft self-score. This system
borrows three load-bearing ideas from a verified data-migration pipeline:

1. **A machine oracle, not a vibe check.** Correctness is decided by tools that exit 0/1,
   not by an LLM grading itself.
2. **Per-section contracts + gates.** The smallest verifiable unit is a section, not the
   whole article, so errors surface early.
3. **A self-improvement loop.** Every shipped piece that revealed a tell feeds a rule back
   into the repo, so the next post starts better.

## The quality funnel (where each check lives)

```
citation_audit.py     →  grounding_gate.py      →  editorial-reviewer  →  human gates
(machine: marker          (LLM judge: does each      (LLM judge: taste,     (angle @ S1,
 exists, fresh,           downstream claim trace     argument, AI-味)       sign-off @ S6)
 coverage)                to upstream — faithfulness)
```

Correctness stays in the **machine** layer on purpose: it sidesteps the LLM-as-judge
saturation trap (a judge can't reliably grade output stronger than itself). The two
machine oracles:

| Tool | Checks | Exit |
|---|---|---|
| `tools/citation_audit.py` | every claim has an `[Sn]` marker (no 裸论断), sources are dated + fresh, word-count / required-keyword / must-cite coverage. CJK-aware. | 0 = PASS / 1 = FAIL |
| `tools/grounding_gate.py` | faithfulness — outline points trace to sources (`source_ids`), draft claims trace to outline (`outline_ids`) with optional source provenance. | 0 = PASS / 1 = FAIL |
| `tools/audit_article.py` | wrapper that audits every section contract and re-checks final structure, section headings/markers, preserved citations, and unioned coverage requirements. | 0 = PASS / 1 = FAIL |

## Pipeline

```mermaid
flowchart TD
  S0[S0 decompose · pick topic, split into section nodes] --> S1[S1 research · live web → dated EN source pack]
  S1 -->|⏸ human approves angle| S2[S2 editorial · per-section contract]
  S2 --> G1[grounding 1→2 · outline grounded in sources?]
  G1 --> S3[S3 write → fact-check → fix · Chinese draft, every claim cited]
  S3 --> G2[grounding 2→3 · draft grounded in outline?]
  G2 --> S4[S4 citation audit · HARD gate]
  S4 --> S5[S5 humanize · 去 AI 味]
  S5 --> S6[S6 editorial review · advisory]
  S6 -->|⏸ human sign-off| S7[S7 output · md / 小红书 .txt + cover]
  S7 -.lessons.-> NOTE[behavior_notes / style_patterns §7]
  NOTE -.next post starts better.-> S0
```

The **orchestrator** (main Claude Code session) owns state and is the only coordinator;
sub-agents cannot spawn sub-agents. Agent specs live in `.claude/agents/`.

## Use it

Open this folder as a Claude Code project, then:

```
/new-article <slug>            # scaffold a per-article workspace
/write-article <topic>         # run the staged pipeline (stops at the angle + sign-off gates)
/status                        # print the pipeline state table
/write-section <k>             # re-run one section's write → fact-check → audit loop
/handoff                       # write a system handoff for the next architect
```

Smoke-test the oracles on the shipped synthetic example (no setup, no network):

```
python3 tools/citation_audit.py articles/article_demo/sections/sec1_draft.md \
  --source-pack articles/article_demo/source_pack.json \
  --contract articles/article_demo/contracts/sec1_contract.json --as-of 2026-06-09   # PASS
python3 tools/grounding_gate.py articles/article_demo/sections/grounding_2to3.json \
  --allowed-outline-ids 1 --allowed-source-ids S1,S2,S3                               # PASS
python3 tools/audit_article.py articles/article_demo --as-of 2026-06-09               # PASS
```

Build the default 小红书 technical long-image package after `final.md` is verified:

```
python3 tools/xhs_image_post.py articles/article_<slug>/final.md \
  --out-dir articles/article_<slug>/assets/xhs \
  --meta articles/article_<slug>/xhs_meta.json --check-caption
```

This writes card HTML, PNG cards when Chrome is available, a paste-ready caption, and
`content_manifest.json` for the manual publish queue. The optional `xhs_meta.json` sidecar
supplies the hook `cover_title` + shortened `caption` (see
`common/behavior_notes/xiaohongshu-baokuan-paradigm.md`); `--check-caption` fails if the
caption uses a number absent from the verified body.

### Optional: a final Chinese polish via Gemini

After both oracles are green, an optional last pass sends the finished text through Gemini
for **fluency only** (never facts/citations). Copy `.env.example` to `.env` (gitignored)
and add `GEMINI_API_KEY`:

```
python3 tools/gemini_polish.py <final.txt> --out <polished.txt> --dry-run   # cost estimate
python3 tools/gemini_polish.py <final.txt> --out <polished.txt>             # send
```

A cost guard refuses any call estimated over $1 (a single post is ≈ $0.001).

## Repo layout

```
CLAUDE.md              project brain + rules
CONTEXT.md             domain glossary (node / source pack / the oracle / 裸论断 …)
RUNBOOK.md             step-by-step
.claude/
  orchestrator.md      main-session playbook + gates + failure-mode防范
  runtime.md           how to run things, where files go
  agents/              9 sub-agent specs (research, editorial, writer, fact-checker,
                       grounding-checker, citation-auditor, humanizer, editorial-reviewer, output)
  commands/            /write-article /new-article /status /write-section /handoff
common/
  style_patterns.md    voice + 去 AI 味 + the §7 hard-rule checklist (single source of truth)
  behavior_notes/      conditional knowledge the writing agents glob (incl. 小红书 mode)
platforms/
  xiaohongshu/         default long-image post adapter
tools/
  citation_audit.py    oracle 1 — marker/freshness/coverage
  grounding_gate.py    oracle 2 — faithfulness
  audit_article.py     article-level wrapper over section/final audits
  xhs_image_post.py    default Xiaohongshu long-image post package builder
  gemini_polish.py     optional final fluency pass
articles/
  _TEMPLATE/           per-article scaffold
  article_demo/        synthetic worked example (used by the smoke tests)
handoff/               system handoffs — each iteration recorded for the next architect
```

Real article workspaces (`articles/article_<slug>/`) are gitignored — this repo ships the
**system**, not generated posts.

## Status

Runs end to end. Both oracles are tested green and correctly red on planted bugs. A real
worked example (a Cursor-mobile-app 小红书 post, grounded in 8 dated English sources) was
produced and published; its generated content stays local by design.

## License

[Apache License 2.0](LICENSE).

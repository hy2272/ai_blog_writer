# Iteration log

A living, append-only record — **one entry per system-iteration PR**, newest first. This
is the lightweight continuity stream that lets the next architect (or Hanfei) resume from
the repo alone, without re-reading every PR. The full per-session `handoff/handoff-<date>.md`
docs remain for session boundaries; this is the per-PR pulse between them.

**Convention (also in CLAUDE.md):** every PR that changes the system appends an entry here
in the same PR — `what / why / risk / verified`. Keep each entry tight; the PR + commit
carry the detail.

---

## 2026-07-06 — coordination layer from agent-fleet v2: run journal + S3 parallel fan-out + S5.9 triage & S6 panel
- **What:** ports the three orchestration mechanisms proven in `hy2272/agent-fleet` v2 into
  this repo's pipeline — patterns only, no code copied; all oracle verdict logic untouched.
  (A) **`run_journal.jsonl`** per article: append-only ledger of every dispatch / agent
  result / gate exit / human decision / stage transition, with tokens+cost when the harness
  surfaces them. New stdlib `tools/journal.py` (`append` validates per-event required fields,
  exit 2 writes nothing; `summary` rolls up per stage + per-section writer-dispatch counts =
  the step budget). Resume protocol now three layers, reconciled in order: result JSONs
  (what is GREEN) → journal (what RAN) → STATE.md (summary, backfilled from the journal when
  it lags). `tools/status.py` gains a journal-driven `cost` column + run-totals line; without
  a journal its output is byte-identical to before. (B) **S3 parallel fan-out**: once every
  S2 contract passes (+ grounding 1→2), ALL sections' write→fact-check→grounding→audit loops
  run concurrently as waves (one parallel message dispatches each unconverged section's next
  step; within a section the chain stays sequential; never two agents on one section per
  wave). Convergence = every `sec<k>_audit.json` with `status:"pass"` (existence alone is
  not green — the audit JSON is written on FAIL too). Per-section step budget (3) unchanged,
  now durable across resumes via journal dispatch counts. Only orchestrator control flow +
  docs changed; agent playbooks and oracles untouched. `/write-section` remains the
  sequential single-section path. (C) **S5.9 findings triage + S6 panel**: new optional
  `findings-triage` agent (agent-fleet triage analog) aggregates + dedupes all surviving
  S3/S4/S5 findings/WARNs into `stage_results/S5-9-findings-triage.json`, VERIFIES each item
  against `must_cite` + the source pack before it reaches the table, and rejects confident
  false positives with a refutation (宁可驳回也不放行错误修改); skipped (journaled) when zero
  findings. S6 now dispatches 2-3 independent `editorial-reviewer` variants (lens EMPHASIS,
  not narrowed scope) each writing `S6-editorial-review-<variant>.json`; the orchestrator
  merges by majority into the canonical `S6-editorial-review.json` (a lone BLOCKER in the
  panel downgrades to WARN, logged in DECISIONS.md, manually escalatable). (D) **CI repair
  (main red since #23):** the `run_oracle` workflow step captured an EXPECTED exit 3 with a
  bare `cmd; rc=$?` — under the workflow's `bash -e` shell the step dies AT cmd, so the
  assert never ran; main's push CI and PR #24 (which inherits main, touches no test.yml)
  both failed with exit 3. Fixed with `rc=0; cmd || rc=$?` (condition context, `-e` exempt)
  and hardened the two sibling `; var=$?` captures in the same step; left a NB comment so
  the pattern isn't reintroduced. PR #24 goes green by updating its branch from main after
  this merges.
- **Why:** the hard-gate stack was solid but the coordination layer above it was thin — a
  crash between an agent's return and a STATE.md update lost the run history; cost was
  discovered after the fact (the agent-fleet 1.04M-token incident); sections ran serially
  for no reason (disjoint files, independent contracts); and one confident reviewer/checker
  could put a false positive on the human's desk (2 of 57 findings in the fleet run were
  exactly that). Each fix is the fleet mechanism re-homed onto this repo's
  orchestrator-dispatches-subagents shape.
- **Risk:** the journal depends on orchestrator discipline (hard rule 7) — nothing enforces
  an append the way the oracles enforce gates; token/cost fields are best-effort (recorded
  only when the harness shows usage). Parallel waves and the S6 panel majority merge are
  DOC-level control flow for the orchestrator LLM — statically consistent but not yet
  exercised by a real `/write-article` run (next live run is the test). status.py now
  imports its sibling `journal` module (script-dir import; fine for `python3 tools/status.py`,
  matters if someone vendors the file alone). Panel majority can downgrade a lone true
  BLOCKER — mitigated by DECISIONS.md logging + manual escalation + the S6 human gate.
- **Verified:** static only, per repo tradition — `py_compile` on all tools; journal.py
  smoke (3 valid events → valid JSONL with ts; gate exit 0 derives status pass; usage errors
  exit 2 and append nothing; summary shows step-budget `sec1 1/3` + cost totals); status.py
  on the journal fixture shows `$0.31`/`$0.14` per section, `$0.52` on S1-research, totals
  `$0.97` with `1 malformed skipped`, and byte-identical legacy output with the journal
  removed; new CI steps cover journal happy + error paths and the no-journal regression.
  The CI fix was verified by full local replica: extracted ALL 39 `run:` blocks from
  test.yml and executed each under `bash -e` from the repo root — 0 failures, including
  the fixed run_oracle step, the gemini_polish step (which had never actually executed in
  CI: main died before reaching it), and the three new journal/status steps. The `-e` kill
  was first reproduced locally (exit 3, assert unreached) before fixing. NOT yet verified
  live: a real parallel S3 run, real token/cost capture, a real triage + panel merge —
  flagged in the handoff.
- **What:** first two pieces of the "one skeleton, N fillings" rework agreed on claude.ai.
  (1) **`tools/run_oracle.py`** — a thin per-track oracle dispatcher (option A + option (i)):
  `--mode <track>` → the one oracle that gates it (`factual_ai_news`→citation_audit,
  `aesthetic_lifestyle`→aesthetic_audit, `mixed_explainer`→explainer_audit), with terse aliases
  (`tech_news`/`aesthetic`/`explainer`). It `execv`s the oracle so exit code + stdout pass through
  untouched — a switch, not a judge; it never reads findings. The three oracles stay independent
  and directly runnable. explainer row is reserved (oracle not shipped → honest exit 3).
  (2) **`tools/gemini_polish.py` v2 → S5.5**: per-mode temperature (factual/explainer 0.3,
  aesthetic 0.85 — the direct-API script is where a temperature knob actually exists, unlike a
  subagent); re-runs the track oracle via the dispatcher on BOTH pre- and post-polish artifact and
  shows the **before→after finding delta** (authoritative signal — the green-dashboard-trap antidote
  at the polish stage) plus an HTML side-by-side diff with per-hunk 🟢🟡🔴 hints; aesthetic path
  polishes only NON-quote card texts (verified quotes keep provenance); `--polished` offline path
  regenerates the diff without an API call. (3) orchestrator gains an **S5.5** step (auto, all
  tracks, never auto-applies — diff goes to the S6 human gate); STATE `track` block gains
  `gemini_polish` + `gemini_temperature`; behavior note rewritten from "optional last-mile" to the
  auto-run oracle-checked step.
- **Why:** collapse "mode→which oracle" into one home (needed at S4 and S5.5) so a 4th track = one
  row; and promote Gemini polish from a forgettable manual script to an auto-run, machine-checked,
  per-mode step the human reviews via diff — keeping correctness on the machine and taste on the human.
- **Risk:** run_oracle is pass-through only (no behavior change to existing gates). gemini_polish v2
  keeps v1 plain-text usage working (no `--mode` → no generationConfig → model default). The S5.5
  live API path (temperature param + response parse) is UNTESTED live — only the offline `--polished`
  path + oracle-delta + diff were exercised. explainer track is NOT wired yet (oracle pending).
- **Verified:** run_oracle parity vs direct calls on aesthetic/factual fixtures (exit 0 and exit 1
  passthrough, aliases, missing-oracle exit 3, usage errors). gemini_polish offline on both tracks:
  aesthetic PASS→FAIL delta catches an injected 破折号; factual PASS→FAIL delta catches a dropped
  `[S2]`; HTML diff renders correct per-hunk 🟢🟡🔴 + reasons.

## 2026-07-01 — close aesthetic-track artifact seams (follow-up to #21)
- **What:** acts on the two round-2 reviews of #21. (1) **quote verification is no longer
  self-certifying** — `aesthetic_audit.py` now requires provenance (`verified_source` URL or
  `verified_by`) on any `verified` quote, and every quote CARD (quote:true / whole-card 「…」)
  must map to such a record (fixes the aesthetic green-dashboard trap; the demo《情书》line
  was corrected to the real 「你好吗？我很好」). (2) **audited object == rendered object** —
  `adapter.py --aesthetic-json` builds cards straight from `aesthetic_post.json` (forces
  photo-triptych, no `[Sn]`), and the manifest now records each card's `text`; no markdown
  round-trip to drift. (3) new **`aesthetic-writer` agent**; `/write-aesthetic-post` dispatches
  it (3 variants) instead of the factual `writer`. (4) em-dash regex drops `--` (false-positive
  on the codeless aesthetic track); (5) card-length default 40→32 (this 栏目 is 一句一卡);
  (6) new **card-rhythm** WARN (adjacent cards sharing an opening char / one char clustering
  across most cards); (7) overline AI regex broadened (`AI|AIGC|人工智能|生成式|智能生成`);
  (8) `citation_audit --banned-phrases-scope body|all` (default body skips the References block
  so a cited source's title can't red the article); (9) `mixed_explainer` marked RESERVED.
- **Why:** review #1 — `verified:true` was trusted blindly (the exact failure the whole system
  exists to prevent) and the thresholds/regex were loose. review #2 — the audit gated a JSON
  but the adapter still ate markdown (audited ≠ published), the command dispatched the wrong
  writer, and References titles could false-positive the banned lint.
- **Risk:** provenance is presence-checked, not fetched (a fake URL passes structurally — same
  limit as the news track's dated-URL rule; the human/fact surface is small here). card-rhythm
  thresholds are conservative (ceil(0.75·N), min 4) to avoid false positives; a very short post
  (<4 cards) skips the clustering check. adapter aesthetic path is CI-tested `--no-render` only
  (PNG still needs Chrome).
- **Verified:** CI — 7 aesthetic bad fixtures FAIL (incl. no-provenance, unregistered quote
  card, woven-in attributed quote), good PASS with 0 WARN; references banned phrase PASSes
  body-scope, FAILs `--scope all`; adapter `--aesthetic-json` manifest card text matches the
  JSON 1:1; caption number-check runs against card text; all #21 + prior gates and the
  markdown/triptych adapter paths still green.
- **Pre-merge review fixes (round 3 on #22):** (a) P0 — the aesthetic-json path fed the
  caption into its own `body_text`, so `--check-caption` self-approved any invented number;
  `body_text` now excludes the caption (checks against card text only). (b) orchestrator S0
  router still said the aesthetic track uses `writer`; corrected to `aesthetic-writer`.
  (c) `aesthetic_audit` docstring example + a woven-in attributed quote (a card naming 《…》
  with a 「…」 quote but no `quote:true`) now also require a verified record. Fixtures:
  `caption_invents_number`, `bad_embedded_quote_no_record`.
- **Pre-merge review fixes (round 4 on #22):** the reviewer approved the merge and flagged the
  quote switch as a backdoor to the hole just closed. (a) P0 — `quote_verification_required` is
  no longer read from the post JSON (the verified party could set it `false` to skip its own
  check, same class as a self-asserted `verified:true`). The exemption is now the CLI flag
  `--allow-unverified-quotes` (mirrors `grounding_gate --allow-empty`: relief lives with whoever
  RUNS the gate); a data-side `quote_verification_required:false` is IGNORED and separately
  WARN'd. (b) card-rhythm now exempts function words / pronouns (我的了是在有…) so the clustering
  WARN fires only on CONTENT-word collapse (光/电影 on most cards), not the natural first-person
  diary voice — kills the permanently-lit yellow light. (c) `_quote_record_for` prefers an EXACT
  (normalized-equal) record before falling back to substring, so a short quote that is a substring
  of another maps to the right record (no cross-attributing provenance). card-length 32 left as-is
  (reviewer said observe first, don't retune). Fixtures: `bad_backdoor_switch` (FAIL + backdoor
  WARN), `warn_rhythm_content` (--strict FAIL), `rhythm_stopword_ok` (我 on 5/6 --strict PASS).
- **What:** turns the two reviewers' converging asks into one PR. (1) `tools/aesthetic_audit.py`
  — the aesthetic track's own oracle (2nd port of the citation_audit *idea*): 破折号, card
  length, banned phrases, 「」 closure, 0X-0N card numbering, overline (no AI), and the residual
  fact surface = quote verification. (2) `common/banned_phrases.json` — the style §3 翻译腔/AI-味
  tics as DATA (phrase/level/reason/suggest); `citation_audit.py --banned-phrases` and
  `aesthetic_audit.py` both consume it; §3 gains a pointer. (3) `grounding_gate.py` now FAILs
  closed on an empty verdict (`--allow-empty` override), matching factcheck_gate. (4)
  `audit_article.py` passes `--source-authority` + `--banned-phrases` through; orchestrator S7
  enables source-authority by default on the factual track. (5) `gen_image.py --dry-run`
  (no API call, no cost) + `--manifest` image-provenance schema (prompt/model/aspect/refs/
  palette/purpose/reusable/date). (6) first-class `track` field in STATE.md + an S0 track
  router in the orchestrator (factual_ai_news / aesthetic_lifestyle / mixed_explainer) +
  `/write-aesthetic-post` command (3 variants → curate). (7) fact-checker.md description fixed
  ("runs after the writer has produced the draft", not "in parallel"). Fixtures + CI for all.
- **Why:** review #1 — the machine layer (the system's strongest part) was OFF on the content
  actually shipped most (aesthetic cards), and the banned list was prose the humanizer had to
  read. review #2 — the aesthetic track lived only in a behavior note, not the orchestrator
  state machine; grounding could pass on empty; S7 didn't use source-authority; the
  fact-checker doc was stale; the image path had no dry-run/manifest.
- **Risk:** banned-phrase matching is naive substring — only always-wrong phrases are FAIL,
  ambiguous ones (深入/直白/更稳/影子) are WARN and single-char calques (炸/硬/吃) are omitted to
  avoid false positives (enforce those by eye). aesthetic_audit consumes an `aesthetic_post.json`
  the aesthetic flow must emit; the gen_image dry-run/manifest is CI-tested but the real paid
  gen path still isn't (needs a key + billing).
- **Verified:** CI — aesthetic_audit good→PASS, 4 bad fixtures→FAIL; banned-phrase draft→FAIL,
  demo stays clean; grounding empty→FAIL, `--allow-empty`→PASS; audit_article passthrough of
  `--source-authority`/`--banned-phrases`; gen_image `--dry-run` writes no image + a manifest.
  All prior gates + xhs adapter tests still green locally.

## 2026-06-30 — #20 aesthetic track + AI-image card pipeline
- **What:** a second, non-factual content track and the visuals for it. `tools/gen_image.py`
  (stdlib Nano Banana / Gemini image gen). `adapter.py --style photo-triptych`: 氛围 triptych
  cover + single-photo body frames, CSS-grade unify, no seams, configurable font (`meta.font`,
  embeds `.otf`), author-controlled CJK line breaks + `nowrap_terms`. `assets/image_library/`
  (raw originals only) gitignored. Two behavior notes (`aesthetic-track`, `ai-image-card-pipeline`);
  `style_patterns` §3/§7 updated (破折号 now general; censorship-adjacent angle = AVOID not soften).
- **Why:** the system could only make factual typographic cards. Hanfei wanted beautiful
  aesthetic/lifestyle posts (生活美学/旅游/诗意). Those have no facts, so the citation/fact/
  grounding gates are a category error and are skipped; the lone residual fact surface is a
  quoted film line (verify only that).
- **Risk:** Gemini image gen is PAID-tier only (no free quota) and costs real money per image
  (flash ~cents); `image_library` + article assets are deliberately NOT committed (local-only,
  reproducible via `gen_image.py`); per-term `nowrap` is whack-a-mole (authored line breaks are
  the real fix). No CI for the image path (needs a key + billing).
- **Verified:** real Nano Banana generations (paid key); full "把日子过成电影" post rendered
  end-to-end (cover triptych + 5 frames), all word-splits fixed via authored breaks; font
  fallback smoke-tested (no `meta.font` → serif, no `@font-face`); adapter syntax-checked.

## 2026-06-30 — #19 align the CI log gate with the pre-commit hook
- **What:** the CI "iteration log" gate now uses the SAME system-path filter as
  `.githooks/pre-commit` — it only requires `ITERATION_LOG.md` when a PR changes system
  paths (`platforms/`, `tools/`, `.claude/`, `.githooks/`, `.github/workflows/`,
  `common/behavior_notes/`, `common/style_patterns.md`, `CLAUDE.md`). Pure doc/handoff/
  article PRs now pass freely.
- **Why:** the two guards disagreed — the local hook exempted pure-doc commits but the CI
  gate required the log on EVERY PR, so a handoff-only PR would fail CI. Surfaced while
  landing the `-4` handoff.
- **Risk:** the two path lists must stay in sync; if you add a system dir to one, add it to
  the other (hook + workflow).
- **Verified:** this PR changes a system path (`.github/workflows/`) and includes this log
  entry, so it satisfies the aligned gate; a hypothetical handoff-only PR would now be
  exempted.

## 2026-06-30 — #18 commit guard (pre-commit hook) + architect end-of-session ritual
- **What:** `.githooks/pre-commit` — rejects a commit touching system paths (`platforms/`,
  `tools/`, `.claude/`, `.githooks/`, `.github/workflows/`, `common/behavior_notes/`,
  `common/style_patterns.md`, `CLAUDE.md`) unless `handoff/ITERATION_LOG.md` is staged too;
  the local counterpart to the CI ITERATION_LOG gate (which is PR-level only). Enable with
  `git config core.hooksPath .githooks` (documented in README "Contributing / dev setup").
  CLAUDE.md gains an **architect end-of-session ritual**: before wrapping up, ask the human
  (1) write a handoff? (2) open a PR? — scoped to the architect role, distinct from the
  orchestrator's own proactive-handoff note. Plus this session's broad handoff
  `handoff-2026-06-30-5.md` (`-4` is the Cursor agent's #7–#16 companion).
- **Why:** the user expected "no iteration-log update → can't commit" but only the PR-level
  CI gate existed (it passes silently on compliance, can't block a local commit, and a
  no-PR push skips it). And the end-of-session handoff/PR ask needed a home the ARCHITECT
  sees (CLAUDE.md, always in context) — not orchestrator.md (that's the pipeline role).
- **Risk:** a hook is local + opt-in (needs the one-time `core.hooksPath` set; a fresh clone
  without it is unguarded — README covers it); `--no-verify` bypasses by design. `.githooks/`
  is itself a guarded path so the guard can't be weakened without a log entry.
- **Verified:** hook self-test — staging a system file without ITERATION_LOG → blocked;
  with ITERATION_LOG staged → passes (this very commit dogfoods it).

## 2026-06-30 — #17 xhs cards: paste-and-post redesign (density, layout, tone rules)
- **What:** `platforms/xiaohongshu/adapter.py` — (a) `MAX_BODY_CHARS` 430→680 so a card's
  body fills the 1440px height (was top-third only) → fewer, denser cards, not a fixed 10;
  (b) `html_card()` redesigned borrowing the course `beautiful-html` `cartesian` aesthetic —
  warm neutral palette, CJK serif titles, letter-spaced eyebrow, accent bar, faded
  page-number watermark; (c) `find_chrome()` finds the macOS `.app` binary so PNG render
  needs no manual wrapper; (d) **cover merges with the "这篇讲什么" reading route** (no sparse
  standalone outline card — hook + map on image 1); (e) **dropped the 参考来源 card**;
  (f) **`[Sn]` stripped from rendered cards** (kept in final.md for the audit + manifest
  citation_ids); (g) **PNG-only output** when rendering (HTML only as the `--no-render`
  fallback); (h) `parse_markdown` extracts a trailing all-hashtag line into the caption's
  tag block (precedence: --tags > draft hashtags > DEFAULT_TAGS) so author-chosen tags are
  used AND never burned into a card. Tone rules stored in `style_patterns.md` §3 +
  `behavior_notes/xiaohongshu-output-mode.md`: bans 「岁月静好」「最香的」「吃(素材)」「开发者
  玩具」「直白(误用)」; sentence-structure 翻译腔 rule (no English inversion/endless-append;
  vague 「一条新闻」ok; 中文省略主语; don't cluster a word; frame demos as 「亲测/分享」not
  「不是官方说明」); §7 + the note add a 平台敏感词 rule (no VPN/翻墙; region lock said vaguely).
  Round 3 (from the author's published-post edits): §3 adds no brand+product stacking
  (谷歌Gemini→Gemini), 影子→审美, hedge→confident (没那么容易→绝对), 第一人称踩坑 > 抽象名词;
  `xiaohongshu-baokuan-paradigm.md` caption section gets these + a process note (the meta
  caption is a separate hand-written field — tone-edit it in the same pass as the body).
  CI: overflow test imports `MAX_BODY_CHARS`; builds-package asserts `card_count>=2` +
  `cards[0].kind=="cover"`.
- **Why:** Hanfei feedback — cards too sparse / wasted swipes, layout not 美观, and the
  deliverable should be paste-and-post (no [Sn]/refs/HTML clutter); plus tone fixes.
- **Risk:** 680 is render-verified for the current type scale — a font/padding change needs
  a re-render check (a clipped card ships silently). Serif display needs a CJK serif (macOS
  Songti SC); falls back to sans. `[Sn]` only stripped at render — final.md still must pass
  the citation audit (it does).
- **Verified:** re-rendered article_nano_banana_2 (10→cover+3 sections, body fills ~85-90%,
  no overflow); citation audit `--strict` PASS (927字, 7/7 cited, 0 WARN); CI fixtures pass
  locally (compile / builds-package card_count + cover kind / long-paragraph max≤cap /
  meta_good check-caption / meta_bad fails).

## 2026-07-01 — #16 outline.json schema + scaffold validator (Cursor #5 + #6)
- **What:** #5 — `outline.json` is now the machine-readable outline (stable `id` per item +
  source_ids); `tools/outline_ids.py` lints it and emits the id list, so
  `--allowed-outline-ids` is generated, not hand-typed (editorial + grounding-checker
  specs updated). #6 — `tools/new_article.py` scaffolds from `_TEMPLATE` and validates the
  layout; `_TEMPLATE` gained `sections/` + `outline.json`; `/new-article` calls the tool.
- **Why:** grounding 2→3 depended on stable outline ids with no schema guarantee; new
  articles started missing `sections/` (template ≠ what /new-article claimed).
- **Risk:** outline.md is now optional/secondary — outline.json is the source of truth;
  agents must keep them in sync if both are kept.
- **Verified:** CI — new_article.py builds a complete workspace (guards template drift);
  outline_ids.py emits `1` on the demo, FAILs a malformed fixture (dup id / empty point /
  bad source id).

## 2026-07-01 — #15 per-stage result files + status aggregator (+ grounding 1→2 fixtures)
- **What:** each section stage now writes its own `sec<k>_<stage>.json` (writer / factcheck
  / grounding / audit) instead of a shared `sec<k>_result.json`; new `tools/status.py`
  reads them into a section × stage matrix (derives factcheck status from the verdict
  claims). Plus grounding 1→2 fixtures (good + no-sources bad) — the first faithfulness
  hop was advertised but untested.
- **Why:** Cursor #3 (last-writer-wins clobbered verdicts → resume/status lied) + #4
  (1→2 had no regression test).
- **Risk:** status.py is read-only reporting (always exit 0), not a gate; agents must use
  the stage-specific filenames (specs updated) or their result falls out of the matrix.
- **Verified:** CI — status.py surfaces sec2's derived fact-check `fail`; grounding 1→2
  good→PASS, no-sources bad→FAIL.

## 2026-07-01 — #14 humanizer artifact: audit the de-flavored text, not stale sections
- **What:** S5 humanizer now writes a first-class `humanized.md`; `audit_article.py --draft`
  generalizes the assembled-draft audit (default `final.md`) so S5 audits `humanized.md`
  and S7 builds `final.md` *from* that verified artifact instead of re-assembling sections.
- **Why:** Cursor finding #1 — the humanizer's de-flavored prose was never a named artifact,
  so the re-run audit read the old section drafts and S7 re-assembled; humanized text could
  fall through the verification chain.
- **Risk:** structural check relies on the humanizer preserving `<!-- section:k -->` markers
  / headings; spec now requires it.
- **Verified:** CI `--draft humanized.md` PASSes; a humanized draft that drops `[S2]` FAILs;
  default `final.md` path unchanged.

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

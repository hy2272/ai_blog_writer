# Iteration log

A living, append-only record — **one entry per system-iteration PR**, newest first. This
is the lightweight continuity stream that lets the next architect (or Hanfei) resume from
the repo alone, without re-reading every PR. The full per-session `handoff/handoff-<date>.md`
docs remain for session boundaries; this is the per-PR pulse between them.

**Convention (also in CLAUDE.md):** every PR that changes the system appends an entry here
in the same PR — `what / why / risk / verified`. Keep each entry tight; the PR + commit
carry the detail.

---

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

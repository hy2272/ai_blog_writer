# S5.5 — Gemini polish pass (per-mode temperature, oracle-checked diff, human picks)

**When this applies:** S5.5, a standard pipeline step the orchestrator runs **automatically**
after S5 humanizer (oracles already green) and **before** the S6 human sign-off — on all three
tracks. It is no longer an optional last-mile you might forget: the orchestrator prepares the
polished version + a diff so that when you read the draft you are already looking at both.

**The rule:** run the finished Chinese through `tools/gemini_polish.py`. Gemini's Chinese reads
more natively; borrow that for **fluency only**. Correctness stays locked by the upstream oracles
— the polish must not touch facts, numbers, `[Sn]` citations, structure, or emoji. The machine
stands *beside* your judgement, it does not replace it: nothing is auto-accepted, nothing is
auto-rejected. You read the diff, see which hunks the machine flags, and decide (default: distrust
a 🔴 hunk unless you are sure the flag is a false positive — "说不定润色更好" is exactly why you,
not the machine, make the call).

**Per-mode temperature (the whole reason this is a direct-API script, not a subagent — a subagent
has no temperature knob; a direct API call does):**
- `factual_ai_news` / `mixed_explainer` → **low temp 0.3**: stay conservative, don't reword facts.
- `aesthetic_lifestyle` → **high temp 0.85**: we WANT it to risk a fresher phrasing. The aesthetic
  oracle (破折号 / card length / 「」) + the diff catch any structural overreach, so high temp is
  safe here. (This is the `gemini_temperature` value from the STATE `track` block.)

**Oracle before→after is the authoritative signal (not a reinvented judge):** the tool re-runs the
SAME per-track oracle via `tools/run_oracle.py` on BOTH the pre- and post-polish artifact and shows
the DELTA. Any finding that appears only after polish is, by definition, something the polish broke.
The per-hunk 🟢🟡🔴 tags in the diff are *local machine hints* (did `[Sn]`/numbers change; did a
破折号/「」 appear) pointing you at the change; the banner's oracle delta is the verdict.

```
# factual/explainer prose (markdown in/out); oracle args after a bare `--`:
python3 tools/gemini_polish.py humanized.md --mode factual_ai_news \
    --out polished.md --diff-html polish_diff.html -- \
    --source-pack source_pack.json --contract contracts/sec1_contract.json
# aesthetic card post (JSON in/out; only NON-quote card texts are polished — a verified quote's
# wording carries provenance and must not be reworded):
python3 tools/gemini_polish.py aesthetic_post.json --mode aesthetic_lifestyle \
    --out polished_post.json --diff-html polish_diff.html
# offline (no API cost): regenerate the diff from an already-polished artifact:
python3 tools/gemini_polish.py humanized.md --mode factual_ai_news \
    --polished polished.md --diff-html polish_diff.html -- --source-pack source_pack.json
```
Key lives in a gitignored `.env` at the project root (`GEMINI_API_KEY`, optional `GEMINI_MODEL`).

**Cost guardrail (Hanfei's rule):** the tool estimates cost and REFUSES if it exceeds `--max-usd`
(default $1.00) unless `--force`. A single ~1000-字 post is ≈ $0.001 (flash), so the per-article
auto-run never trips it; the guard only catches an accidental bulk pass. If a planned run could
exceed $1, STOP and ask Hanfei first.

**Why the oracle re-run matters — a real miss caught (2026-06-30, Cursor post):** Gemini "fixed"
`打 75% off` → `打75折`, the OPPOSITE deal (`75% off` = pay 25% ≈ 2.5 折; `75 折` = pay 75%). The
language was better but the fact was inverted. Lesson: fluency-only never means fact-safe — the
machine layer is what makes it safe, not the LLM's good intentions. (Legacy `--check-facts` still
diffs number+unit/date multisets pre→post and exits 3 on a mismatch; the oracle before→after delta
is the stronger, track-aware version of the same guard.)

**Source:** requested by Hanfei (2026-06-30 session): "Gemini 语言很好，最后让它改一遍" → promoted
to an auto-run, oracle-checked, per-mode-temperature S5.5 step in the 2026 architecture rework.

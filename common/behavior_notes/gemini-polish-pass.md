# Final language polish via Gemini (fluency only, after the oracles)

**When this applies:** the very last step of output (S7), AFTER both oracles are green
(citation_audit + grounding_gate). Optional but recommended for a 小红书 / public post.

**The pattern / rule:** run the finished Chinese text through `tools/gemini_polish.py`.
Gemini's Chinese reads more natively; borrow that for fluency ONLY. Correctness is already
locked upstream by the oracles — the polish must not touch facts, numbers, citations,
structure, or emoji. This keeps the funnel intact: machine oracle decides correctness, a
strong LLM only smooths language.

```
python3 tools/gemini_polish.py <final.txt> --out <final.polished.txt> --dry-run   # estimate first
python3 tools/gemini_polish.py <final.txt> --out <final.polished.txt>             # then send
```
Key lives in a gitignored `.env` at the project root (`GEMINI_API_KEY`, optional
`GEMINI_MODEL`). The polish prompt bans English-calque Chinese and the AI-tell words
(炸 / 硬 / 诚实地说 …, see `style_patterns.md §3`).

**Cost guardrail (Hanfei's rule):** the tool estimates cost and REFUSES if it exceeds
`--max-usd` (default $1.00) unless `--force`. A single ~1000-字 post is ≈ $0.001 (flash),
so normal use never trips it. If a planned run could exceed $1 (a bulk pass over many
posts), STOP and ask Hanfei first — state the necessity and let her decide.

**Re-audit after polish — and DIFF THE FACTS, not just the markers:** the polish can
subtly reword a cited sentence AND corrupt a fact while "improving" it. Run the polish with
`--check-facts` (it diffs number+unit / date / discount multisets pre→post and exits 3 on a
mismatch — it catches a flipped unit like `75% off`→`75折` that a bare-number diff misses,
while ignoring benign reformatting like 日↔号 / 美元↔美金). Then re-run `citation_audit.py`
on the polished text for marker integrity.

```
python3 tools/gemini_polish.py <final.txt> --out <polished.txt> --check-facts   # exit 3 → review the diff
```
- **Real miss caught (2026-06-30, Cursor post):** Gemini "fixed" `打 75% off` → `打75折`,
  which is the OPPOSITE deal (`75% off` = pay 25% ≈ 2.5 折; `75 折` = pay 75%). The
  language was better but the fact was inverted. Lesson: fluency-only never means
  fact-safe — the machine/diff layer is what makes it safe, not the LLM's good intentions.

**Why:** the writer/humanizer already aim for native voice, but a dedicated strong-Chinese
model as a final pass catches residual 翻译腔 the in-house chain misses — without ever
re-opening correctness.

**Source:** requested by Hanfei (2026-06-30 session): "Gemini 语言很好，最后让它改一遍."

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

**Re-audit after polish:** the polish can subtly reword a cited sentence. Re-run
`citation_audit.py` on the polished text before shipping; if a marker was dropped, fix it.

**Why:** the writer/humanizer already aim for native voice, but a dedicated strong-Chinese
model as a final pass catches residual 翻译腔 the in-house chain misses — without ever
re-opening correctness.

**Source:** requested by Hanfei (2026-06-30 session): "Gemini 语言很好，最后让它改一遍."

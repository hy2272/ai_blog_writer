# Aesthetic track — non-factual poetic/lifestyle content

**When this applies:** the post is aesthetic, not informational — 生活美学 / 旅游 / 人生感悟 /
小确幸 / 诗意散文 paired with imagery, where the goal is mood and resonance, not facts. This is
a SECOND track alongside the default AI-news track. Pick it when the brief is "诗意感、轻松、
不费神、有主题就行、内容不用多".

**The pattern / rule:**

1. **Skip the fact machine — it is a category error here.** Non-factual prose has no claims
   and no `[Sn]` markers, so `citation_audit`, `fact-checker`, `grounding-checker`, `research`
   and the `source_pack` do NOT apply. Running `citation_audit` on a poem flags every line as
   裸论断. Drop those gates for this track.
2. **The ONE residual fact surface = quoted material.** A real film line / lyric / attribution
   is the only thing left to verify (the oracle shrinks to just the quote). Verify the quote
   and its attribution (a quick web check), OR don't hard-attribute. Everything else is free.
3. **Keep the editorial / writer / humanizer / taste passes.** Concept + structure, the prose
   itself, 去 AI 味, and taste/flow review are all still valuable — only the factual gates go.
4. **"Temperature" is not a subagent knob in this harness.** The orchestrator cannot set a
   sampling temperature on a Claude Code subagent. Realize creative variation instead by
   (a) instructing lyrical/poetic writing and spawning MULTIPLE independent variant drafts
   (diversity = the controllable substitute for high temperature), then curating/merging; and
   (b) dropping the factual gates that pull output toward the conservative/deterministic.
   Literal temperature control needs a direct-API `tools/` script (+ an API key). This is
   now a fixed procedure, not a verbal convention: `/write-aesthetic-post` MUST spawn 3
   independent `writer` variants and then curate/merge the strongest line per card (the
   orchestrator does the merge; log the choices in DECISIONS.md).

**The aesthetic track has its OWN machine oracle now (`tools/aesthetic_audit.py`).**
Skipping the fact machine does not mean skipping machine checks — it means porting the
`citation_audit` *idea* to this track's real failure modes, which are enumerable and do not
need taste: 破折号 (—), over-long cards, banned 翻译腔 phrases (shared
`common/banned_phrases.json`), unbalanced 「」, the 0X / 0N card-numbering consistency, an
overline that leaks AI, and — the ONE residual fact surface — an attributed film line that
is not marked `verified`. Run it on the `aesthetic_post.json` deliverable:
`python3 tools/aesthetic_audit.py articles/article_<slug>/aesthetic_post.json`. This is the
HARD gate for this track (the LLM taste review stays advisory, for what a tool can't judge).
Enter the whole flow via `/write-aesthetic-post <theme>`.

**Tone rules for this track (HARD):**
- **Don't mention AI / that the content is AI-made** — except on AI-news posts. Readers don't
  care how it was made; it is irrelevant to the piece. (e.g. overline 「生活美学」not「AI·生活美学」.)
- **Name a referenced film/work gently; don't stiffly cite.** 「引用自岩井俊二《情书》」is 呆板;
  weave it: 「我学着那句电影《情书》里的台词」.
- **Quotes go in 「」** — 高级感 + 对话感. The standalone quote reads best as its own final card.
- **No 破折号** (see [[style_patterns]] §3). Censorship-adjacent angles avoided (§7).

**Before → after:**
- ❌ Run the news pipeline on a 生活美学 poem → `citation_audit` fails on every 裸论断 line.
- ✅ editorial-lite → 2 independent poetic drafts → curate/merge → verify only the film quote
  → humanizer → photo-triptych output. No citation/fact/grounding gate.

**Why:** the citation oracle is the spine of the news track, but it presupposes factual claims.
Forcing it onto mood content either blocks everything or produces meaningless green. Matching
the track to the content keeps each oracle where it earns its keep.

**Source:** the "把日子过成电影" piece (2026-06-30); Hanfei explicitly identified the
gate-skip and the temperature question. Visual half: [[ai-image-card-pipeline]].

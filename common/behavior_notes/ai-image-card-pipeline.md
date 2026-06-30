# AI-image card pipeline (Nano Banana → triptych/frame cards)

**When this applies:** building image-rich 小红书 cards where the imagery is AI-generated —
aesthetic/lifestyle covers and frames (see [[aesthetic-track]]), or any post that wants real
photographic/illustrated backgrounds instead of the default typographic `editorial` card.

**The pieces (decoupled on purpose):**
- **`tools/gen_image.py`** — produces image FILES via Google's Gemini image models ("Nano
  Banana"). Stdlib `urllib` only (no SDK). Reads `GEMINI_API_KEY` first, then `GOOGLE_API_KEY`,
  from env then repo `.env`. Models: `gemini-3-pro-image` (Pro, best 高级感) / `gemini-2.5-flash-image`
  (flash — fast/cheap, **good enough for backgrounds**, the default for drafts).
- **`platforms/xiaohongshu/adapter.py --style photo-triptych`** — consumes image files and
  composites short text over them. Cover = a 3-band 氛围 triptych (`meta.triptych.bands`); body
  cards = single-photo film frames (`meta.triptych.body_images`, indexed by body order). No
  image for a slot → a graded gradient placeholder, so layout always renders without any API.

The seam: gen_image only makes files; the adapter only consumes them. A card layout never
depends on how its imagery was made (AI / real photo / CSS placeholder).

**HARD conventions (each cost a real iteration to learn):**
- **Billing:** Gemini image gen has NO free tier (`free_tier ... limit: 0`). The project behind
  the key must be on the PAID tier. A 429-quota error ≠ a bad key (auth is fine; the project is
  free-tier). Creating a key ≠ enabling billing.
- **Image library stores RAW originals ONLY.** Save the un-graded Nano Banana output to
  `assets/image_library/` (+ `manifest.json`: prompt/model/palette/tags/date) for reuse. NEVER
  save the CSS-graded composite — reuse may need a different grade. The grade is applied at
  COMPOSE time in CSS, never baked into the saved image.
- **Assets are NOT committed.** `assets/image_library/` is gitignored; `articles/article_*/` is
  already ignored. Images are binary bloat and reproducible via `gen_image.py`. Keep them local.
- **Harmony comes from a LOCKED palette at generation time.** Generate every image in a set on
  ONE explicit grade ("warm cinematic film grade, soft golden-hour amber...") so separately
  generated shots read as a harmonious set. The CSS `.grade` wash is a light unify only; it
  can't rescue a cold/warm clash. No seam lines between bands (they butt directly).

**CJK typography on photo cards (HARD):**
- **Author-controlled line breaks beat auto-wrap.** Write one phrase per source line in the
  draft; the body template joins them with `<br>`. A word then never wraps mid-term — the poet
  breaks at punctuation. Per-term `white-space:nowrap` is whack-a-mole (you protect 配乐, then
  耳机 splits); authored breaks fix the whole class.
- **Belt-and-suspenders nowrap:** `《》「」（）` are auto-protected; extra nouns via
  `meta.triptych.nowrap_terms`.
- **Font is configurable** (`meta.font` = a family name, or `{family, file}` to EMBED an
  `.otf`/`.ttf` via `@font-face` — Chrome renders local fonts only). **Cover stays on the serif
  (Songti) for a composed hook; body 只言片语 cards use the custom (e.g. handwritten) font.**

**How to run:**
```
python3 tools/gen_image.py --model gemini-2.5-flash-image --aspect 16:9 \
  --out assets/image_library/<name>.png --prompt "<subject>, <LOCKED palette>, no text no people"
python3 platforms/xiaohongshu/adapter.py <article>/draft.md \
  --out-dir <article>/assets/xhs --style photo-triptych --meta <meta>.json \
  --tags "#生活美学,#..."   # content-appropriate tags, NOT the AI-news defaults
```

**Why:** lets the system make genuinely beautiful image posts (the v3-SEO-writer gap) while
keeping the text/correctness machinery intact and the repo clean.

**Source:** the photo-triptych redesign + "把日子过成电影" piece (2026-06-30, Hanfei).

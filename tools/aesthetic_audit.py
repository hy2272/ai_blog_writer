#!/usr/bin/env python3
"""aesthetic_audit.py — the machine-checkable oracle for the AESTHETIC (non-factual) track.

The factual AI-news track has `citation_audit.py`: every claim must trace to a dated source.
The aesthetic track (生活美学 / 治愈系 / 诗意散文 card posts) has NO factual claims, so that
oracle is a category error there (see common/behavior_notes/aesthetic-track.md). But aesthetic
cards still have their own enumerable, machine-checkable failure modes — so this tool is the
SECOND port of the citation_audit *idea*: keep the LLM judge (editorial / taste review) for
what needs taste, and let a deterministic tool catch the hard rules that do not.

What it checks (each independently reported; any FAIL -> non-zero exit):
  1. em-dash            a 破折号 (— / ——) anywhere in card text or caption -> FAIL
                        (style_patterns §3 bans it; this stops relying on human eyes)
  2. card-length        a single card longer than --max-card-chars (default 32) -> WARN
                        (this 栏目 is 一句一卡; 32 flags a card that started to crowd)
  3. banned-phrase      a 翻译腔/AI-味 phrase from common/banned_phrases.json -> FAIL/WARN
                        (shared blacklist, same data citation_audit consumes)
  4. quote-closure      「」 quote marks are unbalanced across the post -> FAIL
  5. quote-placement    a standalone quote card is not the LAST card -> WARN
                        (aesthetic-track rule: the quote reads best as the final card)
  6. card-numbering     card indexes are not 1..N contiguous, or a card's `total`
                        disagrees with the real card count (the 0X / 06 consistency) -> FAIL
  7. overline           overline missing -> WARN; overline mentions AI/AIGC/生成式 -> FAIL
                        (aesthetic-track HARD rule: don't say the content is AI-made)
  8. quote-verification the ONE residual fact surface. A quote-card (quote:true, a whole-card
                        「…」, or a card naming a work 《…》 with a 「…」 quote woven in) must have
                        a matching record in `quotes`; a record that
                        names a work/attribution must be `verified` AND carry provenance
                        (`verified_source` URL or `verified_by`). `verified: true` alone is
                        self-certifying — the aesthetic version of the green-dashboard trap —
                        so it FAILs without provenance, mirroring the news track's dated-URL
                        discipline. A free paraphrase with no attribution is fine. The check is
                        relaxed only via --allow-unverified-quotes (a CLI flag, like
                        grounding_gate's --allow-empty) — never a field in the post JSON, so the
                        writer cannot disable its own verification.
  9. card-rhythm        adjacent cards opening on the same character, or one CJK char
                        recurring across most cards -> WARN (氛围 collapses on repetition;
                        style_patterns "don't cluster the same word", now machine-checked)
 10. hashtags           no caption hashtags -> WARN (nothing ties the post to a theme)

Exit code: 0 = PASS (no FAIL), 1 = FAIL. WARN never fails on its own; --strict promotes
WARN -> FAIL. Mirrors citation_audit.py / factcheck_gate.py / grounding_gate.py.

Input — an aesthetic post JSON (the aesthetic track's deliverable, analogous to the news
track's source_pack + contract):
  {
    "track": "aesthetic_lifestyle",
    "theme": "把今天，过成一部电影",
    "overline": "生活美学",
    "visual_style": "film_morning",
    "cards": [
      {"index": 1, "total": 6, "text": "…"},
      {"index": 6, "total": 6, "text": "「…」", "quote": true}
    ],
    "caption": "… #生活美学 #治愈系日常",
    "hashtags": ["#生活美学", "#治愈系日常"],
    "quotes": [{"text": "…", "work": "《情书》", "verified": true,
                "verified_source": "https://… (or \"verified_by\": \"human@2026-07-01\")"}]
  }

A `verified` quote MUST carry provenance (`verified_source` or `verified_by`); a bare
`verified: true` is self-certifying and FAILs (see check 8).
"""
import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BANNED = REPO_ROOT / "common" / "banned_phrases.json"
# A Chinese 破折号 is U+2014 (—, usually doubled ——) / U+2015 (―) / the two-em variants.
# The ASCII "--" was dropped on purpose: aesthetic cards never contain code (unlike the
# news track, which strips code fences), so "--" here only produced false positives.
EM_DASH_RE = re.compile(r"[—―⸺⸻]")
OPEN_QUOTE = "「"
CLOSE_QUOTE = "」"
# The aesthetic track must not advertise that the content is AI-made. Match liberally —
# on this track an overline mentioning AI/AIGC/生成式 is never legitimate, so over-catching
# is the safe direction (unlike the body, where "AI" is a normal topic word).
AI_RE = re.compile(r"AI|AIGC|人工智能|生成式|智能生成|AI\s*生成|AI\s*制作", re.IGNORECASE)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
# Function words / pronouns are the WRONG target for the clustering check: 我 on 5 of 6 cards
# is normal for a 治愈系日记体 post (the first person IS the voice), so warning on it would be
# a permanently-lit yellow light nobody reads. Only CONTENT-word clustering (光 / 电影 on most
# cards) signals real 氛围 collapse. Exempt the high-frequency structural chars.
RHYTHM_STOPWORDS = set("我你他她它的了是在有也就都不一这那和与之很会要把被让给到又还只能着过去来上下")


class Finding:
    def __init__(self, level, check, message):
        self.level = level  # "FAIL" | "WARN"
        self.check = check
        self.message = message

    def __str__(self):
        return f"  [{self.level}] {self.check}: {self.message}"


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def visible_len(text):
    """Character count excluding whitespace — the reader's sense of how long a card is."""
    return len(re.sub(r"\s+", "", text or ""))


def card_text(card):
    return card.get("text", "") if isinstance(card, dict) else str(card)


def check_em_dash(cards, caption):
    out = []
    for i, card in enumerate(cards, 1):
        if EM_DASH_RE.search(card_text(card)):
            out.append(Finding("FAIL", "em-dash",
                               f"card {i} contains a 破折号 (—); use 。，：or a new line instead"))
    if caption and EM_DASH_RE.search(caption):
        out.append(Finding("FAIL", "em-dash", "caption contains a 破折号 (—); rewrite without it"))
    return out


def check_card_length(cards, max_chars):
    out = []
    for i, card in enumerate(cards, 1):
        n = visible_len(card_text(card))
        if n > max_chars:
            out.append(Finding("WARN", "card-length",
                               f"card {i} is {n} chars (> {max_chars}); too long to read on one card"))
    return out


def check_banned_phrases(cards, caption, banned):
    out = []
    haystacks = [(f"card {i}", card_text(c)) for i, c in enumerate(cards, 1)]
    if caption:
        haystacks.append(("caption", caption))
    for entry in banned.get("phrases", []):
        phrase = entry.get("phrase")
        if not phrase:
            continue
        for where, text in haystacks:
            if phrase.lower() in (text or "").lower():
                level = "FAIL" if str(entry.get("level", "FAIL")).upper() == "FAIL" else "WARN"
                reason = entry.get("reason", "banned phrase")
                suggest = entry.get("suggest")
                msg = f"{where}: 「{phrase}」— {reason}"
                if suggest:
                    msg += f"；改用：{suggest}"
                out.append(Finding(level, "banned-phrase", msg))
    return out


def check_quote_closure(cards, caption):
    out = []
    text = "".join(card_text(c) for c in cards) + (caption or "")
    opens = text.count(OPEN_QUOTE)
    closes = text.count(CLOSE_QUOTE)
    if opens != closes:
        out.append(Finding("FAIL", "quote-closure",
                           f"「 count ({opens}) != 」 count ({closes}); a quote is not closed"))
    return out


def check_quote_placement(cards):
    out = []
    n = len(cards)
    for i, card in enumerate(cards, 1):
        is_quote = isinstance(card, dict) and card.get("quote")
        # A card whose whole text is a 「」 quote reads as a standalone quote card too.
        text = card_text(card).strip()
        looks_quote = text.startswith(OPEN_QUOTE) and text.endswith(CLOSE_QUOTE)
        if (is_quote or looks_quote) and i != n:
            out.append(Finding("WARN", "quote-placement",
                               f"card {i} is a standalone quote but is not the last card "
                               f"(of {n}); the quote reads best as the final card"))
    return out


def check_card_numbering(cards):
    out = []
    n = len(cards)
    if n == 0:
        out.append(Finding("FAIL", "card-numbering", "post has no cards"))
        return out
    indexes = []
    for pos, card in enumerate(cards, 1):
        if not isinstance(card, dict):
            continue
        idx = card.get("index")
        total = card.get("total")
        if idx is not None and idx != pos:
            out.append(Finding("FAIL", "card-numbering",
                               f"card at position {pos} declares index {idx} (out of order)"))
        if idx is not None:
            indexes.append(idx)
        if total is not None and total != n:
            out.append(Finding("FAIL", "card-numbering",
                               f"card {pos} declares total {total} but the post has {n} cards "
                               f"(the 0X / 0{n} numbering is inconsistent)"))
    if indexes and sorted(indexes) != list(range(1, len(indexes) + 1)):
        out.append(Finding("FAIL", "card-numbering",
                           f"card indexes are not contiguous 1..N: {indexes}"))
    return out


def check_overline(post):
    out = []
    overline = post.get("overline")
    if not overline:
        out.append(Finding("WARN", "overline",
                           "no overline set; aesthetic cards want a gentle eyebrow like 「生活美学」"))
        return out
    if AI_RE.search(overline):
        out.append(Finding("FAIL", "overline",
                           f"overline 「{overline}」mentions AI; the aesthetic track must not "
                           f"advertise that the content is AI-made — use 「生活美学」or similar"))
    return out


def _quote_label(q):
    return q.get("work") or q.get("attribution") or q.get("author") or "attributed quote"


def _has_provenance(q):
    """A verified quote must say WHO verified it and WHERE — not just carry a bare boolean.
    Accepts a `verified_source` (URL/citation) or a `verified_by` (e.g. human@date)."""
    return bool(q.get("verified_source") or q.get("verified_by"))


WORK_TITLE_RE = re.compile(r"《[^》]+》")
INLINE_QUOTE_RE = re.compile(r"「[^」]+」")


def _looks_like_quote_card(card):
    text = card_text(card).strip()
    return text.startswith(OPEN_QUOTE) and text.endswith(CLOSE_QUOTE)


def _embeds_attributed_quote(card):
    """A card that names a work (《…》) AND carries a 「…」 quote is an attributed quote even
    if it is woven into prose ("我想起《情书》里的「你好吗？我很好」") and lacks quote:true — so
    it still needs a verified record. Scoped to BOTH markers present to avoid firing on a
    card that merely uses 「」 for emphasis."""
    text = card_text(card)
    return bool(WORK_TITLE_RE.search(text) and INLINE_QUOTE_RE.search(text))


def _norm_quote(text):
    return (text or "").strip().strip(OPEN_QUOTE).strip(CLOSE_QUOTE).strip()


def _quote_record_for(card_text_stripped, quotes):
    """Find the quotes[] record for this card. Prefer an EXACT (normalized-equal) match so a
    short quote that is a substring of another ("我很好" vs "你好吗？我很好。") maps to the right
    record, not merely the first overlapping one — a mis-match would attribute record A's
    provenance to card B. Fall back to substring only when no exact match exists."""
    needle = _norm_quote(card_text_stripped)
    if not needle:
        return None
    records = [q for q in quotes if isinstance(q, dict)]
    for q in records:  # exact first
        if _norm_quote(q.get("text")) == needle:
            return q
    for q in records:  # then containment either way
        qt = _norm_quote(q.get("text"))
        if qt and (qt in needle or needle in qt):
            return q
    return None


def check_quote_verification(post):
    """The aesthetic track's shrunk oracle. Two layers, both closing the "marked-verified !=
    actually-verified" gap:
      (a) every quotes[] record that names a work/attribution must be verified WITH provenance;
      (b) every quote-CARD (quote:true, a whole-card 「…」, or a woven-in 《…》+「…」) must map to
          such a record, so an agent cannot ship a bare `{"text":"「…」","quote":true}` with no
          verification trail.
    A free paraphrase with no attribution and no quote flag is fine — nothing to verify.

    Findings are emitted at FAIL level; the CALLER downgrades them to WARN when the runner
    passes --allow-unverified-quotes. The exemption lives on the CLI (with whoever RUNS the
    gate), NOT in the post JSON — otherwise the writing agent could set
    `quote_verification_required:false` in its own output to walk past the check (the same
    backdoor as a self-asserted verified:true). A data field attempting to turn it off is
    flagged here as a separate WARN regardless."""
    out = []
    quotes = post.get("quotes", []) or []

    if post.get("quote_verification_required") is False:
        out.append(Finding("WARN", "quote-verification",
                           "post JSON sets quote_verification_required:false — this switch is "
                           "IGNORED (exemption is the CLI flag --allow-unverified-quotes, not a "
                           "data field the writer controls). Remove it, or run the gate with the flag"))

    for i, q in enumerate(quotes, 1):
        if not isinstance(q, dict):
            continue
        attributed = q.get("work") or q.get("attribution") or q.get("author") or q.get("attributed")
        if not attributed:
            continue
        if not q.get("verified"):
            out.append(Finding("FAIL", "quote-verification",
                               f"quote {i} attributes to {_quote_label(q)!r} but is not marked "
                               f"verified:true — verify the line + its source, or drop the attribution"))
        elif not _has_provenance(q):
            out.append(Finding("FAIL", "quote-verification",
                               f"quote {i} ({_quote_label(q)!r}) is marked verified:true but has no "
                               f"provenance — add verified_source (URL) or verified_by (who@date). "
                               f"A bare boolean is self-certifying (the green-dashboard trap)"))

    for pos, card in enumerate(post.get("cards", []), 1):
        is_quote_card = ((isinstance(card, dict) and card.get("quote"))
                         or _looks_like_quote_card(card)
                         or _embeds_attributed_quote(card))
        if not is_quote_card:
            continue
        rec = _quote_record_for(card_text(card), quotes)
        if rec is None:
            out.append(Finding("FAIL", "quote-verification",
                               f"card {pos} is a quote card but has no matching record in `quotes` — "
                               f"register the line (with a source) so it can be verified"))
            continue
        if not (rec.get("verified") and _has_provenance(rec)):
            out.append(Finding("FAIL", "quote-verification",
                               f"card {pos}'s quote ({_quote_label(rec)!r}) must be verified with "
                               f"provenance (verified + verified_source/verified_by)"))
    return out


def _downgrade(findings, check, from_level="FAIL", to_level="WARN"):
    for f in findings:
        if f.check == check and f.level == from_level:
            f.level = to_level
    return findings


def check_card_rhythm(cards):
    """Aesthetic cards die on repetition. Two machine-checkable tells:
      - adjacent cards opening on the same character (three cards starting 「光…」reads flat);
      - one CJK character recurring across most cards (over-clustering one word).
    Both WARN — this is taste-adjacent, so it surfaces for a human rather than hard-blocking."""
    out = []
    firsts = []
    for card in cards:
        t = card_text(card).strip().lstrip(OPEN_QUOTE)
        firsts.append(t[0] if t else "")
    for i in range(1, len(firsts)):
        # Skip a shared stopword opening (两张都以「我」开头 is natural in a diary voice).
        if firsts[i] and firsts[i] == firsts[i - 1] and firsts[i] not in RHYTHM_STOPWORDS:
            out.append(Finding("WARN", "card-rhythm",
                               f"cards {i} and {i + 1} both open on 「{firsts[i]}」— vary the opening"))
    counts = {}
    for card in cards:
        for ch in set(CJK_RE.findall(card_text(card))):  # per-card presence, not raw frequency
            if ch in RHYTHM_STOPWORDS:
                continue  # function words / pronouns are not 氛围-flattening clustering
            counts[ch] = counts.get(ch, 0) + 1
    n = len(cards)
    if n >= 4:
        threshold = max(4, (n * 3 + 3) // 4)  # ceil(0.75 * n), min 4
        for ch, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            if c >= threshold:
                out.append(Finding("WARN", "card-rhythm",
                                   f"「{ch}」appears on {c} of {n} cards — clustering one word flattens 氛围"))
    return out


def check_hashtags(post):
    out = []
    tags = post.get("hashtags")
    caption = post.get("caption", "")
    if not tags and "#" not in caption:
        out.append(Finding("WARN", "hashtags",
                           "no hashtags in the post — nothing ties it to a theme/栏目"))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Machine-checkable audit for aesthetic-track card posts.")
    ap.add_argument("post", help="path to the aesthetic post JSON")
    ap.add_argument("--banned-phrases", default=str(DEFAULT_BANNED),
                    help=f"JSON blacklist of 翻译腔/AI-味 phrases (default {DEFAULT_BANNED})")
    ap.add_argument("--skip-banned", action="store_true", help="skip the banned-phrase check")
    ap.add_argument("--max-card-chars", type=int, default=32,
                    help="warn when a single card is longer than this (default 32; this 栏目 is 一句一卡)")
    ap.add_argument("--allow-unverified-quotes", action="store_true",
                    help="relax the requirement that every quote card map to a verified record. "
                         "The exemption lives on the CLI (with whoever RUNS the gate), never in "
                         "the post JSON — a writer must not be able to disable its own check. "
                         "(Attributed-quote records still need provenance; quote cards still need "
                         "a matching record — this only drops the verified-with-provenance demand.)")
    ap.add_argument("--strict", action="store_true", help="promote WARN findings to failures")
    args = ap.parse_args(argv)

    post = load_json(args.post)
    cards = post.get("cards", [])
    caption = post.get("caption", "")

    findings = []
    findings += check_em_dash(cards, caption)
    findings += check_card_length(cards, args.max_card_chars)
    if not args.skip_banned:
        banned_path = Path(args.banned_phrases)
        if banned_path.exists():
            findings += check_banned_phrases(cards, caption, load_json(banned_path))
        else:
            findings.append(Finding("WARN", "banned-phrase",
                                    f"banned-phrase list not found: {banned_path} (check skipped)"))
    findings += check_quote_closure(cards, caption)
    findings += check_quote_placement(cards)
    findings += check_card_numbering(cards)
    findings += check_overline(post)
    quote_findings = check_quote_verification(post)
    if args.allow_unverified_quotes:
        # The RUNNER accepts unverified quotes — findings stay visible but stop blocking.
        _downgrade(quote_findings, "quote-verification")
    findings += quote_findings
    findings += check_card_rhythm(cards)
    findings += check_hashtags(post)

    fails = [f for f in findings if f.level == "FAIL"]
    warns = [f for f in findings if f.level == "WARN"]
    if args.strict:
        fails += warns
        warns = []

    print(f"aesthetic_audit: {args.post}")
    print(f"  cards={len(cards)}  quotes={len(post.get('quotes', []))}  "
          f"overline={post.get('overline')!r}  FAIL={len(fails)}  WARN={len(warns)}")
    for f in findings:
        print(f)

    if fails:
        print("\nRESULT: FAIL")
        return 1
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

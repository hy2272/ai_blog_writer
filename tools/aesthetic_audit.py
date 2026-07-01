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
  2. card-length        a single card longer than --max-card-chars (default 40) -> WARN
                        (a card 读不下去 is a swipe lost)
  3. banned-phrase      a 翻译腔/AI-味 phrase from common/banned_phrases.json -> FAIL/WARN
                        (shared blacklist, same data citation_audit consumes)
  4. quote-closure      「」 quote marks are unbalanced across the post -> FAIL
  5. quote-placement    a standalone quote card is not the LAST card -> WARN
                        (aesthetic-track rule: the quote reads best as the final card)
  6. card-numbering     card indexes are not 1..N contiguous, or a card's `total`
                        disagrees with the real card count (the 0X / 06 consistency) -> FAIL
  7. overline           overline missing -> WARN; overline mentions AI -> FAIL
                        (aesthetic-track HARD rule: don't say the content is AI-made)
  8. quote-verification the ONE residual fact surface. A quote that names a work/attribution
                        but is not marked `verified: true` -> FAIL. This is the aesthetic
                        track's shrunk oracle: verify the film line, everything else is free.
  9. hashtags           no caption hashtags -> WARN (nothing ties the post to a theme)

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
    "quotes": [{"text": "…", "work": "《情书》", "verified": true}]
  }
"""
import argparse
import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BANNED = REPO_ROOT / "common" / "banned_phrases.json"
# Any of these is a Chinese 破折号 (or its calque). A plain hyphen "-" is fine.
EM_DASH_RE = re.compile(r"[—―⸺⸻]|--")
OPEN_QUOTE = "「"
CLOSE_QUOTE = "」"
AI_RE = re.compile(r"\bAI\b|人工智能|AI\s*生成|AI\s*制作", re.IGNORECASE)


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


def check_quote_verification(post):
    """The aesthetic track's shrunk oracle: a quote that names a real work/attribution is the
    only fact surface left, so it must be verified. A free paraphrase with no attribution is
    fine (nothing to verify)."""
    out = []
    for i, q in enumerate(post.get("quotes", []), 1):
        if not isinstance(q, dict):
            continue
        attributed = q.get("work") or q.get("attribution") or q.get("author") or q.get("attributed")
        if attributed and not q.get("verified"):
            label = q.get("work") or q.get("attribution") or q.get("author") or "attributed quote"
            out.append(Finding("FAIL", "quote-verification",
                               f"quote {i} attributes to {label!r} but is not marked "
                               f"verified:true — verify the line + its source, or drop the attribution"))
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
    ap.add_argument("--max-card-chars", type=int, default=40,
                    help="warn when a single card is longer than this (default 40)")
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
    findings += check_quote_verification(post)
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

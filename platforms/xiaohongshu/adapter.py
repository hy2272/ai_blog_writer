#!/usr/bin/env python3
"""Render a verified article as a Xiaohongshu long-image technical post.

Default deliverable:
  - card_01.html ... card_N.html
  - card_01.png  ... card_N.png when Chrome is available
  - post_xiaohongshu.txt paste-ready caption
  - content_manifest.json for the publish queue

The adapter is deliberately stdlib-only. PNG rendering uses a local Chrome binary when
available; CI can pass --no-render and still verify the package structure.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


CARD_W = 1080
CARD_H = 1440
# Display-width budget for one card's body. Calibrated so the body actually FILLS the
# 1440px-tall card at the current type scale (body 36px / line-height 1.66 ≈ 17 lines ×
# ~50 display units), instead of floating in the top third. Higher budget => fewer, denser
# cards (content flows to fill a card, then spills to the next) rather than a fixed count.
# Render-verified against the longest section; keep a safety margin so a 2-line title plus a
# full body never clips. The CI overflow test asserts no card exceeds this value.
MAX_BODY_CHARS = 680
DEFAULT_TAGS = ["#科技资讯早知道", "#人工智能", "#AI工具", "#效率神器", "#vibecoding"]
CITE_RE = re.compile(r"\[(S\d+(?:\s*,\s*S\d+)*)\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
REF_HEADING_RE = re.compile(r"^(references|参考|参考来源|sources|source list)$", re.I)
# A line that is ONLY hashtags (e.g. "#人工智能 #AI出图"). These belong in the caption's
# tag block, not burned into a card image — extracted as tags, kept off the cards.
HASHTAG_LINE_RE = re.compile(r"^#\S+(?:\s+#\S+)*$")


@dataclass
class Section:
    title: str
    paragraphs: list[str]


@dataclass
class Card:
    kind: str
    title: str
    body: list[str]
    kicker: str = ""
    outline: list[str] | None = None  # cover only: the "这篇讲什么" reading route


def display_len(text: str) -> int:
    total = 0
    for ch in text:
        total += 2 if "\u4e00" <= ch <= "\u9fff" else 1
    return total


def strip_markdown_inline(text: str) -> str:
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1", text)
    return text.strip()


def parse_markdown(text: str) -> tuple[str, list[Section], list[str], set[str], list[str]]:
    title = "小红书技术长图文"
    sections: list[Section] = []
    refs: list[str] = []
    tags: list[str] = []
    current: Section | None = None
    in_refs = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("<!--"):
            continue

        m = HEADING_RE.match(line)
        if m:
            heading = strip_markdown_inline(m.group(2))
            if m.group(1) == "#" and title == "小红书技术长图文":
                title = heading
                continue
            if REF_HEADING_RE.match(heading):
                in_refs = True
                current = None
                continue
            current = Section(heading, [])
            sections.append(current)
            in_refs = False
            continue

        if HASHTAG_LINE_RE.match(line):
            tags.extend(line.split())
            continue

        clean = strip_markdown_inline(line)
        if in_refs:
            refs.append(clean)
        else:
            if current is None:
                current = Section("先说结论", [])
                sections.append(current)
            current.paragraphs.append(clean)

    citations = set()
    for m in CITE_RE.finditer(text):
        for tok in m.group(1).split(","):
            citations.add(tok.strip())
    return title, sections, refs, citations, tags


# A "sentence" is text up to a terminal punctuation mark, keeping any citation
# markers ([S1], [S1,S3]) that trail the punctuation attached to their claim so a
# split never orphans a citation onto the next card.
SENTENCE_RE = re.compile(r".+?(?:[。！？!?]+(?:\s*\[S[^\]]*\])*|$)", re.S)


def split_into_sentences(text: str) -> list[str]:
    return [m.group(0).strip() for m in SENTENCE_RE.finditer(text) if m.group(0).strip()]


def hard_split(text: str, max_chars: int) -> list[str]:
    """Last resort for a single sentence with no terminal punctuation that is still
    wider than a card: cut on display width so it can never overflow."""
    out: list[str] = []
    current: list[str] = []
    n = 0
    for ch in text:
        w = 2 if "一" <= ch <= "鿿" else 1
        if current and n + w > max_chars:
            out.append("".join(current))
            current = []
            n = 0
        current.append(ch)
        n += w
    if current:
        out.append("".join(current))
    return out


def split_long_paragraph(para: str, max_chars: int) -> list[str]:
    """Break a paragraph wider than one card into card-sized pieces on sentence
    boundaries (hard-splitting a lone over-wide sentence as a fallback)."""
    if display_len(para) <= max_chars:
        return [para]
    pieces: list[str] = []
    current: list[str] = []
    n = 0
    for sent in split_into_sentences(para):
        s_len = display_len(sent)
        if current and n + s_len > max_chars:
            pieces.append("".join(current))
            current = []
            n = 0
        if s_len > max_chars:
            if current:
                pieces.append("".join(current))
                current = []
                n = 0
            pieces.extend(hard_split(sent, max_chars))
            continue
        current.append(sent)
        n += s_len
    if current:
        pieces.append("".join(current))
    return pieces


def chunk_paragraphs(paragraphs: list[str], max_chars: int = MAX_BODY_CHARS) -> list[list[str]]:
    # Expand any over-wide paragraph into card-sized pieces first, so a single long
    # paragraph can never silently overflow a fixed-height card (cards are the product).
    expanded: list[str] = []
    for para in paragraphs:
        expanded.extend(split_long_paragraph(para, max_chars))

    chunks: list[list[str]] = []
    current: list[str] = []
    n = 0
    for para in expanded:
        p_len = display_len(para)
        if current and n + p_len > max_chars:
            chunks.append(current)
            current = []
            n = 0
        current.append(para)
        n += p_len
    if current:
        chunks.append(current)
    return chunks


def build_cards(
    title: str,
    sections: list[Section],
    refs: list[str],
    citations: set[str],
    cover_title: str | None = None,
    cover_subtitle: str | None = None,
) -> list[Card]:
    # Card 1 merges the hook cover with the "这篇讲什么" reading route. A standalone outline
    # card was too sparse and forced an extra swipe before any value — the reader sees the
    # hook AND the map on the first image. (refs is provenance, not a post asset → dropped.)
    cover_body = [cover_subtitle] if cover_subtitle else ["技术帖长图版"]
    outline = [s.title for s in sections]
    cards: list[Card] = [
        Card("cover", (cover_title or title)[:28], cover_body, "AI / 技术更新",
             outline=outline[:6] or None),
    ]

    # One card per section; a section only splits when its body overflows one card. The
    # final.md segments are the layout basis — three segments → three text cards by default.
    for i, section in enumerate(sections, start=1):
        chunks = chunk_paragraphs(section.paragraphs)
        for j, chunk in enumerate(chunks or [["这一节没有正文。"]], start=1):
            suffix = f" · {j}" if len(chunks) > 1 else ""
            cards.append(Card("body", section.title, chunk, f"{i:02d}{suffix}"))

    return cards


def card_body_width(card: Card) -> int:
    return sum(display_len(p) for p in card.body)


# Citation markers ([S1], [S1,S3]) are STRIPPED from the rendered cards: the cards are the
# paste-and-post deliverable, and inline [Sn] reads like debug output to a 小红书 reader.
# Provenance still lives in final.md (where the citation audit enforces it) and in the
# manifest's citation_ids — it is just not shown on the image.
CITE_SPAN_RE = re.compile(r"\s*\[S\d+(?:\s*,\s*S\d+)*\]")


def _format_paragraph(text: str) -> str:
    stripped = CITE_SPAN_RE.sub("", text)
    stripped = re.sub(r"[ \t]{2,}", " ", stripped).strip()
    return html.escape(stripped)


# ----------------------------------------------------------------------------------------
# Template family. html_card() dispatches on `style`; each style is a cover treatment plus a
# matching body treatment. The default "editorial" style is the clean typographic tech card.
# "photo-triptych" is the 氛围感三段式 art/lifestyle cover: three stacked atmospheric photo
# bands with a serif title overlaid on the middle band. The composition CONSUMES image files
# (produced by tools/gen_image.py); when no image is supplied for a band it falls back to a
# graded gradient so the LAYOUT is always renderable without any image API.
# ----------------------------------------------------------------------------------------

# Self-contained film grain (inline SVG turbulence, no asset). Overlaid at low opacity with
# a blend mode so it reads as photographic grain over either a real photo or the gradient.
GRAIN_URI = (
    "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E"
    "%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' "
    "numOctaves='2' stitchTiles='stitch'/%3E%3C/filter%3E"
    "%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E"
)

# Placeholder grades for the three bands when no real photo is supplied — three dusk moods
# (cool / warm / soft) so the card still reads as "three distinct moments", not one flat block.
_BAND_PLACEHOLDER = (
    "linear-gradient(155deg,#27333f 0%,#3c4a55 100%)",
    "linear-gradient(155deg,#5e4334 0%,#8a5a40 100%)",
    "linear-gradient(155deg,#a78473 0%,#caa996 100%)",
)


def _img_uri(path: str) -> str:
    """Resolve a band image path to something Chrome can load. Absolute paths become
    file:// URIs; a relative path is left as-is (Chrome resolves it against the temp HTML,
    which is written into out_dir, so assets beside the cards just work)."""
    p = Path(path)
    if p.is_absolute() or p.exists():
        return p.resolve().as_uri()
    return path


# Default serif stack for card display type — overridable per-post via meta["font"].
_SERIF_FALLBACK = '"Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", "STSong", serif'


def _resolve_font(meta: dict) -> tuple[str, str]:
    """Return (font_face_block, serif_stack) from meta["font"].

    meta["font"] may be a family-name string (must be installed on the rendering machine),
    or {"family": "...", "file": "/path/to/font.otf"} to EMBED a font file via @font-face so
    it renders without a system install. Chrome renders with local fonts only, so one of the
    two must hold for a custom face to appear; otherwise we fall back to the serif stack."""
    f = (meta or {}).get("font") or {}
    if isinstance(f, str):
        f = {"family": f}
    family = (f.get("family") or "").strip()
    file = (f.get("file") or "").strip()
    face = ""
    if family and file:
        face = (f"@font-face {{ font-family:'{family}'; "
                f"src:url('{_img_uri(file)}'); font-weight:400 700; font-display:swap; }}")
    stack = (f'"{family}", ' if family else "") + _SERIF_FALLBACK
    return face, stack


# CJK line-breaking: a term must never be split across two lines (half on one line, the rest
# on the next). Bracketed titles/quotes (《》「」『』) are ALWAYS protected; extra plain-noun
# terms come from meta["triptych"]["nowrap_terms"]. Each protected run gets white-space:nowrap,
# so if it does not fit it moves WHOLE to the next line. Runs on already-escaped text.
_BRACKET_RE = re.compile(r"《[^》]*》|「[^」]*」|『[^』]*』|（[^）]*）")


def _nowrap_html(escaped_text: str, terms: list[str] | None) -> str:
    out = _BRACKET_RE.sub(lambda m: f'<span class="nw">{m.group(0)}</span>', escaped_text)
    for t in terms or []:
        t = (t or "").strip()
        if t:
            esc = html.escape(t)
            out = out.replace(esc, f'<span class="nw">{esc}</span>')
    return out


def html_cover_triptych(card: Card, idx: int, total: int, meta: dict) -> str:
    trip = (meta or {}).get("triptych", {}) or {}
    bands = list(trip.get("bands") or [])
    overline = html.escape(trip.get("overline") or card.kicker or "")
    tagline = html.escape(trip.get("tagline") or "")  # English italic accent line
    title = html.escape(card.title)
    subtitle = html.escape(card.body[0]) if card.body else ""

    # The cover stays on the stable serif (Songti) for a composed, grown-up hook; the custom
    # handwritten font is reserved for the body "只言片语" cards (set via meta["font"]).
    font_face, serif_stack = "", _SERIF_FALLBACK

    band_divs = []
    for i in range(3):
        src = bands[i] if i < len(bands) and bands[i] else None
        if src:
            photo = f"background-image:url('{_img_uri(src)}');"
        else:
            photo = f"background-image:{_BAND_PLACEHOLDER[i]};"
        overlay = ""
        if i == 1:  # middle band carries the title
            sub = f'<div class="t-sub">{subtitle}</div>' if subtitle else ""
            tag = f'<div class="t-tag">{tagline}</div>' if tagline else ""
            overlay = (
                '<div class="t-veil"></div>'
                f'<div class="t-text">{tag}<h1>{title}</h1>{sub}</div>'
            )
        band_divs.append(
            f'<div class="band b{i+1}"><div class="photo" style="{photo}"></div>{overlay}</div>'
        )
    bands_html = "\n  ".join(band_divs)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width={CARD_W}, initial-scale=1" />
<style>
{font_face}
:root {{
  --serif: {serif_stack};
  --sans: -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", sans-serif;
  --gold: #e7c79b;
  --paper: #f3ede2;
}}
* {{ box-sizing: border-box; }}
body {{ margin:0; width:{CARD_W}px; height:{CARD_H}px; background:#15110d; }}
.trip {{ position:relative; width:{CARD_W}px; height:{CARD_H}px; overflow:hidden; display:flex; flex-direction:column; }}
.band {{ position:relative; flex:1 1 0; overflow:hidden; }}
/* Per-band photo. The sepia+desaturate pass pulls disparate shots (a cool street, a warm
   cafe) toward ONE film grade so three separately-generated images read as a harmonious
   set, not a cold/warm clash. Bands butt directly together — no seam line. */
.photo {{ position:absolute; inset:0; background-size:cover; background-position:center;
  filter:saturate(.88) contrast(1.04) brightness(.97) sepia(.10) hue-rotate(-5deg);
  transform:scale(1.04); }}
/* A light warm wash binds the bands without muddying them — the heavy lifting on harmony is
   done at the source (all three photos generated on one locked palette). */
.grade {{ position:absolute; inset:0; z-index:3; pointer-events:none; mix-blend-mode:soft-light;
  background:linear-gradient(180deg, rgba(196,148,96,.30) 0%, rgba(170,128,86,.18) 50%, rgba(196,148,96,.32) 100%); }}
.t-veil {{ position:absolute; inset:0; z-index:1;
  background:linear-gradient(90deg, rgba(10,8,6,.55) 0%, rgba(10,8,6,.30) 45%, rgba(10,8,6,.55) 100%); }}
.t-text {{ position:absolute; inset:0; z-index:2; display:flex; flex-direction:column;
  align-items:center; justify-content:center; text-align:center; padding:0 90px; }}
.t-tag {{ font-family:var(--serif); font-style:italic; font-size:38px; color:var(--gold);
  letter-spacing:.04em; margin-bottom:22px; text-shadow:0 2px 14px rgba(0,0,0,.5); }}
.t-text h1 {{ font-family:var(--serif); font-weight:700; font-size:88px; line-height:1.18;
  color:#fdfbf6; margin:0; letter-spacing:.01em; text-shadow:0 3px 22px rgba(0,0,0,.55); }}
.t-sub {{ margin-top:26px; font-family:var(--sans); font-size:30px; color:rgba(253,251,246,.9);
  letter-spacing:.02em; text-shadow:0 2px 14px rgba(0,0,0,.5); }}
/* film grain across the whole card */
.grain {{ position:absolute; inset:0; z-index:4; pointer-events:none;
  background-image:url("{GRAIN_URI}"); background-size:140px 140px;
  mix-blend-mode:overlay; opacity:.13; }}
/* editorial corner marks */
.mark {{ position:absolute; z-index:5; font-family:var(--serif); color:rgba(243,237,226,.92);
  font-size:25px; letter-spacing:.18em; text-shadow:0 1px 8px rgba(0,0,0,.55); }}
.mark.eyebrow {{ top:54px; left:64px; text-transform:uppercase; font-family:var(--sans);
  font-weight:700; font-size:24px; }}
.mark.page {{ bottom:50px; right:64px; }}
.mark.dot {{ bottom:50px; left:64px; }}
</style>
</head>
<body>
<main class="trip">
  {bands_html}
  <div class="grade"></div>
  <div class="grain"></div>
  <div class="mark eyebrow">{overline}</div>
  <div class="mark dot">· 收藏 ·</div>
  <div class="mark page">{idx:02d} / {total:02d}</div>
</main>
</body>
</html>
"""


def html_body_photo(card: Card, idx: int, total: int, meta: dict, body_index: int) -> str:
    """A single-photo body card for the aesthetic track: one atmospheric background with a
    short poetic passage centered over it — a film frame. Same warm grade + grain as the
    triptych cover so the whole post reads as one set. Falls back to a gradient if no image."""
    trip = (meta or {}).get("triptych", {}) or {}
    imgs = trip.get("body_images") or []
    src = imgs[body_index] if body_index < len(imgs) and imgs[body_index] else None
    if src:
        photo = f"background-image:url('{_img_uri(src)}');"
    else:
        photo = f"background-image:{_BAND_PLACEHOLDER[body_index % 3]};"
    # Author-controlled line breaks: each source line of the passage is ITS OWN display line
    # (joined with <br>), so a phrase never wraps mid-word — the poet decides every break at a
    # punctuation boundary. nowrap on bracketed titles/quotes is a belt-and-suspenders guard.
    terms = trip.get("nowrap_terms")
    lines = [_nowrap_html(html.escape(ln), terms) for ln in (card.body or [])]
    text = "<br>".join(lines)
    overline = html.escape(trip.get("overline") or "")
    font_face, serif_stack = _resolve_font(meta)

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width={CARD_W}, initial-scale=1" />
<style>
{font_face}
:root {{
  --serif: {serif_stack};
  --gold: #e7c79b;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; width:{CARD_W}px; height:{CARD_H}px; background:#15110d; }}
.frame {{ position:relative; width:{CARD_W}px; height:{CARD_H}px; overflow:hidden; }}
.photo {{ position:absolute; inset:0; background-size:cover; background-position:center;
  filter:saturate(.88) contrast(1.04) brightness(.95) sepia(.10) hue-rotate(-5deg); transform:scale(1.04); }}
.grade {{ position:absolute; inset:0; z-index:1; pointer-events:none; mix-blend-mode:soft-light;
  background:linear-gradient(180deg, rgba(196,148,96,.30), rgba(170,128,86,.18) 50%, rgba(196,148,96,.32)); }}
/* a soft vignette so centered text always sits on enough contrast */
.veil {{ position:absolute; inset:0; z-index:2;
  background:radial-gradient(120% 80% at 50% 50%, rgba(8,6,4,.10) 0%, rgba(8,6,4,.55) 100%); }}
.copy {{ position:absolute; inset:0; z-index:3; display:flex; align-items:center; justify-content:center;
  text-align:center; padding:0 130px; }}
.copy p {{ font-family:var(--serif); font-weight:500; font-size:78px; line-height:1.66; margin:0;
  color:#fdfbf6; letter-spacing:.03em; text-shadow:0 3px 22px rgba(0,0,0,.6); }}
.copy .nw {{ white-space:nowrap; }}
.grain {{ position:absolute; inset:0; z-index:4; pointer-events:none;
  background-image:url("{GRAIN_URI}"); background-size:140px 140px; mix-blend-mode:overlay; opacity:.13; }}
.mark {{ position:absolute; z-index:5; font-family:var(--serif); color:rgba(243,237,226,.9);
  font-size:25px; letter-spacing:.18em; text-shadow:0 1px 8px rgba(0,0,0,.55); }}
.mark.eyebrow {{ top:54px; left:64px; }}
.mark.page {{ bottom:50px; right:64px; }}
</style>
</head>
<body>
<main class="frame">
  <div class="photo" style="{photo}"></div>
  <div class="grade"></div>
  <div class="veil"></div>
  <div class="copy"><p>{text}</p></div>
  <div class="grain"></div>
  <div class="mark eyebrow">{overline}</div>
  <div class="mark page">{idx:02d} / {total:02d}</div>
</main>
</body>
</html>
"""


def html_card(card: Card, idx: int, total: int, style: str = "editorial",
              meta: dict | None = None) -> str:
    if style == "photo-triptych":
        if card.kind == "cover":
            return html_cover_triptych(card, idx, total, meta or {})
        # body cards on this style are single-photo film frames; cover is always card 1,
        # so the Nth body card maps to body_images[idx-2].
        return html_body_photo(card, idx, total, meta or {}, body_index=idx - 2)
    is_cover = card.kind == "cover"
    paras = "\n".join(f"<p>{_format_paragraph(p)}</p>" for p in card.body)
    # A large faded page number anchors the composition and fills the lower field so a
    # shorter trailing card still reads as designed, not empty. Skipped on the cover.
    watermark = "" if is_cover else f'<div class="seq">{idx:02d}</div>'
    cover_class = " cover" if is_cover else ""
    title_size = 84 if is_cover else 50
    body_size = 38 if is_cover else 36
    pill_label = "阅读路线" if is_cover else "技术长图文"
    toc_html = ""
    if is_cover and card.outline:
        items = "\n".join(f"<li>{html.escape(t)}</li>" for t in card.outline)
        toc_html = f'<div class="toc-label">这篇讲什么</div>\n<ol class="toc">{items}</ol>'
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width={CARD_W}, initial-scale=1" />
<style>
:root {{
  --bg-a: #f2ece2;
  --bg-b: #e7dfd2;
  --ink: #211d18;
  --sub: #6c6358;
  --accent: #c75d36;
  --line: #cdc4b5;
  --serif: "Songti SC", "Noto Serif CJK SC", "Source Han Serif SC", "STSong", serif;
  --sans: -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  width: {CARD_W}px;
  height: {CARD_H}px;
  background: var(--bg-a);
  font-family: var(--sans);
  color: var(--ink);
}}
.card {{
  position: relative;
  width: {CARD_W}px;
  height: {CARD_H}px;
  padding: 88px 84px 76px;
  overflow: hidden;
  background:
    radial-gradient(circle at 90% 6%, rgba(199,93,54,.10), transparent 30%),
    linear-gradient(158deg, var(--bg-a) 0%, var(--bg-b) 100%);
  display: flex;
  flex-direction: column;
}}
.card.cover {{ padding: 96px 88px 80px; }}
.ring {{
  position: absolute; top: -120px; right: -120px;
  width: 360px; height: 360px; border-radius: 50%;
  border: 2px solid rgba(199,93,54,.18);
}}
.ring::before {{
  content: ""; position: absolute; inset: 46px;
  border-radius: 50%; border: 1px dashed rgba(33,29,24,.16);
}}
.seq {{
  position: absolute; right: 40px; bottom: 8px;
  font-family: var(--serif); font-size: 360px; line-height: 1;
  color: rgba(199,93,54,.07); z-index: 0; pointer-events: none;
}}
.inner {{ position: relative; z-index: 1; display: flex; flex-direction: column; height: 100%; }}
.eyebrow {{
  font-size: 26px; letter-spacing: .22em; text-transform: uppercase;
  color: var(--accent); font-weight: 700; margin-bottom: 26px;
}}
h1 {{
  font-family: var(--serif);
  font-size: {title_size}px;
  line-height: 1.22;
  font-weight: 700;
  margin: 0 0 30px;
  letter-spacing: .01em;
}}
.rule {{
  width: 96px; height: 5px; border-radius: 3px;
  background: var(--accent); margin: 0 0 40px;
}}
.body {{
  font-size: {body_size}px;
  line-height: 1.66;
  color: #2c2823;
  font-weight: 400;
}}
.cover .body {{ color: var(--sub); }}
.body p {{ margin: 0 0 26px; }}
.body p:last-child {{ margin-bottom: 0; }}
.toc-label {{
  font-size: 26px; letter-spacing: .16em; color: var(--sub);
  font-weight: 700; margin: 46px 0 20px;
}}
.toc {{ margin: 0; padding: 0; list-style: none; counter-reset: toc; }}
.toc li {{
  position: relative; font-size: 38px; line-height: 1.45;
  padding: 18px 0 18px 70px; border-top: 1px solid var(--line); color: var(--ink);
}}
.toc li:last-child {{ border-bottom: 1px solid var(--line); }}
.toc li::before {{
  counter-increment: toc; content: counter(toc, decimal-leading-zero);
  position: absolute; left: 0; top: 18px;
  font-family: var(--serif); color: var(--accent); font-size: 34px; font-weight: 700;
}}
.footer {{
  margin-top: auto; padding-top: 38px;
  display: flex; align-items: center; justify-content: space-between;
  color: var(--sub); font-size: 25px; letter-spacing: .06em;
}}
.pill {{
  border: 1px solid var(--line); border-radius: 999px;
  padding: 11px 22px; background: rgba(255,255,255,.45);
}}
.page {{ font-family: var(--serif); letter-spacing: .12em; }}
</style>
</head>
<body>
<main class="card{cover_class}">
  {'<div class="ring"></div>' if is_cover else ''}
  {watermark}
  <div class="inner">
    <div class="eyebrow">{html.escape(card.kicker)}</div>
    <h1>{html.escape(card.title)}</h1>
    <div class="rule"></div>
    <section class="body">{paras}</section>
    {toc_html}
    <footer class="footer">
      <span class="pill">{pill_label}</span>
      <span class="page">{idx:02d} / {total:02d}</span>
    </footer>
  </div>
</main>
</body>
</html>
"""


# macOS ships Chrome inside an .app bundle that is not on PATH. Return the REAL binary
# path (not a symlink) — Chrome resolves its Frameworks/ relative to argv[0], so a bare
# symlink on PATH crashes; the absolute in-bundle path renders fine headless.
CHROME_CANDIDATES = (
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
)


def find_chrome() -> str | None:
    for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "chrome"):
        path = shutil.which(name)
        if path:
            return path
    for cand in CHROME_CANDIDATES:
        if Path(cand).exists():
            return cand
    return None


def render_png(html_path: Path, png_path: Path, chrome: str, timeout: int) -> None:
    url = html_path.resolve().as_uri()
    with tempfile.TemporaryDirectory(prefix="xhs-chrome-", ignore_cleanup_errors=True) as profile:
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            f"--user-data-dir={profile}",
            f"--window-size={CARD_W},{CARD_H}",
            f"--screenshot={png_path}",
            url,
        ]
        subprocess.run(
            cmd,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )


def caption_text(
    title: str,
    sections: list[Section],
    citations: set[str],
    tags: list[str],
    override: str | None = None,
) -> str:
    # `override` is the agent-written shortened caption (a hook teaser, not the full
    # article). Without it, derive a plain route caption from the sections.
    if override and override.strip():
        prose = override.strip()
    else:
        bullets = [f"▪️ {s.title}" for s in sections[:5]]
        prose = "\n".join(
            [
                title,
                "",
                "这篇做成长图，适合先收藏再慢慢看。",
                "",
                *bullets,
                "",
                f"来源标记：{', '.join(sorted(citations)) if citations else '见图中标注'}",
            ]
        )
    tag_block = "话题用 # 选择器逐个选，别直接粘：\n" + " ".join(tags)
    return prose.strip() + "\n\n" + tag_block + "\n"


# Numbers in the caption must already appear in the verified body — a shortened
# teaser must not invent a fact (the project's no-claim-without-a-source rule). This
# is the machine-checkable hook over the otherwise-editorial caption.
CAPTION_NUM_RE = re.compile(r"\d+(?:\.\d+)?%?")
CN_DIGIT = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
            "5": "五", "6": "六", "7": "七", "8": "八", "9": "九", "10": "十"}


def caption_unverified_numbers(caption: str, body: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for tok in CAPTION_NUM_RE.findall(caption):
        if tok in seen:
            continue
        if tok in body:
            continue
        cn = CN_DIGIT.get(tok)
        if cn and cn in body:
            continue
        seen.add(tok)
        out.append(tok)
    return out


def write_manifest(
    out_dir: Path,
    title: str,
    cards: list[Card],
    rendered: list[str],
    citations: set[str],
    unverified_numbers: list[str],
    persisted_html: list[str] | None = None,
) -> None:
    persisted_html = persisted_html or []
    manifest = {
        "platform": "xiaohongshu",
        "format": "long_image_post",
        "default": True,
        "title": title,
        "cover_title": cards[0].title if cards else title,
        "card_count": len(cards),
        "rendered_count": len(rendered),
        "image_size": {"width": CARD_W, "height": CARD_H},
        "max_body_chars": max((card_body_width(c) for c in cards), default=0),
        "caption_unverified_numbers": unverified_numbers,
        "cards": [
            {
                "index": i,
                "kind": card.kind,
                "title": card.title,
                "html": f"card_{i:02d}.html" if f"card_{i:02d}.html" in persisted_html else None,
                "png": f"card_{i:02d}.png" if f"card_{i:02d}.png" in rendered else None,
            }
            for i, card in enumerate(cards, start=1)
        ],
        "citation_ids": sorted(citations),
        "caption": "post_xiaohongshu.txt",
        "publish_status": "ready_for_manual_review",
    }
    (out_dir / "content_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def generate_package(
    input_path: Path,
    out_dir: Path,
    render: bool,
    tags: list[str],
    render_timeout: int,
    meta: dict | None = None,
    style: str | None = None,
) -> dict:
    meta = meta or {}
    # Precedence: explicit --style > a "style" field in the meta sidecar > editorial default.
    style = style or meta.get("style") or "editorial"
    text = input_path.read_text(encoding="utf-8")
    title, sections, refs, citations, parsed_tags = parse_markdown(text)
    # Precedence: explicit --tags > hashtags authored in the draft > DEFAULT_TAGS. Either
    # way the hashtags live in the caption only, never on a card.
    tags = tags or parsed_tags or DEFAULT_TAGS
    cards = build_cards(
        title, sections, refs, citations,
        cover_title=meta.get("cover_title"),
        cover_subtitle=meta.get("cover_subtitle"),
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[str] = []
    persisted_html: list[str] = []
    total = len(cards)
    # The PNGs are the deliverable. When rendering, the HTML is a transient render input
    # (written to a temp file, screenshotted, discarded) so the post folder holds only
    # images. HTML is persisted to out_dir ONLY when we cannot render (--no-render / no
    # Chrome) — it is then the sole reviewable artifact (and what CI checks).
    chrome = find_chrome() if render else None
    if render and not chrome:
        print("WARN: Chrome not found; writing HTML cards only", file=sys.stderr)
        render = False

    def persist_html(i: int, markup: str) -> None:
        path = out_dir / f"card_{i:02d}.html"
        path.write_text(markup, encoding="utf-8")
        persisted_html.append(path.name)

    for i, card in enumerate(cards, start=1):
        markup = html_card(card, i, total, style=style, meta=meta)
        png_path = out_dir / f"card_{i:02d}.png"
        if not render:
            persist_html(i, markup)
            continue
        with tempfile.NamedTemporaryFile(
            "w", suffix=".html", delete=False, encoding="utf-8", dir=out_dir
        ) as tf:
            tf.write(markup)
            tmp_html = Path(tf.name)
        try:
            render_png(tmp_html, png_path, chrome, render_timeout)
            rendered.append(png_path.name)
        except subprocess.TimeoutExpired:
            if png_path.exists() and png_path.stat().st_size > 0:
                print(f"WARN: render timed out after writing {png_path.name}; accepting PNG",
                      file=sys.stderr)
                rendered.append(png_path.name)
            else:
                print(f"WARN: render timed out for card {i:02d}; falling back to HTML",
                      file=sys.stderr)
                render = False
                persist_html(i, markup)
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or str(exc)).strip().splitlines()[-1:]
            suffix = f" ({detail[0]})" if detail else ""
            print(f"WARN: render failed for card {i:02d}: {exc}{suffix}; falling back to HTML",
                  file=sys.stderr)
            render = False
            persist_html(i, markup)
        finally:
            tmp_html.unlink(missing_ok=True)

    caption = caption_text(title, sections, citations, tags, override=meta.get("caption"))
    (out_dir / "post_xiaohongshu.txt").write_text(caption, encoding="utf-8")
    unverified = caption_unverified_numbers(caption, text)
    write_manifest(out_dir, title, cards, rendered, citations, unverified, persisted_html)
    return {
        "title": title,
        "cover_title": cards[0].title if cards else title,
        "cards": len(cards),
        "rendered": len(rendered),
        "caption_unverified_numbers": unverified,
        "out_dir": str(out_dir),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the default Xiaohongshu long-image post package.")
    ap.add_argument("input", help="verified final.md or section draft markdown")
    ap.add_argument("--out-dir", required=True, help="directory for card HTML/PNG + caption")
    ap.add_argument("--no-render", action="store_true", help="write HTML only; do not call Chrome")
    ap.add_argument("--render-timeout", type=int, default=20, help="seconds to wait per Chrome screenshot")
    ap.add_argument("--tags", help="comma-separated suggested Xiaohongshu topics")
    ap.add_argument("--meta", help="JSON sidecar with cover_title / cover_subtitle / caption / triptych")
    ap.add_argument("--style", choices=["editorial", "photo-triptych"],
                    help="card visual style (default: editorial; meta.style is a fallback)")
    ap.add_argument("--check-caption", action="store_true",
                    help="exit nonzero if the caption contains a number absent from the verified body")
    args = ap.parse_args(argv)

    # None here lets generate_package fall back to draft-authored hashtags, then DEFAULT_TAGS.
    tags = [x.strip() for x in args.tags.split(",")] if args.tags else None
    if tags is not None:
        tags = [x for x in tags if x]
    meta = json.loads(Path(args.meta).read_text(encoding="utf-8")) if args.meta else {}
    result = generate_package(
        Path(args.input), Path(args.out_dir), not args.no_render, tags, args.render_timeout,
        meta=meta, style=args.style,
    )
    print("xhs_image_post:", json.dumps(result, ensure_ascii=False))
    unverified = result["caption_unverified_numbers"]
    if unverified:
        print(f"WARN: caption has numbers not in the verified body: {unverified}", file=sys.stderr)
        if args.check_caption:
            print("FAIL: --check-caption — a shortened caption must not invent a fact", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

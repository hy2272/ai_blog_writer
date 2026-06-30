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
MAX_BODY_CHARS = 430
DEFAULT_TAGS = ["#科技资讯早知道", "#人工智能", "#AI工具", "#效率神器", "#vibecoding"]
CITE_RE = re.compile(r"\[(S\d+(?:\s*,\s*S\d+)*)\]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
REF_HEADING_RE = re.compile(r"^(references|参考|参考来源|sources|source list)$", re.I)


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


def parse_markdown(text: str) -> tuple[str, list[Section], list[str], set[str]]:
    title = "小红书技术长图文"
    sections: list[Section] = []
    refs: list[str] = []
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
    return title, sections, refs, citations


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


def build_cards(title: str, sections: list[Section], refs: list[str], citations: set[str]) -> list[Card]:
    cards: list[Card] = [
        Card("cover", title[:28], ["技术帖长图版", "先看结论，再看依据"], "AI / 技术更新"),
    ]

    outline = [f"{i}. {s.title}" for i, s in enumerate(sections, start=1)]
    if outline:
        cards.append(Card("outline", "这篇讲什么", outline[:8], "阅读路线"))

    for i, section in enumerate(sections, start=1):
        chunks = chunk_paragraphs(section.paragraphs)
        for j, chunk in enumerate(chunks or [["这一节没有正文。"]], start=1):
            suffix = f" · {j}" if len(chunks) > 1 else ""
            cards.append(Card("body", section.title, chunk, f"{i:02d}{suffix}"))

    if citations:
        body = [f"文中引用：{', '.join(sorted(citations))}"]
        if refs:
            body.extend(refs[:5])
        body.append("发布前保留来源清单；平台正文可改成“资料来自官方公告/论文/新闻源”。")
        ref_chunks = chunk_paragraphs(body)
        for j, chunk in enumerate(ref_chunks, start=1):
            suffix = f" · {j}" if len(ref_chunks) > 1 else ""
            cards.append(Card("refs", "参考来源", chunk, f"Provenance{suffix}"))

    return cards


def card_body_width(card: Card) -> int:
    return sum(display_len(p) for p in card.body)


def html_card(card: Card, idx: int, total: int) -> str:
    paras = "\n".join(f"<p>{html.escape(p)}</p>" for p in card.body)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width={CARD_W}, initial-scale=1" />
<style>
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  width: {CARD_W}px;
  height: {CARD_H}px;
  background: #f4efe7;
  font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", sans-serif;
  color: #1f2933;
}}
.card {{
  width: {CARD_W}px;
  height: {CARD_H}px;
  padding: 72px 76px 58px;
  background:
    radial-gradient(circle at 92% 8%, rgba(255, 122, 89, .28), transparent 24%),
    linear-gradient(135deg, #fffaf1 0%, #f7efe2 56%, #edf4ff 100%);
  display: flex;
  flex-direction: column;
}}
.kicker {{
  font-size: 34px;
  letter-spacing: .04em;
  color: #ef6c42;
  font-weight: 800;
  margin-bottom: 28px;
}}
h1 {{
  font-size: {72 if card.kind == "cover" else 56}px;
  line-height: 1.12;
  margin: 0 0 34px;
  letter-spacing: -0.02em;
}}
.body {{
  font-size: {39 if card.kind == "cover" else 34}px;
  line-height: 1.55;
  font-weight: 520;
}}
.body p {{
  margin: 0 0 24px;
}}
.body p::first-letter {{
  font-weight: 800;
}}
.footer {{
  margin-top: auto;
  padding-top: 36px;
  display: flex;
  justify-content: space-between;
  color: #6b7280;
  font-size: 26px;
}}
.pill {{
  border: 2px solid rgba(31,41,51,.16);
  border-radius: 999px;
  padding: 10px 18px;
  background: rgba(255,255,255,.58);
}}
</style>
</head>
<body>
<main class="card">
  <div class="kicker">{html.escape(card.kicker)}</div>
  <h1>{html.escape(card.title)}</h1>
  <section class="body">{paras}</section>
  <footer class="footer">
    <span class="pill">技术长图文</span>
    <span>{idx:02d}/{total:02d}</span>
  </footer>
</main>
</body>
</html>
"""


def find_chrome() -> str | None:
    for name in ("google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
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


def caption_text(title: str, sections: list[Section], citations: set[str], tags: list[str]) -> str:
    bullets = [f"▪️ {s.title}" for s in sections[:5]]
    body = [
        title,
        "",
        "这篇做成长图，适合先收藏再慢慢看。",
        "",
        *bullets,
        "",
        f"来源标记：{', '.join(sorted(citations)) if citations else '见图中标注'}",
        "",
        "话题用 # 选择器逐个选，别直接粘：",
        " ".join(tags),
    ]
    return "\n".join(body).strip() + "\n"


def write_manifest(out_dir: Path, title: str, cards: list[Card], rendered: list[str], citations: set[str]) -> None:
    manifest = {
        "platform": "xiaohongshu",
        "format": "long_image_post",
        "default": True,
        "title": title,
        "card_count": len(cards),
        "rendered_count": len(rendered),
        "image_size": {"width": CARD_W, "height": CARD_H},
        "max_body_chars": max((card_body_width(c) for c in cards), default=0),
        "cards": [
            {
                "index": i,
                "kind": card.kind,
                "title": card.title,
                "html": f"card_{i:02d}.html",
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


def generate_package(input_path: Path, out_dir: Path, render: bool, tags: list[str], render_timeout: int) -> dict:
    text = input_path.read_text(encoding="utf-8")
    title, sections, refs, citations = parse_markdown(text)
    cards = build_cards(title, sections, refs, citations)

    out_dir.mkdir(parents=True, exist_ok=True)
    rendered: list[str] = []
    total = len(cards)
    for i, card in enumerate(cards, start=1):
        html_path = out_dir / f"card_{i:02d}.html"
        png_path = out_dir / f"card_{i:02d}.png"
        html_path.write_text(html_card(card, i, total), encoding="utf-8")
        if render:
            chrome = find_chrome()
            if not chrome:
                print("WARN: Chrome not found; wrote HTML cards only", file=sys.stderr)
                render = False
            else:
                try:
                    render_png(html_path, png_path, chrome, render_timeout)
                except subprocess.TimeoutExpired:
                    if png_path.exists() and png_path.stat().st_size > 0:
                        print(f"WARN: Chrome render timed out after writing {png_path.name}; accepting PNG",
                              file=sys.stderr)
                        rendered.append(png_path.name)
                    else:
                        print(f"WARN: Chrome render timed out for {html_path.name}; kept HTML only",
                              file=sys.stderr)
                        render = False
                except subprocess.CalledProcessError as exc:
                    detail = (exc.stderr or str(exc)).strip().splitlines()[-1:]
                    suffix = f" ({detail[0]})" if detail else ""
                    print(f"WARN: Chrome render failed for {html_path.name}: {exc}{suffix}",
                          file=sys.stderr)
                    render = False
                else:
                    rendered.append(png_path.name)

    (out_dir / "post_xiaohongshu.txt").write_text(
        caption_text(title, sections, citations, tags),
        encoding="utf-8",
    )
    write_manifest(out_dir, title, cards, rendered, citations)
    return {
        "title": title,
        "cards": len(cards),
        "rendered": len(rendered),
        "out_dir": str(out_dir),
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Build the default Xiaohongshu long-image post package.")
    ap.add_argument("input", help="verified final.md or section draft markdown")
    ap.add_argument("--out-dir", required=True, help="directory for card HTML/PNG + caption")
    ap.add_argument("--no-render", action="store_true", help="write HTML only; do not call Chrome")
    ap.add_argument("--render-timeout", type=int, default=20, help="seconds to wait per Chrome screenshot")
    ap.add_argument("--tags", help="comma-separated suggested Xiaohongshu topics")
    args = ap.parse_args(argv)

    tags = [x.strip() for x in args.tags.split(",")] if args.tags else DEFAULT_TAGS
    tags = [x for x in tags if x]
    result = generate_package(Path(args.input), Path(args.out_dir), not args.no_render, tags, args.render_timeout)
    print("xhs_image_post:", json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

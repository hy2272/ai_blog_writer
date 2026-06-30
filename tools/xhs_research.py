#!/usr/bin/env python3
"""小红书 paradigm research: scrape RedNote search results and distil a calibration
summary for common/behavior_notes/xiaohongshu-baokuan-paradigm.md.

This is a one-off CALIBRATION aid, not part of the publish pipeline — it grounds the
paradigm note (cover/title/hashtag conventions) in real engagement data instead of
hand-waving. ToS-gray + per-result cost, so run it deliberately, never in CI.

Usage:
  python3 tools/xhs_research.py --keyword "AI编程" --max 40 \
    --out scratch/xhs_research_aibiancheng.json
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.apify_client import ApifyError, run_actor  # noqa: E402


DEFAULT_ACTOR = "nexgendata~rednote-scraper"
NUM_RE = re.compile(r"\d")


def display_len(text: str) -> int:
    return sum(2 if "一" <= ch <= "鿿" else 1 for ch in text)


def normalize(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for it in items:
        out.append(
            {
                "title": (it.get("title") or "").strip(),
                "hashtags": it.get("hashtags") or [],
                "likes": it.get("likes_count") or 0,
                "collected": it.get("collected_count") or 0,
                "comments": it.get("comments_count") or 0,
                "engagement": it.get("engagement_total") or 0,
                "posted_at": it.get("posted_at") or "",
                "url": it.get("url") or "",
                "cover": (it.get("image_urls") or [""])[0],
            }
        )
    out.sort(key=lambda x: x["engagement"], reverse=True)
    return out


def calibrate(rows: list[dict]) -> dict:
    titled = [r for r in rows if r["title"]]
    has_num = [r["engagement"] for r in titled if NUM_RE.search(r["title"])]
    no_num = [r["engagement"] for r in titled if not NUM_RE.search(r["title"])]
    tags = Counter(t for r in rows for t in r["hashtags"])
    lens = [display_len(r["title"]) for r in titled]
    return {
        "n": len(rows),
        "top_titles": [{"title": r["title"], "engagement": r["engagement"]} for r in rows[:10]],
        "top_hashtags": tags.most_common(15),
        "title_display_len": {
            "median": statistics.median(lens) if lens else 0,
            "min": min(lens) if lens else 0,
            "max": max(lens) if lens else 0,
        },
        # Tests the note's 「量化封面」 claim: do number-in-title posts engage more?
        "number_in_title": {
            "with_number_median_engagement": statistics.median(has_num) if has_num else 0,
            "no_number_median_engagement": statistics.median(no_num) if no_num else 0,
            "with_number_count": len(has_num),
            "no_number_count": len(no_num),
        },
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scrape RedNote search results and distil a calibration summary.")
    ap.add_argument("--keyword", required=True, help="search keyword, e.g. 'AI编程'")
    ap.add_argument("--max", type=int, default=40, help="requested max items (actor may overshoot)")
    ap.add_argument("--actor", default=DEFAULT_ACTOR, help="override the Apify actor id")
    ap.add_argument("--out", help="write the normalized items + calibration JSON here")
    args = ap.parse_args(argv)

    try:
        items = run_actor(args.actor, {"keyword": args.keyword, "maxItems": args.max}, timeout=240)
    except ApifyError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    rows = normalize(items)
    cal = calibrate(rows)
    result = {
        "keyword": args.keyword,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor": args.actor,
        "calibration": cal,
        "items": rows,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {len(rows)} items + calibration -> {args.out}")

    nit = cal["number_in_title"]
    print(f"\n=== calibration for '{args.keyword}' (n={cal['n']}) ===")
    print(f"title display-len median: {cal['title_display_len']['median']} "
          f"(range {cal['title_display_len']['min']}–{cal['title_display_len']['max']})")
    print(f"量化封面 check — median engagement: with-number {nit['with_number_median_engagement']} "
          f"({nit['with_number_count']} posts) vs no-number {nit['no_number_median_engagement']} "
          f"({nit['no_number_count']} posts)")
    print("top hashtags:", ", ".join(f"{t}×{c}" for t, c in cal["top_hashtags"][:8]) or "(none)")
    print("top titles by engagement:")
    for r in cal["top_titles"][:6]:
        print(f"  {r['engagement']:>7}  {r['title'][:42]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

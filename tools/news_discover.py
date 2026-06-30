#!/usr/bin/env python3
"""S0 topic discovery: pull fresh, dated AI news headlines via an Apify Google News actor.

This is a DISCOVERY aid, not a citation source. It answers "what AI topic is hot right
now, and how fresh is it" with each item carrying a publish date + publisher — exactly
the freshness signal S0 needs to pick an angle. The `url` is a Google News redirect, so
the research stage (S1) still fetches the real primary source before anything is cited.

Usage:
  python3 tools/news_discover.py --query "AI agents" --max 20 --timeframe 7d \
    --out articles/article_<slug>/news_discovery.json
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.apify_client import ApifyError, run_actor  # noqa: E402


DEFAULT_ACTOR = "practicaltools~apify-google-news-scraper"


def normalize(items: list[dict]) -> list[dict]:
    out: list[dict] = []
    for it in items:
        out.append(
            {
                "title": (it.get("title") or "").strip(),
                "date": it.get("datetime") or "",      # ISO 8601 — the freshness anchor
                "relative_time": it.get("time") or "",
                "source": it.get("source") or "",       # publisher name
                "url": it.get("link") or "",            # Google News redirect (resolve in S1)
                "image": it.get("image") or "",
                "type": it.get("articleType") or "",
            }
        )
    # Newest first when dates are present; undated items sink to the bottom.
    out.sort(key=lambda x: x["date"] or "", reverse=True)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Discover fresh, dated AI news headlines (S0 aid).")
    ap.add_argument("--query", required=True, help="search term, e.g. 'AI agents'")
    ap.add_argument("--max", type=int, default=20, help="max articles to pull")
    ap.add_argument("--timeframe", default="7d",
                    help="recency window the actor accepts, e.g. 1h / 1d / 7d / 1m / 1y")
    ap.add_argument("--language", default="en")
    ap.add_argument("--country", default="US")
    ap.add_argument("--actor", default=DEFAULT_ACTOR, help="override the Apify actor id")
    ap.add_argument("--out", help="write the normalized JSON here")
    args = ap.parse_args(argv)

    run_input = {
        "searchTerm": args.query,
        "maxArticles": args.max,
        "timeframe": args.timeframe,
        "language": args.language,
        "country": args.country,
    }
    try:
        items = run_actor(args.actor, run_input, timeout=240)
    except ApifyError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    rows = normalize(items)
    result = {
        "query": args.query,
        "timeframe": args.timeframe,
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actor": args.actor,
        "count": len(rows),
        "items": rows,
    }
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                                  encoding="utf-8")
        print(f"wrote {len(rows)} items -> {args.out}")

    # Human-readable scan: date · source · title
    for r in rows:
        day = (r["date"] or "")[:10] or "??????????"
        print(f"{day}  {r['source'][:18]:<18}  {r['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

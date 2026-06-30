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
AUTHORITY_PATH = Path(__file__).resolve().parents[1] / "common" / "source_authority.json"


# Generic subdomain labels that are NOT a brand (blog.google, research.google, …) and
# short tokens (x.ai → "x", ft.com → "ft") over-match inside unrelated names, so skip them.
_GENERIC_BRAND = {"blog", "research", "news", "tech", "the", "www"}


def classify_source_name(name: str, authority: dict) -> str:
    """Best-effort tier from a publisher NAME (Google News gives names, not domains), by
    matching the brand token of each authority domain. Approximate — multi-word outlets
    (e.g. 'The New York Times' vs nytimes.com) can miss; --min-tier is an opt-in convenience."""
    n = (name or "").lower().replace("the ", "").replace(" ", "")
    if not n:
        return "unknown"
    for tier, key in (("tier1", "tier1_primary"), ("tier2", "tier2_reputable")):
        for d in authority.get(key, []):
            brand = str(d).split(".")[0].lower()
            if len(brand) >= 4 and brand not in _GENERIC_BRAND and brand in n:
                return tier
    return "unknown"


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
    ap.add_argument("--min-tier", choices=["tier1", "tier2"],
                    help="keep only items whose publisher maps to this tier or better "
                         "(name-based, approximate); drops are reported, never silent")
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
    if args.min_tier:
        authority = json.loads(AUTHORITY_PATH.read_text(encoding="utf-8"))
        allowed = {"tier1"} if args.min_tier == "tier1" else {"tier1", "tier2"}
        kept = [r for r in rows if classify_source_name(r["source"], authority) in allowed]
        dropped = len(rows) - len(kept)
        print(f"--min-tier {args.min_tier}: kept {len(kept)} / {len(rows)} "
              f"(dropped {dropped} unranked-by-name)")
        rows = kept
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

#!/usr/bin/env python3
"""new_article.py — scaffold a per-article workspace from _TEMPLATE and validate the layout.

Replaces a copy-by-hand step that drifted from the template (e.g. a missing `sections/`),
so a new article never starts half-built. It copies `articles/_TEMPLATE/`, substitutes the
`<slug>` placeholder, and then asserts the required layout exists — which doubles as a CI
guard that the template itself stays complete.

  python3 tools/new_article.py claude-sonnet-5-launch
  python3 tools/new_article.py smoke --articles-dir /tmp/scaffold   # for tests
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path


REQUIRED = [
    "STATE.md",
    "DECISIONS.md",
    "source_pack.json",
    "outline.json",
    "contracts",
    "sections",
    "stage_results",
]
ROOT = Path(__file__).resolve().parents[1]


def substitute_slug(target: Path, slug: str) -> None:
    for name in ("STATE.md", "outline.json"):
        p = target / name
        if p.exists():
            p.write_text(p.read_text(encoding="utf-8").replace("<slug>", slug), encoding="utf-8")


def validate_layout(target: Path) -> list[str]:
    missing = []
    for rel in REQUIRED:
        if not (target / rel).exists():
            missing.append(rel)
    return missing


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Scaffold and validate a per-article workspace.")
    ap.add_argument("slug", help="kebab-case slug, e.g. claude-sonnet-5-launch")
    ap.add_argument("--articles-dir", default=str(ROOT / "articles"),
                    help="where article_<slug>/ is created (default: repo articles/)")
    ap.add_argument("--template", default=str(ROOT / "articles" / "_TEMPLATE"),
                    help="template dir to copy")
    args = ap.parse_args(argv)

    template = Path(args.template)
    if not template.is_dir():
        print(f"ERROR: template not found: {template}", file=sys.stderr)
        return 1

    target = Path(args.articles_dir) / f"article_{args.slug}"
    if target.exists():
        print(f"ERROR: workspace already exists: {target}", file=sys.stderr)
        return 1

    shutil.copytree(template, target)
    substitute_slug(target, args.slug)

    missing = validate_layout(target)
    if missing:
        print(f"ERROR: scaffold incomplete — template is missing: {missing}", file=sys.stderr)
        return 1

    print(f"scaffolded {target}")
    print(f"  layout OK: {', '.join(REQUIRED)}")
    print("  next: run /write-article to begin (S0 topic + decompose)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

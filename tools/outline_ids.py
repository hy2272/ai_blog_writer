#!/usr/bin/env python3
"""outline_ids.py — validate outline.json and emit its stable item ids.

The grounding 2->3 gate checks each draft claim against `outline_ids`, so those ids must
be stable and well-formed — a loose markdown table gave no such guarantee. This tool is
the schema contract for outline.json: it lints the structure and prints the comma-joined
item ids, so `--allowed-outline-ids` is generated, never hand-typed:

  python3 tools/grounding_gate.py <verdict.json> \\
    --allowed-outline-ids "$(python3 tools/outline_ids.py outline.json)" \\
    --allowed-source-ids S1,S2

outline.json schema:
  {
    "slug": "<slug>",
    "through_line": "<one-sentence spine>",
    "items": [
      {"id": "1", "section": 1, "point": "<outline point>", "source_ids": ["S1","S2"]}
    ]
  }

Exit 0 = valid (ids printed to stdout; an empty items list is valid-but-empty). Exit 1 =
malformed (errors to stderr, nothing on stdout). Lint rules: items is a list; each item
has a non-empty id, an int section, a non-empty point, and a source_ids list of `S<n>`
ids; item ids are unique.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


SOURCE_ID_RE = re.compile(r"^S\d+$")


def validate(outline: dict) -> tuple[list[str], list[str]]:
    """Return (ordered ids, errors)."""
    errors: list[str] = []
    items = outline.get("items")
    if not isinstance(items, list):
        return [], ["`items` must be a list"]

    ids: list[str] = []
    seen: set[str] = set()
    for i, it in enumerate(items):
        where = f"items[{i}]"
        if not isinstance(it, dict):
            errors.append(f"{where} must be an object")
            continue
        rid = it.get("id")
        rid = str(rid).strip() if rid is not None else ""
        if not rid:
            errors.append(f"{where} has an empty/missing id")
        elif rid in seen:
            errors.append(f"{where} duplicate id {rid!r}")
        else:
            seen.add(rid)
            ids.append(rid)
        if not isinstance(it.get("section"), int):
            errors.append(f"{where} (id {rid!r}) section must be an integer")
        if not str(it.get("point", "")).strip():
            errors.append(f"{where} (id {rid!r}) point is empty")
        src = it.get("source_ids")
        if not isinstance(src, list):
            errors.append(f"{where} (id {rid!r}) source_ids must be a list")
        else:
            for s in src:
                if not (isinstance(s, str) and SOURCE_ID_RE.match(s)):
                    errors.append(f"{where} (id {rid!r}) bad source id {s!r} (want S<n>)")
    return ids, errors


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Validate outline.json and emit its item ids.")
    ap.add_argument("outline", help="path to outline.json")
    ap.add_argument("--check", action="store_true",
                    help="validate only; print nothing on stdout (use the exit code)")
    args = ap.parse_args(argv)

    try:
        outline = json.loads(Path(args.outline).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"outline_ids: cannot read {args.outline}: {exc}", file=sys.stderr)
        return 1

    ids, errors = validate(outline)
    if errors:
        for e in errors:
            print(f"  [FAIL] {e}", file=sys.stderr)
        print(f"outline_ids: {len(errors)} schema error(s) in {args.outline}", file=sys.stderr)
        return 1
    if not args.check:
        print(",".join(ids))
    return 0


if __name__ == "__main__":
    sys.exit(main())

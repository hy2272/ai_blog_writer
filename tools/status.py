#!/usr/bin/env python3
"""status.py — aggregate per-stage result JSONs into a truthful section × stage matrix.

Each section stage writes its own `sec<k>_<stage>.json` (writer / factcheck / grounding /
audit) instead of one shared `sec<k>_result.json` that was last-writer-wins — so resume
and `/status` can report which stage is actually green/red, not just whichever wrote last.
This tool reads them all and prints the matrix plus the article-level stages. Read-only;
always exits 0 (reporting, not a gate).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


STAGES = ["writer", "factcheck", "grounding", "audit"]
SEC_RE = re.compile(r"^sec(\d+)_(writer|factcheck|grounding|audit)\.json$")
PASS_VERDICT = "SUPPORTED"


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def factcheck_status(data: dict) -> str:
    """Prefer an explicit status; else derive from the verdict's claims (the #13 schema)."""
    if data.get("status"):
        return data["status"]
    claims = data.get("claims")
    if claims is None:
        return "?"
    if not claims:
        return "fail"  # fails closed, mirroring factcheck_gate
    return "pass" if all(c.get("verdict") == PASS_VERDICT for c in claims) else "fail"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Aggregate per-stage section result JSONs.")
    ap.add_argument("article_dir", help="articles/article_<slug> directory")
    args = ap.parse_args(argv)
    root = Path(args.article_dir)

    sections: dict[int, dict[str, str]] = {}
    sec_dir = root / "sections"
    if sec_dir.is_dir():
        for f in sorted(sec_dir.glob("sec*_*.json")):
            m = SEC_RE.match(f.name)
            if not m:
                continue
            k, stage = int(m.group(1)), m.group(2)
            data = load(f) or {}
            status = factcheck_status(data) if stage == "factcheck" else (data.get("status") or "?")
            sections.setdefault(k, {})[stage] = status

    print(f"status: {root}")
    print("\nsection stages:")
    if sections:
        print("  sec  " + "".join(f"{s:<11}" for s in STAGES))
        for k in sorted(sections):
            row = sections[k]
            print(f"  {k:<4} " + "".join(f"{row.get(s, '—'):<11}" for s in STAGES))
    else:
        print("  (no section stage results yet)")

    sr = root / "stage_results"
    article_files = sorted(sr.glob("*.json")) if sr.is_dir() else []
    if article_files:
        print("\narticle stages:")
        for f in article_files:
            data = load(f) or {}
            print(f"  {f.stem:<24} {data.get('status', '?')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

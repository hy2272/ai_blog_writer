#!/usr/bin/env python3
"""status.py — aggregate per-stage result JSONs into a truthful section × stage matrix.

Each section stage writes its own `sec<k>_<stage>.json` (writer / factcheck / grounding /
audit) instead of one shared `sec<k>_result.json` that was last-writer-wins — so resume
and `/status` can report which stage is actually green/red, not just whichever wrote last.
This tool reads them all and prints the matrix plus the article-level stages. Read-only;
always exits 0 (reporting, not a gate).

If the article has a `run_journal.jsonl` (see `tools/journal.py`), the matrix gains a
`cost` column (recorded cost, else token estimate, summed per section from the journal's
result events) and a run-total line. No journal → output is unchanged.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import journal as journal_mod  # sibling module in tools/ (script dir is on sys.path)


STAGES = ["writer", "factcheck", "grounding", "audit"]
SEC_RE = re.compile(r"^sec(\d+)_(writer|factcheck|grounding|audit)\.json$")
PASS_VERDICT = "SUPPORTED"


def load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def cost_cell(cost: float, tokens: int) -> str:
    """One matrix cell: recorded dollars beat a token estimate; neither → em dash."""
    if cost > 0:
        return f"${cost:.2f}"
    if tokens >= 1000:
        return f"~{round(tokens / 1000)}k tok"
    if tokens > 0:
        return f"~{tokens} tok"
    return "—"


def journal_rollup(recs: list[dict]):
    """Sum tokens/cost per section (int keys) and per article-level stage (str keys).
    Any event may carry usage; section-tagged events roll into the section row."""
    sec: dict[int, dict] = {}
    art: dict[str, dict] = {}
    total = {"tokens": 0, "cost": 0.0}
    for r in recs:
        tok = journal_mod.tokens_total(r)
        cost = float(r.get("cost_usd") or 0)
        if not tok and not cost:
            continue
        total["tokens"] += tok
        total["cost"] += cost
        section = r.get("section")
        if isinstance(section, int):
            bucket = sec.setdefault(section, {"tokens": 0, "cost": 0.0})
        else:
            bucket = art.setdefault(str(r.get("stage", "?")), {"tokens": 0, "cost": 0.0})
        bucket["tokens"] += tok
        bucket["cost"] += cost
    return sec, art, total


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

    recs, bad = journal_mod.load(root)
    sec_usage, art_usage, total_usage = journal_rollup(recs)
    has_journal = bool(recs)

    print(f"status: {root}")
    print("\nsection stages:")
    if sections:
        header = "  sec  " + "".join(f"{s:<11}" for s in STAGES)
        if has_journal:
            header += "cost"
        print(header)
        for k in sorted(sections):
            row = sections[k]
            line = f"  {k:<4} " + "".join(f"{row.get(s, '—'):<11}" for s in STAGES)
            if has_journal:
                u = sec_usage.get(k, {"tokens": 0, "cost": 0.0})
                line += cost_cell(u["cost"], u["tokens"])
            print(line)
    else:
        print("  (no section stage results yet)")

    sr = root / "stage_results"
    article_files = sorted(sr.glob("*.json")) if sr.is_dir() else []
    if article_files:
        print("\narticle stages:")
        for f in article_files:
            data = load(f) or {}
            line = f"  {f.stem:<24} {data.get('status', '?')}"
            u = art_usage.get(f.stem)
            if u:
                line += f"   {cost_cell(u['cost'], u['tokens'])}"
            print(line)

    if has_journal:
        note = f", {bad} malformed skipped" if bad else ""
        print(f"\njournal: {len(recs)} events{note} · tokens {total_usage['tokens']}"
              f" · recorded cost ${total_usage['cost']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

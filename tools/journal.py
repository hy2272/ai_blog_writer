#!/usr/bin/env python3
"""journal.py — append-only run ledger for one article (`run_journal.jsonl`).

The orchestrator appends one JSON line per orchestration event: agent dispatch, agent
result, machine-gate exit, human-gate decision, stage transition. The journal is the
ground truth for WHAT RAN (dispatch counts / step budget, tokens, cost, human
decisions); the per-stage result JSONs + oracle exit codes stay the ground truth for
WHAT IS GREEN; STATE.md stays the human-readable summary. On resume, reconcile in that
order (see `.claude/orchestrator.md`, "State you own").

Ported pattern: agent-fleet v2's `journal.jsonl` (append-only, never rewritten, resume
reads it instead of trusting memory). This repo's variant journals ORCHESTRATION events
rather than call-input hashes — the per-stage result files already make outputs
resumable; what was missing was the ledger of dispatches, budgets, and cost.

Append (auto-timestamps; creates the file, never rewrites it):
  python3 tools/journal.py append <article_dir> --event dispatch \
      --stage S3-writer --section 2 --agent writer
  python3 tools/journal.py append <article_dir> --event result \
      --stage S3-writer --section 2 --agent writer --status pass \
      --tokens-total 48213 --cost-usd 0.31
  python3 tools/journal.py append <article_dir> --event gate \
      --stage S4-citation-audit --section 2 --gate citation_audit --exit-code 0
  python3 tools/journal.py append <article_dir> --event human_gate \
      --stage S1 --decision approved --note "angle ok, sources fresh"
  python3 tools/journal.py append <article_dir> --event stage --stage S5.9 --status skip

Summarize (read-only, always exit 0, tolerates malformed lines):
  python3 tools/journal.py summary <article_dir>

Stage names use the result-file stems (S1-research, S3-writer, S3-fact-check,
S3-grounding-2to3, S4-citation-audit, S5-humanize, S5-9-findings-triage,
S6-editorial-review, S7-output) so `tools/status.py` can join journal cost onto its
matrix. Record tokens/cost only when the harness surfaces them — never invent numbers.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

JOURNAL_NAME = "run_journal.jsonl"
EVENTS = ("dispatch", "result", "gate", "human_gate", "stage", "note")
RESULT_STATUSES = ("pass", "fail", "blocked")
STAGE_STATUSES = ("start", "done", "skip")
SECTION_BUDGET = 3  # max write→fact-check→grounding→audit iterations (orchestrator.md)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _err(msg: str) -> int:
    print(f"ERROR: {msg}", file=sys.stderr)
    return 2


def append(args) -> int:
    root = Path(args.article_dir)
    if not root.is_dir():
        return _err(f"article dir not found: {root} (typo guard — journal never mkdirs)")

    rec: dict = {"ts": _now(), "event": args.event}
    if args.extra:
        try:
            extra = json.loads(args.extra)
        except json.JSONDecodeError as e:
            return _err(f"--extra is not valid JSON: {e}")
        if not isinstance(extra, dict):
            return _err("--extra must be a JSON object")
        rec.update(extra)  # explicit flags below overwrite colliding extra keys

    # per-event required fields (fail fast, agent-fleet validate_config spirit)
    if args.event != "note" and not args.stage:
        return _err(f"--stage is required for event '{args.event}'")
    if args.event == "result" and args.status not in RESULT_STATUSES:
        return _err(f"--status pass|fail|blocked is required for event 'result'")
    if args.event == "gate" and (args.gate is None or args.exit_code is None):
        return _err("--gate and --exit-code are required for event 'gate'")
    if args.event == "human_gate" and not args.decision:
        return _err("--decision is required for event 'human_gate'")
    if args.event == "stage" and args.status not in STAGE_STATUSES:
        return _err("--status start|done|skip is required for event 'stage'")

    for key, val in (("stage", args.stage), ("section", args.section),
                     ("agent", args.agent), ("model", args.model),
                     ("gate", args.gate), ("exit_code", args.exit_code),
                     ("decision", args.decision), ("status", args.status),
                     ("cost_usd", args.cost_usd), ("note", args.note)):
        if val is not None:
            rec[key] = val
    if args.event == "gate" and "status" not in rec:
        rec["status"] = "pass" if args.exit_code == 0 else "fail"

    tokens = {k: v for k, v in (("total", args.tokens_total),
                                ("input", args.tokens_input),
                                ("output", args.tokens_output)) if v is not None}
    if tokens:
        rec["tokens"] = tokens

    with (root / JOURNAL_NAME).open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"journal += {rec['event']} {rec.get('stage', '')}".rstrip())
    return 0


def load(root: Path) -> tuple[list[dict], int]:
    """Return (records, malformed_count). Malformed lines are skipped, not fatal —
    a corrupt line must not make the whole ledger unreadable on resume."""
    path = root / JOURNAL_NAME
    recs: list[dict] = []
    bad = 0
    if not path.exists():
        return recs, bad
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if isinstance(rec, dict):
            recs.append(rec)
        else:
            bad += 1
    return recs, bad


def tokens_total(rec: dict) -> int:
    t = rec.get("tokens")
    if not isinstance(t, dict):
        return 0
    if t.get("total") is not None:
        return int(t["total"])
    return int(t.get("input") or 0) + int(t.get("output") or 0)


def summary(args) -> int:
    root = Path(args.article_dir)
    recs, bad = load(root)
    if not recs:
        print(f"no {JOURNAL_NAME} in {root}" if bad == 0
              else f"{JOURNAL_NAME}: 0 readable events ({bad} malformed)")
        return 0

    stages: dict[str, dict] = {}
    writer_dispatches: dict[str, int] = {}
    total_tokens = 0
    total_cost = 0.0
    passed = failed = 0
    for r in recs:
        stage = str(r.get("stage", "?"))
        s = stages.setdefault(stage, {"dispatch": 0, "pass": 0, "fail": 0,
                                      "tokens": 0, "cost": 0.0})
        if r.get("event") == "dispatch":
            s["dispatch"] += 1
            if stage == "S3-writer":
                key = f"sec{r.get('section', '?')}"
                writer_dispatches[key] = writer_dispatches.get(key, 0) + 1
        if r.get("event") in ("result", "gate"):
            if r.get("status") == "pass":
                s["pass"] += 1
                passed += 1
            elif r.get("status") in ("fail", "blocked"):
                s["fail"] += 1
                failed += 1
        tok = tokens_total(r)
        cost = float(r.get("cost_usd") or 0)
        s["tokens"] += tok
        s["cost"] += cost
        total_tokens += tok
        total_cost += cost

    print(f"run journal: {root / JOURNAL_NAME} ({len(recs)} events"
          + (f", {bad} malformed skipped" if bad else "") + ")")
    print(f"  {'stage':<26}{'dispatch':>9}{'pass':>6}{'fail':>6}{'tokens':>10}{'cost':>9}")
    for stage in sorted(stages):
        s = stages[stage]
        cost = f"${s['cost']:.2f}" if s["cost"] else "—"
        print(f"  {stage:<26}{s['dispatch']:>9}{s['pass']:>6}{s['fail']:>6}"
              f"{s['tokens']:>10}{cost:>9}")
    if writer_dispatches:
        budget = ", ".join(f"{k} {n}/{SECTION_BUDGET}"
                           for k, n in sorted(writer_dispatches.items()))
        print(f"  writer dispatches vs step budget: {budget}")
    print(f"  totals: {passed} pass / {failed} fail · tokens {total_tokens}"
          f" · recorded cost ${total_cost:.2f}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Append to / summarize an article's run_journal.jsonl.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("append", help="append one event (auto-timestamped)")
    a.add_argument("article_dir")
    a.add_argument("--event", required=True, choices=EVENTS)
    a.add_argument("--stage")
    a.add_argument("--section", type=int)
    a.add_argument("--agent")
    a.add_argument("--model")
    a.add_argument("--gate")
    a.add_argument("--exit-code", type=int, dest="exit_code")
    a.add_argument("--decision")
    a.add_argument("--status", choices=sorted(set(RESULT_STATUSES) | set(STAGE_STATUSES)))
    a.add_argument("--tokens-total", type=int, dest="tokens_total")
    a.add_argument("--tokens-input", type=int, dest="tokens_input")
    a.add_argument("--tokens-output", type=int, dest="tokens_output")
    a.add_argument("--cost-usd", type=float, dest="cost_usd")
    a.add_argument("--note")
    a.add_argument("--extra", help="JSON object of additional fields (explicit flags win)")
    a.set_defaults(func=append)

    s = sub.add_parser("summary", help="read-only rollup (always exit 0)")
    s.add_argument("article_dir")
    s.set_defaults(func=summary)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())

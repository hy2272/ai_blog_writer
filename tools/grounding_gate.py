#!/usr/bin/env python3
"""grounding_gate.py — turn an LLM faithfulness verdict into a deterministic gate.

The grounding-checker agent (LLM-as-judge, via the shared gateway) reads a downstream
artifact (outline at 1->2, draft at 2->3) against its upstream artifact (sources, outline)
and emits a per-item verdict JSON. This tool turns that human-readable verdict into a
machine PASS/FAIL the orchestrator can gate on — text for the "why", structure for the
"does it pass". Exit 0 = PASS, 1 = FAIL, mirroring citation_audit.py.

This is the FAITHFULNESS layer (does each downstream item trace to upstream), distinct
from citation_audit (does a claim carry a marker — existence) and the fact-checker (is
the source itself true — external correctness). Cross-lingual by design: upstream sources
are English, downstream items are Chinese — the LLM judge handles the language gap; this
tool only validates the verdict's structure.

Verdict JSON schema:
  {
    "stage": "1->2" | "2->3",
    "items": [
      {"id": 1, "claim": "<the downstream point/claim>",
       "grounded": true, "sources": ["S1","S3"], "note": "<why>"}
    ]
  }

Gate logic — an item FAILS if:
  - grounded is false                        (downstream item not supported upstream)
  - grounded is true but sources is empty    (claims support but cites nothing — contradiction)
  - a cited source id is not in --allowed-ids (if provided; e.g. the source-pack ids,
                                               or the upstream outline item ids)
Pass only if every item is clean.
"""
import argparse
import json
import sys


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic gate over a grounding verdict.")
    ap.add_argument("verdict", help="path to the grounding verdict JSON")
    ap.add_argument("--allowed-ids", help="comma-separated upstream ids the verdict may cite "
                                          "(e.g. S1,S2,S3 for 1->2, or outline item ids for 2->3)")
    args = ap.parse_args(argv)

    v = load(args.verdict)
    items = v.get("items", [])
    allowed = None
    if args.allowed_ids:
        allowed = {x.strip() for x in args.allowed_ids.split(",") if x.strip()}

    failures = []
    for it in items:
        cid = it.get("id", "?")
        srcs = it.get("sources") or []
        if not it.get("grounded", False):
            failures.append((cid, "NOT grounded in upstream", it.get("claim", "")))
            continue
        if not srcs:
            failures.append((cid, "grounded=true but no source cited", it.get("claim", "")))
            continue
        if allowed is not None:
            bad = [s for s in srcs if s not in allowed]
            if bad:
                failures.append((cid, f"cites unknown upstream id(s): {bad}", it.get("claim", "")))

    stage = v.get("stage", "?")
    print(f"grounding_gate: stage {stage} — {len(items)} items, {len(failures)} ungrounded")
    for cid, why, claim in failures:
        snippet = (claim or "")[:60]
        print(f"  [FAIL] item {cid}: {why}  —  \"{snippet}…\"")

    if failures:
        print("\nRESULT: FAIL")
        return 1
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

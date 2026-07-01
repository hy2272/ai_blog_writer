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
       "grounded": true,
       "source_ids": ["S1","S3"],
       "outline_ids": ["1.2"],
       "note": "<why>"}
    ]
  }

Gate logic — an item FAILS if:
  - grounded is false                        (downstream item not supported upstream)
  - 1->2: grounded=true but source_ids is empty
  - 2->3: grounded=true but outline_ids is empty
  - a cited id is not in the corresponding allow-list
Pass only if every item is clean.

Fails CLOSED on an empty/absent item list, mirroring factcheck_gate.py: a grounding check
that judged NOTHING is a judge that did not run, not a success — the same "never ship on a
green audit that checked nothing" logic (CLAUDE.md). Override with --allow-empty only for a
hop that genuinely has no downstream item to trace (rare; log the reason).
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
    ap.add_argument("--allowed-ids", help="legacy comma-separated upstream ids. For 1->2 this "
                                          "means source ids; for 2->3 this means outline ids.")
    ap.add_argument("--allowed-source-ids", help="comma-separated source ids the verdict may cite")
    ap.add_argument("--allowed-outline-ids", help="comma-separated outline ids the verdict may cite")
    ap.add_argument("--allow-empty", action="store_true",
                    help="treat an empty item list as PASS (default: FAIL — a grounding check "
                         "that checked nothing must not read as green)")
    args = ap.parse_args(argv)

    v = load(args.verdict)
    items = v.get("items", [])
    stage = v.get("stage", "?")

    def parse_ids(raw):
        if not raw:
            return None
        return {x.strip() for x in raw.split(",") if x.strip()}

    allowed_sources = parse_ids(args.allowed_source_ids)
    allowed_outline = parse_ids(args.allowed_outline_ids)
    legacy_allowed = parse_ids(args.allowed_ids)
    if legacy_allowed is not None:
        if stage == "1->2" and allowed_sources is None:
            allowed_sources = legacy_allowed
        elif stage == "2->3" and allowed_outline is None:
            allowed_outline = legacy_allowed

    failures = []
    for it in items:
        cid = it.get("id", "?")
        # Backward compatibility: older 1->2 verdicts used "sources".
        source_ids = it.get("source_ids")
        if source_ids is None and stage == "1->2":
            source_ids = it.get("sources")
        source_ids = source_ids or []
        outline_ids = it.get("outline_ids") or []

        if not it.get("grounded", False):
            failures.append((cid, "NOT grounded in upstream", it.get("claim", "")))
            continue

        if stage == "1->2":
            if not source_ids:
                failures.append((cid, "grounded=true but no source_ids cited", it.get("claim", "")))
                continue
        elif stage == "2->3":
            if not outline_ids:
                if it.get("sources") and not it.get("source_ids"):
                    failures.append((cid, "stage 2->3 requires outline_ids; source_ids are optional",
                                     it.get("claim", "")))
                else:
                    failures.append((cid, "grounded=true but no outline_ids cited", it.get("claim", "")))
                continue
        else:
            failures.append((cid, f"unknown stage {stage!r}", it.get("claim", "")))
            continue

        if allowed_sources is not None:
            bad = [s for s in source_ids if s not in allowed_sources]
            if bad:
                failures.append((cid, f"cites unknown source id(s): {bad}", it.get("claim", "")))
        if allowed_outline is not None:
            bad = [s for s in outline_ids if s not in allowed_outline]
            if bad:
                failures.append((cid, f"cites unknown outline id(s): {bad}", it.get("claim", "")))

    empty_fail = not items and not args.allow_empty

    print(f"grounding_gate: stage {stage} — {len(items)} items, {len(failures)} ungrounded")
    for cid, why, claim in failures:
        snippet = (claim or "")[:60]
        print(f"  [FAIL] item {cid}: {why}  —  \"{snippet}…\"")
    if empty_fail:
        print("  [FAIL] no items in verdict — a grounding check that traced nothing is not a pass")

    if failures or empty_fail:
        print("\nRESULT: FAIL")
        return 1
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

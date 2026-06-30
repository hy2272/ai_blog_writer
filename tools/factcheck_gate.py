#!/usr/bin/env python3
"""factcheck_gate.py — turn the fact-checker's per-claim verdict into a deterministic gate.

`citation_audit.py` proves a claim HAS a marker (existence); the fact-checker reads the
cited source and judges whether the source actually SUPPORTS the claim (external
correctness). That judgment used to be a markdown table + loose result JSON — advisory and
un-gateable. This tool makes it a hard machine gate: any claim that is not SUPPORTED fails.
It closes the project's named most-dangerous gap ("cited but wrong" — the green-dashboard
trap), now enforceable in CI alongside `citation_audit.py` and `grounding_gate.py`.

Fails CLOSED (deliberately unlike grounding_gate, which passes on zero items): an empty or
absent claim list FAILs, because a fact-check that checked nothing must never read as green
— "never ship on a green audit without the fact-check having run" (CLAUDE.md). Override
only with --allow-empty for a section that genuinely carries no factual claim.

Verdict JSON schema (the fact-checker writes this):
  {
    "stage": "S3-fact-check",
    "section": 1,
    "claims": [
      {"id": 1, "claim": "<the sentence>", "citation": "S1",
       "verdict": "SUPPORTED" | "MISATTRIBUTED" | "UNSOURCED" | "UNVERIFIED",
       "evidence": "<what the source says / why it fails>",
       "fix": "<for non-SUPPORTED: correct id / soften / drop>"}
    ]
  }

Gate logic — a claim FAILS if its verdict is anything other than exactly "SUPPORTED"
(MISATTRIBUTED / UNSOURCED / UNVERIFIED all fail), if the verdict is missing, or if it is
an unknown value. The section FAILS if any claim fails, or the claim list is empty (unless
--allow-empty). Exit 0 = PASS, 1 = FAIL, mirroring citation_audit.py / grounding_gate.py.
"""
import argparse
import json
import sys


PASS_VERDICT = "SUPPORTED"
FAIL_VERDICTS = {"MISATTRIBUTED", "UNSOURCED", "UNVERIFIED"}


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Deterministic gate over a fact-check verdict.")
    ap.add_argument("verdict", help="path to the fact-check verdict JSON")
    ap.add_argument("--allow-empty", action="store_true",
                    help="treat an empty claim list as PASS (default: FAIL — a fact-check "
                         "that checked nothing must not read as green)")
    args = ap.parse_args(argv)

    v = load(args.verdict)
    claims = v.get("claims", [])
    section = v.get("section", "?")

    failures = []
    for c in claims:
        cid = c.get("id", "?")
        verdict = c.get("verdict")
        if verdict == PASS_VERDICT:
            continue
        if verdict is None:
            why = "no verdict (claim not classified)"
        elif verdict in FAIL_VERDICTS:
            why = verdict
        else:
            why = f"unknown verdict {verdict!r}"
        failures.append((cid, why, c.get("claim", "")))

    empty_fail = not claims and not args.allow_empty

    print(f"factcheck_gate: section {section} — {len(claims)} claims, {len(failures)} not SUPPORTED")
    for cid, why, claim in failures:
        snippet = (claim or "")[:60]
        print(f"  [FAIL] claim {cid}: {why}  —  \"{snippet}…\"")
    if empty_fail:
        print("  [FAIL] no claims in verdict — a fact-check that checked nothing is not a pass")

    if failures or empty_fail:
        print("\nRESULT: FAIL")
        return 1
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Run the article-level audit suite.

This wrapper prevents a common pipeline gap: section drafts pass their contracts, then
the assembled final draft loses a required keyword/citation during humanizing or output.
It runs citation_audit.py on every section contract and, when final.md exists, re-checks
the final article against the union of all section coverage requirements.
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def ordered_unique(values):
    out = []
    seen = set()
    for value in values:
        if value not in seen:
            out.append(value)
            seen.add(value)
    return out


def run(cmd):
    print("\n$ " + " ".join(str(x) for x in cmd))
    proc = subprocess.run(cmd, text=True, capture_output=True)
    if proc.stdout:
        print(proc.stdout, end="")
    if proc.stderr:
        print(proc.stderr, end="", file=sys.stderr)
    return proc.returncode


def section_number(path):
    stem = path.stem
    digits = "".join(ch for ch in stem if ch.isdigit())
    return int(digits or 0)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Audit all section drafts and the final article.")
    ap.add_argument("article_dir", help="articles/article_<slug> directory")
    ap.add_argument("--as-of", help="reference date YYYY-MM-DD for freshness")
    ap.add_argument("--check-links", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)

    root = Path(args.article_dir)
    source_pack = root / "source_pack.json"
    if not source_pack.exists():
        print(f"ERROR: missing source pack: {source_pack}", file=sys.stderr)
        return 1

    tool = Path(__file__).with_name("citation_audit.py")
    contracts = sorted((root / "contracts").glob("sec*_contract.json"), key=section_number)
    if not contracts:
        print(f"ERROR: no section contracts found under {root / 'contracts'}", file=sys.stderr)
        return 1

    failures = 0
    required_keywords = []
    must_cite = []

    for contract in contracts:
        k = section_number(contract)
        draft = root / "sections" / f"sec{k}_draft.md"
        if not draft.exists():
            print(f"\n[FAIL] missing section draft for {contract.name}: {draft}")
            failures += 1
            continue

        c = load_json(contract)
        required_keywords.extend(c.get("required_keywords", []))
        must_cite.extend(c.get("must_cite", []))

        cmd = [sys.executable, str(tool), str(draft), "--source-pack", str(source_pack),
               "--contract", str(contract)]
        if args.as_of:
            cmd += ["--as-of", args.as_of]
        if args.check_links:
            cmd.append("--check-links")
        if args.strict:
            cmd.append("--strict")
        failures += 1 if run(cmd) else 0

    final = root / "final.md"
    if final.exists():
        final_contract = {
            "required_keywords": ordered_unique(required_keywords),
            "must_cite": ordered_unique(must_cite),
        }
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as fh:
            json.dump(final_contract, fh, ensure_ascii=False, indent=2)
            final_contract_path = fh.name
        cmd = [sys.executable, str(tool), str(final), "--source-pack", str(source_pack),
               "--contract", final_contract_path]
        if args.as_of:
            cmd += ["--as-of", args.as_of]
        if args.check_links:
            cmd.append("--check-links")
        if args.strict:
            cmd.append("--strict")
        failures += 1 if run(cmd) else 0
    else:
        print(f"\n[WARN] final.md not found; skipped final article coverage audit: {final}")

    if failures:
        print(f"\nARTICLE AUDIT: FAIL ({failures} failing check groups)")
        return 1
    print("\nARTICLE AUDIT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

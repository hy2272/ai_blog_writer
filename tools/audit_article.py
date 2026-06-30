#!/usr/bin/env python3
"""Run the article-level audit suite.

This wrapper prevents a common pipeline gap: section drafts pass their contracts, then
the assembled final draft loses a section, keyword, or citation during humanizing/output.
It runs citation_audit.py on every section contract and, when final.md exists, re-checks
the final article against the union of all section coverage requirements plus structural
checks that every section made it into the assembled post.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


CITE_RE = re.compile(r"\[(S\d+(?:\s*,\s*S\d+)*)\]")
SECTION_MARKER_RE = re.compile(r"<!--\s*section:(\d+)\s*-->")
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$", re.MULTILINE)


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


def parse_citations(text):
    ids = set()
    for m in CITE_RE.finditer(text):
        for tok in m.group(1).split(","):
            ids.add(tok.strip())
    return ids


def first_heading(text):
    m = HEADING_RE.search(text)
    if not m:
        return None
    return normalize_heading(m.group(1))


def normalize_heading(text):
    text = re.sub(r"\s*\[[^\]]+\]\s*", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip().lower()


def final_section_findings(final_text, section_infos):
    findings = []
    markers = [int(x) for x in SECTION_MARKER_RE.findall(final_text)]
    expected = {info["k"] for info in section_infos}
    matched = set()

    if markers:
        marker_set = set(markers)
        missing = sorted(expected - marker_set)
        extra = sorted(marker_set - expected)
        if len(markers) != len(section_infos):
            findings.append(f"final has {len(markers)} section marker(s), expected {len(section_infos)}")
        if missing:
            findings.append(f"final missing section marker(s): {missing}")
        if extra:
            findings.append(f"final has unknown section marker(s): {extra}")
        matched |= marker_set & expected

    final_headings = {normalize_heading(h) for h in HEADING_RE.findall(final_text)}
    for info in section_infos:
        if info["heading"] and info["heading"] in final_headings:
            matched.add(info["k"])

    missing_sections = sorted(expected - matched)
    if missing_sections:
        findings.append("final missing section heading/marker for section(s): "
                        + ",".join(str(x) for x in missing_sections))

    final_citations = parse_citations(final_text)
    for info in section_infos:
        missing_citations = sorted(info["citations"] - final_citations)
        if missing_citations:
            findings.append(f"final missing citation(s) from section {info['k']}: {missing_citations}")

    return findings


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
    section_infos = []

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
        draft_text = draft.read_text(encoding="utf-8")
        section_infos.append({
            "k": k,
            "heading": first_heading(draft_text),
            "citations": parse_citations(draft_text),
        })

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
        final_text = final.read_text(encoding="utf-8")
        for finding in final_section_findings(final_text, section_infos):
            print(f"\n[FAIL] final-structure: {finding}")
            failures += 1

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

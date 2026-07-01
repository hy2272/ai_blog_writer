#!/usr/bin/env python3
"""citation_audit.py — the machine-checkable correctness oracle for prose.

This is the article-writer analog of sas2pyspark's `csv_compare_v2` + `fidelity-auditor`.
Prose has no "output equality" oracle, but an AI-hot-topic article DOES have a ground
truth: the facts. This tool checks the part of article quality that is mechanically
verifiable, so the soft LLM-judge only has to cover what a machine genuinely cannot.

Checks (each is independently reported; any FAIL → non-zero exit):
  1. citation-validity   every [Sn] marker used in the draft exists in the source pack
  2. uncited-claim       claim-like sentences (numbers / dates / claim verbs) with no
                         nearby [Sn] marker  ->  hallucination risk ("裸论断")
  3. source-freshness    every cited source has a date; warn if older than --max-age-days
                         (AI news goes stale fast — this is the "PHI" hard edge here)
  4. source-utilization  sources in the pack never cited  ->  warn (over-broad research)
  5. word-count          draft length within the contract's [word_min, word_max]
  6. required-coverage   every contract `required_keywords` phrase appears in the draft
  7. link-resolves       (opt-in, --check-links) every cited URL returns HTTP < 400
  8. source-authority    (opt-in, --source-authority) a cited domain on the blacklist ->
                         FAIL; a piece anchored on NO tier-1/2 source -> WARN; an unranked
                         domain -> WARN. Closes the "green-dashboard trap": cited + faithful
                         is not enough if the source itself is a content farm.
  9. banned-phrase       (opt-in, --banned-phrases) a 翻译腔/AI-味 phrase from the shared
                         common/banned_phrases.json appears in the draft. FAIL-level phrases
                         (赋能, 无缝, 岁月静好, …) fail the gate; WARN-level surface for a human.
                         Moves the style_patterns §3 blacklist from "humanizer reads markdown"
                         to a machine check.

Exit code: 0 = PASS (no FAIL-level findings), 1 = FAIL. WARN-level findings never
fail the gate on their own; use --strict to promote WARN -> FAIL.

Inputs:
  draft.md            the section or full-article markdown
  --source-pack FILE  JSON: {"sources":[{"id":"S1","url":..,"title":..,"date":"YYYY-MM-DD"}]}
  --contract FILE     optional JSON: {"word_min":..,"word_max":..,"required_keywords":[..],
                                      "must_cite":["S1","S3"]}
  --as-of YYYY-MM-DD  reference date for freshness (no system clock dependence)
  --max-age-days N    freshness threshold (default 180)
  --check-links       resolve cited URLs over the network (default off → deterministic)
  --strict            treat WARN findings as failures

Citation marker convention in the draft:  [S1]  [S1,S3]  [S1][S7]
"""
import argparse
import json
import re
import sys
from datetime import date
from urllib.parse import urlparse


CITE_RE = re.compile(r"\[(S\d+(?:\s*,\s*S\d+)*)\]")
# A heading that starts the references/sources block. The banned-phrase scan stops here by
# default: a source's OWN title may legitimately contain 打造/赋能 etc., and the article
# body is not "AI 味" because it quoted a real headline. Body prose is what we lint.
REF_HEADING_RE = re.compile(
    r"^\s{0,3}#{1,6}\s*(references|参考|参考来源|参考资料|来源|资料来源|sources|source list)\s*$",
    re.IGNORECASE | re.MULTILINE)
# Sentence split must be CJK-aware: Chinese terminators (。！？；) are NOT followed by a
# space, so requiring trailing whitespace (the Latin rule) would merge a whole Chinese
# paragraph into one "sentence" and neuter the uncited-claim check. Split AFTER a CJK
# terminator directly; for Latin .!? still require following whitespace so decimals
# (4.6) and URLs are not split.
SENT_SPLIT_RE = re.compile(r"(?<=[。！？；])\s*|(?<=[.!?])\s+|\n+")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)

# A sentence is "claim-like" (asserts a checkable fact) if it carries hard data or a
# reporting/announcement verb. Heuristic on purpose: it flags CANDIDATES for a human,
# exactly like a linter — false positives are cheaper than a shipped hallucination.
CLAIM_SIGNAL_RE = re.compile(
    r"\d|%|％|\$|￥|"
    r"(?:亿|万|百万|十亿)|"
    r"(?:发布|宣布|推出|上线|达到|增长|下降|融资|开源|超过|首次|据|表示|报道|声称)|"
    r"\b(?:announced|released|launched|reported|according|raised|reached|"
    r"billion|million|percent|surged|dropped|claims?|unveiled)\b",
    re.IGNORECASE,
)


class Finding:
    def __init__(self, level, check, message):
        self.level = level  # "FAIL" | "WARN"
        self.check = check
        self.message = message

    def __str__(self):
        return f"  [{self.level}] {self.check}: {self.message}"


def strip_code(text):
    text = FENCE_RE.sub("", text)
    return HTML_COMMENT_RE.sub("", text)


def parse_citations(text):
    """Return the set of source ids referenced anywhere in the text."""
    ids = set()
    for m in CITE_RE.finditer(text):
        for tok in m.group(1).split(","):
            ids.add(tok.strip())
    return ids


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def check_citation_validity(used_ids, pack_ids):
    out = []
    for cid in sorted(used_ids):
        if cid not in pack_ids:
            out.append(Finding("FAIL", "citation-validity",
                               f"draft cites {cid} but it is not in the source pack"))
    return out


def check_uncited_claims(text):
    out = []
    body = strip_code(text)
    for raw in SENT_SPLIT_RE.split(body):
        sent = raw.strip()
        if len(sent) < 12:
            continue
        if sent.lstrip().startswith(("#", ">", "|", "-", "*")):
            continue  # headings / quotes / list scaffolding / tables
        if CLAIM_SIGNAL_RE.search(sent) and not CITE_RE.search(sent):
            snippet = sent[:70].replace("\n", " ")
            out.append(Finding("FAIL", "uncited-claim",
                               f"claim-like sentence has no [Sn] source: \"{snippet}…\""))
    return out


def check_freshness(used_ids, by_id, as_of, max_age_days):
    out = []
    for cid in sorted(used_ids):
        src = by_id.get(cid)
        if not src:
            continue  # already reported by citation-validity
        d = src.get("date")
        if not d:
            out.append(Finding("FAIL", "source-freshness",
                               f"{cid} is cited but has no date in the pack"))
            continue
        try:
            sd = date.fromisoformat(d)
        except ValueError:
            out.append(Finding("FAIL", "source-freshness",
                               f"{cid} has an unparseable date: {d!r}"))
            continue
        age = (as_of - sd).days
        if age > max_age_days:
            out.append(Finding("WARN", "source-freshness",
                               f"{cid} is {age} days old (> {max_age_days}); "
                               f"verify it is still current for an AI hot-topic piece"))
    return out


def check_utilization(used_ids, pack_ids):
    out = []
    for cid in sorted(pack_ids):
        if cid not in used_ids:
            out.append(Finding("WARN", "source-utilization",
                               f"{cid} is in the pack but never cited (over-broad research?)"))
    return out


def check_word_count(text, contract):
    out = []
    wmin = contract.get("word_min")
    wmax = contract.get("word_max")
    # CJK-aware length: count CJK characters individually + whitespace-split tokens.
    cjk = len(re.findall(r"[一-鿿]", text))
    latin = len(re.findall(r"[A-Za-z][A-Za-z'-]*", text))
    n = cjk + latin
    if wmin is not None and n < wmin:
        out.append(Finding("FAIL", "word-count", f"draft is {n} words, below word_min {wmin}"))
    if wmax is not None and n > wmax:
        out.append(Finding("FAIL", "word-count", f"draft is {n} words, above word_max {wmax}"))
    return out, n


def check_required_coverage(text, contract):
    out = []
    low = text.lower()
    for kw in contract.get("required_keywords", []):
        if kw.lower() not in low:
            out.append(Finding("FAIL", "required-coverage",
                               f"contract requires keyword/claim \"{kw}\" — not found in draft"))
    return out


def check_must_cite(used_ids, contract):
    out = []
    for cid in contract.get("must_cite", []):
        if cid not in used_ids:
            out.append(Finding("FAIL", "required-coverage",
                               f"contract requires citing {cid} — not cited in draft"))
    return out


def check_links(used_ids, by_id):
    import urllib.request
    out = []
    for cid in sorted(used_ids):
        src = by_id.get(cid)
        if not src or not src.get("url"):
            continue
        url = src["url"]
        try:
            req = urllib.request.Request(url, method="HEAD",
                                         headers={"User-Agent": "citation-audit/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status >= 400:
                    out.append(Finding("FAIL", "link-resolves",
                                       f"{cid} URL returned HTTP {resp.status}: {url}"))
        except Exception as exc:  # noqa: BLE001 — network is best-effort
            out.append(Finding("WARN", "link-resolves",
                               f"{cid} URL could not be reached ({exc.__class__.__name__}): {url}"))
    return out


def _domain_of(url):
    """Registrable host of a URL, lowercased, without a leading www."""
    try:
        netloc = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    netloc = netloc.split("@")[-1].split(":")[0]
    return netloc[4:] if netloc.startswith("www.") else netloc


def _domain_matches(domain, listed):
    listed = str(listed).lower().lstrip(".")
    return domain == listed or domain.endswith("." + listed)


def classify_domain(domain, authority):
    """blacklist | tier1 | tier2 | unknown — first match wins, blacklist first."""
    if not domain:
        return "unknown"
    for tier, key in (("blacklist", "blacklist"),
                      ("tier1", "tier1_primary"),
                      ("tier2", "tier2_reputable")):
        for d in authority.get(key, []):
            if isinstance(d, str) and _domain_matches(domain, d):
                return tier
    return "unknown"


def check_source_authority(used_ids, by_id, authority):
    """A blacklisted/aggregator domain -> FAIL. A piece with NO tier-1/2 source -> WARN.
    An unranked domain -> WARN. Domain is derived here (machine truth), not trusted from
    any `tier` field a source may carry."""
    out = []
    has_authoritative = False
    cited_any = False
    for cid in sorted(used_ids):
        src = by_id.get(cid)
        if not src:
            continue  # already reported by citation-validity
        cited_any = True
        domain = _domain_of(src.get("url", ""))
        tier = classify_domain(domain, authority)
        if tier == "blacklist":
            out.append(Finding("FAIL", "source-authority",
                               f"{cid} cites a blacklisted/aggregator source "
                               f"({domain or src.get('url')!r}); cite the primary publisher, not this"))
        elif tier in ("tier1", "tier2"):
            has_authoritative = True
        else:
            out.append(Finding("WARN", "source-authority",
                               f"{cid} ({domain or 'no url'}) is not in the authority list; "
                               f"verify it is credible or add it to common/source_authority.json"))
    if cited_any and not has_authoritative:
        out.append(Finding("WARN", "source-authority",
                           "no cited source is tier-1/2 authoritative — the piece rests only on "
                           "low-authority/unranked sources; anchor a key claim to a primary or major outlet"))
    return out


def strip_references(text):
    """Drop everything from the first References/参考来源 heading onward. Used to scope the
    banned-phrase scan to body prose so a cited source's title can't red the article."""
    m = REF_HEADING_RE.search(text)
    return text[:m.start()] if m else text


def check_banned_phrases(text, banned, scope="body"):
    """A phrase from the shared blacklist appears in the draft. Naive substring match
    (case-insensitive for Latin); level comes from the data file. Code fences/comments are
    stripped first so a phrase quoted inside an example block does not fire. scope="body"
    (default) also drops the references/sources block so a cited source's title does not
    trip the lint; scope="all" scans the whole document."""
    out = []
    body = strip_code(text)
    if scope == "body":
        body = strip_references(body)
    low = body.lower()
    for entry in banned.get("phrases", []):
        phrase = entry.get("phrase")
        if not phrase:
            continue
        if phrase.lower() in low:
            level = "FAIL" if str(entry.get("level", "FAIL")).upper() == "FAIL" else "WARN"
            reason = entry.get("reason", "banned phrase")
            suggest = entry.get("suggest")
            msg = f"「{phrase}」— {reason}"
            if suggest:
                msg += f"；改用：{suggest}"
            out.append(Finding(level, "banned-phrase", msg))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Machine-checkable citation/fact audit for prose.")
    ap.add_argument("draft", help="path to the section/article markdown")
    ap.add_argument("--source-pack", required=True, help="JSON source pack")
    ap.add_argument("--contract", help="optional JSON contract (word_min/max, required_keywords, must_cite)")
    ap.add_argument("--as-of", help="reference date YYYY-MM-DD for freshness (default: pack max date)")
    ap.add_argument("--max-age-days", type=int, default=180)
    ap.add_argument("--check-links", action="store_true")
    ap.add_argument("--source-authority",
                    help="optional JSON of domain tiers (tier1_primary/tier2_reputable/blacklist); "
                         "blacklisted source -> FAIL, no tier-1/2 source -> WARN")
    ap.add_argument("--banned-phrases",
                    help="optional JSON blacklist of 翻译腔/AI-味 phrases "
                         "(common/banned_phrases.json); FAIL-level hit -> FAIL, WARN-level -> WARN")
    ap.add_argument("--banned-phrases-scope", choices=("body", "all"), default="body",
                    help="where to scan for banned phrases: 'body' (default) skips the "
                         "references/sources block so a cited source's title can't trip the "
                         "lint; 'all' scans the whole document")
    ap.add_argument("--strict", action="store_true", help="promote WARN findings to failures")
    args = ap.parse_args(argv)

    with open(args.draft, encoding="utf-8") as fh:
        draft = fh.read()
    pack = load_json(args.source_pack)
    contract = load_json(args.contract) if args.contract else {}

    sources = pack.get("sources", [])
    by_id = {s["id"]: s for s in sources}
    pack_ids = set(by_id)
    used_ids = parse_citations(draft)

    if args.as_of:
        as_of = date.fromisoformat(args.as_of)
    else:
        dates = [date.fromisoformat(s["date"]) for s in sources if s.get("date")]
        as_of = max(dates) if dates else date.fromisoformat("2000-01-01")

    findings = []
    findings += check_citation_validity(used_ids, pack_ids)
    findings += check_uncited_claims(draft)
    findings += check_freshness(used_ids, by_id, as_of, args.max_age_days)
    findings += check_utilization(used_ids, pack_ids)
    wc_findings, n_words = check_word_count(draft, contract)
    findings += wc_findings
    findings += check_required_coverage(draft, contract)
    findings += check_must_cite(used_ids, contract)
    if args.check_links:
        findings += check_links(used_ids, by_id)
    if args.source_authority:
        findings += check_source_authority(used_ids, by_id, load_json(args.source_authority))
    if args.banned_phrases:
        findings += check_banned_phrases(draft, load_json(args.banned_phrases),
                                         scope=args.banned_phrases_scope)

    fails = [f for f in findings if f.level == "FAIL"]
    warns = [f for f in findings if f.level == "WARN"]
    if args.strict:
        fails += warns
        warns = []

    print(f"citation_audit: {args.draft}")
    print(f"  words={n_words}  sources={len(pack_ids)}  cited={len(used_ids)}  "
          f"as_of={as_of}  FAIL={len(fails)}  WARN={len(warns)}")
    for f in findings:
        print(f)

    if fails:
        print("\nRESULT: FAIL")
        return 1
    print("\nRESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

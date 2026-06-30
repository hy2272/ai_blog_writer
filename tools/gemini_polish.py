#!/usr/bin/env python3
"""gemini_polish.py — final language polish pass via the Gemini API.

A LAST-mile pass: after the post passes both oracles (citation_audit + grounding_gate),
send the finished Chinese text through Gemini to improve fluency ONLY — never facts,
never citations, never structure. Gemini's Chinese reads more natively; this borrows that
without letting it touch correctness (which is already locked by the oracles upstream).

Reads the API key from a local .env (gitignored) in the project root:
  GEMINI_API_KEY=...           (required)
  GEMINI_MODEL=gemini-2.5-flash    (optional; override if it 404s, e.g. gemini-3-pro)
  GEMINI_PRICE_IN / GEMINI_PRICE_OUT  (optional; USD per 1M tokens, for the cost estimate)

Cost guardrail (Hanfei's rule): if the estimated call cost exceeds --max-usd (default 1.0),
the tool REFUSES and asks you to confirm with --force. A single ~1000-字 post is far under
$1 (≈ a fraction of a cent on flash), so normal use never trips it; the guard only catches
an accidental bulk run.

Privacy note: this SENDS the text to Google. Fine for a post that is about to be public;
do not use it on anything sensitive.

Usage:
  python3 tools/gemini_polish.py <input.txt> [--out polished.txt] [--dry-run] [--max-usd 1.0] [--force]
  --dry-run prints the model, the prompt size, and the cost estimate WITHOUT sending.
"""
import argparse
import collections
import json
import os
import re
import sys
import urllib.request
import urllib.error

DEFAULT_MODEL = "gemini-2.5-flash"
# Conservative flash-tier defaults (USD per 1M tokens). Override via env for a Pro model.
DEFAULT_PRICE_IN = 0.30
DEFAULT_PRICE_OUT = 2.50

# The polish instruction. Keep meaning/facts/structure; fix only the Chinese. The avoid-list
# is Hanfei's: no English-calque Chinese, no 炸 / 硬 / 诚实地说-style AI tells.
POLISH_INSTRUCTION = """你是一名母语中文编辑。下面是一篇已经定稿、事实与引用都核对过的小红书文案。
只做语言润色，让中文更地道、更口语、更有网感。严格遵守：

1. 不改事实、不改数字、不加新信息、不删内容要点。保留所有 emoji、分点符号(▪️▫️)、段落结构。
2. 不要"翻译腔"——把任何像英文直译的中文改写成中文母语者真的会说的话。
3. 避免这些一看就是 AI 的词/腔调：「炸」「硬」「诚实地说/诚实讲」「值得注意的是」「总而言之」
   「深入」「赋能」「打造」「拥抱」「无缝」「强大的」「丰富的」，以及任何空洞的过渡和排比凑数。
4. 保持第一人称、真诚分享体，不要测评腔，不要客套。
5. 标题如果有，保持短而有网感。

只输出润色后的全文，不要解释，不要加引号或代码块。

原文：
---
"""


# --- fact diff (--check-facts) ---------------------------------------------------------
# Catch the dangerous case where polish keeps a number but flips its unit/meaning
# (e.g. "75% off" → "75折" — both contain 75, so a bare-number diff misses it). We compare
# a multiset of (number+unit) tokens AND a multiset of bare numbers. Synonymous units are
# normalized so harmless reformatting (日↔号, 美金↔美元) does not raise a false alarm.
_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(美元|美金|折|倍|月|年|日|号|周|天|亿|万|元|%|分|秒)")
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_UNIT_NORM = {"号": "日", "美金": "美元"}


def extract_facts(text):
    units = collections.Counter()
    for num, unit in _UNIT_RE.findall(text):
        units[f"{num}{_UNIT_NORM.get(unit, unit)}"] += 1
    nums = collections.Counter(_NUM_RE.findall(text))
    return units, nums


def fact_diff(src, dst):
    """Return a list of human-readable diff lines; empty list == facts match."""
    su, sn = extract_facts(src)
    du, dn = extract_facts(dst)
    out = []
    for tok, n in (su - du).items():
        out.append(f"  [unit gone]   original has '{tok}' (x{n}) — not in polished")
    for tok, n in (du - su).items():
        out.append(f"  [unit new]    polished has '{tok}' (x{n}) — not in original  ← likely a changed fact")
    for tok, n in (sn - dn).items():
        out.append(f"  [number gone] original has {tok} (x{n}) — not in polished")
    for tok, n in (dn - sn).items():
        out.append(f"  [number new]  polished has {tok} (x{n}) — not in original")
    return out


def load_env(path):
    env = {}
    if not os.path.exists(path):
        return env
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def estimate_tokens(text):
    # Rough mixed CN/EN estimate: ~3 chars per token. Good enough for a cost guard.
    return max(1, len(text) // 3)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Final Chinese polish via Gemini (fluency only).")
    ap.add_argument("input", help="path to the finished post text")
    ap.add_argument("--out", help="write polished text here (default: stdout)")
    ap.add_argument("--env", default=".env", help="path to .env (default: ./.env)")
    ap.add_argument("--dry-run", action="store_true", help="estimate + show request, do NOT send")
    ap.add_argument("--max-usd", type=float, default=1.0, help="refuse if estimate exceeds this")
    ap.add_argument("--force", action="store_true", help="send even if estimate exceeds --max-usd")
    ap.add_argument("--check-facts", action="store_true",
                    help="after polishing, diff numbers/units (dates/discounts) vs the input; "
                         "exits 3 if any differ (some may be benign reformatting — review)")
    args = ap.parse_args(argv)

    with open(args.input, encoding="utf-8") as fh:
        text = fh.read()

    env = load_env(args.env)
    api_key = (env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
               or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    model = env.get("GEMINI_MODEL") or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    price_in = float(env.get("GEMINI_PRICE_IN", DEFAULT_PRICE_IN))
    price_out = float(env.get("GEMINI_PRICE_OUT", DEFAULT_PRICE_OUT))

    prompt = POLISH_INSTRUCTION + text + "\n---\n"
    in_tok = estimate_tokens(prompt)
    out_tok = int(estimate_tokens(text) * 1.2)  # output ~ same length as input + slack
    est_usd = in_tok / 1_000_000 * price_in + out_tok / 1_000_000 * price_out

    print(f"gemini_polish: model={model}  in≈{in_tok}tok  out≈{out_tok}tok  "
          f"est≈${est_usd:.4f}  (max ${args.max_usd:.2f})")

    if est_usd > args.max_usd and not args.force:
        print(f"\nREFUSED: estimate ${est_usd:.4f} exceeds --max-usd ${args.max_usd:.2f}. "
              f"Confirm necessity, then re-run with --force.")
        return 2

    if args.dry_run:
        print("\n[dry-run] not sending. Prompt head:\n" + prompt[:300] + " …")
        return 0

    if not api_key:
        print("\nERROR: no GEMINI_API_KEY in .env (or env). Add it to ./.env "
              "(copy .env.example). The file is gitignored.")
        return 1

    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}]}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        print(f"\nHTTP {e.code}: {detail}")
        if e.code == 404:
            print("→ the model id may be wrong for now; set GEMINI_MODEL in .env "
                  "(e.g. gemini-2.5-flash / gemini-3-pro).")
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"\nrequest failed: {exc.__class__.__name__}: {exc}")
        return 1

    try:
        out = data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        print("\nunexpected response shape:\n" + json.dumps(data, ensure_ascii=False)[:500])
        return 1

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(out)
        print(f"\npolished → {args.out}")
    else:
        print("\n" + out)

    if args.check_facts:
        warnings = fact_diff(text, out)
        if warnings:
            print("\n=== fact-diff: ⚠️  REVIEW — numbers/units changed pre→post polish ===")
            for line in warnings:
                print(line)
            print("Verify each (some may be benign reformatting); watch discounts / comparisons / negations.")
            return 3
        print("\nfact-diff: ✅ numbers & units match pre/post polish")
    return 0


if __name__ == "__main__":
    sys.exit(main())

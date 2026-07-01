#!/usr/bin/env python3
"""gemini_polish.py — the S5.5 language-polish pass (per-mode temperature + oracle-checked diff).

Where this sits: AFTER S5 humanizer (the oracles are already green), BEFORE the S6 human
sign-off. The orchestrator runs it automatically so the human never has to remember to; the
human then reads a side-by-side diff (humanized ↔ polished) and picks, per change, what to keep.

The whole design principle (from the architecture discussion): the machine STANDS BESIDE the
human's judgement, it does not replace it. So this tool:
  * polishes language only (never facts / citations / structure), and
  * re-runs the SAME per-track oracle (via tools/run_oracle.py) on BOTH the pre- and post-
    polish artifact, and shows the DELTA — any finding that appears only after polish is, by
    definition, something the polish introduced. That before→after delta is the authoritative
    signal. Nothing is auto-accepted and nothing is auto-rejected: the human reads the diff,
    sees which hunks the machine flags, and decides (default: distrust a 🔴 hunk unless sure).

Per-mode temperature (this is why it's a direct-API script, not a subagent — a subagent has no
temperature knob; a direct API call does):
  * factual_ai_news / mixed_explainer -> LOW temp (0.3): stay conservative, don't reword facts.
  * aesthetic_lifestyle              -> HIGH temp (0.85): we WANT it to risk a fresher phrasing;
    the aesthetic oracle (破折号 / card length / 「」) + the diff catch any structural overreach.

Reads the API key from a local .env (gitignored) in the project root:
  GEMINI_API_KEY=...           (required for a live call)
  GEMINI_MODEL=gemini-2.5-flash    (optional; override if it 404s)
  GEMINI_PRICE_IN / GEMINI_PRICE_OUT  (optional; USD per 1M tokens, for the cost estimate)

Cost guardrail (Hanfei's rule): refuse if the estimate exceeds --max-usd (default 1.0) unless
--force. A single post is a fraction of a cent; the guard only catches an accidental bulk run.
Privacy: this SENDS the text to Google. Fine for a post about to be public.

Usage:
  # factual / explainer prose (markdown in, markdown out):
  python3 tools/gemini_polish.py humanized.md --mode factual_ai_news \\
      --out polished.md --diff-html polish_diff.html -- \\
      --source-pack source_pack.json --contract contracts/sec1_contract.json
  # aesthetic card post (JSON in, JSON out — only non-quote card texts are polished):
  python3 tools/gemini_polish.py aesthetic_post.json --mode aesthetic_lifestyle \\
      --out polished_post.json --diff-html polish_diff.html
  # offline (no API): supply an already-polished artifact and just (re)build the diff+oracle delta:
  python3 tools/gemini_polish.py humanized.md --mode factual_ai_news \\
      --polished polished.md --diff-html polish_diff.html -- --source-pack source_pack.json

Everything after a bare `--` is forwarded verbatim to the oracle (the dispatcher's option (i)).
"""
import argparse
import collections
import html
import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import run_oracle  # single source of truth for mode aliases + the mode→oracle map

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_PRICE_IN = 0.30
DEFAULT_PRICE_OUT = 2.50

# Per-mode sampling temperature. None (no --mode, no --temperature) => omit generationConfig
# and keep the model default (backward compatible with the old plain-text usage).
MODE_TEMPERATURE = {
    "factual_ai_news": 0.3,
    "mixed_explainer": 0.3,
    "aesthetic_lifestyle": 0.85,
}

POLISH_INSTRUCTION = """你是一名母语中文编辑。下面是一篇已经定稿、事实与引用都核对过的中文文案。
只做语言润色，让中文更地道、更口语、更有网感。严格遵守：

1. 不改事实、不改数字、不加新信息、不删内容要点。保留所有 emoji、分点符号(▪️▫️)、段落结构。
   保留所有形如 [S1] [S2,S3] 的引用标记，位置和内容都不许动。
2. 不要"翻译腔"——把任何像英文直译的中文改写成中文母语者真的会说的话。
3. 避免这些一看就是 AI 的词/腔调：「炸」「硬」「诚实地说/诚实讲」「值得注意的是」「总而言之」
   「深入」「赋能」「打造」「拥抱」「无缝」「强大的」「丰富的」，以及任何空洞的过渡和排比凑数。
4. 保持第一人称、真诚分享体，不要测评腔，不要客套。
5. 标题如果有，保持短而有网感。

只输出润色后的全文，不要解释，不要加引号或代码块。

原文：
---
"""

# Aesthetic cards want fewer rules (facts are a non-issue) and a lighter, poetic touch.
POLISH_INSTRUCTION_AESTHETIC = """你是一名擅长生活美学文案的中文编辑。下面是一张卡片上的一句氛围文案。
在保持原意与画面感的前提下，把它润色得更有灵气、更耐读、更像人写的（不是 AI 腔）。严格遵守：

1. 绝对不要出现破折号（— 或 ——）；需要停顿就用。，：或断句。
2. 不要 AI 味/翻译腔词：「岁月静好」「治愈」「赋能」「打造」「拥抱」「值得注意的是」等。
3. 保持简短（这是一句一卡，尽量不超过 30 字），不要展开成多句说教。
4. 不提 AI，不加标签，不加解释。

只输出润色后的这一句，不要引号、不要代码块、不要多余说明。

原文：
---
"""

# --- number/unit fact diff (kept from v1; also reused per-hunk for the factual hints) --------
_UNIT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(美元|美金|折|倍|月|年|日|号|周|天|亿|万|元|%|分|秒)")
_NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_UNIT_NORM = {"号": "日", "美金": "美元"}
_CITE_RE = re.compile(r"\[([Ss]\d+(?:\s*,\s*[Ss]\d+)*)\]")
_EM_DASH_RE = re.compile(r"—")
# Parse an oracle's printed findings back into normalized strings for set math.
_FINDING_RE = re.compile(r"\[(FAIL|WARN)\]\s+([\w-]+):\s+(.*)")


def extract_facts(text):
    units = collections.Counter()
    for num, unit in _UNIT_RE.findall(text):
        units[f"{num}{_UNIT_NORM.get(unit, unit)}"] += 1
    nums = collections.Counter(_NUM_RE.findall(text))
    return units, nums


def fact_diff(src, dst):
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


def markers(text):
    ids = set()
    for m in _CITE_RE.finditer(text):
        for tok in m.group(1).split(","):
            ids.add(tok.strip().upper())
    return ids


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
    return max(1, len(text) // 3)


# --- Gemini API ------------------------------------------------------------------------------
def gemini_call(prompt, api_key, model, temperature, timeout=60):
    """One generateContent call. Returns the text, or raises RuntimeError with a readable msg."""
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model}:generateContent?key={api_key}")
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    if temperature is not None:
        payload["generationConfig"] = {"temperature": temperature}
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        hint = ("  → the model id may be wrong; set GEMINI_MODEL in .env"
                if e.code == 404 else "")
        raise RuntimeError(f"HTTP {e.code}: {detail}{hint}")
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"request failed: {exc.__class__.__name__}: {exc}")
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        raise RuntimeError("unexpected response shape:\n"
                           + json.dumps(data, ensure_ascii=False)[:500])


# --- oracle before/after (via the dispatcher — one place knows mode→oracle) -------------------
def run_oracle_findings(mode, target, oracle_args):
    """Run tools/run_oracle.py on `target`; return (exit_code, set_of_finding_strings)."""
    cmd = [sys.executable, os.path.join(HERE, "run_oracle.py"), "--mode", mode, target, *oracle_args]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    found = set()
    for line in (proc.stdout + "\n" + proc.stderr).splitlines():
        m = _FINDING_RE.search(line)
        if m:
            found.add(f"[{m.group(1)}] {m.group(2)}: {m.group(3)}")
    return proc.returncode, found


# --- diff model ------------------------------------------------------------------------------
def split_prose(text):
    """Split markdown into paragraph segments (blank-line separated), keeping non-empty."""
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip()]


def hint_for_change(mode, orig, pol):
    """Return (state, reason) for a changed segment. state ∈ {'red','yellow'}.
    These are LOCAL machine hints — the same primitives the oracle gates on, computed per hunk —
    so a 🔴 means 'this change touched something the oracle cares about', pointing you at it.
    The authoritative verdict is the whole-doc before→after oracle delta shown in the banner."""
    canonical = run_oracle.resolve_mode(mode) or mode
    if canonical == "aesthetic_lifestyle":
        if _EM_DASH_RE.search(pol) and not _EM_DASH_RE.search(orig):
            return "red", "新增破折号（aesthetic oracle FAIL 项）"
        if (pol.count("「") - pol.count("」")) != (orig.count("「") - orig.count("」")):
            return "red", "「」闭合改变"
        vis = len(re.sub(r"\s", "", pol))
        if vis > 32 and len(re.sub(r"\s", "", orig)) <= 32:
            return "yellow", f"卡变长至 {vis} 字（>32 触发 WARN）"
        return "yellow", "仅措辞变化"
    # factual / explainer / default: markers + numbers are the machine-checkable surface
    if markers(orig) != markers(pol):
        return "red", f"引用标记变化 {sorted(markers(orig))}→{sorted(markers(pol))}"
    if extract_facts(orig) != extract_facts(pol):
        return "red", "数字/单位变化"
    return "yellow", "仅措辞变化"


def build_segment_rows(mode, orig_segs, pol_segs):
    """Align orig↔pol segments (SequenceMatcher) and tag each row 🟢/🟡/🔴."""
    import difflib
    sm = difflib.SequenceMatcher(a=orig_segs, b=pol_segs, autojunk=False)
    rows = []  # (state, reason, orig_text, pol_text)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                rows.append(("green", "未改动", orig_segs[i1 + k], pol_segs[j1 + k]))
        elif tag == "replace":
            # pair them up positionally; leftover on either side shown alone
            span = max(i2 - i1, j2 - j1)
            for k in range(span):
                o = orig_segs[i1 + k] if i1 + k < i2 else ""
                p = pol_segs[j1 + k] if j1 + k < j2 else ""
                state, reason = hint_for_change(mode, o, p)
                rows.append((state, reason, o, p))
        elif tag == "delete":
            for k in range(i1, i2):
                rows.append(("red", "整段被删除", orig_segs[k], ""))
        elif tag == "insert":
            for k in range(j1, j2):
                rows.append(("red", "整段被新增", "", pol_segs[k]))
    return rows


_STATE_STYLE = {
    "green":  ("🟢", "#e8f5e9"),
    "yellow": ("🟡", "#fff8e1"),
    "red":    ("🔴", "#ffebee"),
}


def render_html(mode, model, temperature, rows, oracle_banner, out_path):
    def cell(text):
        return html.escape(text).replace("\n", "<br>")
    trs = []
    for state, reason, o, p in rows:
        emoji, bg = _STATE_STYLE[state]
        rbg = bg if state != "green" else "#fafafa"
        trs.append(
            f'<tr style="background:{rbg}">'
            f'<td class="tag">{emoji}<div class="reason">{html.escape(reason)}</div></td>'
            f'<td class="col">{cell(o)}</td>'
            f'<td class="col">{cell(p)}</td></tr>')
    temp_s = "model default" if temperature is None else f"{temperature}"
    doc = f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>gemini_polish diff — {html.escape(mode)}</title>
<style>
 body{{font:15px/1.7 -apple-system,"PingFang SC",sans-serif;margin:24px;color:#222}}
 h1{{font-size:18px}} .meta{{color:#666;font-size:13px;margin-bottom:14px}}
 .banner{{border-radius:8px;padding:12px 16px;margin:12px 0;font-size:14px}}
 .legend{{font-size:13px;color:#555;margin:8px 0 16px}}
 table{{border-collapse:collapse;width:100%;table-layout:fixed}}
 th{{text-align:left;font-size:13px;color:#888;border-bottom:2px solid #ddd;padding:6px 10px}}
 td{{vertical-align:top;padding:10px;border-bottom:1px solid #eee}}
 td.tag{{width:150px;font-size:13px}} td.col{{width:calc((100% - 150px)/2);white-space:pre-wrap}}
 .reason{{color:#a33;font-size:12px;margin-top:4px}}
 code{{background:#f0f0f0;padding:0 3px;border-radius:3px}}
</style></head><body>
<h1>S5.5 润色 diff · mode=<code>{html.escape(mode)}</code></h1>
<div class="meta">model={html.escape(model)} · temperature={temp_s} · 左=humanized(原) · 右=polished(润色)</div>
{oracle_banner}
<div class="legend">就地提示（本地机检，指向被改动处）：🟢 未改动 · 🟡 仅措辞变化 · 🔴 触到机检项（引用标记/数字/破折号/「」）——默认存疑，除非你确信误报再采纳。
权威判定看上方 banner 的 oracle 前后 delta。</div>
<table><tr><th>提示</th><th>humanized（原）</th><th>polished（润色）</th></tr>
{''.join(trs)}
</table></body></html>"""
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(doc)


def oracle_banner_html(pre_code, pre_findings, post_code, post_findings):
    new = sorted(post_findings - pre_findings)
    resolved = sorted(pre_findings - post_findings)
    new_fail = [f for f in new if f.startswith("[FAIL]")]
    if not new:
        color = "#e8f5e9"; head = "✅ oracle：润色未引入任何新发现（前后一致）"
    elif new_fail:
        color = "#ffebee"; head = f"🔴 oracle：润色引入了 {len(new_fail)} 条新的 FAIL（下面列出，重点看）"
    else:
        color = "#fff8e1"; head = f"🟡 oracle：润色引入了 {len(new)} 条新的 WARN（无新 FAIL）"
    lines = [f"<b>{html.escape(head)}</b>",
             f"<div style='font-size:13px;color:#555;margin-top:4px'>"
             f"exit(pre)={pre_code} → exit(post)={post_code}</div>"]
    if new:
        lines.append("<div style='margin-top:6px;font-size:13px'>润色新增：<ul>"
                     + "".join(f"<li>{html.escape(f)}</li>" for f in new) + "</ul></div>")
    if resolved:
        lines.append("<div style='font-size:13px;color:#2e7d32'>润色顺带消解：<ul>"
                     + "".join(f"<li>{html.escape(f)}</li>" for f in resolved) + "</ul></div>")
    return f'<div class="banner" style="background:{color}">' + "".join(lines) + "</div>"


# --- per-mode artifact handling --------------------------------------------------------------
def polish_prose(text, api_key, model, temperature):
    return gemini_call(POLISH_INSTRUCTION + text + "\n---\n", api_key, model, temperature)


def polish_aesthetic(post, api_key, model, temperature):
    """Polish ONLY non-quote card texts. Quote cards, quotes[], caption, hashtags are left
    untouched — a verified quote's wording carries provenance and must not be reworded."""
    out = json.loads(json.dumps(post))  # deep copy
    for card in out.get("cards", []):
        if card.get("quote"):
            continue
        t = card.get("text", "")
        if not t.strip():
            continue
        card["text"] = gemini_call(POLISH_INSTRUCTION_AESTHETIC + t + "\n---\n",
                                   api_key, model, temperature).strip()
    return out


def aesthetic_segments(post):
    """The comparable text units for the diff: each card's text in order."""
    return [c.get("text", "") for c in post.get("cards", [])]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="S5.5 Chinese polish via Gemini (per-mode temperature + oracle-checked diff).",
        epilog="Everything after a bare `--` is forwarded verbatim to the oracle.")
    ap.add_argument("input", help="humanized artifact: markdown (factual/explainer) or aesthetic_post.json")
    ap.add_argument("--mode", "-m", help="content track (sets temperature + which oracle); "
                    "see run_oracle.py for names/aliases. Omit for plain-text v1 behavior.")
    ap.add_argument("--temperature", type=float, help="override the per-mode temperature")
    ap.add_argument("--out", help="write polished artifact here (default: stdout)")
    ap.add_argument("--diff-html", help="write the side-by-side oracle-checked diff here")
    ap.add_argument("--polished", help="OFFLINE: use this already-polished artifact instead of "
                    "calling the API (regenerate the diff without paying)")
    ap.add_argument("--env", default=os.path.join(os.getcwd(), ".env"))
    ap.add_argument("--dry-run", action="store_true", help="estimate + show request, do NOT send")
    ap.add_argument("--max-usd", type=float, default=1.0, help="refuse if estimate exceeds this")
    ap.add_argument("--force", action="store_true", help="send even if estimate exceeds --max-usd")
    ap.add_argument("--check-facts", action="store_true",
                    help="diff numbers/units pre→post (text mode); exits 3 if any differ")

    # Split off oracle args on the literal `--` BEFORE argparse — REMAINDER would greedily
    # swallow our own flags (--mode/--diff-html) since `input` is positional and comes first.
    if argv is None:
        argv = sys.argv[1:]
    if "--" in argv:
        cut = argv.index("--")
        oracle_args = argv[cut + 1:]
        argv = argv[:cut]
    else:
        oracle_args = []
    args = ap.parse_args(argv)

    canonical = run_oracle.resolve_mode(args.mode) if args.mode else None
    if args.mode and canonical is None:
        ap.error(f"unknown --mode {args.mode!r}")

    temperature = args.temperature
    if temperature is None and canonical:
        temperature = MODE_TEMPERATURE.get(canonical)

    is_aesthetic = canonical == "aesthetic_lifestyle"

    with open(args.input, encoding="utf-8") as fh:
        raw = fh.read()

    env = load_env(args.env)
    api_key = (env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
               or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))
    model = env.get("GEMINI_MODEL") or os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL
    price_in = float(env.get("GEMINI_PRICE_IN", DEFAULT_PRICE_IN))
    price_out = float(env.get("GEMINI_PRICE_OUT", DEFAULT_PRICE_OUT))

    # cost estimate (skipped when injecting an offline --polished artifact)
    if not args.polished:
        in_tok = estimate_tokens(raw) + 400
        out_tok = int(estimate_tokens(raw) * 1.2)
        est_usd = in_tok / 1_000_000 * price_in + out_tok / 1_000_000 * price_out
        print(f"gemini_polish: mode={canonical or '(none)'}  temp={temperature}  model={model}  "
              f"in≈{in_tok}tok out≈{out_tok}tok est≈${est_usd:.4f} (max ${args.max_usd:.2f})")
        if est_usd > args.max_usd and not args.force:
            print(f"\nREFUSED: estimate ${est_usd:.4f} exceeds --max-usd ${args.max_usd:.2f}. "
                  f"Re-run with --force.")
            return 2
        if args.dry_run:
            print("\n[dry-run] not sending.")
            return 0
        if not api_key:
            print("\nERROR: no GEMINI_API_KEY in .env (or env). Add it to ./.env (gitignored).")
            return 1

    # --- produce the polished artifact ---
    try:
        if is_aesthetic:
            post = json.loads(raw)
            if args.polished:
                with open(args.polished, encoding="utf-8") as fh:
                    polished_post = json.load(fh)
            else:
                polished_post = polish_aesthetic(post, api_key, model, temperature)
            polished_str = json.dumps(polished_post, ensure_ascii=False, indent=2)
        else:
            if args.polished:
                with open(args.polished, encoding="utf-8") as fh:
                    polished_str = fh.read()
            else:
                polished_str = polish_prose(raw, api_key, model, temperature)
    except RuntimeError as exc:
        print(f"\n{exc}")
        return 1

    # write the polished artifact
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(polished_str)
        print(f"polished → {args.out}")
    elif not args.diff_html:
        print("\n" + polished_str)

    # --- oracle before/after (needs a mode + files on disk) ---
    oracle_banner = ""
    if canonical:
        # write both artifacts to temp paths for the oracle to read (aesthetic needs .json)
        import tempfile
        suffix = ".json" if is_aesthetic else ".md"
        pre_path = args.input
        with tempfile.NamedTemporaryFile("w", suffix=suffix, delete=False, encoding="utf-8") as tf:
            tf.write(polished_str); post_path = tf.name
        pre_code, pre_f = run_oracle_findings(canonical, pre_path, oracle_args)
        post_code, post_f = run_oracle_findings(canonical, post_path, oracle_args)
        os.unlink(post_path)
        oracle_banner = oracle_banner_html(pre_code, pre_f, post_code, post_f)
        new_fail = [f for f in (post_f - pre_f) if f.startswith("[FAIL]")]
        print(f"\noracle delta: exit {pre_code}→{post_code}  new_findings={len(post_f - pre_f)}  "
              f"new_FAIL={len(new_fail)}")
        for f in sorted(post_f - pre_f):
            print(f"  + {f}")

    # --- HTML diff ---
    if args.diff_html:
        if is_aesthetic:
            orig_segs = aesthetic_segments(json.loads(raw))
            pol_segs = aesthetic_segments(json.loads(polished_str))
        else:
            orig_segs = split_prose(raw)
            pol_segs = split_prose(polished_str)
        rows = build_segment_rows(canonical or (args.mode or ""), orig_segs, pol_segs)
        render_html(canonical or "(none)", model, temperature, rows, oracle_banner, args.diff_html)
        print(f"diff → {args.diff_html}")

    # --- legacy number/unit fact diff (text mode only) ---
    if args.check_facts and not is_aesthetic:
        warnings = fact_diff(raw, polished_str)
        if warnings:
            print("\n=== fact-diff: ⚠️  numbers/units changed pre→post ===")
            for line in warnings:
                print(line)
            return 3
        print("\nfact-diff: ✅ numbers & units match")
    return 0


if __name__ == "__main__":
    sys.exit(main())

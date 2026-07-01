#!/usr/bin/env python3
"""run_oracle.py — the per-track oracle dispatcher (a transparent transit adapter).

One job, on purpose: given a `--mode`, look up the ONE oracle that gates that track,
then exec it with every remaining argument forwarded verbatim and its exit code / stdout /
stderr passed straight back. Nothing is parsed, judged, or reshaped here.

Why this exists (see the architecture discussion): the "mode -> which oracle" mapping is
needed in at least two places — the S4 hard gate and the S5.5 post-polish re-check. Collapsing
it into one table (like banned words -> banned_phrases.json) means the map has a single home;
callers just say "audit this, mode=X" and never hard-code which script that is. Adding a
fourth content track = adding one row here, not touching every caller.

Design invariants (do NOT erode these — a "smart" dispatcher is the start of the mess):
  * It is a switch, not a judge. It never reads or interprets the oracle's findings.
    Any "read the result and decide" logic belongs to the orchestrator or the human gate.
  * It is dumb about oracle args (option (i)). The caller passes each oracle's own flags
    (--source-pack / --contract / --strict / …) as trailing args; the dispatcher forwards
    them untouched. It does NOT know each track's file conventions.
  * The three oracles stay three independent scripts. This is an extra entry point, not a
    replacement — citation_audit.py / aesthetic_audit.py / explainer_audit.py are still
    directly runnable (CI, manual smoke tests) exactly as before.

Usage (put --mode FIRST; everything after is forwarded to the oracle unchanged):
  python3 tools/run_oracle.py --mode <mode> <target> [oracle args…]

  # factual AI-news section (citation_audit.py):
  python3 tools/run_oracle.py --mode factual_ai_news sec1_draft.md \
      --source-pack source_pack.json --contract contracts/sec1_contract.json --strict
  # aesthetic card post (aesthetic_audit.py):
  python3 tools/run_oracle.py --mode aesthetic_lifestyle aesthetic_post.json --strict

Modes accept the canonical STATE.md `track` names and a few short aliases.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

# The whole mapping, in one place. Add a content track = add a row (+ ship its oracle).
MODE_ORACLE = {
    "factual_ai_news": "citation_audit.py",
    "aesthetic_lifestyle": "aesthetic_audit.py",
    "mixed_explainer": "explainer_audit.py",  # oracle ships with the explainer track
}

# Short aliases so callers can use the terse discussion names without a second vocabulary.
ALIASES = {
    "tech_news": "factual_ai_news",
    "news": "factual_ai_news",
    "factual": "factual_ai_news",
    "aesthetic": "aesthetic_lifestyle",
    "lifestyle": "aesthetic_lifestyle",
    "explainer": "mixed_explainer",
}


def resolve_mode(mode):
    """Canonicalize a mode/alias; return None if unknown."""
    m = mode.strip()
    m = ALIASES.get(m, m)
    return m if m in MODE_ORACLE else None


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Dispatch to the per-track oracle (transparent pass-through).",
        epilog="Put --mode first; all following args are forwarded to the oracle verbatim.",
    )
    ap.add_argument("--mode", "-m", required=True,
                    help="content track: " + " | ".join(sorted(MODE_ORACLE)) +
                         " (aliases: " + ", ".join(sorted(ALIASES)) + ")")
    ap.add_argument("rest", nargs=argparse.REMAINDER,
                    help="the oracle target + its own flags, forwarded unchanged")
    args = ap.parse_args(argv)

    canonical = resolve_mode(args.mode)
    if canonical is None:
        ap.error(f"unknown mode {args.mode!r}. Known: "
                 + ", ".join(sorted(MODE_ORACLE))
                 + "; aliases: " + ", ".join(sorted(ALIASES)))

    if not args.rest:
        ap.error("no target given. Usage: run_oracle.py --mode <mode> <target> [oracle args…]")

    script = MODE_ORACLE[canonical]
    script_path = os.path.join(HERE, script)
    if not os.path.exists(script_path):
        # Honest failure for a mode whose oracle has not shipped yet (e.g. explainer).
        sys.stderr.write(
            f"run_oracle: mode {canonical!r} maps to {script} but {script_path} does not "
            f"exist yet. Ship the oracle before gating this track.\n")
        return 3

    # exec so the oracle's exit code / stdout / stderr are OUR exit code / stdout / stderr.
    # Nothing in between reads or rewrites them — the point of a transit adapter.
    os.execv(sys.executable, [sys.executable, script_path, *args.rest])
    return 0  # unreachable if execv succeeds


if __name__ == "__main__":
    sys.exit(main())

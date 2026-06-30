---
description: Generate a system handoff for the next architect iterating the aiblog multi-agent system.
---

Write a complete, self-contained handoff to `handoff/handoff-<YYYY-MM-DD>.md` (suffix
`-2`, `-3` if same-day; NEVER overwrite an existing one). This is a SYSTEM handoff — about
the multi-agent architecture itself, not any single article — so the next architect can
keep iterating with zero context loss. (Specialized from the global /handoff: ours is
repo-committed, not written to OS temp.)

Include, in this order:
1. **State of the system** — what the pipeline is (stages, agents, gates, the two oracles:
   `citation_audit.py` + `grounding_gate.py`), and what is solid vs partial.
2. **What changed this iteration** — every architectural change since the last handoff
   (new agent, new gate, new behavior note, a bug fixed in a tool), each with the WHY.
3. **Lessons written back** — which `behavior_notes/` files or `style_patterns.md §7`
   lines were added this session, and the divergence that triggered each (the
   self-improvement loop's audit trail).
4. **Open threads / next improvements** — ranked. What the next architect should pick up
   (e.g. an image sub-agent; a real grounding-checker sub-agent dispatch; full-rigor run).
5. **How to verify it still works** — the exact commands to smoke-test both oracles
   (good→PASS, planted-bug→FAIL) and to run a real article end to end.
6. **Known risks / [ASSUMED] items** — anything unverified that could bite.

Read `CLAUDE.md`, the latest `handoff/handoff-*.md`, and the per-article `STATE.md` files
before writing, so the handoff is accurate and cumulative.

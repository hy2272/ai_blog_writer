---
description: Start a new AI-hot-topic article. Hands off to the orchestrator.
---

Enter the orchestrator playbook at `.claude/orchestrator.md` and run the staged
pipeline for a new article.

Topic (optional): $ARGUMENTS

Steps:
1. Read `.claude/orchestrator.md`, `CLAUDE.md`, `common/style_patterns.md`.
2. If no article workspace exists for this topic, run `/new-article <slug>` first.
3. Begin at S0: confirm the hot topic + angle with the human, decompose into 3-5
   section nodes, write them into STATE.md.
4. Proceed stage by stage, STOPPING at the S1 human gate (angle) and the S4 citation
   gate (facts). Never skip a gate.

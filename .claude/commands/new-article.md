---
description: Scaffold a per-article workspace (articles/article_<slug>/).
---

Scaffold a new article workspace.

Slug: $ARGUMENTS  (kebab-case, e.g. `claude-opus-48-launch`)

Steps:
1. Run `python3 tools/new_article.py <slug>`. It copies `articles/_TEMPLATE/`, substitutes
   the `<slug>` placeholder, and validates the layout (STATE.md, DECISIONS.md,
   source_pack.json, outline.json, contracts/, sections/, stage_results/) — failing if the
   scaffold is incomplete. Do not hand-copy directories.
2. Fill the STATE.md header (date, topic) once the scaffold exists.
3. Report the path and tell the user to run `/write-article` to begin.

Do NOT start research or writing here — this command only scaffolds.

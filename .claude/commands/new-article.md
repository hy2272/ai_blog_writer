---
description: Scaffold a per-article workspace (articles/article_<slug>/).
---

Scaffold a new article workspace by copying the template.

Slug: $ARGUMENTS  (kebab-case, e.g. `claude-opus-48-launch`)

Steps:
1. Copy `articles/_TEMPLATE/` to `articles/article_<slug>/`.
2. Fill the STATE.md header (slug, date, topic placeholder).
3. Confirm the layout exists (contracts/, sections/, source_pack.json, DECISIONS.md).
4. Report the path and tell the user to run `/write-article` to begin.

Do NOT start research or writing here — this command only scaffolds.

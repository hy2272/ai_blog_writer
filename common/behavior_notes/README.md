# behavior_notes — conditional knowledge the writing agents glob

These are the "hot" conditional-knowledge channel (the analog of sas2pyspark's
`behavior_notes/`). Always-needed rules live in `common/style_patterns.md`; situational
techniques live here, one file per topic, and the writer/humanizer glob the relevant
ones by filename.

To add knowledge WITHOUT editing any agent spec: copy `_TEMPLATE.md` to a descriptive
filename and write the note. The writer reads `style_patterns.md` always, and globs
this folder for notes whose names match the situation it is in.

This is half of the self-improvement loop: every shipped article that revealed a
recurring pattern should leave a note here (or a line in `style_patterns.md`).

Seed notes:
- `ai-flavor-removal.md` — concrete before/after for the "去 AI 味" pass.
- `freshness-and-sourcing.md` — how to source a fast-moving AI story without staleness.

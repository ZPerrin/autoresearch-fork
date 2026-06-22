---
name: refine-linter
description: Reconcile the doc linter (doc-lint.py) against docs/README.md — keep its kinds/statuses, path globs, module-README list, canonical headers, and link rules matching what docs/README.md declares. Use when the doc structure or conventions change. Twin of refine-context.
---

Keep [doc-lint.py](../refine-docs/doc-lint.py) honest against [docs/README.md](../../../docs/README.md) — the negotiated source of truth for what docs mean here. The linter is a literal encoding of that file; this skill reconciles it when the conventions or structure drift. Same iterate-with-the-operator loop as `/refine-context`. Follow [docs/README.md](../../../docs/README.md). Stage; never commit.

## What derives from docs/README.md

- `KINDS` / `STATUSES` ← the frontmatter enum block in "Nomenclature".
- `frontmatter_docs()` globs ← the `docs/` "Module Map" (the documentation index).
- `stamped_readmes()` list ← the module set (root + module READMEs).
- the `## Overview` stamp + canonical header names ← "Canonical headers".
- `CODELINK` / `MISSING` link rules ← the "Links vs. code-spans" rule.

## Workflow

1. Read `docs/README.md` (Module Map, Canonical headers, Nomenclature, Links rule) and the current `doc-lint.py` constants/checks.
2. Diff intent vs. encoding: list every place the linter and `docs/README.md` disagree (a kind absent from the enum, a module README not in `stamped_readmes()`, a renamed dir, a changed header).
3. Reconcile with the operator confirming each change: rewrite the linter's Python constants/checks to match the doc. Keep it plain Python — do NOT make it parse prose `docs/README.md` at runtime.
4. Run the linter clean to prove it: `python3 .claude/skills/refine-docs/doc-lint.py`.

## Boundaries

Owns only the linter. Does not change `docs/README.md` (that is `/refine-docs`); if the *convention itself* should change, that is a doc edit first, then this skill follows. The module-README list in `stamped_readmes()` is generated-to-match, not assumed — update it when modules are added or removed.

## Output

Report the disagreements found, the linter edits made, the clean lint run, and — if linter and doc already agreed — say so and change nothing.
